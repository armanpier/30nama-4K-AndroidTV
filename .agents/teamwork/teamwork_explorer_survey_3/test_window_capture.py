import ctypes
from ctypes import wintypes
import time
from PIL import Image

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
gdi32 = ctypes.windll.gdi32

# Ensure input desktop
h_input = user32.OpenInputDesktop(0, False, 0x01FF)
if h_input:
    user32.SetThreadDesktop(h_input)

# DPI Awareness
user32.SetProcessDPIAware()

DWMWA_EXTENDED_FRAME_BOUNDS = 9
PW_RENDERFULLCONTENT = 2

def list_open_windows():
    windows = []
    
    def enum_windows_callback(hwnd, extra):
        if not user32.IsWindowVisible(hwnd):
            return True
        
        # Check window title
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()
        
        if not title:
            return True

        # Check cloaked status (Windows 10/11 virtual desktops & UWP suspended apps)
        is_cloaked = ctypes.c_int(0)
        DWMWA_CLOAKED = 14
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(is_cloaked), ctypes.sizeof(is_cloaked))
        if is_cloaked.value != 0:
            return True

        # Check bounds
        rect = wintypes.RECT()
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        
        # Skip microscopic/zero windows
        if w <= 10 or h <= 10:
            return True
            
        is_minimized = bool(user32.IsIconic(hwnd))
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
            "width": w,
            "height": h,
            "minimized": is_minimized
        })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return windows

def capture_window_printwindow(hwnd, bounds):
    w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
    if w <= 0 or h <= 0:
        return None

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    h_old = gdi32.SelectObject(hdc_mem, hbitmap)

    # Call PrintWindow with PW_RENDERFULLCONTENT
    # If PW_RENDERFULLCONTENT fails or window is hardware accelerated (DirectX/Chrome/WPF),
    # fallback to BitBlt or standard PrintWindow
    success = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
    if not success:
        # Fallback to standard PrintWindow (0)
        success = user32.PrintWindow(hwnd, hdc_mem, 0)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    buffer = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, h, ctypes.byref(buffer), ctypes.byref(bmi), 0)

    # Cleanup
    gdi32.SelectObject(hdc_mem, h_old)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    img = Image.frombuffer("RGBA", (w, h), buffer, "raw", "BGRA", 0, 1)
    return img

if __name__ == '__main__':
    wins = list_open_windows()
    print(f"Found {len(wins)} eligible open application windows:")
    for i, w in enumerate(wins[:10]):
        print(f"[{i}] HWND={w['hwnd']} | Rect={w['rect']} ({w['width']}x{w['height']}) | Minimized={w['minimized']} | Title='{w['title']}'")

    if wins:
        target = wins[0]
        print(f"\nTesting capture of window: '{target['title']}'")
        t0 = time.perf_counter()
        img = capture_window_printwindow(target['hwnd'], target['rect'])
        t1 = time.perf_counter()
        if img:
            print(f"Captured window successfully! Image size: {img.size}, elapsed: {(t1-t0)*1000:.2f}ms")
