import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Clearing logcat...")
adb("logcat -c")

print("2. Pressing DPAD_CENTER (keyevent 23)...")
adb("shell input keyevent 23")

print("3. Waiting 4 seconds...")
time.sleep(4)

print("4. Taking screenshot...")
adb("shell screencap -p /sdcard/play_action.png")
adb(r'pull /sdcard/play_action.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\play_action.png"')

print("5. Dumping UI...")
adb("shell uiautomator dump /sdcard/dump_play.xml")
adb("pull /sdcard/dump_play.xml dump_play.xml")

try:
    tree = ET.parse("dump_play.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        resid = n.attrib.get("resource-id")
        cls = n.attrib.get("class")
        b = n.attrib.get("bounds")
        if t or (resid and ("jw" in resid or "player" in resid.lower())):
            print(f"{cls} | {t} | {b} | res={resid}")
except Exception as e:
    print("Error parsing dump:", e)

print("\n6. Checking logcat...")
res = subprocess.run(f'"{ADB}" logcat -d', shell=True, capture_output=True, text=True, errors='replace').stdout
lines = [l for l in res.splitlines() if any(k in l.lower() for k in ['stream', 'action', 'hana-api', '30nama', 'okhttp', 'network', 'c-api-key', 'c-token', 'jwplayer', 'exoplayer', 'error'])]
print(f"Total matching lines: {len(lines)}")
for l in lines[-40:]:
    print(l)

with open('play_action_logcat.txt', 'w', encoding='utf-8') as f:
    f.write(res)
