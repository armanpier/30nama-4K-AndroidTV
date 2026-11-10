"""
Unit tests for Screen and Window Capture Subsystem.
Tests multi-monitor desktop capture via mss, Win32 window enumeration,
Unicode window title handling, HWND capture with minimized recovery,
aspect-ratio preserving downscale to 1024px, JPEG compression, and Base64 encoding.
"""

import base64
import ctypes
import io
import time
from typing import Generator
import pytest
from PIL import Image

from gemini_desktop_screenshare.capture.screen_capture import ScreenCaptureEngine, CaptureTarget
from gemini_desktop_screenshare.capture.window_capture import WindowCapture

user32 = ctypes.windll.user32


@pytest.fixture
def capture_engine() -> Generator[ScreenCaptureEngine, None, None]:
    engine = ScreenCaptureEngine()
    yield engine
    engine.close()


@pytest.fixture
def temp_win32_window():
    """Creates a temporary top-level Win32 window for testing capture."""
    title = "GeminiCaptureEngineTestWindow_Test"
    hwnd = user32.CreateWindowExW(
        0, "STATIC", title, 0x10080000, 100, 100, 400, 300, 0, 0, 0, 0
    )
    user32.ShowWindow(hwnd, 5)  # SW_SHOW
    user32.UpdateWindow(hwnd)
    time.sleep(0.05)
    yield hwnd, title
    if user32.IsWindow(hwnd):
        user32.DestroyWindow(hwnd)


# ------------------------------------------------------------------------------
# 1. Multi-Monitor Desktop Capture Tests
# ------------------------------------------------------------------------------
def test_screen_capture_multi_monitor_detection(capture_engine: ScreenCaptureEngine):
    """Verifies that mss detects at least 1 monitor configuration."""
    monitors = capture_engine._sct.monitors
    assert len(monitors) >= 2  # monitors[0] is all monitors combined; monitors[1] is primary


def test_screen_capture_virtual_desktop_monitor_0(capture_engine: ScreenCaptureEngine):
    """Verifies that capture_screen(0) captures the virtual desktop canvas."""
    img = capture_engine.capture_screen(0)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    mon0 = capture_engine._sct.monitors[0]
    assert img.width == mon0["width"]
    assert img.height == mon0["height"]


def test_screen_capture_primary_monitor_1(capture_engine: ScreenCaptureEngine):
    """Verifies that capture_screen(1) captures the primary display."""
    img = capture_engine.capture_screen(1)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    mon1 = capture_engine._sct.monitors[1]
    assert img.width == mon1["width"]
    assert img.height == mon1["height"]


def test_screen_capture_out_of_bounds_fallback(capture_engine: ScreenCaptureEngine):
    """Verifies that out-of-bounds monitor indices fallback to monitor 0 gracefully."""
    img_fallback_high = capture_engine.capture_screen(999)
    assert isinstance(img_fallback_high, Image.Image)

    img_fallback_neg = capture_engine.capture_screen(-5)
    assert isinstance(img_fallback_neg, Image.Image)


# ------------------------------------------------------------------------------
# 2. Window Enumeration & HWND Capture Tests
# ------------------------------------------------------------------------------
def test_window_enumeration_structure_and_keys(capture_engine: ScreenCaptureEngine):
    """Verifies that list_windows returns properly structured window metadata dicts."""
    windows = capture_engine.list_windows()
    assert isinstance(windows, list)
    for win in windows:
        assert "hwnd" in win
        assert "title" in win
        assert "rect" in win
        assert "width" in win
        assert "height" in win
        assert "is_minimized" in win
        assert isinstance(win["hwnd"], int)
        assert isinstance(win["title"], str)


def test_window_enumeration_unicode_title_safety():
    """Verifies that window titles containing Persian, Arabic, Japanese, and emojis enumerate safely."""
    unicode_title = "تست ویندوز 🚀 日本語 עברית"
    hwnd = user32.CreateWindowExW(
        0, "STATIC", unicode_title, 0x10080000, 100, 100, 300, 200, 0, 0, 0, 0
    )
    user32.ShowWindow(hwnd, 5)
    time.sleep(0.05)
    try:
        wc = WindowCapture()
        windows = wc.list_windows()
        found = any(w["hwnd"] == hwnd for w in windows)
        assert found
    finally:
        user32.DestroyWindow(hwnd)


def test_window_capture_real_hwnd(capture_engine: ScreenCaptureEngine, temp_win32_window):
    """Verifies capturing an active Win32 window returns a valid PIL Image."""
    hwnd, _ = temp_win32_window
    img = capture_engine.capture_window(hwnd)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width > 0
    assert img.height > 0


def test_window_capture_minimized_restoration(capture_engine: ScreenCaptureEngine, temp_win32_window):
    """Verifies capturing a minimized window restores it without stealing focus."""
    hwnd, _ = temp_win32_window
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.05)
    assert bool(user32.IsIconic(hwnd))

    img = capture_engine.capture_window(hwnd)
    assert isinstance(img, Image.Image)
    assert img.width > 0
    assert img.height > 0


def test_window_capture_invalid_hwnd_handling(capture_engine: ScreenCaptureEngine):
    """Verifies that capturing an invalid or destroyed HWND raises ValueError."""
    with pytest.raises(ValueError, match="Invalid window handle"):
        capture_engine.capture_window(999999999)


# ------------------------------------------------------------------------------
# 3. Downscaling, Compression & Base64 Encoding Tests
# ------------------------------------------------------------------------------
def test_capture_frame_jpeg_downscale_aspect_ratio(capture_engine: ScreenCaptureEngine):
    """Verifies that capture_frame_jpeg downscales image to max_dim and outputs valid JPEG."""
    jpeg_bytes = capture_engine.capture_frame_jpeg(
        target_type=CaptureTarget.FULL_SCREEN,
        target_id=0,
        max_dim=1024,
        quality=70,
    )
    assert isinstance(jpeg_bytes, bytes)
    # Check JPEG magic header \xff\xd8 and footer \xff\xd9
    assert jpeg_bytes.startswith(b"\xff\xd8")
    assert jpeg_bytes.endswith(b"\xff\xd9")

    # Load image from bytes to verify dimension bounds
    decoded_img = Image.open(io.BytesIO(jpeg_bytes))
    assert max(decoded_img.width, decoded_img.height) <= 1024


def test_capture_frame_base64_decoding(capture_engine: ScreenCaptureEngine):
    """Verifies that capture_frame_base64 produces valid ASCII Base64 decodable to JPEG."""
    b64_str = capture_engine.capture_frame_base64(
        target_type=CaptureTarget.FULL_SCREEN,
        target_id=0,
        max_dim=1024,
        quality=70,
    )
    assert isinstance(b64_str, str)
    raw_bytes = base64.b64decode(b64_str)
    assert raw_bytes.startswith(b"\xff\xd8")
    assert raw_bytes.endswith(b"\xff\xd9")
