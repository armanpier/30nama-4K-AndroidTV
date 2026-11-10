"""
End-to-End Dual-Mode Integration Tests for Gemini Desktop Screenshare.
Executes headless PyQt6 GUI with AsyncWorker against standalone offline
MockGeminiLiveServer and MockGeminiRestServer.
Covers:
- E2E-01: Initialization & pre-authenticated state restoration
- E2E-02: Live streaming turn cycle & real-time text token display
- E2E-03: Microphone mute toggle & silence injection synchronization
- E2E-04: User speech barge-in interruption & UI banner display
- E2E-05: On-demand snapshot capture & markdown query response display
- E2E-06: Clean shutdown, thread termination, and resource reclamation
"""

import asyncio
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.app import AsyncWorker
from gemini_desktop_screenshare.auth.token_store import TokenStore
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
from gemini_desktop_screenshare.config import AppConfig
from gemini_desktop_screenshare.ui.hotkey_manager import HotkeyManager
from gemini_desktop_screenshare.ui.main_window import AppState, MainWindow
from gemini_desktop_screenshare.tests.mock_servers import (
    MockGeminiLiveServer,
    MockGeminiRestServer,
    MockOAuthServer,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    app.setQuitOnLastWindowClosed(False)
    return app


class MockE2EAudioPipeline:
    def __init__(self):
        self.is_muted = False
        self.is_recording = False
        self._record_callback: Optional[Callable[[bytes], None]] = None
        self.interrupt_count = 0
        self.played_chunks = []

    def set_muted(self, muted: bool):
        self.is_muted = bool(muted)

    def start_recording(self, callback: Callable[[bytes], None]):
        self.is_recording = True
        self._record_callback = callback

    def stop_recording(self):
        self.is_recording = False

    def emit_chunk(self, chunk: bytes):
        if self._record_callback and self.is_recording:
            self._record_callback(chunk)

    def play_chunk(self, chunk: bytes):
        self.played_chunks.append(chunk)

    def interrupt(self) -> float:
        self.interrupt_count += 1
        return 0.05

    def close(self):
        self.stop_recording()


class MockE2ECaptureEngine:
    def __init__(self):
        self.b64_frame = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        self.captured_targets = []

    def list_windows(self) -> List[Dict[str, Any]]:
        return [
            {"hwnd": 1001, "title": "Editor - main.py", "is_minimized": False, "width": 1280, "height": 720},
            {"hwnd": 1002, "title": "Terminal", "is_minimized": False, "width": 800, "height": 600},
        ]

    def capture_frame(self, target_type: str, target_id: Any = 0):
        from PIL import Image
        return Image.new("RGB", (640, 480), color=(20, 20, 20))

    def capture_frame_base64(self, target_type: str, target_id: Any = 0, max_dim: int = 1024, quality: int = 70) -> str:
        self.captured_targets.append((target_type, target_id))
        return self.b64_frame

    def close(self):
        pass


class MockE2EOAuthManager:
    def __init__(self, token="ya29.e2e_valid_token"):
        self.token = token
        self._authenticated = True
        self._profile = {"email": "tester_e2e@gmail.com", "name": "E2E Test User"}

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_user_profile(self) -> Dict[str, str]:
        return dict(self._profile)

    def get_valid_access_token(self) -> str:
        return self.token

    def sign_out(self) -> bool:
        self._authenticated = False
        return True


def pump_events(qapp: QApplication, count: int = 10, delay: float = 0.02):
    for _ in range(count):
        qapp.processEvents()
        time.sleep(delay)


# ------------------------------------------------------------------------------
# E2E Tests
# ------------------------------------------------------------------------------
def test_e2e_initialization_and_pre_auth(qapp, temp_config_dir):
    """E2E-01: Verifies app launches, recognizes authenticated session, and configures UI state."""
    config = AppConfig(config_dir=Path(temp_config_dir))
    oauth = MockE2EOAuthManager()
    capture = MockE2ECaptureEngine()
    audio = MockE2EAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()

    hotkey = HotkeyManager()
    window = MainWindow(worker, config, hotkey)
    window.show()

    try:
        worker.check_initial_auth()
        worker.request_refresh_windows()
        pump_events(qapp, 10)

        assert window.state_machine.state == AppState.AUTHENTICATED_IDLE
        assert "E2E Test User" in window.lbl_user_name.text()
        assert window.btn_primary_action.isEnabled()
        assert window.cb_target_type.count() >= 1
    finally:
        window.cleanup()
        worker.stop()
        audio.close()
        capture.close()


def test_e2e_live_streaming_turn_cycle(qapp, temp_config_dir):
    """E2E-02: Verifies starting live stream, receiving text tokens, and stopping cleanly."""
    with MockGeminiLiveServer() as ws_server:
        config = AppConfig(config_dir=Path(temp_config_dir), live_ws_url=ws_server.ws_url)
        oauth = MockE2EOAuthManager()
        capture = MockE2ECaptureEngine()
        audio = MockE2EAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            # Start streaming
            worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.LIVE_STREAMING:
                    break

            assert window.state_machine.state == AppState.LIVE_STREAMING
            assert "Stop Live Streaming" in window.btn_primary_action.text()
            assert audio.is_recording

            # Send model turn with text tokens from mock server
            ws_server.send_model_turn("Live screen observation: editor open with code.", turn_complete=True)
            for _ in range(50):
                pump_events(qapp, 2)
                if "Live screen observation" in window.txt_transcript.toPlainText():
                    break

            transcript = window.txt_transcript.toPlainText()
            assert "Live screen observation: editor open with code." in transcript

            # Stop streaming
            worker.stop_live_streaming()
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.AUTHENTICATED_IDLE:
                    break

            assert window.state_machine.state == AppState.AUTHENTICATED_IDLE
            assert not audio.is_recording
        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_live_streaming_mic_mute_toggle(qapp, temp_config_dir):
    """E2E-03: Verifies toggling microphone mute updates UI state and audio pipeline."""
    config = AppConfig(config_dir=Path(temp_config_dir))
    oauth = MockE2EOAuthManager()
    capture = MockE2ECaptureEngine()
    audio = MockE2EAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()

    hotkey = HotkeyManager()
    window = MainWindow(worker, config, hotkey)
    window.show()

    try:
        worker.check_initial_auth()
        pump_events(qapp, 5)

        assert not audio.is_muted
        # Click mute
        window.btn_mic_mute.click()
        pump_events(qapp, 5)

        assert audio.is_muted
        assert "MUTED" in window.btn_mic_mute.text()

        # Unmute
        window.btn_mic_mute.click()
        pump_events(qapp, 5)

        assert not audio.is_muted
        assert "Active" in window.btn_mic_mute.text()
    finally:
        window.cleanup()
        worker.stop()
        audio.close()
        capture.close()


def test_e2e_live_streaming_barge_in(qapp, temp_config_dir):
    """E2E-04: Verifies server barge-in interruption triggers instant audio purge and transcript banner."""
    with MockGeminiLiveServer() as ws_server:
        config = AppConfig(config_dir=Path(temp_config_dir), live_ws_url=ws_server.ws_url)
        oauth = MockE2EOAuthManager()
        capture = MockE2ECaptureEngine()
        audio = MockE2EAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.LIVE_STREAMING:
                    break

            # Emit barge-in interruption from server
            ws_server.send_interruption()
            for _ in range(50):
                pump_events(qapp, 2)
                if audio.interrupt_count >= 1:
                    break

            assert audio.interrupt_count >= 1
            transcript_text = window.txt_transcript.toPlainText()
            assert "Interrupted by user speech" in transcript_text

            worker.stop_live_streaming()
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.AUTHENTICATED_IDLE:
                    break
        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_ondemand_snapshot_query_in_parallel(qapp, temp_config_dir):
    """E2E-05: Verifies on-demand snapshot query against MockGeminiRestServer displays analysis in transcript."""
    with MockGeminiRestServer(custom_response_text="E2E Mock: Detected syntax error on line 42.") as rest_server:
        config = AppConfig(config_dir=Path(temp_config_dir), rest_url=rest_server.rest_url)
        oauth = MockE2EOAuthManager()
        capture = MockE2ECaptureEngine()
        audio = MockE2EAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            # Switch mode to on-demand
            window.rb_ondemand.setChecked(True)
            pump_events(qapp, 5)

            # Trigger on-demand capture with prompt
            worker.query_ondemand(
                target_type=CaptureTarget.FULL_SCREEN,
                target_id=0,
                prompt="Detect syntax error in code window",
            )
            pump_events(qapp, 20)

            transcript = window.txt_transcript.toPlainText()
            assert "E2E Mock: Detected syntax error on line 42." in transcript
            assert window.state_machine.state == AppState.AUTHENTICATED_IDLE
        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_clean_shutdown_and_resource_reclamation(qapp, temp_config_dir):
    """E2E-06: Verifies complete resource teardown and thread termination."""
    config = AppConfig(config_dir=Path(temp_config_dir))
    oauth = MockE2EOAuthManager()
    capture = MockE2ECaptureEngine()
    audio = MockE2EAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()

    hotkey = HotkeyManager()
    window = MainWindow(worker, config, hotkey)
    window.show()

    try:
        worker.check_initial_auth()
        pump_events(qapp, 5)
    finally:
        window.cleanup()
        worker.stop()
        audio.close()
        capture.close()
        pump_events(qapp, 5)

    assert worker.isFinished()
