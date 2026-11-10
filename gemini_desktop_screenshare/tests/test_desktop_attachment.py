"""
Empirical test for desktop attachment and win32ui vs ctypes GDI interaction.
Matrix of tests:
Case 1: Pure ctypes GDI / no win32ui:
   - Call OpenInputDesktop -> SetThreadDesktop
   - Test if SetThreadDesktop succeeds or fails (and GetLastError).
   - Test if mss.MSS() and PIL.ImageGrab.grab() work after SetThreadDesktop.
Case 2: Import win32ui BEFORE SetThreadDesktop:
   - In a fresh process, import win32ui first, then call OpenInputDesktop -> SetThreadDesktop.
   - Record exact return value and GetLastError().
Case 3: Import win32ui AFTER SetThreadDesktop:
   - In a fresh process, call SetThreadDesktop first, then import win32ui and use it.
Case 4: win32ui imported in main thread, but SetThreadDesktop called in a dedicated worker thread.
   - Does a worker thread escape ERROR_BUSY?
"""

import subprocess
import sys
import json

def run_isolated_code(code_str):
    cmd = [sys.executable, "-c", code_str]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
        "exit_code": res.returncode
    }

def main():
    print("Testing Case 1: Pure ctypes SetThreadDesktop and subsequent mss / PIL capture...")
    code_case1 = """
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

DESKTOP_ALL = 0x01FF
h_input = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
err_open = kernel32.GetLastError() if not h_input else 0

set_ok = user32.SetThreadDesktop(h_input)
err_set = kernel32.GetLastError() if not set_ok else 0

print(f"OpenInputDesktop: handle={h_input}, err={err_open}")
print(f"SetThreadDesktop: ok={set_ok}, err={err_set}")

# Now test mss and PIL
import mss
mss_ok = False
mss_err = None
try:
    with mss.MSS() as sct:
        img = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
        mss_ok = (img.width > 0 and img.height > 0)
except Exception as e:
    mss_err = str(e)

from PIL import ImageGrab
pil_ok = False
pil_err = None
try:
    pimg = ImageGrab.grab()
    pil_ok = (pimg.width > 0 and pimg.height > 0)
except Exception as e:
    pil_err = str(e)

print(f"mss_result: ok={mss_ok}, err={mss_err}")
print(f"pil_result: ok={pil_ok}, err={pil_err}")
"""
    res1 = run_isolated_code(code_case1)
    print("Result Case 1:")
    print("STDOUT:", res1["stdout"])
    print("STDERR:", res1["stderr"])

    print("\nTesting Case 2: import win32ui BEFORE SetThreadDesktop...")
    code_case2 = """
import win32ui # Imported BEFORE SetThreadDesktop
import ctypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

h_input = user32.OpenInputDesktop(0, False, 0x01FF)
set_ok = user32.SetThreadDesktop(h_input)
err_set = kernel32.GetLastError() if not set_ok else 0

print(f"SetThreadDesktop after import win32ui: ok={set_ok}, err={err_set}")
"""
    res2 = run_isolated_code(code_case2)
    print("Result Case 2:")
    print("STDOUT:", res2["stdout"])
    print("STDERR:", res2["stderr"])

    print("\nTesting Case 3: SetThreadDesktop BEFORE import win32ui...")
    code_case3 = """
import ctypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

h_input = user32.OpenInputDesktop(0, False, 0x01FF)
set_ok = user32.SetThreadDesktop(h_input)
err_set = kernel32.GetLastError() if not set_ok else 0

print(f"SetThreadDesktop before import win32ui: ok={set_ok}, err={err_set}")

# Now import win32ui
try:
    import win32ui
    import win32gui
    mfc_dc = win32ui.CreateDCFromHandle(user32.GetDC(0))
    print("win32ui import and usage succeeded!")
except Exception as e:
    print(f"win32ui failed: {e}")
"""
    res3 = run_isolated_code(code_case3)
    print("Result Case 3:")
    print("STDOUT:", res3["stdout"])
    print("STDERR:", res3["stderr"])

    print("\nTesting Case 4: win32ui in main thread, SetThreadDesktop in dedicated worker thread...")
    code_case4 = """
import win32ui
import threading
import ctypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

worker_result = {}

def worker():
    h_input = user32.OpenInputDesktop(0, False, 0x01FF)
    set_ok = user32.SetThreadDesktop(h_input)
    err_set = kernel32.GetLastError() if not set_ok else 0
    worker_result["ok"] = set_ok
    worker_result["err"] = err_set
    
    # Also test mss in worker thread
    import mss
    try:
        with mss.MSS() as sct:
            img = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
            worker_result["mss_ok"] = (img.width > 0)
    except Exception as e:
        worker_result["mss_ok"] = False
        worker_result["mss_err"] = str(e)

t = threading.Thread(target=worker)
t.start()
t.join()

print(f"Worker thread result: {worker_result}")
"""
    res4 = run_isolated_code(code_case4)
    print("Result Case 4:")
    print("STDOUT:", res4["stdout"])
    print("STDERR:", res4["stderr"])

if __name__ == "__main__":
    main()
