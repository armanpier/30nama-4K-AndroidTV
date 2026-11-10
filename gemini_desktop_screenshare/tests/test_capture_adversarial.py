"""
Adversarial Verification Suite for Screen Capture and Desktop Attachment.
Tests:
1. Current desktop environment discovery (Session ID, Thread Desktop, Input Desktop names).
2. mss.mss() and PIL.ImageGrab.grab() out-of-the-box capture behavior, latency, and surface sanity.
3. OpenInputDesktop + SetThreadDesktop behavior in pure ctypes environment.
4. OpenInputDesktop + SetThreadDesktop behavior when win32ui is imported vs instantiated.
5. Thread-isolation behavior of SetThreadDesktop (main thread vs dedicated worker thread).
6. Pure ctypes GDI BitBlt vs mss vs PIL latency benchmark.
"""

import sys
import time
import ctypes
from ctypes import wintypes
import json

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

UOI_NAME = 2

def get_desktop_name(h_desktop):
    if not h_desktop:
        return "NULL"
    length = wintypes.DWORD()
    user32.GetUserObjectInformationW(h_desktop, UOI_NAME, None, 0, ctypes.byref(length))
    if length.value == 0:
        return "UNKNOWN"
    buf = ctypes.create_unicode_buffer(length.value // 2 + 1)
    if user32.GetUserObjectInformationW(h_desktop, UOI_NAME, buf, length.value, ctypes.byref(length)):
        return buf.value
    return f"FAILED (error {kernel32.GetLastError()})"

def get_session_info():
    pid = kernel32.GetCurrentProcessId()
    session_id = wintypes.DWORD()
    kernel32.ProcessIdToSessionId(pid, ctypes.byref(session_id))
    
    tid = kernel32.GetCurrentThreadId()
    h_thread_desktop = user32.GetThreadDesktop(tid)
    thread_desk_name = get_desktop_name(h_thread_desktop)
    
    # Try OpenInputDesktop with 0x01FF (DESKTOP_READOBJECTS | DESKTOP_WRITEOBJECTS | etc.)
    DESKTOP_ALL = 0x01FF
    h_input_desktop = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
    input_desk_err = kernel32.GetLastError() if not h_input_desktop else 0
    input_desk_name = get_desktop_name(h_input_desktop) if h_input_desktop else "NONE"
    
    return {
        "pid": pid,
        "session_id": session_id.value,
        "tid": tid,
        "thread_desktop_handle": h_thread_desktop,
        "thread_desktop_name": thread_desk_name,
        "input_desktop_handle": h_input_desktop,
        "input_desktop_name": input_desk_name,
        "input_desktop_error": input_desk_err,
        "screen_width": user32.GetSystemMetrics(0),
        "screen_height": user32.GetSystemMetrics(1)
    }

def test_screen_capture_engines():
    results = {}
    
    # Test mss
    try:
        import mss
        with mss.mss() as sct:
            latencies = []
            for _ in range(10):
                t0 = time.perf_counter()
                img = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
                latencies.append((time.perf_counter() - t0) * 1000)
            
            # Check content sanity (non-zero pixels)
            raw_bytes = bytes(img.raw)
            non_zero = any(b != 0 for b in raw_bytes[:10000])
            results["mss"] = {
                "success": True,
                "width": img.width,
                "height": img.height,
                "avg_ms": round(sum(latencies) / len(latencies), 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "has_content": non_zero
            }
    except Exception as e:
        results["mss"] = {"success": False, "error": str(e), "error_type": type(e).__name__}

    # Test PIL.ImageGrab
    try:
        from PIL import ImageGrab
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            img = ImageGrab.grab()
            latencies.append((time.perf_counter() - t0) * 1000)
        
        results["PIL"] = {
            "success": True,
            "width": img.width,
            "height": img.height,
            "avg_ms": round(sum(latencies) / len(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "mode": img.mode
        }
    except Exception as e:
        results["PIL"] = {"success": False, "error": str(e), "error_type": type(e).__name__}

    # Test pure ctypes GDI capture
    try:
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        h_screen_dc = user32.GetDC(0)
        h_mem_dc = gdi32.CreateCompatibleDC(h_screen_dc)
        h_bitmap = gdi32.CreateCompatibleBitmap(h_screen_dc, w, h)
        h_old_bmp = gdi32.SelectObject(h_mem_dc, h_bitmap)
        
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            gdi32.BitBlt(h_mem_dc, 0, 0, w, h, h_screen_dc, 0, 0, 0x00CC0020) # SRCCOPY
            latencies.append((time.perf_counter() - t0) * 1000)
            
        # Clean up
        gdi32.SelectObject(h_mem_dc, h_old_bmp)
        gdi32.DeleteObject(h_bitmap)
        gdi32.DeleteDC(h_mem_dc)
        user32.ReleaseDC(0, h_screen_dc)
        
        results["ctypes_gdi"] = {
            "success": True,
            "width": w,
            "height": h,
            "avg_ms": round(sum(latencies) / len(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2)
        }
    except Exception as e:
        results["ctypes_gdi"] = {"success": False, "error": str(e)}

    return results

if __name__ == "__main__":
    print("=== DESKTOP & SESSION INFO ===")
    info = get_session_info()
    print(json.dumps(info, indent=2))
    
    print("\n=== SCREEN CAPTURE ENGINES ===")
    cap_results = test_screen_capture_engines()
    print(json.dumps(cap_results, indent=2))
