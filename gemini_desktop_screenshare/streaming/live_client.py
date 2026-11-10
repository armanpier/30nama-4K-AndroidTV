"""
Gemini Multimodal Live WebSocket client for Windows desktop screensharing.
Handles bidirectional full-duplex streaming of 1.0 FPS downscaled JPEG desktop frames,
16kHz PCM microphone audio, 24kHz model speech playback, text transcript streaming,
and instantaneous barge-in interruption handling.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
import websockets

from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline
from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.config import (
    DEFAULT_LIVE_WS_URL,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_INSTRUCTION,
    DEFAULT_VOICE,
    JPEG_QUALITY,
    MAX_IMAGE_DIM,
    VALID_VOICES,
    VIDEO_FPS,
)

logger = logging.getLogger(__name__)


class GeminiLiveClient:
    """
    Stateful WebSocket client for Gemini Multimodal Live API.
    Uses Bearer token authentication via additional_headers (websockets 14+),
    manages the setup negotiation handshake, and coordinates concurrent
    video and audio streaming loops.
    """

    def __init__(
        self,
        oauth_manager: OAuthManager,
        capture_engine: ScreenCaptureEngine,
        audio_pipeline: AudioPipeline,
        host: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.oauth_manager = oauth_manager
        self.capture_engine = capture_engine
        self.audio_pipeline = audio_pipeline
        self.host = host or DEFAULT_LIVE_WS_URL
        self.model = model or DEFAULT_MODEL

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected: bool = False
        self._is_streaming: bool = False

        self._video_task: Optional[asyncio.Task] = None
        self._audio_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        self._audio_queue: Optional[asyncio.Queue[bytes]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_connected(self) -> bool:
        """Returns True if the WebSocket connection and setup are active."""
        return self._is_connected and self.ws is not None

    @property
    def is_streaming(self) -> bool:
        """Returns True if continuous video and audio streaming loops are running."""
        return self._is_streaming

    def set_model(self, model: str) -> None:
        """Updates the active model identifier for live streaming."""
        self.model = model

    async def connect(
        self,
        voice_name: str = DEFAULT_VOICE,
        system_instruction: str = "",
    ) -> Dict[str, Any]:
        """
        Connects to the Gemini Multimodal Live WebSocket endpoint with Bearer authentication
        and completes the initial setup handshake.
        """
        if voice_name not in VALID_VOICES:
            logger.warning("Voice '%s' not recognized; falling back to '%s'.", voice_name, DEFAULT_VOICE)
            voice_name = DEFAULT_VOICE

        instruction = system_instruction or (
            "You are Gemini Live with real-time desktop vision observing the user's active computer screen and listening to their voice. "
            "You continuously receive real-time video frames (JPEG) of their desktop or active application window. You can see everything on their screen. "
            "When asked if you can see their screen or what is on screen, confirm that you see their screen and describe the visible applications, windows, code, or content. "
            "Keep your spoken answers concise, conversational, and direct."
        )

        # Retrieve valid access token from OAuthManager or append API key
        token = ""
        ws_url = self.host
        headers = {}
        api_key = getattr(getattr(self.oauth_manager, "config", None), "api_key", "")
        if api_key:
            sep = "&" if "?" in ws_url else "?"
            ws_url = f"{ws_url}{sep}key={api_key}"
        else:
            try:
                token = self.oauth_manager.get_valid_access_token()
            except Exception as e:
                logger.warning("Could not obtain access token from OAuthManager: %s", e)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        proxy_url = getattr(getattr(self.oauth_manager, "config", None), "proxy", None) or None
        logger.info("Connecting to Gemini Live WebSocket: %s (proxy=%s)", ws_url, proxy_url)
        self.ws = await websockets.connect(ws_url, additional_headers=headers, proxy=proxy_url)

        # Transmit Schema 1: Initial Setup Frame
        live_model = self.model
        if not live_model or ("live" not in live_model.lower()):
            live_model = DEFAULT_MODEL

        setup_payload = {
            "setup": {
                "model": live_model,
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice_name
                            }
                        }
                    },
                    "temperature": 0.7,
                },
                "systemInstruction": {
                    "parts": [{"text": instruction}]
                },
            }
        }
        await self.ws.send(json.dumps(setup_payload))
        logger.info("Sent setup handshake payload for model '%s' with voice '%s'.", self.model, voice_name)

        # Await Schema 2: Server Setup Confirmation
        raw_resp = await self.ws.recv()
        resp_data = json.loads(raw_resp)

        if "error" in resp_data:
            err_msg = resp_data["error"]
            logger.error("Gemini Live setup failed: %s", err_msg)
            await self.ws.close()
            self.ws = None
            raise RuntimeError(f"Gemini Live setup rejected: {err_msg}")

        if "setupComplete" not in resp_data:
            logger.warning("Unexpected response to setup frame: %s", resp_data)

        self._is_connected = True
        logger.info("Gemini Live setup negotiation complete. Ready for streaming.")
        return resp_data

    def _drain_audio_queue(self) -> None:
        """Drains any buffered microphone audio chunks to prevent unbounded memory growth."""
        if self._audio_queue is not None:
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except Exception:
                    break

    def _handle_disconnection(
        self,
        reason: str,
        on_error: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Cleans up streaming state and notifies callbacks when unexpected disconnection occurs.
        Guarantees microphone recording is stopped and queues drained to prevent zombie sessions.
        """
        was_streaming = self._is_streaming
        self._is_streaming = False
        self.audio_pipeline.stop_recording()
        self._drain_audio_queue()

        if was_streaming:
            logger.warning("Streaming session disconnected: %s", reason)
            if on_disconnect:
                try:
                    on_disconnect()
                except Exception as cb_err:
                    logger.error("Error in on_disconnect callback: %s", cb_err)
            if on_error:
                try:
                    on_error(reason)
                except Exception as cb_err:
                    logger.error("Error in on_error callback: %s", cb_err)

            current = asyncio.current_task()
            for t in [self._video_task, self._audio_task, self._receive_task]:
                if t and t != current and not t.done():
                    t.cancel()

    async def start_streaming(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        on_text: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Starts the real-time continuous streaming session:
        - 1.0 FPS downscaled JPEG desktop frames (Schema 3).
        - 16,000 Hz linear PCM audio chunks (Schema 3).
        - Dispatches inbound text to on_text callback.
        - Dispatches inbound 24kHz audio chunks to AudioPipeline.
        - Handles user barge-in interruptions via instantaneous buffer purging.
        """
        if not self.is_connected or self.ws is None:
            raise RuntimeError("Cannot start streaming: WebSocket is not connected.")

        if self._is_streaming:
            logger.warning("start_streaming called while streaming is already active.")
            return

        self._loop = asyncio.get_running_loop()
        self._audio_queue = asyncio.Queue()
        self._is_streaming = True

        # Audio recording callback pushes 16kHz PCM chunks into asyncio queue
        def _on_mic_audio(chunk: bytes) -> None:
            if self._is_streaming and self._audio_queue and self._loop:
                self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, chunk)

        # Start microphone recording
        self.audio_pipeline.start_recording(_on_mic_audio)

        # Sanitize target_id: full_screen must strictly default to monitor index 0
        actual_target_id = 0 if target_type == CaptureTarget.FULL_SCREEN else target_id

        # Spawn concurrent streaming tasks (_video_stream_loop transmits Frame 0 on its very first iteration)
        self._video_task = asyncio.create_task(
            self._video_stream_loop(target_type, actual_target_id, on_error, on_disconnect)
        )
        self._audio_task = asyncio.create_task(
            self._audio_stream_loop(on_error, on_disconnect)
        )
        self._receive_task = asyncio.create_task(
            self._receive_loop(on_text, on_error, on_disconnect)
        )
        logger.info("Continuous live streaming started (target_type=%s, target_id=%s).", target_type, actual_target_id)

    async def _video_stream_loop(
        self,
        target_type: str,
        target_id: Any,
        on_error: Optional[Callable[[str], None]],
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """Continuously captures and transmits screen frames at 1.0 FPS."""
        frame_interval = 1.0 / VIDEO_FPS
        mon_target_id = 0 if target_type == CaptureTarget.FULL_SCREEN else target_id

        while self._is_streaming and self.ws:
            t0 = time.perf_counter()
            try:
                # Execute frame capture and downscaling off the event loop
                b64_frame = await asyncio.to_thread(
                    self.capture_engine.capture_frame_base64,
                    target_type,
                    mon_target_id,
                    MAX_IMAGE_DIM,
                    JPEG_QUALITY,
                )

                payload = {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "image/jpeg",
                                "data": b64_frame,
                            }
                        ]
                    }
                }
                await self.ws.send(json.dumps(payload))
                logger.debug("Streamed 1.0 FPS video frame (~%d bytes base64)", len(b64_frame))

            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed during video stream.")
                self._handle_disconnection("WebSocket disconnected", on_error, on_disconnect)
                break
            except Exception as e:
                logger.warning("Transient frame capture error in video stream loop: %s", e)
                try:
                    await asyncio.sleep(frame_interval)
                except asyncio.CancelledError:
                    break
                continue

            elapsed = time.perf_counter() - t0
            sleep_time = max(0.0, frame_interval - elapsed)
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    async def _audio_stream_loop(
        self,
        on_error: Optional[Callable[[str], None]],
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """Streams 16kHz PCM microphone audio chunks to Gemini Live."""
        while self._is_streaming and self.ws and self._audio_queue:
            try:
                chunk = await self._audio_queue.get()
                b64_pcm = base64.b64encode(chunk).decode("ascii")

                payload = {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "audio/pcm;rate=16000",
                                "data": b64_pcm,
                            }
                        ]
                    }
                }
                await self.ws.send(json.dumps(payload))
            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed during audio stream.")
                self._handle_disconnection("WebSocket disconnected", on_error, on_disconnect)
                break
            except Exception as e:
                logger.error("Error in audio stream loop: %s", e)
                self._handle_disconnection(f"Audio stream error: {e}", on_error, on_disconnect)
                break

    async def _receive_loop(
        self,
        on_text: Optional[Callable[[str], None]],
        on_error: Optional[Callable[[str], None]],
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """Processes inbound server messages: text transcripts, 24kHz audio, and interruptions."""
        while self._is_streaming and self.ws:
            # 1. Transport receive
            try:
                raw_msg = await self.ws.recv()
            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.info("WebSocket connection closed in receive loop: %s", e)
                self._handle_disconnection("WebSocket disconnected", on_error, on_disconnect)
                break
            except Exception as e:
                logger.error("Transport error in receive loop: %s", e)
                self._handle_disconnection(f"Transport error: {e}", on_error, on_disconnect)
                break

            # 2. Guard against malformed JSON or unexpected non-dict frames
            try:
                if isinstance(raw_msg, bytes):
                    raw_msg = raw_msg.decode("utf-8")
                data = json.loads(raw_msg)
                if not isinstance(data, dict):
                    logger.warning("Received non-dict JSON frame from server, discarding: %s", type(data))
                    if on_error:
                        try:
                            on_error(f"Malformed frame: expected dict root, got {type(data).__name__}")
                        except Exception:
                            pass
                    continue
            except Exception as json_err:
                logger.error("Malformed JSON frame received from server; discarding frame: %s", json_err)
                if on_error:
                    try:
                        on_error(f"Receive loop error: {json_err}")
                    except Exception:
                        pass
                continue

            # 3. Defensive payload processing
            try:
                server_content = data.get("serverContent")
                if not server_content or not isinstance(server_content, dict):
                    continue

                # 3.1 Interruption handling (User barge-in)
                if server_content.get("interrupted"):
                    logger.info("Received barge-in interruption signal; purging speaker queue.")
                    self.audio_pipeline.interrupt()

                # 3.2 Model turn parts (text and 24kHz synthetic speech)
                model_turn = server_content.get("modelTurn")
                if isinstance(model_turn, dict):
                    parts = model_turn.get("parts", [])
                    if isinstance(parts, list):
                        for part in parts:
                            if not isinstance(part, dict):
                                continue

                            # Spoken text token delta
                            if "text" in part and on_text:
                                on_text(part["text"])

                            # Synthetic model speech
                            inline_data = part.get("inlineData")
                            if isinstance(inline_data, dict):
                                mime = inline_data.get("mimeType", "")
                                b64_data = inline_data.get("data")
                                if "audio/pcm" in mime and b64_data:
                                    try:
                                        pcm_bytes = base64.b64decode(b64_data)
                                        self.audio_pipeline.play_chunk(pcm_bytes)
                                    except Exception as pcm_err:
                                        logger.warning("Failed to decode audio PCM data: %s", pcm_err)
                                        if on_error:
                                            try:
                                                on_error(f"Corrupted audio payload: {pcm_err}")
                                            except Exception:
                                                pass

                # 3.3 Model turn completed
                if server_content.get("turnComplete"):
                    logger.debug("Model turn complete.")

            except Exception as proc_err:
                logger.error("Error processing serverContent payload; discarding frame: %s", proc_err)
                if on_error:
                    try:
                        on_error(f"Frame processing error: {proc_err}")
                    except Exception:
                        pass
                continue

    async def send_client_content(self, text: str, image_b64: Optional[str] = None) -> None:
        """
        Sends a discrete turn (Schema 6) over the active WebSocket connection.
        Used for on-demand questions or direct text queries during a live session.
        """
        if not self.is_connected or self.ws is None:
            raise RuntimeError("WebSocket is not connected.")

        parts: list = []
        if image_b64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": image_b64,
                }
            })
        parts.append({"text": text})

        payload = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": parts,
                    }
                ],
                "turnComplete": True,
            }
        }
        await self.ws.send(json.dumps(payload))
        logger.info("Dispatched discrete clientContent turn.")

    async def stop_streaming(self) -> None:
        """Stops continuous video and audio streaming loops and pauses microphone capture."""
        self._is_streaming = False
        self.audio_pipeline.stop_recording()
        self._drain_audio_queue()

        current = asyncio.current_task()
        for task in [self._video_task, self._audio_task, self._receive_task]:
            if task and task != current and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug("Error awaiting cancelled task: %s", e)

        self._video_task = None
        self._audio_task = None
        self._receive_task = None
        self._audio_queue = None
        logger.info("Continuous live streaming stopped.")

    async def disconnect(self) -> None:
        """Closes the streaming session and terminates the WebSocket connection."""
        await self.stop_streaming()

        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception as e:
                logger.debug("Error closing WebSocket: %s", e)
            finally:
                self.ws = None

        self._is_connected = False
        self._is_streaming = False
        logger.info("Disconnected from Gemini Live WebSocket.")
