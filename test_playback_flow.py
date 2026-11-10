import subprocess
import time
import xml.etree.ElementTree as ET

ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def run_adb(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout

def dump_ui():
    run_adb("shell uiautomator dump /sdcard/window_dump.xml")
    run_adb("pull /sdcard/window_dump.xml current_screen.xml")
    try:
        tree = ET.parse("current_screen.xml")
        return tree.getroot()
    except Exception as e:
        print("Error parsing UI:", e)
        return None

def find_node_with_text(root, text_sub):
    for node in root.iter():
        t = node.attrib.get('text', '')
        d = node.attrib.get('content-desc', '')
        if text_sub in t or text_sub in d:
            return node
    return None

def get_node_center(node):
    # bounds="[x1,y1][x2,y2]"
    bounds = node.attrib.get('bounds', '')
    import re
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None

def tap(x, y):
    run_adb(f"shell input tap {x} {y}")

def keyevent(code):
    run_adb(f"shell input keyevent {code}")

print("Automation script helper ready.")
