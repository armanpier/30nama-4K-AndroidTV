import time
import io
import base64
import ctypes
from ctypes import wintypes
import numpy as np
from PIL import Image, ImageGrab
import mss
import cv2

# Set thread desktop before any UI or MFC hooks
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

h_input = user32.OpenInputDesktop(0, False, 0x01FF)
if h_input:
    res = user32.SetThreadDesktop(h_input)
    print(f"Attached thread to OpenInputDesktop: result={res}")
else:
    print(f"OpenInputDesktop failed, error={ctypes.GetLastError()}")

def ctypes_capture_screen():
    # Full screen via ctypes GDI
    user32.SetProcessDPIAware()
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    h_old = gdi32.SelectObject(hdc_mem, hbitmap)
    
    # BitBlt
    SRCCOPY = 0x00CC0020
    CAPTUREBLT = 0x40000000
    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, SRCCOPY | CAPTUREBLT)
    
    # Extract bits
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
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    buffer = (ctypes.c_char * (width * height * 4))()
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, ctypes.byref(buffer), ctypes.byref(bmi), 0)

    # Cleanup GDI
    gdi32.SelectObject(hdc_mem, h_old)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
    return img

def benchmark_full_screen():
    print("\n=== Full Screen Capture Benchmark ===")
    
    # 1. PIL ImageGrab
    try:
        times_pil = []
        for _ in range(5):
            t0 = time.perf_counter()
            img = ImageGrab.grab()
            t1 = time.perf_counter()
            times_pil.append((t1 - t0) * 1000)
        print(f"PIL.ImageGrab: size={img.size}, avg={np.mean(times_pil):.2f}ms, min={np.min(times_pil):.2f}ms, max={np.max(times_pil):.2f}ms")
    except Exception as e:
        print(f"PIL.ImageGrab failed: {type(e).__name__}: {e}")

    # 2. MSS
    try:
        times_mss = []
        with mss.MSS() as sct:
            mon = sct.monitors[1] # Primary monitor
            for _ in range(5):
                t0 = time.perf_counter()
                sct_img = sct.grab(mon)
                img_pil = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                t1 = time.perf_counter()
                times_mss.append((t1 - t0) * 1000)
        print(f"MSS: size={img_pil.size}, avg={np.mean(times_mss):.2f}ms, min={np.min(times_mss):.2f}ms, max={np.max(times_mss):.2f}ms")
    except Exception as e:
        print(f"MSS failed: {type(e).__name__}: {e}")

    # 3. Pure ctypes GDI BitBlt
    try:
        times_gdi = []
        for _ in range(5):
            t0 = time.perf_counter()
            img_gdi = ctypes_capture_screen()
            t1 = time.perf_counter()
            times_gdi.append((t1 - t0) * 1000)
        print(f"Ctypes GDI: size={img_gdi.size}, avg={np.mean(times_gdi):.2f}ms, min={np.min(times_gdi):.2f}ms, max={np.max(times_gdi):.2f}ms")
    except Exception as e:
        print(f"Ctypes GDI failed: {type(e).__name__}: {e}")

def benchmark_downscaling_and_compression():
    print("\n=== Downscaling and Compression Benchmark ===")
    with mss.MSS() as sct:
        sct_img = sct.grab(sct.monitors[1])
        raw_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    print(f"Source frame resolution: {raw_img.size}")

    targets = [(1280, 720), (1024, 768), (960, 540)]
    np_raw = np.array(raw_img)

    for target in targets:
        # Resize: PIL vs OpenCV
        t0 = time.perf_counter()
        resized_pil = raw_img.resize(target, Image.Resampling.BILINEAR)
        t_pil = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        resized_cv = cv2.resize(np_raw, target, interpolation=cv2.INTER_LINEAR)
        t_cv = (time.perf_counter() - t0) * 1000

        print(f"\nTarget {target}: PIL Bilinear={t_pil:.2f}ms | OpenCV Linear={t_cv:.2f}ms")

        # Compression test: PIL JPEG vs OpenCV imencode
        for q in [60, 70, 80]:
            # PIL JPEG
            t0 = time.perf_counter()
            buf = io.BytesIO()
            resized_pil.save(buf, format="JPEG", quality=q)
            pil_bytes = buf.getvalue()
            b64_pil = base64.b64encode(pil_bytes).decode("ascii")
            t_comp_pil = (time.perf_counter() - t0) * 1000

            # OpenCV JPEG
            t0 = time.perf_counter()
            _, cv_encoded = cv2.imencode(".jpg", resized_cv, [int(cv2.IMWRITE_JPEG_QUALITY), q])
            cv_bytes = cv_encoded.tobytes()
            b64_cv = base64.b64encode(cv_bytes).decode("ascii")
            t_comp_cv = (time.perf_counter() - t0) * 1000

            print(f"  Quality {q}: PIL={len(pil_bytes)/1024:.1f}KB ({t_comp_pil:.2f}ms) | OpenCV={len(cv_bytes)/1024:.1f}KB ({t_comp_cv:.2f}ms)")

if __name__ == '__main__':
    benchmark_full_screen()
    benchmark_downscaling_and_compression()
