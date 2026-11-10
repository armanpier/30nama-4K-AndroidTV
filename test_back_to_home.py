import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Pressing BACK twice to return to Home screen...")
adb("shell input keyevent 4")
time.sleep(1)
adb("shell input keyevent 4")
time.sleep(2)

print("2. Taking screenshot of Home...")
adb("shell screencap -p /sdcard/home_back.png")
adb(r'pull /sdcard/home_back.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\home_back.png"')

print("3. Dumping UI...")
adb("shell uiautomator dump /sdcard/dump_hb.xml")
adb("pull /sdcard/dump_hb.xml dump_hb.xml")

try:
    tree = ET.parse("dump_hb.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        f = n.attrib.get("focused")
        b = n.attrib.get("bounds")
        if t or f == "true":
            print(f"focused={f} | {repr(t)} | {b}")
except Exception as e:
    print("Error parsing dump:", e)
