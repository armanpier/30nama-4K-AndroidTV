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

def get_focused():
    run_adb("shell uiautomator dump /sdcard/dump.xml")
    run_adb("pull /sdcard/dump.xml dump.xml")
    try:
        tree = ET.parse("dump.xml")
        for n in tree.iter("node"):
            if n.attrib.get("focused") == "true":
                t = n.attrib.get("text") or n.attrib.get("content-desc")
                b = n.attrib.get("bounds")
                return t, b
    except:
        pass
    return None, None

print("Initial focused:", get_focused())

for key, name in [(20, "DOWN"), (20, "DOWN"), (21, "LEFT"), (22, "RIGHT"), (19, "UP")]:
    run_adb(f"shell input keyevent {key}")
    time.sleep(0.5)
    print(f"After {name}:", get_focused())
