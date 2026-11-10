"""
Low-latency bidirectional audio pipeline for Gemini Live screensharing.
Handles 16,000 Hz 1-channel 16-bit PCM microphone capture (100ms blocks = 3200 bytes),
microphone muting with silence byte injection,
24,000 Hz 1-channel 16-bit PCM model speech playback via callback-driven RawOutputStream,
and sub-millisecond barge-in interruption buffer draining without stream stalls.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Optional
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioPipeline:
    """
    Bidirectional audio input/output pipeline.
    - Input: 16kHz 1-channel int16 PCM (3200 bytes per 100ms block).
    - Output: 24kHz 1-channel int16 PCM via callback-driven RawOutputStream.
    - Interruption: Immediate queue drain (<0.1ms) without blocking driver calls.
    """

    def __init__(
        self,
        input_rate: int = 16000,
        output_rate: int = 24000,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
    ) -> None:
        self.input_rate = input_rate
        self.output_rate = output_rate
        self.input_device = input_device
        self.output_device = output_device

        # 100ms blocks: 1600 samples * 2 bytes = 3200 bytes
        self.input_block_size = int(self.input_rate * 0.1)
        self.output_block_size = 1024

        self._is_muted = False
        self._is_recording = False
        self._is_playing = False

        self._input_stream: Optional[sd.RawInputStream] = None
        self._output_stream: Optional[sd.RawOutputStream] = None

        self._output_queue: queue.Queue[bytes] = queue.Queue()
        self._leftover_output_bytes: bytes = b""
        self._record_callback: Optional[Callable[[bytes], None]] = None
        self._lock = threading.Lock()

    @property
    def is_muted(self) -> bool:
        """Returns True if the microphone is muted."""
        return self._is_muted

    @property
    def is_recording(self) -> bool:
        """Returns True if recording is actively running."""
        return self._is_recording

    def set_muted(self, muted: bool) -> None:
        """
        Toggles microphone muting.
        When muted, 3200 bytes of silence (b'\\x00'*3200) are emitted per block.
        """
        self._is_muted = bool(muted)
        logger.info("AudioPipeline microphone mute state set to: %s", self._is_muted)

    def start_recording(self, callback: Callable[[bytes], None]) -> None:
        """
        Starts 16kHz 1-channel int16 PCM microphone capture.
        The callback receives 3200-byte blocks (100ms) of PCM data.
        """
        with self._lock:
            if self._is_recording and self._input_stream is not None:
                logger.warning("start_recording called but stream is already running.")
                return

            self._record_callback = callback

            def _in_callback(indata: bytes, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
                if status:
                    logger.debug("RawInputStream status: %s", status)

                bytes_needed = frames * 2  # 16-bit mono = 2 bytes per frame
                if self._is_muted:
                    # Directive: send silence bytes when muted
                    chunk = b"\x00" * bytes_needed
                else:
                    chunk = bytes(indata)

                if self._record_callback:
                    try:
                        self._record_callback(chunk)
                    except Exception as e:
                        logger.error("Error in audio record callback: %s", e)

            try:
                self._input_stream = sd.RawInputStream(
                    samplerate=self.input_rate,
                    blocksize=self.input_block_size,
                    channels=1,
                    dtype="int16",
                    device=self.input_device,
                    callback=_in_callback,
                )
            except Exception as e:
                if self.input_device is None:
                    logger.warning("Default input audio device failed (%s); searching available devices...", e)
                    for i, d in enumerate(sd.query_devices()):
                        if d.get("max_input_channels", 0) > 0:
                            try:
                                self._input_stream = sd.RawInputStream(
                                    samplerate=self.input_rate,
                                    blocksize=self.input_block_size,
                                    channels=1,
                                    dtype="int16",
                                    device=i,
                                    callback=_in_callback,
                                )
                                self.input_device = i
                                logger.info("Bound to working audio input device %d (%s).", i, d.get("name"))
                                break
                            except Exception:
                                pass
                if self._input_stream is None:
                    logger.error("Failed to start RawInputStream: %s", e)
                    raise

            try:
                self._input_stream.start()
                self._is_recording = True
                logger.info("AudioPipeline recording started (16kHz, 1-ch, blocksize=%s).", self.input_block_size)
            except Exception as e:
                logger.error("Failed to start RawInputStream: %s", e)
                raise

    def stop_recording(self) -> None:
        """Stops and closes the microphone input stream outside self._lock."""
        stream = None
        with self._lock:
            stream = self._input_stream
            self._input_stream = None
            self._is_recording = False
            self._record_callback = None

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logger.debug("Error stopping input stream: %s", e)
        logger.info("AudioPipeline recording stopped.")

    def _ensure_output_stream(self) -> None:
        """Initializes and starts the callback-driven RawOutputStream if not active."""
        if self._output_stream is not None:
            return

        def _out_callback(outdata: memoryview, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
            if status:
                logger.debug("RawOutputStream status: %s", status)

            bytes_needed = frames * 2
            collected = bytearray()

            try:
                with self._lock:
                    if self._leftover_output_bytes:
                        take = min(len(self._leftover_output_bytes), bytes_needed)
                        collected.extend(self._leftover_output_bytes[:take])
                        self._leftover_output_bytes = self._leftover_output_bytes[take:]

                    while len(collected) < bytes_needed:
                        try:
                            chunk = self._output_queue.get_nowait()
                        except queue.Empty:
                            break

                        rem = bytes_needed - len(collected)
                        if len(chunk) <= rem:
                            collected.extend(chunk)
                        else:
                            collected.extend(chunk[:rem])
                            self._leftover_output_bytes = chunk[rem:]
                            break
            except Exception as e:
                logger.error("Error in audio output callback: %s", e)

            # If queue is empty or ran out of data, pad outdata with silence
            if len(collected) < bytes_needed:
                collected.extend(b"\x00" * (bytes_needed - len(collected)))

            outdata[:] = bytes(collected)

        try:
            self._output_stream = sd.RawOutputStream(
                samplerate=self.output_rate,
                blocksize=self.output_block_size,
                channels=1,
                dtype="int16",
                device=self.output_device,
                callback=_out_callback,
            )
            self._output_stream.start()
            self._is_playing = True
            logger.info("AudioPipeline playback stream started (24kHz, 1-ch, blocksize=%s).", self.output_block_size)
            return
        except Exception as e:
            if self._output_stream is not None:
                try:
                    self._output_stream.close()
                except Exception:
                    pass
                self._output_stream = None

            if self.output_device is None:
                logger.warning("Default output audio device failed (%s); searching available devices...", e)
                for i, d in enumerate(sd.query_devices()):
                    if d.get("max_output_channels", 0) > 0:
                        test_stream = None
                        try:
                            test_stream = sd.RawOutputStream(
                                samplerate=self.output_rate,
                                blocksize=self.output_block_size,
                                channels=1,
                                dtype="int16",
                                device=i,
                                callback=_out_callback,
                            )
                            test_stream.start()
                            self._output_stream = test_stream
                            self._is_playing = True
                            self.output_device = i
                            logger.info("Bound to working audio output device %d (%s).", i, d.get("name"))
                            return
                        except Exception:
                            if test_stream is not None:
                                try:
                                    test_stream.close()
                                except Exception:
                                    pass

            logger.error("Failed to start RawOutputStream: %s", e)
            raise

    def play_chunk(self, pcm_bytes: bytes) -> None:
        """
        Enqueues 24,000 Hz 1-channel 16-bit PCM audio bytes for playback.
        Ensures the callback output stream is initialized and running.
        Handles device errors gracefully without raising into caller.
        """
        if not pcm_bytes:
            return

        with self._lock:
            self._output_queue.put(pcm_bytes)
            try:
                self._ensure_output_stream()
            except Exception as e:
                logger.error("Audio playback error in play_chunk: %s", e)

    def interrupt(self) -> float:
        """
        Instantaneous barge-in interruption.
        Immediately flushes the internal output audio queue and leftover buffer.
        DOES NOT call stream.stop(), preventing PortAudio/WASAPI driver thread stalls.
        Returns the duration of the purge in milliseconds.
        """
        t0 = time.perf_counter()
        purged_count = 0
        with self._lock:
            self._leftover_output_bytes = b""
            while not self._output_queue.empty():
                try:
                    self._output_queue.get_nowait()
                    purged_count += 1
                except queue.Empty:
                    break

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.debug("AudioPipeline barge-in interrupt: purged %s chunks in %.4f ms", purged_count, elapsed_ms)
        return elapsed_ms

    def close(self) -> None:
        """Closes all audio streams and frees PortAudio resources outside self._lock."""
        self.stop_recording()
        self.interrupt()

        stream = None
        with self._lock:
            stream = self._output_stream
            self._output_stream = None
            self._is_playing = False

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logger.debug("Error closing output stream: %s", e)
        logger.info("AudioPipeline fully closed.")

    def __enter__(self) -> "AudioPipeline":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
