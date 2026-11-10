"""
Unit & Integration tests for Gemini Multimodal Live Streaming Subsystem.
Tests full-duplex WebSocket connection, setup handshake negotiation, 1.0 FPS video streaming,
16kHz audio transmission, inbound text tokens, 24kHz audio synthesis, barge-in interruptions,
discrete client content turns, malformed frame resilience, and abrupt disconnection handling.
"""

import asyncio
import base64
import json
import time
import pytest

from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
from gemini_desktop_screenshare.streaming.live_client import GeminiLiveClient
from gemini_desktop_screenshare.tests.mock_servers import MockGeminiLiveServer


class MockAudioPipeline:
    def __init__(self):
        self.is_recording = False
        self._callback = None
        self.played_chunks = []
        self.interrupt_count = 0

    def start_recording(self, callback):
        self.is_recording = True
        self._callback = callback

    def stop_recording(self):
        self.is_recording = False

    def emit_chunk(self, chunk: bytes):
        if self._callback and self.is_recording:
            self._callback(chunk)

    def play_chunk(self, pcm_bytes: bytes):
        self.played_chunks.append(pcm_bytes)

    def interrupt(self):
        self.interrupt_count += 1

    def close(self):
        self.stop_recording()


class MockCaptureEngine:
    def __init__(self):
        # 1x1 JPEG base64
        self.b64_frame = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        self.capture_count = 0

    def capture_frame_base64(self, target_type="full_screen", target_id=0, max_dim=1024, quality=70):
        self.capture_count += 1
        return self.b64_frame

    def list_windows(self):
        return []

    def close(self):
        pass


class MockOAuthManager:
    def __init__(self, token="mock_access_token_123"):
        self.token = token

    def get_valid_access_token(self):
        return self.token


# ------------------------------------------------------------------------------
# 1. Setup Handshake & Connection Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_client_connect_and_setup_handshake():
    """Verifies that GeminiLiveClient connects, transmits setup frame, and completes setup."""
    with MockGeminiLiveServer(expected_bearer_token="mock_access_token_123") as server:
        oauth = MockOAuthManager("mock_access_token_123")
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        resp = await client.connect(voice_name="Aoede", system_instruction="Test system instruction.")
        assert client.is_connected
        assert "setupComplete" in resp
        assert server.received_setup is not None
        assert server.received_setup.get("generationConfig", {}).get("speechConfig", {}).get("voiceConfig", {}).get("prebuiltVoiceConfig", {}).get("voiceName") == "Aoede"

        await client.disconnect()
        assert not client.is_connected


@pytest.mark.asyncio
async def test_live_client_setup_error_handling():
    """Verifies that server setup rejection raises RuntimeError and resets connection."""
    with MockGeminiLiveServer(simulate_setup_error="Model quota exceeded") as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        with pytest.raises(RuntimeError, match="Gemini Live setup rejected"):
            await client.connect()

        assert not client.is_connected


# ------------------------------------------------------------------------------
# 2. Continuous Video & Audio Streaming Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_client_video_and_audio_streaming():
    """Verifies that live client transmits 1 FPS video frames and 16kHz PCM audio chunks."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        text_tokens = []
        errors = []

        await client.start_streaming(
            target_type=CaptureTarget.FULL_SCREEN,
            target_id=0,
            on_text=lambda t: text_tokens.append(t),
            on_error=lambda e: errors.append(e),
        )

        assert client.is_streaming
        assert audio.is_recording

        # Emit 3 simulated microphone chunks (16kHz PCM = 3200 bytes per chunk)
        for _ in range(3):
            audio.emit_chunk(b"\x00\x01" * 1600)
            await asyncio.sleep(0.05)

        # Wait for video loop to emit frames (at 1.0 FPS)
        await asyncio.sleep(1.2)

        await client.stop_streaming()
        await client.disconnect()

        assert len(server.received_frames) >= 1
        assert len(server.received_audio) >= 2
        assert not client.is_streaming
        assert not audio.is_recording


# ------------------------------------------------------------------------------
# 3. Inbound Server Content, Audio Synthesis & Interruption Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_client_inbound_text_token_dispatch():
    """Verifies that server text tokens are dispatched to on_text callback."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        received_text = []
        await client.start_streaming(on_text=lambda t: received_text.append(t))

        # Send model turn with text from mock server
        server.send_model_turn(text="Hello from mock Gemini!", turn_complete=True)
        await asyncio.sleep(0.1)

        assert "Hello from mock Gemini!" in received_text

        await client.stop_streaming()
        await client.disconnect()


@pytest.mark.asyncio
async def test_live_client_inbound_audio_dispatch():
    """Verifies that server 24kHz synthetic speech is decoded and routed to audio_pipeline.play_chunk."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        await client.start_streaming()

        fake_pcm = b"\x12\x34" * 1024
        server.send_model_turn(pcm_bytes=fake_pcm, turn_complete=True)
        await asyncio.sleep(0.1)

        assert len(audio.played_chunks) >= 1
        assert audio.played_chunks[0] == fake_pcm

        await client.stop_streaming()
        await client.disconnect()


@pytest.mark.asyncio
async def test_live_client_barge_in_interruption():
    """Verifies that server interrupted: true triggers audio_pipeline.interrupt()."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        await client.start_streaming()

        server.send_interruption()
        await asyncio.sleep(0.1)

        assert audio.interrupt_count == 1

        await client.stop_streaming()
        await client.disconnect()


# ------------------------------------------------------------------------------
# 4. Discrete Client Content Turns & Fault Resilience Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_client_discrete_client_content_turn():
    """Verifies sending a discrete user turn (Schema 6) over active WebSocket."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        await client.send_client_content(text="Explain this window", image_b64=cap.b64_frame)

        await asyncio.sleep(0.1)
        assert len(server.received_client_turns) == 1
        turn = server.received_client_turns[0]
        assert turn["turns"][0]["parts"][1]["text"] == "Explain this window"
        assert turn["turnComplete"] is True

        await client.disconnect()


@pytest.mark.asyncio
async def test_live_client_malformed_server_frame_resilience():
    """Verifies that malformed JSON or non-dict payloads from server do not crash client."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        errors = []
        await client.start_streaming(on_error=lambda e: errors.append(e))

        # Send invalid JSON
        server.send_raw_frame("INVALID_RAW_JSON_STRING_1234")
        # Send non-dict valid JSON
        server.send_raw_frame("[1, 2, 3]")
        await asyncio.sleep(0.1)

        # Client should remain connected and streaming despite garbage
        assert client.is_streaming
        assert len(errors) >= 1

        await client.stop_streaming()
        await client.disconnect()


@pytest.mark.asyncio
async def test_live_client_network_disconnect_handling():
    """Verifies that abrupt server termination cleanly invokes disconnect callbacks."""
    with MockGeminiLiveServer() as server:
        oauth = MockOAuthManager()
        cap = MockCaptureEngine()
        audio = MockAudioPipeline()
        client = GeminiLiveClient(oauth, cap, audio, host=server.ws_url)

        await client.connect()
        disconnect_called = []
        await client.start_streaming(on_disconnect=lambda: disconnect_called.append(True))

        server.close_connection_abruptly()
        await asyncio.sleep(0.4)

        assert len(disconnect_called) >= 1
        assert not client.is_streaming
        assert not audio.is_recording
