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

print("2. Clicking Play (DPAD_CENTER on focused play button)...")
run_adb("shell input keyevent 23")
time.sleep(4)

print("3. Pulling screenshot...")
run_adb("shell screencap -p /sdcard/s.png")
run_adb(r"pull /sdcard/s.png C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\stream_playback.png")

print("4. Dumping UI...")
run_adb("shell uiautomator dump /sdcard/dump.xml")
run_adb("pull /sdcard/dump.xml dump.xml")

tree = ET.parse("dump.xml")
for n in tree.iter("node"):
    t = n.attrib.get("text") or n.attrib.get("content-desc")
    resid = n.attrib.get("resource-id")
    b = n.attrib.get("bounds")
    if t or (resid and "jw" in resid):
        print(f"{t} | {b} | {resid}")

print("\n5. Searching logcat for network / stream calls...")
res = subprocess.run(f'"{ADB}" logcat -d', shell=True, capture_output=True, text=True, errors='replace')
lines = [l for l in res.stdout.splitlines() if any(k in l.lower() for k in ['stream', 'hana-api', '30nama', 'et7brh', 'vdapnk', 'exoplayer', 'jwplayer'])]
print(f"Found {len(lines)} log lines:")
for l in lines[-30:]:
    print(l)
