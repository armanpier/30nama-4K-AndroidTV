"""
Full-screen and window capture engine.
Uses mss.MSS() for high-performance multi-monitor desktop capture and
WindowCapture for Win32 HWND capture, with aspect-ratio-preserving downscaling
and JPEG compression.
"""

import base64
import io
import logging
import threading
from typing import Any, Dict, List, Optional
import mss
from PIL import Image, ImageGrab

from gemini_desktop_screenshare.capture.window_capture import (
    WindowCapture,
    attach_thread_to_input_desktop,
    set_dpi_awareness,
)

logger = logging.getLogger(__name__)

_tls = threading.local()


def _get_thread_sct() -> mss.MSS:
    """Returns a thread-local mss.MSS instance attached to the input desktop."""
    attach_thread_to_input_desktop()
    if not hasattr(_tls, "sct") or _tls.sct is None:
        _tls.sct = mss.MSS()
    return _tls.sct


class CaptureTarget:
    """Capture target modes."""
    FULL_SCREEN = "full_screen"
    WINDOW = "window"


class ScreenCaptureEngine:
    """
    Unified capture engine for Windows full desktop and specific application windows.
    Handles downscaling to max dimension 1024, JPEG compression (quality 70),
    and Base64 encoding.
    """

    def __init__(self) -> None:
        set_dpi_awareness()
        attach_thread_to_input_desktop()
        self._window_capture = WindowCapture()

    @property
    def monitors(self) -> List[Dict[str, Any]]:
        return _get_thread_sct().monitors

    @property
    def _sct(self) -> Any:
        return _get_thread_sct()

    def capture_screen(self, monitor_index: int = 0) -> Image.Image:
        """
        Captures the full desktop or a specific monitor.
        monitor_index = 0: All monitors combined (virtual desktop).
        monitor_index = 1: Primary monitor.
        monitor_index >= 2: Additional individual monitors.
        """
        attach_thread_to_input_desktop()
        sct = _get_thread_sct()
        monitors = sct.monitors
        if not monitors:
            raise RuntimeError("No monitors detected by mss.")

        # Bounds check for monitor index
        if monitor_index < 0 or monitor_index >= len(monitors):
            logger.warning(
                "Requested monitor index %s out of range (%s available); defaulting to 0.",
                monitor_index,
                len(monitors),
            )
            monitor_index = 0

        target_monitor = monitors[monitor_index]
        try:
            sct_img = sct.grab(target_monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            logger.warning("Primary mss grab failed (%s); refreshing thread desktop & context...", e)
            attach_thread_to_input_desktop()
            if hasattr(_tls, "sct") and _tls.sct is not None:
                try:
                    _tls.sct.close()
                except Exception:
                    pass
                _tls.sct = None
            try:
                _tls.sct = mss.MSS()
                sct_img = _tls.sct.grab(target_monitor)
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as e2:
                logger.warning("Fallback to PIL ImageGrab due to mss error: %s", e2)
                attach_thread_to_input_desktop()
                try:
                    return ImageGrab.grab(all_screens=True)
                except Exception:
                    try:
                        return ImageGrab.grab(all_screens=False)
                    except Exception as e3:
                        logger.error("All screen capture methods failed: %s", e3)
                        raise e2

    def capture_window(self, hwnd: int) -> Image.Image:
        """
        Captures the surface of a specific top-level window by HWND.
        """
        return self._window_capture.capture_window(hwnd)

    def capture_frame(self, target_type: str, target_id: Any = 0) -> Image.Image:
        """
        Captures an image based on target_type ('full_screen' or 'window').
        """
        if target_type == CaptureTarget.WINDOW:
            if target_id is None:
                raise ValueError("Window target_id (HWND) must be provided for WINDOW capture.")
            return self.capture_window(int(target_id))
        else:
            mon_idx = int(target_id) if target_id is not None else 0
            return self.capture_screen(mon_idx)

    def capture_frame_jpeg(
        self,
        target_type: str,
        target_id: Any = 0,
        max_dim: int = 1024,
        quality: int = 70,
    ) -> bytes:
        """
        Captures a frame, downscales it preserving aspect ratio so neither dimension exceeds max_dim,
        and compresses it to JPEG at specified quality.
        """
        img = self.capture_frame(target_type, target_id)

        # Downscale preserving aspect ratio
        width, height = img.size
        if max(width, height) > max_dim:
            scale = max_dim / float(max(width, height))
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Compress to JPEG
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def capture_frame_base64(
        self,
        target_type: str,
        target_id: Any = 0,
        max_dim: int = 1024,
        quality: int = 70,
    ) -> str:
        """
        Captures a frame and returns its Base64-encoded JPEG representation.
        """
        jpeg_bytes = self.capture_frame_jpeg(
            target_type=target_type,
            target_id=target_id,
            max_dim=max_dim,
            quality=quality,
        )
        return base64.b64encode(jpeg_bytes).decode("ascii")

    def list_windows(self) -> List[Dict[str, Any]]:
        """
        Enumerates all eligible top-level application windows.
        Ensures calling background threads are attached to the interactive input desktop.
        """
        attach_thread_to_input_desktop()
        return self._window_capture.list_windows()

    def close(self) -> None:
        """Closes the underlying mss instance."""
        if hasattr(_tls, "sct") and _tls.sct is not None:
            try:
                _tls.sct.close()
            except Exception as e:
                logger.debug("Error closing thread-local mss: %s", e)
            _tls.sct = None

    def __enter__(self) -> "ScreenCaptureEngine":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
