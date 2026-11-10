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

print("1. Navigating to Poor Things...")
run_adb("shell input keyevent 20") # DOWN
time.sleep(0.3)
run_adb("shell input keyevent 20") # DOWN
time.sleep(0.3)
run_adb("shell input keyevent 21") # LEFT
time.sleep(0.3)

print("2. Clicking Poor Things (DPAD_CENTER)...")
run_adb("shell input keyevent 23")
time.sleep(3)

print("3. Pulling screenshot...")
run_adb("shell screencap -p /sdcard/s.png")
run_adb(r"pull /sdcard/s.png C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\poor_things_detail.png")

print("4. Dumping UI...")
run_adb("shell uiautomator dump /sdcard/dump.xml")
run_adb("pull /sdcard/dump.xml dump.xml")

tree = ET.parse("dump.xml")
texts = []
for n in tree.iter("node"):
    t = n.attrib.get("text") or n.attrib.get("content-desc")
    f = n.attrib.get("focused")
    b = n.attrib.get("bounds")
    if t:
        print(f"focused={f} | {t} | {b}")
