"""
Adversarial test: EnumWindows with and without SetThreadDesktop to Input Desktop.
"""

import ctypes
from ctypes import wintypes
import json

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14

def enumerate_windows():
    windows = []
    def enum_cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        
        is_visible = bool(user32.IsWindowVisible(hwnd))
        cloaked = ctypes.c_int(0)
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "visible": is_visible,
            "cloaked": cloaked.value
        })
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
    return windows

if __name__ == "__main__":
    print("1. EnumWindows on default thread desktop:")
    w1 = enumerate_windows()
    print(f"Count on unattached thread desktop: {len(w1)}")

    print("\n2. Calling OpenInputDesktop and SetThreadDesktop...")
    DESKTOP_ALL = 0x01FF
    h_input = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
    set_ok = user32.SetThreadDesktop(h_input)
    print(f"OpenInputDesktop: {h_input}, SetThreadDesktop: {set_ok}, err: {kernel32.GetLastError()}")

    print("\n3. EnumWindows AFTER SetThreadDesktop:")
    w2 = enumerate_windows()
    print(f"Count on input desktop: {len(w2)}")
    visible_w2 = [w for w in w2 if w["visible"]]
    print(f"Visible on input desktop: {len(visible_w2)}")
    uncloaked = [w for w in visible_w2 if w["cloaked"] == 0 and len(w["title"].strip()) > 0]
    print(f"Visible, uncloaked, titled windows: {len(uncloaked)}")
    for w in uncloaked[:10]:
        print(f"  HWND {w['hwnd']}: Title='{w['title']}' Cloaked={w['cloaked']}")
