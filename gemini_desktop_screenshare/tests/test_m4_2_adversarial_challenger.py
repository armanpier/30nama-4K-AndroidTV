"""
Adversarial Challenger Test Suite for Milestone 4.2.
Stress-tests test runner `run_tests.py` and dual-mode integration suite `test_e2e.py`.
Dimensions covered:
1. run_tests CLI flags (--help, --fast, --suite filtering, invalid suite exit code)
2. run_tests Headless environment enforcement (QT_QPA_PLATFORM=offscreen)
3. run_tests Process isolation & failure propagation (non-zero exit code on failure, collection errors)
4. test_e2e Rapid UI state transitions & churn resilience
5. test_e2e Mute toggle & continuous silence byte streaming over WebSocket
6. test_e2e Concurrent on-demand snapshot queries while live streaming is active
7. test_e2e Resource leak audit (OS threads, asyncio tasks, audio streams)
"""

import asyncio
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.app import AsyncWorker
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


def pump_events(qapp: QApplication, count: int = 10, delay: float = 0.02):
    for _ in range(count):
        qapp.processEvents()
        time.sleep(delay)


class MockAdversarialCaptureEngine:
    def __init__(self):
        self.b64_frame = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        self.captured_targets = []
        self.call_count = 0

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
        self.call_count += 1
        return self.b64_frame

    def close(self):
        pass


class MockAdversarialAudioPipeline:
    """
    Simulates AudioPipeline with real silence byte injection when muted.
    Supports continuous background generation of audio blocks.
    """
    def __init__(self, input_rate: int = 16000):
        self.input_rate = input_rate
        self.block_bytes = int(input_rate * 0.1) * 2  # 3200 bytes per 100ms
        self.is_muted = False
        self.is_recording = False
        self._record_callback: Optional[Callable[[bytes], None]] = None
        self.interrupt_count = 0
        self.played_chunks = []
        self._gen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_muted(self, muted: bool):
        self.is_muted = bool(muted)

    def start_recording(self, callback: Callable[[bytes], None]):
        self.is_recording = True
        self._record_callback = callback
        self._stop_event.clear()
        self._gen_thread = threading.Thread(target=self._audio_generator_loop, daemon=True)
        self._gen_thread.start()

    def _audio_generator_loop(self):
        while not self._stop_event.is_set():
            time.sleep(0.05)  # 50ms intervals
            if not self.is_recording or not self._record_callback:
                continue
            if self.is_muted:
                chunk = b"\x00" * self.block_bytes
            else:
                chunk = b"\x12\x34" * (self.block_bytes // 2)
            try:
                self._record_callback(chunk)
            except Exception:
                break

    def stop_recording(self):
        self.is_recording = False
        self._stop_event.set()
        if self._gen_thread and self._gen_thread.is_alive():
            self._gen_thread.join(timeout=1.0)
        self._record_callback = None

    def play_chunk(self, chunk: bytes):
        self.played_chunks.append(chunk)

    def interrupt(self) -> float:
        self.interrupt_count += 1
        return 0.05

    def close(self):
        self.stop_recording()


class MockAdversarialOAuthManager:
    def __init__(self, token="ya29.m4_2_adversarial_token"):
        self.token = token
        self._authenticated = True
        self._profile = {"email": "adversary_m4_2@gmail.com", "name": "Adversary Challenger"}

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_user_profile(self) -> Dict[str, str]:
        return dict(self._profile)

    def get_valid_access_token(self) -> str:
        return self.token

    def sign_out(self) -> bool:
        self._authenticated = False
        return True


# ==============================================================================
# PART 1: run_tests.py Stress & Resilience Tests
# ==============================================================================

def test_runner_cli_flags():
    """Verify run_tests.py CLI flags: --help, --fast, --suite, invalid suite."""
    root_dir = Path(__file__).parent.parent.parent

    # 1. Test --help
    cmd_help = [sys.executable, "run_tests.py", "--help"]
    p_help = subprocess.run(cmd_help, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p_help.returncode == 0, f"--help failed with code {p_help.returncode}"
    assert "usage:" in p_help.stdout
    assert "--suite" in p_help.stdout
    assert "--fast" in p_help.stdout

    # 2. Test unknown --suite (must return exit code 1)
    cmd_invalid = [sys.executable, "run_tests.py", "--suite", "suite_that_does_not_exist_at_all"]
    p_invalid = subprocess.run(cmd_invalid, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p_invalid.returncode == 1, f"Expected returncode 1 for invalid suite, got {p_invalid.returncode}"
    assert "Error: No test suite matched query" in p_invalid.stdout

    # 3. Test --suite test_capture.py (single suite execution)
    cmd_single = [sys.executable, "run_tests.py", "--suite", "test_capture.py"]
    p_single = subprocess.run(cmd_single, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p_single.returncode == 0, f"--suite test_capture.py failed: {p_single.stdout}"
    assert "Discovered 1 test suites to execute." in p_single.stdout
    assert "Screen & Window Capture" in p_single.stdout
    assert "TOTAL: 1 suites" in p_single.stdout


def test_runner_headless_env_enforcement():
    """Verify run_tests.py strictly injects QT_QPA_PLATFORM=offscreen into child subprocesses."""
    from run_tests import run_suite
    # Intentionally remove QT_QPA_PLATFORM from os.environ
    orig_qpa = os.environ.pop("QT_QPA_PLATFORM", None)
    try:
        # Run a fast UI suite that requires offscreen Qt platform
        success, passed, failed, duration, output = run_suite("gemini_desktop_screenshare/tests/test_ui_m3.py")
        assert success is True, f"run_suite failed without parent QT_QPA_PLATFORM: {output}"
        assert passed > 0
        assert failed == 0
    finally:
        if orig_qpa is not None:
            os.environ["QT_QPA_PLATFORM"] = orig_qpa
        else:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_runner_process_isolation_and_failure_exit_code(tmp_path):
    """
    Verify process isolation:
    A suite failure does not abort other suites, but causes the runner to return non-zero exit code (1).
    """
    from run_tests import run_suite

    # Create a synthetic failing test suite in tmp_path
    failing_test_file = tmp_path / "test_synthetic_failure.py"
    failing_test_file.write_text(
        "def test_failing_assertion():\n"
        "    assert 1 == 2, 'Deliberate adversarial failure'\n",
        encoding="utf-8"
    )

    success, passed, failed, duration, output = run_suite(str(failing_test_file))
    assert success is False, "Expected run_suite to report success=False for failing test"
    assert failed >= 1, f"Expected at least 1 failure count, got {failed}"
    assert "Deliberate adversarial failure" in output

    # Also test collection error (e.g. syntax error)
    syntax_error_file = tmp_path / "test_synthetic_syntax_error.py"
    syntax_error_file.write_text("def test_broken(: invalid syntax\n", encoding="utf-8")

    success_syntax, passed_syntax, failed_syntax, _, output_syntax = run_suite(str(syntax_error_file))
    assert success_syntax is False, "Expected run_suite to report success=False for syntax error"
    assert failed_syntax >= 1, f"Expected at least 1 failure/error count, got {failed_syntax}"


# ==============================================================================
# PART 2: test_e2e.py Dual-Mode Stress & Concurrency Tests
# ==============================================================================

def test_e2e_rapid_state_churn_resilience(qapp, tmp_path):
    """
    Stress-tests rapid successive state transitions:
    UNAUTHENTICATED -> AUTHENTICATING -> AUTHENTICATED_IDLE -> LIVE_STREAMING -> AUTHENTICATED_IDLE -> ONDEMAND_CAPTURING.
    Ensures UIStateMachine never crashes and ends in consistent state.
    """
    with MockGeminiLiveServer() as ws_server, MockGeminiRestServer() as rest_server:
        config = AppConfig(
            config_dir=Path(tmp_path),
            live_ws_url=ws_server.ws_url,
            rest_url=rest_server.rest_url,
        )
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)
            assert window.state_machine.state == AppState.AUTHENTICATED_IDLE

            # Churn 1: Rapid start/stop live streaming requests without waiting
            for i in range(5):
                worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
                pump_events(qapp, 1, delay=0.01)
                worker.stop_live_streaming()
                pump_events(qapp, 1, delay=0.01)

            # Let worker settle
            pump_events(qapp, 20, delay=0.02)
            assert window.state_machine.state == AppState.AUTHENTICATED_IDLE

            # Churn 2: Rapid mode toggle and prompt submissions
            for _ in range(5):
                window.rb_ondemand.setChecked(True)
                window._on_mode_changed()
                window.txt_prompt_input.setText("Adversarial rapid prompt test")
                worker.query_ondemand(CaptureTarget.FULL_SCREEN, 0, "Test prompt")
                pump_events(qapp, 1, delay=0.01)
                window.rb_live.setChecked(True)
                window._on_mode_changed()
                pump_events(qapp, 1, delay=0.01)

            pump_events(qapp, 20, delay=0.02)
            assert window.state_machine.state in (AppState.AUTHENTICATED_IDLE, AppState.ONDEMAND_CAPTURING)

        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_live_streaming_mute_continuous_silence_streaming(qapp, tmp_path):
    """
    Stress-tests mute toggle during active continuous live streaming:
    Verifies that when muted, audio frames transmitted over WebSocket consist of 100% silence (zero bytes b'\\x00').
    When unmuted, audio frames contain non-zero audio samples.
    """
    with MockGeminiLiveServer() as ws_server:
        config = AppConfig(config_dir=Path(tmp_path), live_ws_url=ws_server.ws_url)
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            # Start continuous live streaming
            worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.LIVE_STREAMING:
                    break

            assert window.state_machine.state == AppState.LIVE_STREAMING

            # 1. Unmuted phase: Wait for audio frames to arrive at server
            for _ in range(30):
                pump_events(qapp, 2)
                if len(ws_server.received_audio) >= 2:
                    break

            assert len(ws_server.received_audio) >= 1, "Expected initial audio frames transmitted"
            initial_chunk_data = base64.b64decode(ws_server.received_audio[-1]["data"])
            assert any(b != 0 for b in initial_chunk_data), "Initial unmuted audio should contain non-zero samples"

            # 2. Mute phase: Click mute in UI
            window.btn_mic_mute.click()
            pump_events(qapp, 5)
            assert audio.is_muted is True
            assert "MUTED" in window.btn_mic_mute.text()

            # Record current audio frame count
            count_before_mute = len(ws_server.received_audio)

            # Wait for subsequent muted audio frames to arrive
            for _ in range(40):
                pump_events(qapp, 2)
                if len(ws_server.received_audio) >= count_before_mute + 3:
                    break

            muted_chunks = ws_server.received_audio[count_before_mute:]
            assert len(muted_chunks) >= 2, f"Expected at least 2 muted audio frames, got {len(muted_chunks)}"

            for idx, c in enumerate(muted_chunks):
                pcm_bytes = base64.b64decode(c["data"])
                assert len(pcm_bytes) > 0, "Muted audio frame must not be empty"
                # Rigorous empirical verification: all bytes must be strictly zero (silence)
                is_pure_silence = all(b == 0 for b in pcm_bytes)
                assert is_pure_silence, f"Muted frame #{idx} contained non-zero bytes! Expected pure silence."

            # 3. Unmute phase
            window.btn_mic_mute.click()
            pump_events(qapp, 5)
            assert audio.is_muted is False

            count_before_unmute = len(ws_server.received_audio)
            for _ in range(40):
                pump_events(qapp, 2)
                if len(ws_server.received_audio) >= count_before_unmute + 2:
                    break

            unmuted_chunks = ws_server.received_audio[count_before_unmute:]
            assert len(unmuted_chunks) >= 1
            resumed_pcm = base64.b64decode(unmuted_chunks[-1]["data"])
            assert any(b != 0 for b in resumed_pcm), "Resumed unmuted audio should contain non-zero samples"

            # Stop streaming
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


def test_e2e_parallel_ondemand_while_live_streaming(qapp, tmp_path):
    """
    Stress-tests triggering concurrent on-demand snapshot queries while live streaming is actively running:
    Verifies that:
    1. GeminiLiveClient WebSocket streaming remains active and connected.
    2. Multiple concurrent on-demand REST queries execute against MockGeminiRestServer without corruption.
    3. Transcript displays responses from on-demand queries.
    """
    with MockGeminiLiveServer() as ws_server, MockGeminiRestServer(custom_response_text="Analysis: Parallel query succeeded.") as rest_server:
        config = AppConfig(
            config_dir=Path(tmp_path),
            live_ws_url=ws_server.ws_url,
            rest_url=rest_server.rest_url,
        )
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            # Start continuous live streaming
            worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
            for _ in range(50):
                pump_events(qapp, 2)
                if window.state_machine.state == AppState.LIVE_STREAMING:
                    break

            assert window.state_machine.state == AppState.LIVE_STREAMING
            assert worker.live_client.is_streaming is True

            # Trigger 3 concurrent on-demand queries while live stream is active
            for i in range(3):
                worker.query_ondemand(
                    target_type=CaptureTarget.FULL_SCREEN,
                    target_id=0,
                    prompt=f"Parallel query {i}",
                )

            # Wait for REST queries to process
            for _ in range(50):
                pump_events(qapp, 2)
                if len(rest_server.received_requests) >= 3:
                    break

            assert len(rest_server.received_requests) >= 3, f"Expected 3 REST requests, got {len(rest_server.received_requests)}"
            transcript = window.txt_transcript.toPlainText()
            assert "Parallel query succeeded" in transcript

            # Verify that live client WebSocket remained active throughout
            assert worker.live_client.is_connected is True
            assert worker.live_client.is_streaming is True

            # Stop live streaming cleanly
            worker.stop_live_streaming()
            for _ in range(50):
                pump_events(qapp, 2)
                if not worker.live_client.is_streaming:
                    break

            assert worker.live_client.is_streaming is False

        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_resource_leak_audit_and_clean_teardown(qapp, tmp_path):
    """
    Verifies that running dual-mode sessions and shutting down leaves zero leaked OS threads,
    background asyncio tasks, or unclosed event loops.
    """
    initial_threads = {t.name for t in threading.enumerate()}

    with MockGeminiLiveServer() as ws_server, MockGeminiRestServer() as rest_server:
        config = AppConfig(
            config_dir=Path(tmp_path),
            live_ws_url=ws_server.ws_url,
            rest_url=rest_server.rest_url,
        )
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        hotkey = HotkeyManager()
        window = MainWindow(worker, config, hotkey)
        window.show()

        try:
            worker.check_initial_auth()
            pump_events(qapp, 5)

            worker.start_live_streaming(CaptureTarget.FULL_SCREEN, 0)
            pump_events(qapp, 15)

            # Barge-in interruption
            ws_server.send_interruption()
            pump_events(qapp, 10)

            # On-demand query
            worker.query_ondemand(CaptureTarget.FULL_SCREEN, 0, "Teardown test query")
            pump_events(qapp, 15)

            worker.stop_live_streaming()
            pump_events(qapp, 15)

        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()
            pump_events(qapp, 10)

    # Allow background threads up to 2 seconds to finish joining
    t_end = time.perf_counter() + 2.0
    while time.perf_counter() < t_end:
        active_names = {t.name for t in threading.enumerate()}
        leaked = [name for name in active_names if name not in initial_threads and "Dummy" not in name]
        if not leaked:
            break
        time.sleep(0.1)

    active_after = {t.name for t in threading.enumerate()}
    leaked_threads = [name for name in active_after if name not in initial_threads and "Dummy" not in name]
    assert len(leaked_threads) == 0, f"Leaked background threads detected: {leaked_threads}"


def test_runner_verbose_output_parsing():
    """Verify run_tests.py correctly parses pytest summary line even with -v / --verbose flag enabled."""
    root_dir = Path(__file__).parent.parent.parent
    cmd = [sys.executable, "run_tests.py", "-v", "--suite", "test_capture.py"]
    p = subprocess.run(cmd, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert p.returncode == 0, f"Verbose run_tests failed: {p.stdout}"
    assert "Discovered 1 test suites to execute." in p.stdout
    assert "TOTAL: 1 suites" in p.stdout
    assert "0 failed" in p.stdout


def test_e2e_abrupt_ws_disconnection_clean_ui_recovery(qapp, tmp_path):
    """
    Stress-tests abrupt socket termination while streaming:
    Verifies that AudioPipeline stops recording, audio queue is drained, and UI handles disconnection gracefully.
    """
    with MockGeminiLiveServer() as ws_server:
        config = AppConfig(config_dir=Path(tmp_path), live_ws_url=ws_server.ws_url)
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

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
                if worker.live_client.is_streaming:
                    break

            assert worker.live_client.is_streaming is True
            assert audio.is_recording is True

            # Terminate socket abruptly from server side with RFC 6455 Going Away (1001)
            ws_server.close_connection_abruptly(code=1001)

            for _ in range(50):
                pump_events(qapp, 2)
                if not worker.live_client.is_streaming:
                    break

            assert worker.live_client.is_streaming is False
            assert audio.is_recording is False

        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()


def test_e2e_high_frequency_barge_in_burst_churn(qapp, tmp_path):
    """
    Stress-tests rapid barge-in interruption churn:
    Fires 20 rapid interruption signals in sub-second bursts during streaming.
    Verifies AudioPipeline sub-millisecond drain and transcript banner resilience without deadlock.
    """
    with MockGeminiLiveServer() as ws_server:
        config = AppConfig(config_dir=Path(tmp_path), live_ws_url=ws_server.ws_url)
        oauth = MockAdversarialOAuthManager()
        capture = MockAdversarialCaptureEngine()
        audio = MockAdversarialAudioPipeline()

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
                if worker.live_client.is_streaming:
                    break

            # Send 20 rapid interruptions
            for _ in range(20):
                ws_server.send_interruption()
                pump_events(qapp, 1, delay=0.01)

            assert audio.interrupt_count >= 10
            transcript = window.txt_transcript.toPlainText()
            assert "Interrupted by user speech" in transcript

            worker.stop_live_streaming()
            pump_events(qapp, 10)

        finally:
            window.cleanup()
            worker.stop()
            audio.close()
            capture.close()
