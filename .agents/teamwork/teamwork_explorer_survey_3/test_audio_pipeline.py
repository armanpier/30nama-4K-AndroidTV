import sys
import time
import queue
import threading
import sounddevice as sd
import numpy as np

def inspect_devices():
    print("=== Sounddevice Audio Devices ===")
    devices = sd.query_devices()
    print(devices)
    default_in, default_out = sd.default.device
    print(f"\nDefault Input Device: {default_in}")
    print(f"Default Output Device: {default_out}")

def test_audio_pipeline():
    print("\n=== Testing Audio Pipeline Capabilities ===")
    # 1. Test Input Stream configuration (Gemini Live expects 16kHz 16-bit mono PCM)
    in_sr = 16000
    in_channels = 1
    in_dtype = 'int16'
    
    # Check if default input device supports 16kHz
    try:
        sd.check_input_settings(device=None, channels=in_channels, dtype=in_dtype, samplerate=in_sr)
        print(f"Input stream: {in_sr}Hz, {in_channels}ch, {in_dtype} is SUPPORTED by default input device!")
    except Exception as e:
        print(f"Input stream check failed: {e}")

    # 2. Test Output Stream configuration (Gemini Live sends 24kHz 16-bit mono PCM)
    out_sr = 24000
    out_channels = 1
    out_dtype = 'int16'
    try:
        sd.check_output_settings(device=None, channels=out_channels, dtype=out_dtype, samplerate=out_sr)
        print(f"Output stream: {out_sr}Hz, {out_channels}ch, {out_dtype} is SUPPORTED by default output device!")
    except Exception as e:
        print(f"Output stream check failed: {e}")

class AudioPlayer:
    """Low-latency streaming PCM player with interruption support."""
    def __init__(self, samplerate=24000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.audio_queue = queue.Queue(maxsize=100)
        self.is_playing = threading.Event()
        self.interrupted = threading.Event()
        self.stream = None

    def _callback(self, outdata, frames, time_info, status):
        bytes_needed = frames * self.channels * 2 # 2 bytes per int16
        written = 0
        out_bytes = bytearray(bytes_needed)

        if self.interrupted.is_set():
            # Flush queue immediately on interrupt
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            self.interrupted.clear()
            outdata[:] = bytes(bytes_needed)
            return

        while written < bytes_needed:
            try:
                chunk = self.audio_queue.get_nowait()
                chunk_len = len(chunk)
                can_write = min(chunk_len, bytes_needed - written)
                out_bytes[written:written + can_write] = chunk[:can_write]
                written += can_write
                if can_write < chunk_len:
                    # Put remaining bytes back into queue
                    self.audio_queue.put(chunk[can_write:])
            except queue.Empty:
                # Underflow / silence
                break

        outdata[:] = bytes(out_bytes)

    def start(self):
        self.stream = sd.RawOutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='int16',
            blocksize=1024,
            callback=self._callback
        )
        self.stream.start()
        self.is_playing.set()

    def play_chunk(self, pcm_bytes: bytes):
        if not self.interrupted.is_set():
            try:
                self.audio_queue.put(pcm_bytes, timeout=0.05)
            except queue.Full:
                pass

    def interrupt(self):
        """Called when Gemini sends 'interrupted: true' flag."""
        self.interrupted.set()

    def stop(self):
        self.is_playing.clear()
        if self.stream:
            self.stream.stop()
            self.stream.close()

class AudioRecorder:
    """16kHz mono PCM recorder with mute toggle and Gemini chunk streaming."""
    def __init__(self, samplerate=16000, channels=1, chunk_duration_ms=100):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = int(samplerate * chunk_duration_ms / 1000) # e.g. 1600 samples for 100ms
        self.is_recording = False
        self.is_muted = False
        self.stream = None
        self.on_audio_chunk = None # Callback taking bytes

    def _callback(self, indata, frames, time_info, status):
        if not self.is_recording:
            return
        if self.is_muted:
            # Send silence or drop
            raw = bytes(len(indata))
        else:
            raw = bytes(indata)
        if self.on_audio_chunk:
            self.on_audio_chunk(raw)

    def start(self, callback):
        self.on_audio_chunk = callback
        self.is_recording = True
        self.stream = sd.RawInputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.blocksize,
            callback=self._callback
        )
        self.stream.start()

    def set_mute(self, muted: bool):
        self.is_muted = muted

    def stop(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()

if __name__ == '__main__':
    inspect_devices()
    test_audio_pipeline()
