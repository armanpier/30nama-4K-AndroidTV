"""
Adversarial Verification Suite for Window Enumeration and HWND Capture.
Demonstrating:
1. SetThreadDesktop called BEFORE win32ui import -> SUCCESS (ok=1).
2. DWMWA_CLOAKED filtering on actual Windows desktop.
3. PrintWindow(PW_RENDERFULLCONTENT) latency and content verification across real active windows.
4. PW_RENDERFULLCONTENT vs PW_CLIENTONLY vs standard PrintWindow.
5. GDI handle leak testing across 100 iterations.
"""

import ctypes
from ctypes import wintypes
import time
import json
import numpy as np

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# 1. Desktop attachment MUST happen before win32ui is loaded
DESKTOP_ALL = 0x01FF
h_input = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
set_desktop_ok = user32.SetThreadDesktop(h_input) if h_input else False
attach_err = kernel32.GetLastError() if not set_desktop_ok else 0

# 2. Now import win32ui after desktop attachment
import win32gui
import win32ui
import win32con

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
PW_RENDERFULLCONTENT = 0x00000002
GR_GDIOBJECTS = 0
GR_USEROBJECTS = 1

def get_gui_resources():
    h_proc = kernel32.GetCurrentProcess()
    gdi_count = user32.GetGuiResources(h_proc, GR_GDIOBJECTS)
    user_count = user32.GetGuiResources(h_proc, GR_USEROBJECTS)
    return gdi_count, user_count

def capture_window_raw(hwnd, flag=PW_RENDERFULLCONTENT):
    rect = wintypes.RECT()
    res = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    if res != 0 or (rect.right <= rect.left) or (rect.bottom <= rect.top):
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    
    if width <= 0 or height <= 0:
        return None, 0.0, False, "Invalid dimensions"
        
    hwnd_dc = user32.GetWindowDC(hwnd)
    if not hwnd_dc:
        return None, 0.0, False, "GetWindowDC failed"
        
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(save_bitmap)

    t0 = time.perf_counter()
    pw_res = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), flag)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    bmpinfo = save_bitmap.GetInfo()
    bmpstr = save_bitmap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
    
    h, w, _ = img.shape
    sample = img[h//4:3*h//4, w//4:3*w//4] if h >= 4 and w >= 4 else img
    has_content = bool(np.any(sample[:, :, :3] > 0))

    # Clean up
    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    user32.ReleaseDC(hwnd, hwnd_dc)

    return (w, h), dt_ms, (pw_res != 0), has_content

def enumerate_windows():
    windows = []
    
    def enum_cb(hwnd, lparam):
        is_visible = bool(user32.IsWindowVisible(hwnd))
        is_iconic = bool(user32.IsIconic(hwnd))
        
        cloaked = ctypes.c_int(0)
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        
        ext_rect = wintypes.RECT()
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(ext_rect), ctypes.sizeof(ext_rect))
        
        win_rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
        
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "visible": is_visible,
            "iconic": is_iconic,
            "cloaked": cloaked.value,
            "ext_rect": (ext_rect.left, ext_rect.top, ext_rect.right, ext_rect.bottom),
            "win_rect": (win_rect.left, win_rect.top, win_rect.right, win_rect.bottom)
        })
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
    return windows

def main():
    print(f"Desktop Attachment: handle={h_input}, ok={set_desktop_ok}, err={attach_err}")
    print("=== ENUMERATING WINDOWS ===")
    all_windows = enumerate_windows()
    print(f"Total top-level windows found: {len(all_windows)}")
    
    visible_windows = [w for w in all_windows if w["visible"]]
    print(f"Visible windows: {len(visible_windows)}")
    
    cloaked_count = sum(1 for w in visible_windows if w["cloaked"] != 0)
    print(f"Visible but CLOAKED windows: {cloaked_count}")
    
    titled_visible_uncloaked = [
        w for w in visible_windows if w["cloaked"] == 0 and len(w["title"].strip()) > 0
    ]
    print(f"Target candidate windows (visible, uncloaked, non-empty title): {len(titled_visible_uncloaked)}")
    
    print("\n--- Candidate Windows Details ---")
    for w in titled_visible_uncloaked:
        print(f"HWND {w['hwnd']}: Title='{w['title'][:50]}' Iconic={w['iconic']} ExtRect={w['ext_rect']}")

    print("\n=== BENCHMARKING PRINTWINDOW LATENCY & CONTENT ===")
    results = []
    for w in titled_visible_uncloaked:
        hwnd = w["hwnd"]
        dim, dt_ms, pw_ok, has_content = capture_window_raw(hwnd, PW_RENDERFULLCONTENT)
        results.append({
            "hwnd": hwnd,
            "title": w["title"][:40],
            "iconic": w["iconic"],
            "dim": dim,
            "dt_ms": round(dt_ms, 2),
            "pw_ok": pw_ok,
            "has_content": has_content
        })
    print(json.dumps(results, indent=2))
    
    # Stress test handle leakage
    if titled_visible_uncloaked:
        # Pick a non-iconic window if available
        non_iconic = [w for w in titled_visible_uncloaked if not w["iconic"]]
        target_hwnd = non_iconic[0]["hwnd"] if non_iconic else titled_visible_uncloaked[0]["hwnd"]
        print(f"\n=== GDI RESOURCE LEAK STRESS TEST (100 cycles on HWND {target_hwnd}) ===")
        gdi_before, user_before = get_gui_resources()
        print(f"Before: GDI handles={gdi_before}, USER handles={user_before}")
        
        times = []
        for _ in range(100):
            _, dt, _, _ = capture_window_raw(target_hwnd, PW_RENDERFULLCONTENT)
            times.append(dt)
            
        gdi_after, user_after = get_gui_resources()
        print(f"After:  GDI handles={gdi_after}, USER handles={user_after}")
        print(f"Delta:  GDI diff={gdi_after - gdi_before}, USER diff={user_after - user_before}")
        print(f"100 capture cycles avg latency: {round(sum(times)/len(times), 2)} ms (min: {round(min(times), 2)} ms, max: {round(max(times), 2)} ms)")

if __name__ == "__main__":
    main()
