"""
Adversarial Stress Test Suite for Milestone 3 UI, Lifecycle & Memory Stability.
Empirically stress-tests:
1. Rapid bursts of 1,000+ text tokens to transcript widget: throughput, smart auto-scroll,
   memory stability, XSS/adversarial token injection, and barge-in churn.
2. Preview frame flooding at 50+ FPS with high-resolution simulated JPEG frames (1080p and 4K),
   verifying QImage.loadFromData() memory safety, heap stability, and corruption resilience.
3. Clean shutdown under stress: instantiating and destroying MainWindow and AsyncWorker
   15+ times in a tight loop, validating thread lifecycle, timers, and Win32 hooks.

Includes strict empirical verification tests for confirmed bugs:
- BUG A: Smart auto-scroll viewport yanking on streamed tokens.
- BUG B: AsyncWorker.stop() race condition causing 5-second hang and permanent OS thread leak.
- BUG C: AsyncWorker in QThread accumulating zombie _DummyThread instances in threading._active.
"""

import asyncio
import ctypes
from ctypes import wintypes
import gc
import io
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw
import psutil
import pytest

# Ensure headless execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.app import AsyncWorker
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
from gemini_desktop_screenshare.config import AppConfig
from gemini_desktop_screenshare.ui.hotkey_manager import (
    ERROR_HOTKEY_ALREADY_REGISTERED,
    HOTKEY_ID_LIVE,
    HOTKEY_ID_ONDEMAND,
    HotkeyManager,
)
from gemini_desktop_screenshare.ui.main_window import (
    AppState,
    MainWindow,
    UIAction,
    UIStateMachine,
    simple_markdown_to_html,
)
from gemini_desktop_screenshare.ui.styles import PALETTE, apply_theme


# ---------------------------------------------------------------------------
# Test Fixtures & Mocks
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    return app


class StressAudioPipeline:
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
        return 0.02

    def close(self) -> None:
        self.stop_recording()


class StressOAuthManager:
    def __init__(self, authenticated: bool = True) -> None:
        self._authenticated = authenticated
        self._profile = {"name": "Stress Tester", "email": "stress@example.com"}

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_user_profile(self) -> Dict[str, str]:
        return dict(self._profile) if self._authenticated else {}

    def get_valid_access_token(self) -> str:
        return "mock_stress_token"

    def refresh_access_token(self) -> str:
        return "mock_refreshed_stress_token"

    def start_loopback_and_login(self, timeout: float = 120.0) -> Dict[str, Any]:
        self._authenticated = True
        return {"access_token": "mock_stress_token", "user_profile": self._profile}

    def sign_out(self) -> bool:
        self._authenticated = False
        return True


class StressScreenCaptureEngine:
    def __init__(self) -> None:
        self._windows = [
            {"hwnd": 30001, "title": "Chrome - Gemini", "is_minimized": False, "width": 1920, "height": 1080},
            {"hwnd": 30002, "title": "Notepad", "is_minimized": True, "width": 640, "height": 480},
        ]

    def list_windows(self) -> List[Dict[str, Any]]:
        return list(self._windows)

    def capture_frame(self, target_type: str, target_id: Any = 0):
        return Image.new("RGB", (640, 480), color=(40, 44, 52))

    def capture_frame_base64(self, target_type: str, target_id: Any = 0, max_dim: int = 1024, quality: int = 70) -> str:
        return "data:image/jpeg;base64,/9j/4AAQSkZJRg=="

    def close(self) -> None:
        pass


def create_jpeg_buffer(width: int, height: int, color: tuple = (70, 130, 180), quality: int = 75) -> bytes:
    """Creates a genuine JPEG byte buffer with simulated image content."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, width - 10, height - 10], outline=(255, 255, 255), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# OBJECTIVE 1: TRANSCRIPT TOKEN BURST, AUTO-SCROLL & MEMORY STABILITY
# ---------------------------------------------------------------------------
def test_transcript_burst_1000_tokens_throughput_and_memory(qapp):
    """
    Adversarial Challenge 1.1:
    Stream bursts of 1,200+ text tokens in rapid succession to the transcript widget.
    Verifies:
    - High token throughput without UI thread lockup.
    - Exact preservation of streamed token ordering.
    - Bounded memory growth (no runaway Qt text document memory explosion).
    - Clean turn completion and turn state transitions.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    proc = psutil.Process()
    gc.collect()
    rss_before = proc.memory_info().rss

    win.txt_transcript.clear()
    assert win.txt_transcript.toPlainText() == ""

    # Generate 1,200 distinct realistic tokens
    tokens = []
    sample_words = [
        "the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog.",
        " Gemini", " Live", " streams", " multimodal", " screen", " frames",
        " at", " 1 FPS", " with", " 16kHz", " audio.", " Latency", " is", " sub-second.",
        " Analysis:", " **active window**", " shows", " `main.py`", " lines", " 100-250.",
        " No", " anomalies", " detected.", "\n",
    ]
    for i in range(1200):
        tokens.append(sample_words[i % len(sample_words)])

    t_start = time.perf_counter()

    # Stream all 1,200 tokens
    for idx, token in enumerate(tokens):
        win.on_text_token_received(token)
        # Process events every 100 tokens to simulate GUI event loop handling under load
        if idx % 100 == 0:
            qapp.processEvents()

    qapp.processEvents()
    t_elapsed = time.perf_counter() - t_start

    # Conclude turn
    win.on_turn_complete_received()
    qapp.processEvents()

    # Assertions
    assert not win._in_turn, "Turn state must be reset to False upon turn complete"
    assert len(win._current_model_tokens) == 1200, f"Expected 1200 tokens, got {len(win._current_model_tokens)}"

    plain_text = win.txt_transcript.toPlainText()
    assert len(plain_text) > 1000, "Transcript text must contain the full streamed content"
    assert "Gemini" in plain_text
    assert "multimodal" in plain_text
    assert "main.py" in plain_text

    # Verify throughput: 1,200 tokens processed in under 5 seconds
    assert t_elapsed < 5.0, f"Streaming 1,200 tokens took too long: {t_elapsed:.2f}s"

    # Memory assertion: memory growth should be bounded
    gc.collect()
    rss_after = proc.memory_info().rss
    rss_delta_mb = (rss_after - rss_before) / (1024 * 1024)
    assert rss_delta_mb < 50.0, f"Runaway memory growth detected: +{rss_delta_mb:.2f} MB"

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


def test_transcript_smart_autoscroll_under_token_burst(qapp):
    """
    Adversarial Challenge 1.2:
    Tests smart auto-scroll behavior under an active stream:
    - When user scrolls up to read past messages, incoming tokens MUST NOT yank the scroll position.
    - Fails due to unconditional setTextCursor(cursor) in on_text_token_received.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    win.txt_transcript.clear()
    sb = win.txt_transcript.verticalScrollBar()

    # 1. Stream lines to build scrollable document
    for i in range(200):
        win.on_text_token_received(f"Line {i}: Testing auto scroll behavior with high content volume.\n")
        if i % 25 == 0:
            qapp.processEvents()
    qapp.processEvents()

    assert sb.maximum() > 50, f"Expected scrollbar range, max={sb.maximum()}"

    # Ensure at bottom: jump button should NOT be visible
    sb.setValue(sb.maximum())
    qapp.processEvents()
    assert not win.btn_jump_latest.isVisible(), "Jump button should be hidden when at bottom"

    # 2. Simulate user scrolling up towards the top (reading earlier history)
    sb.setValue(10)
    qapp.processEvents()
    assert win.btn_jump_latest.isVisible(), "Jump button must become visible when scrolled up"

    # 3. Stream tokens while scrolled up: viewport MUST NOT be yanked to bottom
    for i in range(50):
        win.on_text_token_received(f"BurstToken_{i} ")
        if i % 10 == 0:
            qapp.processEvents()
    qapp.processEvents()

    # Assertion: Viewport position should be preserved, not yanked to maximum
    current_pos = sb.value()
    assert current_pos < (sb.maximum() - 50), (
        f"Smart auto-scroll violently yanked viewport to bottom! Pos={current_pos}, Max={sb.maximum()}"
    )

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


def test_transcript_adversarial_token_payloads(qapp):
    """
    Adversarial Challenge 1.3:
    Stress-tests the transcript engine with hostile, boundary-case token payloads:
    - Empty tokens and single whitespace tokens
    - Raw HTML injections (<script>, <img onerror>, <style>, <iframe>)
    - Deeply nested markdown and unmatched backticks
    - Massive 20,000-character unbroken string token (tests word-wrap / layout engine)
    - Multibyte Unicode, emojis, zero-width characters, RTL text
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    hostile_tokens = [
        "",  # Empty token
        "   ",  # Pure spaces
        "\t\t\n\r\n",  # Mixed whitespace
        "<script>alert('XSS_ATTACK')</script>",
        "<img src='invalid' onerror='window.close()'>",
        "<iframe src='javascript:void(0)'></iframe>",
        "<style>body { display: none; }</style>",
        "```python\ndef test():\n    return 'unclosed markdown code block\n",
        "**bold *nested italic `inline code with unmatched tick",
        "🚀" * 50,  # Repeated emojis
        "مرحبا بالعالم - שלום עולם - 日本語テスト - 🌟🔥💻",  # Mixed scripts & RTL
        "\u200b\u200c\u200d\ufeff" * 100,  # Zero-width spaces and joiners
        "A" * 20000,  # 20k unbroken character string
        "\x00\x01\x02\x03\x04\x05",  # Control characters
    ]

    for token in hostile_tokens:
        win.on_text_token_received(token)
        qapp.processEvents()

    win.on_turn_complete_received()
    qapp.processEvents()

    # Verify transcript didn't crash and text is present
    plain = win.txt_transcript.toPlainText()
    assert "XSS_ATTACK" in plain
    assert "مرحبا" in plain
    assert "日本語テスト" in plain
    assert len(plain) >= 20000

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


def test_transcript_rapid_barge_in_and_turn_churn(qapp):
    """
    Adversarial Challenge 1.4:
    Rapidly cycles 25 alternating model turns and barge-in interruptions in tight sequence.
    Verifies that state flags (_in_turn, token buffers) do not leak or desynchronize.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    for cycle in range(25):
        # 1. Start turn with a few tokens
        win.on_text_token_received(f"[Turn {cycle} token 1]")
        win.on_text_token_received(f" [Turn {cycle} token 2]")
        assert win._in_turn is True

        if cycle % 2 == 0:
            # Simulate barge-in interruption
            win.on_interrupted_received()
            assert win._in_turn is False
        else:
            # Simulate normal turn completion
            win.on_turn_complete_received()
            assert win._in_turn is False

        qapp.processEvents()

    plain = win.txt_transcript.toPlainText()
    assert "Interrupted by user speech" in plain
    assert "[Turn 24 token 1]" in plain

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# OBJECTIVE 2: PREVIEW FLOODING & QIMAGE MEMORY SAFETY
# ---------------------------------------------------------------------------
def test_preview_flooding_60_fps_high_res_frames(qapp):
    """
    Adversarial Challenge 2.1:
    Floods preview updates with 60 high-resolution (1080p and 4K) simulated JPEG frames
    in rapid succession (< 1.5 seconds) to stress QImage.loadFromData() memory safety,
    pixmap caching, and heap stability.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    # Pre-generate 1080p and 4K genuine JPEG buffers
    frame_1080p = create_jpeg_buffer(1920, 1080, color=(30, 80, 150), quality=80)
    frame_4k = create_jpeg_buffer(3840, 2160, color=(180, 50, 40), quality=85)
    frame_std = create_jpeg_buffer(640, 480, color=(50, 120, 60), quality=70)

    assert len(frame_1080p) > 20000, "1080p frame size should be substantial"
    assert len(frame_4k) > 50000, "4K frame size should be substantial"

    frames = [frame_1080p, frame_4k, frame_std] * 20  # 60 frames total

    proc = psutil.Process()
    gc.collect()
    rss_before = proc.memory_info().rss

    t_start = time.perf_counter()
    loaded_count = 0

    # Flood frames directly through QImage.loadFromData and win.on_preview_frame_received
    for idx, raw_jpeg in enumerate(frames):
        qimg = QImage()
        success = qimg.loadFromData(raw_jpeg, "JPEG")
        assert success is True, f"QImage.loadFromData failed on frame {idx}"
        win.on_preview_frame_received(qimg)
        loaded_count += 1

        # Process Qt events periodically
        if idx % 10 == 0:
            qapp.processEvents()

    qapp.processEvents()
    t_elapsed = time.perf_counter() - t_start

    assert loaded_count == 60
    assert win.lbl_preview.pixmap() is not None
    assert not win.lbl_preview.pixmap().isNull()

    # Flooding 60 high-res frames should complete efficiently without stalling
    assert t_elapsed < 5.0, f"Preview flooding 60 frames took {t_elapsed:.2f}s (too slow)"

    # Check heap stability: pixmap should replace in-place without unbounded growth
    gc.collect()
    rss_after = proc.memory_info().rss
    rss_growth_mb = (rss_after - rss_before) / (1024 * 1024)
    assert rss_growth_mb < 60.0, f"Memory growth after 60 high-res frames is excessive: +{rss_growth_mb:.2f} MB"

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


def test_preview_cross_thread_signal_flooding(qapp):
    """
    Adversarial Challenge 2.2:
    Floods QImage preview frames across threads via worker.sig_preview_frame at high frequency.
    Ensures that Qt's QueuedConnection event queue handles cross-thread image delivery cleanly
    without memory corruption or dropping the main thread.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    jpeg_data = create_jpeg_buffer(800, 600, color=(100, 100, 200))
    received_frames = []

    def _track_frame(qimg):
        received_frames.append(qimg.size())

    win.worker.sig_preview_frame.connect(_track_frame)

    # Background thread emitting 50 frames rapidly
    def _flooder():
        for _ in range(50):
            qimg = QImage()
            if qimg.loadFromData(jpeg_data, "JPEG"):
                worker.sig_preview_frame.emit(qimg)
            time.sleep(0.005)  # 200 fps burst

    flood_thread = threading.Thread(target=_flooder)
    flood_thread.start()
    flood_thread.join(timeout=3.0)

    # Process all queued cross-thread signals
    for _ in range(10):
        qapp.processEvents()
        time.sleep(0.02)

    assert len(received_frames) == 50, f"Expected 50 frames across threads, got {len(received_frames)}"

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


def test_qimage_loadfromdata_adversarial_malformed_inputs(qapp):
    """
    Adversarial Challenge 2.3:
    Stress-tests QImage.loadFromData() with deliberately malformed and hostile payloads:
    - Empty byte buffers
    - Truncated JPEG headers
    - Corrupted JPEG data (valid SOI header but random noise payload)
    - Non-JPEG data (random bytes, plaintext, HTML)
    - Massive 3 MB buffer of garbage
    Verifies zero crashes, zero access violations, and graceful False return values.
    """
    test_cases = [
        b"",  # Empty
        b"\xff\xd8",  # Truncated SOI header only
        b"\xff\xd8\xff\xe0" + b"\x00" * 20,  # Incomplete APP0 segment
        b"\xff\xd8\xff" + os.urandom(256),  # Random bytes after SOI
        b"<html><body>Not a JPEG</body></html>",  # Plain text / HTML
        b"\x00" * 4096,  # Null bytes
        os.urandom(1024 * 1024 * 3),  # 3 MB of random noise
    ]

    for idx, bad_data in enumerate(test_cases):
        qimg = QImage()
        # Must return False gracefully without raising exceptions or segfaulting
        result = qimg.loadFromData(bad_data, "JPEG")
        assert result is False, f"Expected loadFromData to return False for bad payload #{idx}"
        assert qimg.isNull(), f"QImage must be null after failed loadFromData for payload #{idx}"


def test_preview_minimized_window_safeguard_under_flood(qapp):
    """
    Adversarial Challenge 2.4:
    Verifies that when target is a minimized window, preview flooding safely invokes
    _create_placeholder_image without leaking QPainter resources or restoring the window.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    # Set active target to window with mock HWND
    win.active_target_type = CaptureTarget.WINDOW
    win.active_target_id = 99999

    with patch("ctypes.windll.user32.IsIconic", return_value=1) as mock_is_iconic:
        # Trigger 50 rapid preview updates
        for _ in range(50):
            win._trigger_preview_update()
            qapp.processEvents()

        assert mock_is_iconic.call_count == 50
        assert win.lbl_preview.pixmap() is not None
        assert not win.lbl_preview.pixmap().isNull()

    # Cleanup
    win.cleanup()
    hotkey_mgr.unregister_all()
    worker.stop()
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# OBJECTIVE 3: CLEAN SHUTDOWN UNDER STRESS & ZERO LEAK HARNESS
# ---------------------------------------------------------------------------
def test_lifecycle_stress_15_iterations_clean_os_threads(qapp):
    """
    Adversarial Challenge 3.1:
    Instantiate and destroy MainWindow, AsyncWorker, and HotkeyManager 15 times
    in a tight loop with proper event-loop synchronization.
    Verifies:
    - Zero Windows OS thread leaks: psutil.Process().num_threads() does not accumulate.
    - Zero orphaned timers: win.preview_timer is stopped every time.
    - Zero dangling Win32 global hotkeys: RegisterHotKey succeeds on EVERY iteration;
      any leak would trigger error 1409 ERROR_HOTKEY_ALREADY_REGISTERED.
    - Native event filter cleanly removed on each cycle.
    - Process RSS memory remains stable without continuous inflation.
    """
    config = AppConfig()
    proc = psutil.Process()
    gc.collect()

    initial_os_threads = proc.num_threads()
    initial_rss = proc.memory_info().rss

    iterations = 15
    for i in range(iterations):
        oauth = StressOAuthManager(authenticated=True)
        capture = StressScreenCaptureEngine()
        audio = StressAudioPipeline()

        # 1. Instantiate & start worker
        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()

        # 2. Instantiate hotkey manager & register keys
        hotkey_mgr = HotkeyManager()
        status = hotkey_mgr.register_default_hotkeys()
        # CRITICAL ADVERSARIAL CHECK: If previous iteration leaked hotkeys,
        # register_default_hotkeys() would return False with error 1409!
        assert status.get("Alt+S") is True, f"Iteration {i}: Alt+S registration failed! Hotkey leaked!"
        assert status.get("Alt+L") is True, f"Iteration {i}: Alt+L registration failed! Hotkey leaked!"

        # 3. Instantiate MainWindow
        win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
        win.show()
        qapp.processEvents()

        # 4. Perform live operations during lifecycle
        win.on_text_token_received(f"Iteration_{i}_Token ")
        win.on_turn_complete_received()

        preview_jpeg = create_jpeg_buffer(320, 240, color=(i * 15 % 255, 100, 150))
        qimg = QImage()
        qimg.loadFromData(preview_jpeg, "JPEG")
        win.on_preview_frame_received(qimg)
        qapp.processEvents()

        # 5. Verify timer is active before cleanup
        assert win.preview_timer.isActive() is True

        # Wait a tiny moment to ensure worker event loop has entered run_forever
        worker._loop_ready.wait(timeout=2.0)

        # 6. Teardown sequence
        hotkey_mgr.unregister_all()
        win.cleanup()
        worker.stop()
        audio.close()
        capture.close()
        win.close()
        win.deleteLater()
        qapp.processEvents()

        # 7. Post-teardown assertions for this iteration
        assert not worker.isRunning(), f"Iteration {i}: AsyncWorker is still running after stop()!"
        assert not win.preview_timer.isActive(), f"Iteration {i}: preview_timer is still active after cleanup()!"

    # Allow Qt deferred deletions and garbage collector to run
    gc.collect()
    qapp.processEvents()

    final_os_threads = proc.num_threads()
    final_rss = proc.memory_info().rss
    rss_growth_mb = (final_rss - initial_rss) / (1024 * 1024)

    # OS Thread leak check: Windows OS thread count must not continuously grow
    os_thread_delta = final_os_threads - initial_os_threads
    assert os_thread_delta <= 2, f"OS thread leak: started with {initial_os_threads}, ended with {final_os_threads}"

    # Memory growth check across 15 complete GUI + worker cycles
    assert rss_growth_mb < 95.0, f"Memory growth after 15 lifecycle iterations is excessive: +{rss_growth_mb:.2f} MB"


def test_worker_rapid_start_stop_race_hang(qapp):
    """
    Adversarial Challenge 3.2:
    Rapidly starts and stops AsyncWorker without pause.
    Demonstrates race condition where worker thread is orphaned and hangs.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    # Immediately stop before loop_ready - triggers the race condition
    worker.stop()

    audio.close()
    capture.close()

    # Assertion: worker must be stopped, but due to bug it remains running!
    assert not worker.isRunning(), "CONFIRMED BUG: Worker thread failed to stop and is hung!"


def test_lifecycle_dummy_thread_leak(qapp):
    """
    Adversarial Challenge 3.3:
    Verifies that running AsyncWorker in QThread leaves uncollectable _DummyThread
    objects in Python's threading._active table.
    """
    config = AppConfig()
    initial_threads = threading.active_count()

    for idx in range(5):
        oauth = StressOAuthManager(authenticated=True)
        capture = StressScreenCaptureEngine()
        audio = StressAudioPipeline()

        worker = AsyncWorker(config, oauth, capture, audio)
        worker.start()
        worker._loop_ready.wait(timeout=2.0)
        worker.stop()
        audio.close()
        capture.close()

    gc.collect()
    final_threads = threading.active_count()
    delta = final_threads - initial_threads

    # In clean environment delta should be 0; due to bug, delta == 5
    assert delta == 0, f"CONFIRMED BUG: Leaked {delta} _DummyThread objects in threading._active!"


def test_shutdown_during_active_streaming_state(qapp):
    """
    Adversarial Challenge 3.4:
    Simulates abrupt application shutdown while actively in LIVE_STREAMING state with
    active timers and in-flight coroutines. Verifies that teardown does not deadlock or raise.
    """
    config = AppConfig()
    oauth = StressOAuthManager(authenticated=True)
    capture = StressScreenCaptureEngine()
    audio = StressAudioPipeline()

    worker = AsyncWorker(config, oauth, capture, audio)
    worker.start()
    hotkey_mgr = HotkeyManager()
    win = MainWindow(worker=worker, config=config, hotkey_manager=hotkey_mgr)
    win.show()
    qapp.processEvents()

    # Transition through authenticated idle to live streaming
    win.state_machine.transition_to(AppState.AUTHENTICATED_IDLE)
    win.state_machine.transition_to(AppState.LIVE_STREAMING)
    assert win.state_machine.state == AppState.LIVE_STREAMING

    # Submit an active async task on the loop
    async def _long_coro():
        try:
            await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            pass

    future = worker.submit_coro(_long_coro())

    # Wait for loop to be active
    worker._loop_ready.wait(timeout=2.0)

    # Abrupt teardown
    hotkey_mgr.unregister_all()
    win.cleanup()
    worker.stop()  # Must cancel pending tasks and stop loop within timeout
    audio.close()
    capture.close()
    win.close()
    qapp.processEvents()

    assert not worker.isRunning(), "Worker failed to stop cleanly during active streaming!"
    assert not win.preview_timer.isActive(), "Timer must be stopped!"
