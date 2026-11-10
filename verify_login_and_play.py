import time
import subprocess
import xml.etree.ElementTree as ET

ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def adb(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def dump_ui():
    adb("shell uiautomator dump /sdcard/window_dump.xml")
    adb("pull /sdcard/window_dump.xml ./current_dump.xml")
    try:
        tree = ET.parse("current_dump.xml")
        nodes = []
        for n in tree.iter("node"):
            t = n.attrib.get("text", "")
            d = n.attrib.get("content-desc", "")
            b = n.attrib.get("bounds", "")
            f = n.attrib.get("focused", "")
            c = n.attrib.get("class", "")
            if t or d:
                nodes.append((b, f, c, t, d))
        return nodes
    except Exception as e:
        print("Dump error:", e)
        return []

def is_logged_in():
    nodes = dump_ui()
    for b, f, c, t, d in nodes:
        if "auth/" in t:
            return False, t
    return True, None

if __name__ == "__main__":
    logged_in, url = is_logged_in()
    print("Logged in:", logged_in, "Current URL:", url)
