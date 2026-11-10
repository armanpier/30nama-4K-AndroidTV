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

def dump_ui():
    run_adb("shell uiautomator dump /sdcard/dump.xml")
    run_adb("pull /sdcard/dump.xml dump.xml")
    try:
        tree = ET.parse("dump.xml")
        texts = []
        for n in tree.iter("node"):
            t = n.attrib.get("text") or n.attrib.get("content-desc")
            if t:
                texts.append(t)
        return texts
    except Exception as e:
        return []

def capture_screen(filename):
    run_adb(f"exec-out screencap -p > {filename}")

print("Monitoring login state...")
while True:
    texts = dump_ui()
    is_qr_screen = any("auth/" in t for t in texts)
    if not is_qr_screen:
        print("[SUCCESS] Transition detected! User is logged in!")
        capture_screen(r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\logged_in_home.png")
        print("Screen texts:", texts[:10])
        break
    time.sleep(2)
