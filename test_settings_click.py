import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Tapping Settings button at (1816, 1008)...")
adb("shell input tap 1816 1008")

print("2. Waiting 2 seconds...")
time.sleep(2)

print("3. Taking screenshot...")
adb("shell screencap -p /sdcard/settings_click.png")
adb(r'pull /sdcard/settings_click.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\settings_click.png"')

print("4. Dumping UI...")
adb("shell uiautomator dump /sdcard/dump_settings.xml")
adb("pull /sdcard/dump_settings.xml dump_settings.xml")

try:
    tree = ET.parse("dump_settings.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        f = n.attrib.get("focused")
        b = n.attrib.get("bounds")
        cls = n.attrib.get("class")
        if t or f == "true":
            print(f"{cls} | focused={f} | {repr(t)} | {b}")
except Exception as e:
    print("Error parsing dump:", e)
