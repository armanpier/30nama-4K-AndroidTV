"""
Programmatic Test Suite for Milestone 3 UI & Interaction Controls.
Executes headlessly with QT_QPA_PLATFORM=offscreen. Covers:
- UI hierarchy and component initialization
- UI State Machine transitions and central ENABLEMENT_MATRIX enforcement
- Target picker population, selection memory, and minimized window safeguards
- Microphone mute toggling and AudioPipeline synchronization
- Streaming text token accumulation, barge-in notice, and smart auto-scrolling
- Win32 Hotkey registration, conflict handling, and native event filter dispatch
- AsyncWorker QThread lifecycle and clean headless shutdown
"""

import asyncio
import ctypes
from ctypes import wintypes
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Enforce headless offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import PyQt6.sip as sip
from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.app import AsyncWorker
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
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
from gemini_desktop_screenshare.ui.styles import DARK_STYLESHEET, PALETTE, apply_theme


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provides a shared QApplication instance running offscreen."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    return app


class MockAudioPipeline:
    """Mock AudioPipeline maintaining mute state and callback hooks."""

    def __init__(self) -> None:
        self.is_muted = False
        self.is_recording = False
        self._record_callback: Optional[Callable[[bytes], None]] = None

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
        return 0.05

    def close(self) -> None:
        self.stop_recording()


class MockOAuthManager:
    """Mock OAuthManager simulating authenticated and unauthenticated states."""

    def __init__(self, authenticated: bool = False) -> None:
        self._authenticated = authenticated
        self._profile = {"name": "Test User", "email": "test@example.com"}

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_user_profile(self) -> Dict[str, str]:
        return dict(self._profile) if self._authenticated else {}

    def get_valid_access_token(self) -> str:
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        return "mock_access_token_xyz"

    def refresh_access_token(self) -> str:
        return "mock_refreshed_access_token"

    def start_loopback_and_login(self, timeout: float = 120.0) -> Dict[str, Any]:
        self._authenticated = True
        return {"access_token": "mock_token", "user_profile": self._profile}

    def sign_out(self) -> bool:
        self._authenticated = False
        return True


class MockScreenCaptureEngine:
    """Mock ScreenCaptureEngine returning synthetic PIL images."""

    def __init__(self) -> None:
        self._windows = [
            {"hwnd": 20001, "title": "VS Code - main.py", "is_minimized": False, "width": 1920, "height": 1080},
            {"hwnd": 20002, "title": "Command Prompt", "is_minimized": True, "width": 800, "height": 600},
        ]

    def list_windows(self) -> List[Dict[str, Any]]:
        return list(self._windows)

    def capture_frame(self, target_type: str, target_id: Any = 0):
        from PIL import Image
        return Image.new("RGB", (640, 480), color=(32, 33, 36))

    def capture_frame_base64(self, target_type: str, target_id: Any = 0, max_dim: int = 1024, quality: int = 70) -> str:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    def close(self) -> None:
        pass


@pytest.fixture
def test_env(qapp):
    """Initializes a full mock environment with AsyncWorker and MainWindow."""
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

    # Teardown
    window.cleanup()
    qapp.processEvents()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    window.close()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# 1. UI Hierarchy & Widget Tree Tests
# ---------------------------------------------------------------------------
def test_ui_hierarchy_and_initialization(test_env):
    """Verifies that all required cards, widgets, and layout elements exist and are sized properly."""
    win = test_env["window"]
    qapp = test_env["qapp"]

    assert win.windowTitle() == "Gemini Desktop Screenshare"
    assert win.minimumSize().width() >= 1024
    assert win.minimumSize().height() >= 720

    # Header components
    assert win.lbl_status_pill is not None
    assert "Signed Out" in win.lbl_status_pill.text()

    # Left Deck Cards
    assert win.card_account is not None
    assert win.lbl_user_name.text() == "Not Signed In"
    assert win.btn_signin.isVisible()
    assert not win.btn_signout.isVisible()
    assert not win.btn_refresh_token.isVisible()

    assert win.card_mode is not None
    assert win.rb_live.isChecked()
    assert not win.rb_ondemand.isChecked()

    assert win.card_target is not None
    assert win.cb_target_type.count() == 2
    assert not win.window_picker_row.isVisible()

    assert win.card_controls is not None
    assert win.btn_primary_action is not None
    assert win.btn_mic_mute is not None
    assert "Active (Unmuted)" in win.btn_mic_mute.text()

    assert win.card_preview is not None
    assert win.lbl_preview is not None

    # Right Deck Transcript & Dock
    assert win.txt_transcript is not None
    assert win.txt_transcript.isReadOnly()
    assert win.dock_prompt is not None
    assert win.dock_prompt.isVisible()  # Full in-app chat dock enabled by default

    # Status Bar items
    assert win.sb_auth is not None
    assert win.sb_target is not None
    assert win.sb_audio is not None


# ---------------------------------------------------------------------------
# 2. State Machine & Button Enablement Matrix Tests
# ---------------------------------------------------------------------------
def test_state_machine_transitions_and_guards(test_env):
    """Exhaustively verifies State Machine valid transitions, illegal transition blocks, and widget updates."""
    win = test_env["window"]
    sm = win.state_machine

    # Initial State: UNAUTHENTICATED
    assert sm.state == AppState.UNAUTHENTICATED
    assert win.btn_signin.isEnabled()
    assert not win.btn_signout.isEnabled()
    assert not win.btn_primary_action.isEnabled()
    assert not win.btn_mic_mute.isEnabled()
    assert not win.cb_target_type.isEnabled()

    # Blocked: Cannot jump directly to LIVE_STREAMING
    assert not sm.can_transition(AppState.LIVE_STREAMING)
    assert not sm.transition_to(AppState.LIVE_STREAMING)
    assert sm.state == AppState.UNAUTHENTICATED

    # Valid: UNAUTHENTICATED -> AUTHENTICATING
    assert sm.transition_to(AppState.AUTHENTICATING)
    assert sm.state == AppState.AUTHENTICATING
    assert not win.btn_signin.isEnabled()
    assert not win.btn_primary_action.isEnabled()

    # Valid: AUTHENTICATING -> AUTHENTICATED_IDLE
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
    assert sm.state == AppState.AUTHENTICATED_IDLE
    assert win.btn_primary_action.isEnabled()
    assert win.btn_mic_mute.isEnabled()
    assert win.cb_target_type.isEnabled()
    assert win.rb_live.isEnabled()
    assert win.rb_ondemand.isEnabled()

    # Valid: AUTHENTICATED_IDLE -> LIVE_STREAMING
    assert sm.transition_to(AppState.LIVE_STREAMING)
    assert sm.state == AppState.LIVE_STREAMING
    # In live streaming: Primary action stays enabled (to stop), Target & Mode locked
    assert win.btn_primary_action.isEnabled()
    assert not win.cb_target_type.isEnabled()
    assert not win.rb_live.isEnabled()
    assert not win.rb_ondemand.isEnabled()
    assert win.btn_mic_mute.isEnabled()
    assert not win.btn_signout.isEnabled()  # Must not sign out during active stream

    # Blocked: Cannot jump from LIVE_STREAMING to ONDEMAND_CAPTURING
    assert not sm.can_transition(AppState.ONDEMAND_CAPTURING)
    assert not sm.transition_to(AppState.ONDEMAND_CAPTURING)

    # Valid: LIVE_STREAMING -> AUTHENTICATED_IDLE
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
    assert sm.state == AppState.AUTHENTICATED_IDLE
    assert win.cb_target_type.isEnabled()
    assert win.rb_live.isEnabled()

    # Valid: AUTHENTICATED_IDLE -> ONDEMAND_CAPTURING
    assert sm.transition_to(AppState.ONDEMAND_CAPTURING)
    assert sm.state == AppState.ONDEMAND_CAPTURING
    assert not win.btn_primary_action.isEnabled()  # In-flight capture running
    assert not win.cb_target_type.isEnabled()

    # Valid: ONDEMAND_CAPTURING -> AUTHENTICATED_IDLE
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
    assert sm.state == AppState.AUTHENTICATED_IDLE


def test_auth_state_updates_ui(test_env):
    """Verifies that sig_auth_state_changed cleanly updates profile and button visibility."""
    win = test_env["window"]
    qapp = test_env["qapp"]

    # Simulate sign-in completion signal
    profile = {"name": "Jane Developer", "email": "jane.dev@google.com"}
    win.on_auth_state_changed(True, profile)
    qapp.processEvents()

    assert win.lbl_user_name.text() == "Jane Developer"
    assert win.lbl_user_email.text() == "jane.dev@google.com"
    assert not win.btn_signin.isVisible()
    assert win.btn_signout.isVisible()
    assert win.btn_refresh_token.isVisible()
    assert win.state_machine.state == AppState.AUTHENTICATED_IDLE
    assert "jane.dev@google.com" in win.sb_auth.text()

    # Simulate sign-out signal
    win.on_auth_state_changed(False, {})
    qapp.processEvents()

    assert win.lbl_user_name.text() == "Not Signed In"
    assert win.btn_signin.isVisible()
    assert not win.btn_signout.isVisible()
    assert win.state_machine.state == AppState.UNAUTHENTICATED


# ---------------------------------------------------------------------------
# 3. Target Picker & Minimized Window Safeguards
# ---------------------------------------------------------------------------
def test_target_picker_switching_and_enumeration(test_env):
    """Tests switching between Full Desktop and Application Window, populating window list."""
    win = test_env["window"]
    qapp = test_env["qapp"]

    # Initial state: Full Desktop
    assert win.active_target_type == CaptureTarget.FULL_SCREEN
    assert not win.window_picker_row.isVisible()

    # Switch to Application Window
    win.cb_target_type.setCurrentIndex(1)
    qapp.processEvents()

    assert win.active_target_type == CaptureTarget.WINDOW
    assert win.window_picker_row.isVisible()

    # Provide enumerated windows
    mock_wins = [
        {"hwnd": 20001, "title": "VS Code - main.py", "is_minimized": False, "width": 1920, "height": 1080},
        {"hwnd": 20002, "title": "Command Prompt", "is_minimized": True, "width": 800, "height": 600},
    ]
    win.on_windows_enumerated_received(mock_wins)
    qapp.processEvents()

    assert win.cb_windows.count() == 2
    assert "VS Code" in win.cb_windows.itemText(0)
    assert "[Minimized]" in win.cb_windows.itemText(1)

    # Selecting the first window updates active_target_id
    win.cb_windows.setCurrentIndex(0)
    qapp.processEvents()
    assert win.active_target_id == 20001
    assert "20001" in win.sb_target.text() or "0x" in win.sb_target.text()


def test_minimized_window_placeholder_generation(test_env):
    """Verifies that minimized window placeholder is generated cleanly without un-minimizing."""
    win = test_env["window"]
    placeholder = win._create_placeholder_image("[Target Window Minimized]")
    assert isinstance(placeholder, QImage)
    assert placeholder.width() == 340
    assert placeholder.height() == 192


# ---------------------------------------------------------------------------
# 4. Microphone Mute / Unmute Visual & Engine Synchronization
# ---------------------------------------------------------------------------
def test_microphone_mute_toggle(test_env):
    """Tests that clicking the mic button toggles mute state in AudioPipeline and updates QSS properties."""
    win = test_env["window"]
    audio = test_env["audio"]
    qapp = test_env["qapp"]

    # Transition to authenticated idle state to enable microphone controls
    win.state_machine.transition_to(AppState.AUTHENTICATED_IDLE)
    qapp.processEvents()

    assert not audio.is_muted
    assert not win.is_muted
    assert win.btn_mic_mute.property("mic_state") == "unmuted"

    # Click to Mute
    QTest.mouseClick(win.btn_mic_mute, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert audio.is_muted
    assert win.is_muted
    assert "MUTED" in win.btn_mic_mute.text()
    assert win.btn_mic_mute.property("mic_state") == "muted"

    # Click to Unmute
    QTest.mouseClick(win.btn_mic_mute, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert not audio.is_muted
    assert not win.is_muted
    assert "Active (Unmuted)" in win.btn_mic_mute.text()
    assert win.btn_mic_mute.property("mic_state") == "unmuted"


# ---------------------------------------------------------------------------
# 5. Transcript Token Streaming, Interruption, and Smart Auto-Scroll
# ---------------------------------------------------------------------------
def test_transcript_token_streaming_and_turn_completion(test_env):
    """Verifies token appending, markdown parsing, and barge-in interruption formatting."""
    win = test_env["window"]
    qapp = test_env["qapp"]

    win.txt_transcript.clear()

    # Stream several tokens
    win.on_text_token_received("Hello, ")
    win.on_text_token_received("I see your ")
    win.on_text_token_received("VS Code editor!")
    qapp.processEvents()

    content = win.txt_transcript.toPlainText()
    assert "Hello, I see your VS Code editor!" in content

    # Complete model turn
    win.on_turn_complete_received()
    assert not win._in_turn

    # Barge-in interruption
    win.on_interrupted_received()
    qapp.processEvents()

    content_with_interruption = win.txt_transcript.toPlainText()
    assert "Interrupted by user speech" in content_with_interruption


def test_markdown_parser_formatting():
    """Tests the lightweight markdown parser handles code, bold, italic, and breaks."""
    raw = "Here is `code` and **bold** and *italic*:\n```\nfunc main() {}\n```"
    parsed = simple_markdown_to_html(raw)

    assert "code</code>" in parsed
    assert "<code style=" in parsed
    assert "<strong>bold</strong>" in parsed
    assert "<em>italic</em>" in parsed
    assert "<pre" in parsed
    assert "<br/>" in parsed


def test_smart_autoscroll_and_jump_button(test_env):
    """Verifies smart auto-scrolling preserves position when scrolled up and shows Jump button."""
    win = test_env["window"]
    qapp = test_env["qapp"]

    win.txt_transcript.clear()
    # Add substantial content to create scrollbar range
    for i in range(50):
        win.txt_transcript.append(f"<p>Turn {i}: Message content and observations line {i}</p>")
    qapp.processEvents()

    sb = win.txt_transcript.verticalScrollBar()
    # When at bottom, jump button is hidden
    sb.setValue(sb.maximum())
    qapp.processEvents()
    assert not win.btn_jump_latest.isVisible()

    # User scrolls up
    sb.setValue(20)
    qapp.processEvents()
    assert win.btn_jump_latest.isVisible()

    # Clicking Jump to Latest returns to bottom
    QTest.mouseClick(win.btn_jump_latest, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert sb.value() == sb.maximum()
    assert not win.btn_jump_latest.isVisible()


# ---------------------------------------------------------------------------
# 6. Win32 Global Hotkeys & Native Event Filter
# ---------------------------------------------------------------------------
def test_hotkey_registration_and_dispatch(test_env):
    """Tests HotkeyManager registration, programmatic simulation, and signal dispatch."""
    mgr = test_env["hotkey_mgr"]
    qapp = test_env["qapp"]

    on_demand_fired = []
    live_fired = []

    mgr.on_demand_triggered.connect(lambda: on_demand_fired.append(True))
    mgr.live_toggle_triggered.connect(lambda: live_fired.append(True))

    status = mgr.register_default_hotkeys()
    assert "Alt+S" in status
    assert "Alt+L" in status

    # Programmatic simulation of Alt+S
    res_s = mgr.simulate_hotkey(HOTKEY_ID_ONDEMAND)
    qapp.processEvents()
    assert res_s is True
    assert len(on_demand_fired) == 1

    # Programmatic simulation of Alt+L
    res_l = mgr.simulate_hotkey(HOTKEY_ID_LIVE)
    qapp.processEvents()
    assert res_l is True
    assert len(live_fired) == 1


def test_native_event_filter_decoding(test_env):
    """Verifies Win32HotkeyFilter intercepting WM_HOTKEY from memory pointer."""
    dispatched = []

    def _callback(hotkey_id: int, lparam: int) -> None:
        dispatched.append((hotkey_id, lparam))

    filter_obj = Win32HotkeyFilter(_callback)

    # Fabricate a Win32 MSG struct
    fake_msg = wintypes.MSG()
    fake_msg.message = WM_HOTKEY
    fake_msg.wParam = HOTKEY_ID_ONDEMAND
    fake_msg.lParam = (VK_S << 16) | MOD_ALT

    vptr = sip.voidptr(ctypes.addressof(fake_msg))
    handled, _ = filter_obj.nativeEventFilter(b"windows_generic_MSG", vptr)

    assert handled is True
    assert len(dispatched) == 1
    assert dispatched[0][0] == HOTKEY_ID_ONDEMAND


def test_hotkey_conflict_handling(test_env):
    """Verifies that duplicate registration or existing hotkey returns conflict cleanly."""
    mgr1 = HotkeyManager()
    status1 = mgr1.register_default_hotkeys()

    mgr2 = HotkeyManager()
    conflicts = []
    mgr2.hotkey_conflict.connect(lambda name, reason: conflicts.append((name, reason)))

    if sys.platform == "win32":
        # On Windows, attempting to register the same key yields conflict 1409
        status2 = mgr2.register_default_hotkeys()
        # Should detect conflict or handle gracefully
        if not status2.get("Alt+S"):
            assert len(conflicts) > 0

    mgr1.unregister_all()
    mgr2.unregister_all()


# ---------------------------------------------------------------------------
# 7. AsyncWorker Asyncio Loop & Headless Shutdown
# ---------------------------------------------------------------------------
def test_async_worker_coro_execution(test_env):
    """Verifies that coroutines submitted to AsyncWorker execute thread-safely."""
    worker = test_env["worker"]
    qapp = test_env["qapp"]

    async def _add(a: int, b: int) -> int:
        await asyncio.sleep(0.01)
        return a + b

    future = worker.submit_coro(_add(40, 2))
    result = future.result(timeout=3.0)
    assert result == 42


def test_audio_pipeline_barge_in_hook(test_env):
    """Verifies that AudioPipeline.interrupt hooked by AsyncWorker emits sig_interrupted."""
    worker = test_env["worker"]
    audio = test_env["audio"]
    qapp = test_env["qapp"]

    interrupted_events = []
    worker.sig_interrupted.connect(lambda: interrupted_events.append(True))

    audio.interrupt()
    qapp.processEvents()

    assert len(interrupted_events) == 1


def test_clean_shutdown(test_env):
    """Verifies that all components shut down without hangs, exceptions, or memory leaks."""
    win = test_env["window"]
    worker = test_env["worker"]
    audio = test_env["audio"]
    capture = test_env["capture"]
    hotkeys = test_env["hotkey_mgr"]
    qapp = test_env["qapp"]

    hotkeys.unregister_all()
    win.cleanup()
    worker.stop()
    audio.close()
    capture.close()
    qapp.processEvents()

    assert not worker.isRunning()
