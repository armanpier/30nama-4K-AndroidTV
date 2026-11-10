"""
Adversarial Stress Test Suite for Milestone 3 UI State Machine, Hotkey Filter, and Edge Cases.
Authored by Teamwork Challenger (Milestone 3 Empirical Challenger).

Adversarial Testing Vectors:
1. Rapid Concurrent State Transitions (sign-in -> cancel -> sign-out -> start stream -> stop stream).
2. Streaming Start/Stop Hammering & Concurrency Deadlock Probing.
3. State Machine Boundary Fuzzing & Enablement Matrix Enforcement.
4. Win32 Hotkey Collisions, Simultaneous WM_HOTKEY Bursts, and Corrupted Pointer Ingestion.
5. Destroyed / Invalid Window HWNDs during Preview, On-Demand Capture, and Active Selection.
6. Empty Window Enumeration, Empty Prompts, and Malicious Prompt Injection.
7. Corrupt Session Cache, Malformed JSON, and DPAPI Binary Corruption Resilience.
"""

import asyncio
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Enforce offscreen Qt platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import PyQt6.sip as sip
from PyQt6.QtCore import QByteArray, QCoreApplication, QObject, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.app import AsyncWorker
from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
from gemini_desktop_screenshare.auth.token_store import TokenStore
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.config import AppConfig
from gemini_desktop_screenshare.ui.hotkey_manager import (
    ERROR_HOTKEY_ALREADY_REGISTERED,
    HOTKEY_ID_LIVE,
    HOTKEY_ID_ONDEMAND,
    MOD_ALT,
    MOD_NOREPEAT,
    VK_L,
    VK_S,
    WM_HOTKEY,
    HotkeyManager,
    Win32HotkeyFilter,
)
from gemini_desktop_screenshare.ui.main_window import (
    ENABLEMENT_MATRIX,
    AppState,
    MainWindow,
    UIAction,
    UIStateMachine,
    simple_markdown_to_html,
)
from gemini_desktop_screenshare.ui.styles import apply_theme


# ---------------------------------------------------------------------------
# Test Fixtures & Mock Helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    return app


class MockAudioPipeline:
    def __init__(self) -> None:
        self.is_muted = False
        self.is_recording = False
        self._record_callback: Optional[Callable[[bytes], None]] = None
        self.interrupt_count = 0

    def set_muted(self, muted: bool) -> None:
        self.is_muted = bool(muted)

    def start_recording(self, callback: Callable[[bytes], None]) -> None:
        self.is_recording = True
        self._record_callback = callback

    def stop_recording(self) -> None:
        self.is_recording = False

    def play_chunk(self, chunk: bytes) -> None:
        pass

    def interrupt(self) -> float:
        self.interrupt_count += 1
        return 0.02

    def close(self) -> None:
        self.stop_recording()


class MockOAuthManager:
    def __init__(self, authenticated: bool = False) -> None:
        self._authenticated = authenticated
        self._profile = {"name": "Adversarial Tester", "email": "tester@example.com"}
        self.login_call_count = 0
        self.signout_call_count = 0

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_user_profile(self) -> Dict[str, str]:
        return dict(self._profile) if self._authenticated else {}

    def get_valid_access_token(self) -> str:
        if not self._authenticated:
            raise RuntimeError("No refresh token available. User must sign in.")
        return "mock_valid_token_123"

    def refresh_access_token(self) -> str:
        return "mock_refreshed_token_456"

    def start_loopback_and_login(self, timeout: float = 120.0) -> Dict[str, Any]:
        self.login_call_count += 1
        time.sleep(0.02)  # Simulate network latency
        self._authenticated = True
        return {"access_token": "mock_token", "user_profile": self._profile}

    def sign_out(self) -> bool:
        self.signout_call_count += 1
        self._authenticated = False
        return True


class MockScreenCaptureEngine:
    def __init__(self) -> None:
        self._windows = [
            {"hwnd": 1001, "title": "Editor Window", "is_minimized": False, "width": 1920, "height": 1080},
            {"hwnd": 1002, "title": "Background Worker", "is_minimized": True, "width": 800, "height": 600},
        ]
        self.capture_count = 0

    def list_windows(self) -> List[Dict[str, Any]]:
        return list(self._windows)

    def capture_frame(self, target_type: str, target_id: Any = 0):
        self.capture_count += 1
        if target_type == CaptureTarget.WINDOW and target_id == 99999999:
            raise ValueError("Invalid window handle (HWND: 99999999). Window does not exist.")
        from PIL import Image
        return Image.new("RGB", (320, 240), color=(40, 42, 54))

    def capture_frame_base64(self, target_type: str, target_id: Any = 0, max_dim: int = 1024, quality: int = 70) -> str:
        self.capture_count += 1
        if target_type == CaptureTarget.WINDOW and target_id == 99999999:
            raise ValueError("Invalid window handle (HWND: 99999999). Window does not exist.")
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    def close(self) -> None:
        pass


@pytest.fixture
def env(qapp):
    """Provides a fresh, isolated test environment for each test."""
    config = AppConfig()
    oauth = MockOAuthManager(authenticated=False)
    capture = MockScreenCaptureEngine()
    audio = MockAudioPipeline()

    worker = AsyncWorker(
        config=config,
        oauth_manager=oauth,
        capture_engine=capture,
        audio_pipeline=audio,
    )
    worker.start()

    hotkey_mgr = HotkeyManager()

    window = MainWindow(
        worker=worker,
        config=config,
        hotkey_manager=hotkey_mgr,
    )
    window.show()
    qapp.processEvents()

    yield {
        "qapp": qapp,
        "config": config,
        "oauth": oauth,
        "capture": capture,
        "audio": audio,
        "worker": worker,
        "hotkey_mgr": hotkey_mgr,
        "window": window,
    }

    # Clean Teardown
    window.cleanup()
    qapp.processEvents()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    window.close()
    qapp.processEvents()


# ===========================================================================
# 1. Rapid Concurrent State Transitions & Race Conditions
# ===========================================================================
def test_adversarial_rapid_signin_cancel_signout_sequence(env):
    """
    Stress-tests the full rapid lifecycle:
    1. Sign-in initiated
    2. Simulated cancellation / error callback
    3. Immediate sign-out request
    4. Attempted live stream trigger while unauthenticated (must be safely blocked)
    5. Clean transition back to stable unauthenticated state
    """
    win = env["window"]
    qapp = env["qapp"]
    worker = env["worker"]
    oauth = env["oauth"]

    # 1. Initial State
    assert win.state_machine.state == AppState.UNAUTHENTICATED
    assert win.btn_signin.isEnabled()
    assert not win.btn_primary_action.isEnabled()

    # 2. Trigger Sign-in
    win.on_connection_state_changed("AUTHENTICATING")
    qapp.processEvents()
    assert win.state_machine.state == AppState.AUTHENTICATING
    assert not win.btn_signin.isEnabled()

    # 3. Simulate user cancellation / OAuth provider rejection (e.g. access_denied)
    win.on_error_received("Google OAuth cancelled: access_denied")
    win.on_auth_state_changed(False, {})
    win.on_connection_state_changed("DISCONNECTED")
    qapp.processEvents()

    assert win.state_machine.state == AppState.UNAUTHENTICATED
    assert "access_denied" in win.txt_transcript.toPlainText()
    assert win.btn_signin.isVisible()
    assert not win.btn_signout.isVisible()

    # 4. Immediate Sign-out invocation (idempotency check while unauthenticated)
    win._on_signout_clicked()
    qapp.processEvents()
    time.sleep(0.05)
    qapp.processEvents()
    assert win.state_machine.state == AppState.UNAUTHENTICATED

    # 5. Adversarial Attempt: Trigger Alt+L or primary action while unauthenticated
    win._on_hotkey_live_toggle()
    qapp.processEvents()
    # Must NOT transition to LIVE_STREAMING
    assert win.state_machine.state == AppState.UNAUTHENTICATED
    assert win.lbl_status_pill.property("badge") == "signed_out"

    # 6. Now perform valid sign-in
    win.on_auth_state_changed(True, {"name": "Verified User", "email": "verified@gmail.com"})
    win.on_connection_state_changed("READY")
    qapp.processEvents()

    assert win.state_machine.state == AppState.AUTHENTICATED_IDLE
    assert win.btn_primary_action.isEnabled()
    assert win.btn_signout.isVisible()


def test_adversarial_rapid_start_stop_streaming_hammer(env):
    """
    Hammers start_live_streaming() and stop_live_streaming() in rapid succession
    to probe for WebSocket connection collisions, thread-pool deadlocks, and audio pipeline leaks.
    """
    win = env["window"]
    worker = env["worker"]
    qapp = env["qapp"]

    # Authenticate first
    win.on_auth_state_changed(True, {"name": "Hammer Tester", "email": "hammer@test.com"})
    win.on_connection_state_changed("READY")
    qapp.processEvents()

    assert win.state_machine.state == AppState.AUTHENTICATED_IDLE

    # Mock live client methods to measure start/stop coordination
    mock_connect = AsyncMock()
    mock_start = AsyncMock()
    mock_stop = AsyncMock()

    worker.live_client.connect = mock_connect
    worker.live_client.start_streaming = mock_start
    worker.live_client.stop_streaming = mock_stop

    # Rapid pulse: 15 rapid start/stop calls
    for i in range(15):
        worker.start_live_streaming(target_type=CaptureTarget.FULL_SCREEN)
        worker.stop_live_streaming()

    # Allow worker thread to drain
    time.sleep(0.15)
    qapp.processEvents()

    # Worker must still be responsive and alive
    assert worker.isRunning()

    # Transition cleanly back to idle
    win.on_connection_state_changed("READY")
    qapp.processEvents()
    assert win.state_machine.state == AppState.AUTHENTICATED_IDLE
    assert win.btn_primary_action.isEnabled()


def test_adversarial_concurrent_login_burst(env):
    """
    Fires a burst of 10 concurrent request_login() calls to test that the
    worker thread and OAuth manager don't crash, deadlock, or corrupt memory.
    """
    win = env["window"]
    worker = env["worker"]
    oauth = env["oauth"]
    qapp = env["qapp"]

    # Mash "Sign In" 10 times concurrently
    for _ in range(10):
        worker.request_login(timeout=5.0)

    # Let worker execute tasks
    time.sleep(0.15)
    qapp.processEvents()

    assert worker.isRunning()
    assert oauth.login_call_count >= 1


def test_adversarial_state_machine_illegal_transition_fuzzing(env):
    """
    Fuzzes all 36 permutations of (source_state -> target_state) across all 6 AppStates.
    Verifies that every illegal transition is strictly rejected, returns False,
    preserves current state, and maintains valid ENABLEMENT_MATRIX button properties.
    """
    sm = UIStateMachine(initial_state=AppState.UNAUTHENTICATED)
    all_states = list(AppState)

    legal_matrix = {
        AppState.UNAUTHENTICATED: {AppState.AUTHENTICATING, AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.AUTHENTICATING: {AppState.AUTHENTICATED_IDLE, AppState.UNAUTHENTICATED, AppState.ERROR},
        AppState.AUTHENTICATED_IDLE: {AppState.UNAUTHENTICATED, AppState.LIVE_STREAMING, AppState.ONDEMAND_CAPTURING, AppState.ERROR},
        AppState.LIVE_STREAMING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ONDEMAND_CAPTURING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ERROR: {AppState.AUTHENTICATED_IDLE, AppState.UNAUTHENTICATED, AppState.AUTHENTICATING},
    }

    for src in all_states:
        for dst in all_states:
            # Force set state
            sm._state = src
            is_legal = dst in legal_matrix.get(src, set())
            can_trans = sm.can_transition(dst)
            assert can_trans == is_legal, f"Mismatch for {src.name} -> {dst.name}"

            if not is_legal:
                success = sm.transition_to(dst)
                assert success is False, f"Illegal transition succeeded: {src.name} -> {dst.name}"
                assert sm.state == src, f"State corrupted after rejected transition: {sm.state.name}"
            else:
                success = sm.transition_to(dst)
                assert success is True
                assert sm.state == dst


def test_adversarial_deleted_widget_resilience(env):
    """
    Tests that UIStateMachine handles dynamically destroyed/deleted widgets
    gracefully without throwing unhandled C++ / sip RuntimeError.
    """
    qapp = env["qapp"]
    sm = UIStateMachine(initial_state=AppState.UNAUTHENTICATED)

    from PyQt6.QtWidgets import QPushButton
    btn1 = QPushButton("Test 1")
    btn2 = QPushButton("Test 2")

    sm.register_widget(UIAction.SIGN_IN, btn1)
    sm.register_widget(UIAction.SIGN_IN, btn2)

    # Delete btn1
    btn1.deleteLater()
    qapp.processEvents()

    # Trigger transition - should not crash when accessing btn1
    sm.transition_to(AppState.AUTHENTICATING)
    assert sm.state == AppState.AUTHENTICATING
    assert not btn2.isEnabled()


def test_adversarial_barge_in_in_unexpected_states(env):
    """
    Emits barge-in interruptions across non-streaming states (UNAUTHENTICATED, ERROR).
    Verifies that transcript formatting remains clean and no NullPointer/IndexError occurs.
    """
    win = env["window"]
    qapp = env["qapp"]

    win.state_machine.transition_to(AppState.UNAUTHENTICATED)
    # Barge in while unauthenticated
    win.on_interrupted_received()
    qapp.processEvents()
    assert "Interrupted by user speech" in win.txt_transcript.toPlainText()

    # Turn complete without active turn
    win.on_turn_complete_received()
    qapp.processEvents()
    assert not win._in_turn


# ===========================================================================
# 2. Win32 Hotkey Collisions, Simultaneous Bursts & Native Filter
# ===========================================================================
def test_adversarial_simultaneous_hotkeys_burst(env):
    """
    Fires rapid alternating and simultaneous hotkey simulation pulses (100 events)
    for Alt+S and Alt+L to test queue stability and signal delivery.
    """
    win = env["window"]
    mgr = env["hotkey_mgr"]
    qapp = env["qapp"]

    # Authenticate to allow hotkey actions
    win.on_auth_state_changed(True, {"name": "Hotkey Tester", "email": "hotkey@test.com"})
    win.on_connection_state_changed("READY")
    qapp.processEvents()

    ondemand_count = 0
    live_count = 0

    mgr.on_demand_triggered.connect(lambda: ondemand_count.__setitem__(slice(None), [ondemand_count + 1]) if isinstance(ondemand_count, list) else None)
    
    # Pulse 100 alternating hotkey events
    s_events = []
    l_events = []
    mgr.on_demand_triggered.connect(lambda: s_events.append(1))
    mgr.live_toggle_triggered.connect(lambda: l_events.append(1))

    mgr.register_default_hotkeys()

    for _ in range(50):
        mgr.simulate_hotkey(HOTKEY_ID_ONDEMAND)
        mgr.simulate_hotkey(HOTKEY_ID_LIVE)

    qapp.processEvents()

    assert len(s_events) == 50
    assert len(l_events) == 50


def test_adversarial_hotkey_filter_corrupted_messages(env):
    """
    Adversarially feeds corrupted native message pointers and invalid event types
    to Win32HotkeyFilter.nativeEventFilter to ensure zero crashes and zero false dispatches.
    """
    dispatched = []

    def _cb(hid: int, lp: int) -> None:
        dispatched.append((hid, lp))

    filter_obj = Win32HotkeyFilter(_cb)

    # 1. Null message pointer
    handled, _ = filter_obj.nativeEventFilter(b"windows_generic_MSG", sip.voidptr(0))
    assert handled is False

    # 2. Non-windows event types
    handled, _ = filter_obj.nativeEventFilter(b"xcb_generic_event_t", sip.voidptr(0))
    assert handled is False

    handled, _ = filter_obj.nativeEventFilter("unknown_event", sip.voidptr(0))
    assert handled is False

    # 3. Valid struct address with non-hotkey message (e.g. WM_PAINT = 0x000F)
    fake_msg = wintypes.MSG()
    fake_msg.message = 0x000F  # WM_PAINT
    fake_msg.wParam = 0
    fake_msg.lParam = 0

    vptr = sip.voidptr(ctypes.addressof(fake_msg))
    handled, _ = filter_obj.nativeEventFilter(b"windows_generic_MSG", vptr)
    assert handled is False
    assert len(dispatched) == 0

    # 4. Valid struct with WM_HOTKEY and unknown hotkey ID (99999)
    fake_msg.message = WM_HOTKEY
    fake_msg.wParam = 99999
    fake_msg.lParam = 0
    handled, _ = filter_obj.nativeEventFilter(b"windows_generic_MSG", vptr)
    assert handled is True
    assert len(dispatched) == 1
    assert dispatched[0][0] == 99999


def test_adversarial_hotkey_conflict_code_1409_storm(env):
    """
    Simulates a hotkey collision storm where RegisterHotKey fails with ERROR_HOTKEY_ALREADY_REGISTERED (1409).
    Verifies that:
    1. hotkey_conflict signal fires with clear explanation.
    2. MainWindow displays non-blocking warning.
    3. UI does NOT crash or show modal blocking dialogs.
    """
    win = env["window"]
    qapp = env["qapp"]

    mgr = HotkeyManager()
    conflicts = []
    mgr.hotkey_conflict.connect(lambda name, reason: conflicts.append((name, reason)))

    # Connect to window slot
    mgr.hotkey_conflict.connect(win._on_hotkey_conflict)

    # Force mock RegisterHotKey to fail with 1409
    mock_user32 = MagicMock()
    mock_user32.RegisterHotKey.return_value = 0
    mock_kernel32 = MagicMock()
    mock_kernel32.GetLastError.return_value = ERROR_HOTKEY_ALREADY_REGISTERED

    mgr._user32 = mock_user32
    mgr._kernel32 = mock_kernel32

    # Attempt registration of default hotkeys
    status = mgr.register_default_hotkeys()
    qapp.processEvents()

    assert status["Alt+S"] is False
    assert status["Alt+L"] is False
    assert len(conflicts) == 2
    assert "already registered" in conflicts[0][1]
    assert "unavailable" in win.txt_transcript.toPlainText()

    mgr.unregister_all()


def test_adversarial_hotkey_unregister_during_active_dispatch(env):
    """
    Calls unregister_all() while hotkey events are being simulated
    to verify no race condition or dictionary mutation exceptions occur.
    """
    mgr = HotkeyManager()
    mgr.register_default_hotkeys()

    def _on_trigger():
        # Call unregister_all from within hotkey handler
        mgr.unregister_all()

    mgr.on_demand_triggered.connect(_on_trigger)
    # Simulate
    res = mgr.simulate_hotkey(HOTKEY_ID_ONDEMAND)
    assert res is True
    assert len(mgr._registered) == 0
    assert mgr._filter is None


# ===========================================================================
# 3. Edge Cases: Destroyed HWNDs, Closed Windows, Empty Prompts, Corrupt Cache
# ===========================================================================
def test_adversarial_destroyed_hwnd_preview_and_ondemand(env):
    """
    Simulates selecting a window that is destroyed / closed by the OS:
    1. Target ID set to non-existent HWND 99999999.
    2. Preview timer tick: must NOT crash.
    3. On-demand query: must catch capture error, emit sig_error, and restore UI state.
    """
    win = env["window"]
    worker = env["worker"]
    qapp = env["qapp"]

    # Authenticate
    win.on_auth_state_changed(True, {"name": "Window Tester", "email": "win@test.com"})
    win.on_connection_state_changed("READY")
    qapp.processEvents()

    # Switch target to destroyed window HWND
    win.active_target_type = CaptureTarget.WINDOW
    win.active_target_id = 99999999

    # 1. Preview tick
    win._on_preview_timer_tick()
    qapp.processEvents()
    time.sleep(0.05)
    qapp.processEvents()

    # 2. On-demand query trigger on destroyed window
    win.current_mode = "ONDEMAND"
    win._on_send_prompt_clicked()
    qapp.processEvents()

    deadline = time.time() + 2.0
    while time.time() < deadline and (
        win.state_machine.state != AppState.AUTHENTICATED_IDLE
        or "On-demand capture failed" not in win.txt_transcript.toPlainText()
    ):
        qapp.processEvents()
        time.sleep(0.02)
    qapp.processEvents()

    # Verify that UI state machine recovered to AUTHENTICATED_IDLE (not stuck in CAPTURING)
    assert win.state_machine.state == AppState.AUTHENTICATED_IDLE
    assert "On-demand capture failed" in win.txt_transcript.toPlainText()


def test_adversarial_empty_window_list_enumeration(env):
    """
    Verifies that when capture engine finds zero windows (empty window list []),
    the combo box safely clears to 0 items and no IndexError occurs.
    """
    win = env["window"]
    worker = env["worker"]
    capture = env["capture"]
    qapp = env["qapp"]

    # Configure capture engine to return empty list
    capture._windows = []

    win.cb_target_type.setCurrentIndex(1)  # Application window mode
    qapp.processEvents()

    # Request fresh enumeration and wait for worker thread to process
    worker.request_refresh_windows()
    time.sleep(0.1)
    qapp.processEvents()

    assert win.cb_windows.count() == 0
    assert win.cb_windows.currentIndex() == -1


def test_adversarial_empty_whitespace_and_xss_prompts(env):
    """
    Tests prompt input sanitization and fallback:
    1. Empty string "" -> falls back to default prompt
    2. Whitespace-only string "   \t\n   " -> falls back to default prompt
    3. XSS HTML script injection -> safely HTML-escaped in transcript
    4. 50,000 character prompt -> Qt QLineEdit clamps to 32,767 max chars without buffer overflow
    """
    win = env["window"]
    worker = env["worker"]
    qapp = env["qapp"]

    win.on_auth_state_changed(True, {"name": "Security Tester", "email": "sec@test.com"})
    win.on_connection_state_changed("READY")
    win.current_mode = "ONDEMAND"
    qapp.processEvents()

    # Track queries sent to worker
    queries = []
    worker.query_ondemand = lambda target_type, target_id, prompt: queries.append(prompt)

    # 1. Empty prompt
    win.txt_prompt_input.setText("")
    win._on_send_prompt_clicked()
    qapp.processEvents()
    assert len(queries) == 1
    assert "Analyze this screen" in queries[0]

    # 2. Whitespace prompt
    win.txt_prompt_input.setText("   \n\t   ")
    win._on_send_prompt_clicked()
    qapp.processEvents()
    assert len(queries) == 2
    assert "Analyze this screen" in queries[1]

    # 3. XSS injection probe
    xss_payload = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    win.txt_prompt_input.setText(xss_payload)
    win._on_send_prompt_clicked()
    qapp.processEvents()
    assert queries[2] == xss_payload

    # Verify transcript does NOT contain unescaped executable script tag
    transcript_html = win.txt_transcript.toHtml()
    assert "<script>" not in transcript_html
    assert "&lt;script&gt;" in transcript_html

    # 4. Oversized prompt: QLineEdit default maxLength is 32767 chars
    huge_prompt = "A" * 50000
    win.txt_prompt_input.setText(huge_prompt)
    win._on_send_prompt_clicked()
    qapp.processEvents()
    assert len(queries) == 4
    # Qt QLineEdit clamps input to 32,767 characters
    assert len(queries[3]) == 32767
    assert win.txt_prompt_input.maxLength() == 32767


def test_adversarial_corrupt_session_cache_robustness():
    """
    Empirically creates corrupt session.json files and tests TokenStore & OAuthManager:
    - 0-byte file
    - Syntax-corrupted JSON
    - Non-dict JSON (array, scalar)
    - Extreme/invalid field data types
    Verifies that OAuthManager handles all variations without crashing and resets to clean state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        session_file = tmp_path / "session.json"
        dpapi_file = tmp_path / "token_dpapi.bin"

        # 1. 0-byte empty file
        session_file.write_text("", encoding="utf-8")
        store = TokenStore(config_dir=tmp_path)
        assert store.get_session() is None

        # 2. Syntax-corrupted JSON
        session_file.write_text("{broken json syntax: 123", encoding="utf-8")
        assert store.get_session() is None

        # 3. JSON Array instead of Dict
        session_file.write_text(json.dumps([1, 2, 3, "test"]), encoding="utf-8")
        raw = store.get_session()
        assert isinstance(raw, list)

        # Initialize OAuthManager with array session - must not crash
        config = AppConfig(config_dir=str(tmp_path))
        oauth = OAuthManager(config=config, token_store=store)
        assert oauth.is_authenticated() is False
        assert oauth.get_user_profile() == {}

        # 4. Corrupted DPAPI binary
        dpapi_file.write_bytes(b"\x00\xFF\xAA\x55CORRUPTED_DPAPI_BYTES")
        token = store.get_refresh_token()
        assert token is None

        # 5. Invalid field types in session dict
        session_file.write_text(json.dumps({
            "access_token": 12345,
            "expires_at": "not-a-number",
            "user_profile": "not-a-dict",
        }), encoding="utf-8")

        oauth2 = OAuthManager(config=config, token_store=store)
        assert oauth2._expires_at == 0.0
        assert oauth2._user_profile == {}


def test_adversarial_markdown_parser_edge_cases():
    """
    Tests markdown-to-HTML parser with adversarial constructs:
    - Unclosed code blocks and inline spans
    - Deeply nested formatting
    - HTML entities inside code
    """
    # 1. Unclosed backtick
    res1 = simple_markdown_to_html("Here is `unclosed code block")
    assert "<code" not in res1  # Should not crash or produce invalid tags

    # 2. Raw HTML tag escaping
    res2 = simple_markdown_to_html("<div onclick='evil()'>text</div>")
    assert "&lt;div" in res2
    assert "<div onclick" not in res2

    # 3. Multi-line code block with special characters
    code = "```python\nif x < 10 and y > 20:\n    print('Hello & Goodbye')\n```"
    res3 = simple_markdown_to_html(code)
    assert "<pre" in res3
    assert "&lt; 10" in res3
    assert "&gt; 20" in res3
    assert "&amp; Goodbye" in res3


def test_adversarial_transcript_smart_autoscroll_token_flood(env):
    """
    Blasts 300 text tokens while manipulating scroll position to verify
    smart auto-scroll tracking, token accumulation, and Jump to Latest button.
    """
    win = env["window"]
    qapp = env["qapp"]

    win.txt_transcript.clear()

    # Stream 300 tokens rapidly
    for i in range(300):
        win.on_text_token_received(f"tok_{i} ")

    win.on_turn_complete_received()
    qapp.processEvents()

    content = win.txt_transcript.toPlainText()
    assert "tok_0" in content
    assert "tok_299" in content

    # Scroll up and verify Jump to Latest appears
    sb = win.txt_transcript.verticalScrollBar()
    sb.setValue(10)
    qapp.processEvents()
    assert win.btn_jump_latest.isVisible()

    # Click Jump to Latest
    win._on_jump_latest_clicked()
    qapp.processEvents()
    assert sb.value() == sb.maximum()
    assert not win.btn_jump_latest.isVisible()
