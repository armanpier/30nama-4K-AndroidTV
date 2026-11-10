import sys
import time
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Playing Poor Things (DPAD_CENTER on focused play button [804, 55])...")
adb("shell input keyevent 23")
time.sleep(4)

print("2. Opening Video Settings (tap 1816, 1008)...")
adb("shell input tap 1816 1008")
time.sleep(2)

print("3. Capturing screenshot...")
adb("shell screencap -p /sdcard/pt_settings.png")
adb(r'pull /sdcard/pt_settings.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\pt_settings.png"')

print("4. Inspecting View Hierarchy from dumpsys...")
res = subprocess.run([ADB, 'shell', 'dumpsys', 'activity', 'top'], capture_output=True, text=True, errors='replace').stdout
lines = res.splitlines()

inside = False
for l in lines:
    if '#440b280' in l or '#30af' in l:
        inside = True
    if inside:
        if any(k in l for k in ['ReactTextView', '#7ebee37', '#300f', '#2feb', '#2ff5', '#2fff', '#3009', '7935fa4']):
            print(l.strip())
        if 'ViewRoot:' in l or 'Looper' in l:
            break
