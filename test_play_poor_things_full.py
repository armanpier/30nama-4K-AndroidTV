import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Moving focus to Poor Things (DPAD_LEFT)...")
adb("shell input keyevent 21")
time.sleep(0.5)

print("2. Opening Poor Things (DPAD_CENTER)...")
adb("shell input keyevent 23")
time.sleep(3)

print("3. Dumping Details screen UI...")
adb("shell uiautomator dump /sdcard/dump_pt.xml")
adb("pull /sdcard/dump_pt.xml dump_pt.xml")

try:
    tree = ET.parse("dump_pt.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        f = n.attrib.get("focused")
        b = n.attrib.get("bounds")
        c = n.attrib.get("clickable")
        if t or f == "true":
            print(f"focused={f} | clk={c} | {repr(t)} | {b}")
except Exception as e:
    print("Error parsing dump:", e)

adb("shell screencap -p /sdcard/pt_detail.png")
adb(r'pull /sdcard/pt_detail.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\pt_detail.png"')
