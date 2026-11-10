import sys
import time
import subprocess
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    return subprocess.run(f'"{ADB}" {cmd}', shell=True, capture_output=True, text=True, errors='replace').stdout.strip()

print("1. Sending KEYCODE_MEDIA_PAUSE (127)...")
adb("shell input keyevent 127")
time.sleep(1)

print("2. Trying uiautomator dump...")
out = adb("shell uiautomator dump /sdcard/dump_paused.xml")
print("Dump output:", out)

if "dumped to" in out:
    adb("pull /sdcard/dump_paused.xml dump_paused.xml")
    tree = ET.parse("dump_paused.xml")
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        f = n.attrib.get("focused")
        b = n.attrib.get("bounds")
        cls = n.attrib.get("class")
        if t:
            print(f"{cls} | focused={f} | text={repr(t)} | {b}")
else:
    print("Trying media play/pause keyevent 85...")
    adb("shell input keyevent 85")
    time.sleep(1)
    out2 = adb("shell uiautomator dump /sdcard/dump_paused.xml")
    print("Dump output 2:", out2)
    if "dumped to" in out2:
        adb("pull /sdcard/dump_paused.xml dump_paused.xml")
        tree = ET.parse("dump_paused.xml")
        for n in tree.iter("node"):
            t = n.attrib.get("text") or n.attrib.get("content-desc")
            f = n.attrib.get("focused")
            b = n.attrib.get("bounds")
            cls = n.attrib.get("class")
            if t:
                print(f"{cls} | focused={f} | text={repr(t)} | {b}")
