"""
Win32 Window Capture Module.
Handles window enumeration, cloaking/iconic filtering, Unicode sanitization,
desktop attachment, and HWND bitmap capture via PrintWindow(PW_RENDERFULLCONTENT).
"""

import ctypes
from ctypes import wintypes
import logging
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# Win32 Constants
PW_RENDERFULLCONTENT = 0x00000002
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_RESTORE = 9
WM_SYSCOMMAND = 0x0112
SC_RESTORE = 0xF120
DESKTOP_ALL = 0x01FF


def set_dpi_awareness() -> None:
    """Sets Per-Monitor DPI awareness (v2) to avoid scaling distortion."""
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.debug("Process DPI awareness set to Per-Monitor (2).")
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            logger.debug("Process DPI awareness set via SetProcessDPIAware.")
        except Exception as e:
            logger.debug("Could not set process DPI awareness: %s", e)


def attach_thread_to_input_desktop() -> bool:
    """
    Attaches the current calling thread to the active input desktop.
    Must be called in worker threads before any win32ui imports or GDI hooks
    to prevent Error 170 (ERROR_BUSY).
    """
    try:
        user32 = ctypes.windll.user32
        h_input = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
        if h_input:
            ok = user32.SetThreadDesktop(h_input)
            logger.debug("SetThreadDesktop status: %s", ok)
            return bool(ok)
    except Exception as e:
        logger.debug("attach_thread_to_input_desktop error: %s", e)
    return False


# Execute initial setup before win32ui module binding
set_dpi_awareness()
attach_thread_to_input_desktop()

import win32con
import win32gui
import win32ui


class WindowCapture:
    """
    High-performance Win32 application window capture engine.
    Uses PrintWindow with PW_RENDERFULLCONTENT and cleans up all GDI handles.
    """

    def __init__(self) -> None:
        set_dpi_awareness()

    def list_windows(self) -> List[Dict[str, Any]]:
        """
        Enumerates all visible, uncloaked top-level application windows.
        Sanitizes titles for Unicode display and tracks minimized (iconic) status.
        """
        attach_thread_to_input_desktop()
        windows: List[Dict[str, Any]] = []
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        def enum_cb(hwnd: int, lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True

            # Filter cloaked windows (hidden virtual desktop / background UWP apps)
            cloaked = ctypes.c_int(0)
            dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if cloaked.value != 0:
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            raw_title = buf.value.strip()
            if not raw_title:
                return True

            # Sanitize window title to prevent Unicode encoding crashes on console/logs
            enc = getattr(sys.stdout, "encoding", None) or "utf-8"
            clean_text = "".join(ch for ch in raw_title if ch.isprintable() or ch in " \t")
            try:
                sanitized_title = clean_text.encode(enc, errors="replace").decode(enc)
            except Exception:
                sanitized_title = clean_text.encode("ascii", errors="replace").decode("ascii")

            # Obtain bounding rectangle
            rect = wintypes.RECT()
            res = dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
            )
            if res != 0 or (rect.right <= rect.left) or (rect.bottom <= rect.top):
                user32.GetWindowRect(hwnd, ctypes.byref(rect))

            width = rect.right - rect.left
            height = rect.bottom - rect.top

            # Ignore tiny system utility windows (e.g. 0x0 or tooltip overlays)
            if width <= 10 or height <= 10:
                return True

            is_iconic = bool(user32.IsIconic(hwnd))

            windows.append({
                "hwnd": hwnd,
                "title": sanitized_title,
                "rect": (rect.left, rect.top, rect.right, rect.bottom),
                "width": width,
                "height": height,
                "is_minimized": is_iconic,
            })
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
        return windows

    def capture_window(self, hwnd: int) -> Image.Image:
        """
        Captures a specific window by HWND using PrintWindow(PW_RENDERFULLCONTENT).
        Automatically restores minimized windows without stealing focus and cleans up GDI handles.
        """
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        if not user32.IsWindow(hwnd):
            raise ValueError(f"Invalid window handle (HWND: {hwnd}). Window does not exist.")

        # Ensure current thread is attached to input desktop
        attach_thread_to_input_desktop()

        # Handle minimized window: restore without activating focus
        if user32.IsIconic(hwnd):
            logger.info("Window %s is minimized; restoring without activating focus.", hwnd)
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
            time.sleep(0.05)  # Allow DWM surface to update

        # Get true window dimensions
        rect = wintypes.RECT()
        res = dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if res != 0 or (rect.right <= rect.left) or (rect.bottom <= rect.top):
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            raise RuntimeError(f"Window {hwnd} has invalid dimensions ({width}x{height}).")

        hwnd_dc = user32.GetWindowDC(hwnd)
        if not hwnd_dc:
            raise RuntimeError(f"GetWindowDC failed for HWND {hwnd}.")

        mfc_dc = None
        save_dc = None
        save_bitmap = None
        img = None
        needs_fallback = False

        try:
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)

            # Print window content into memory DC
            pw_res = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
            if pw_res == 0:
                # Fallback to standard PrintWindow if PW_RENDERFULLCONTENT fails
                pw_res = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)

            if pw_res != 0:
                bmpinfo = save_bitmap.GetInfo()
                bmpstr = save_bitmap.GetBitmapBits(True)

                # Convert bitmap buffer to PIL Image
                # Windows bitmaps are BGRX, convert to RGB
                img = Image.frombuffer(
                    "RGB",
                    (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                    bmpstr,
                    "raw",
                    "BGRX",
                    0,
                    1,
                )
                # Check for completely black image (all pixels zero)
                if img.getbbox() is None:
                    needs_fallback = True
            else:
                needs_fallback = True

        finally:
            # Guarantees zero GDI handle leaks
            if save_bitmap is not None:
                win32gui.DeleteObject(save_bitmap.GetHandle())
            if save_dc is not None:
                save_dc.DeleteDC()
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
            user32.ReleaseDC(hwnd, hwnd_dc)

        if needs_fallback or img is None:
            logger.info(
                "PrintWindow returned 0 or produced pure black frame for HWND %s; falling back to foreground mss crop.",
                hwnd,
            )
            return self._fallback_foreground_mss_crop(hwnd)

        return img.copy()

    def _fallback_foreground_mss_crop(self, hwnd: int) -> Image.Image:
        """
        Fallback capture for windows that return 0 or produce a pure black frame with PrintWindow.
        Brings window to foreground via ShowWindow / SetForegroundWindow and crops from mss full capture.
        """
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        if user32.IsIconic(hwnd):
            user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)

        user32.SetForegroundWindow(hwnd)
        time.sleep(0.08)  # Allow DWM and window to repaint

        rect = wintypes.RECT()
        res = dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if res != 0 or (rect.right <= rect.left) or (rect.bottom <= rect.top):
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        cur_w = rect.right - rect.left
        cur_h = rect.bottom - rect.top

        if cur_w <= 0 or cur_h <= 0:
            raise RuntimeError(f"Window {hwnd} has invalid dimensions ({cur_w}x{cur_h}) during fallback.")

        import mss
        with mss.MSS() as sct:
            bbox = {
                "left": rect.left,
                "top": rect.top,
                "width": cur_w,
                "height": cur_h,
            }
            sct_img = sct.grab(bbox)
            fallback_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return fallback_img.copy()
