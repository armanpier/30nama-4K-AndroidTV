import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def run_adb(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

print("1. Clearing logcat...")
run_adb("logcat -c")

print("2. Launching playback of Spider-Noir (DPAD_CENTER)...")
run_adb("shell input keyevent 23")

print("3. Waiting 4 seconds for playback initialization...")
time.sleep(4)

print("4. Capturing screenshot...")
run_adb("shell screencap -p /sdcard/s.png")
run_adb(r"pull /sdcard/s.png C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\spider_noir_playing.png")

print("5. Dumping UI...")
run_adb("shell uiautomator dump /sdcard/dump.xml")
run_adb("pull /sdcard/dump.xml dump.xml")

try:
    tree = ET.parse("dump.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        resid = n.attrib.get("resource-id")
        b = n.attrib.get("bounds")
        if t or (resid and "jw" in resid):
            print(f"{t} | {b} | {resid}")
except Exception as e:
    print("Error parsing dump:", e)

print("\n6. Inspecting logcat...")
res = subprocess.run(f'"{ADB}" logcat -d', shell=True, capture_output=True, text=True, errors='replace')
lines = [l for l in res.stdout.splitlines() if any(k in l.lower() for k in ['stream', 'jwplayer', 'exoplayer', 'hana-api', '30nama', 'medias', 'error', 'failed', 'quality'])]
print(f"Total matching log lines: {len(lines)}")
for l in lines[-35:]:
    print(l)

with open('spider_noir_logs.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
