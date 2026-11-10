"""
Capture module for full-screen and window-specific capture.
"""

from gemini_desktop_screenshare.capture.screen_capture import (
    CaptureTarget,
    ScreenCaptureEngine,
)
from gemini_desktop_screenshare.capture.window_capture import (
    WindowCapture,
    attach_thread_to_input_desktop,
    set_dpi_awareness,
)

__all__ = [
    "CaptureTarget",
    "ScreenCaptureEngine",
    "WindowCapture",
    "attach_thread_to_input_desktop",
    "set_dpi_awareness",
]
