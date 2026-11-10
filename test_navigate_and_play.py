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

print("2. Sending DPAD_CENTER (keyevent 23) to focused item...")
adb("shell input keyevent 23")

print("3. Waiting 3 seconds...")
time.sleep(3)

print("4. Capturing screenshot...")
adb("shell screencap -p /sdcard/after_click.png")
adb(r'pull /sdcard/after_click.png "C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\after_click.png"')

print("5. Dumping UI...")
adb("shell uiautomator dump /sdcard/dump_after.xml")
adb("pull /sdcard/dump_after.xml dump_after.xml")

try:
    tree = ET.parse("dump_after.xml")
    nodes = []
    for n in tree.iter("node"):
        t = n.attrib.get("text") or n.attrib.get("content-desc")
        f = n.attrib.get("focused")
        b = n.attrib.get("bounds")
        cls = n.attrib.get("class")
        resid = n.attrib.get("resource-id")
        if f == "true" or t or (resid and "jw" in resid):
            nodes.append(f"{cls} | focused={f} | text={repr(t)} | {b} | res={resid}")
    print(f"Total relevant nodes: {len(nodes)}")
    for node in nodes[:30]:
        print(node)
except Exception as e:
    print("Error parsing dump:", e)

print("\n6. Checking logcat for network requests...")
res = subprocess.run(f'"{ADB}" logcat -d', shell=True, capture_output=True, text=True, errors='replace').stdout
lines = [l for l in res.splitlines() if any(k in l.lower() for k in ['stream', 'action', 'hana-api', '30nama', 'okhttp', 'c-api-key', 'c-token', 'jwplayer', 'exoplayer'])]
print(f"Total matching lines: {len(lines)}")
for l in lines[-30:]:
    print(l)
