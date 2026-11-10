import urllib.request
import json
import time
import subprocess
import os

ADB = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')

def rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params: payload['params'] = params
    req = urllib.request.Request('http://127.0.0.1:8080/jsonrpc', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r: return json.loads(r.read().decode('utf-8'))

# Open main menu
rpc('GUI.ActivateWindow', {'window': 'videos', 'parameters': ['plugin://plugin.video.30nama/']})
time.sleep(2)

subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/sleek_main_menu.png'])
dest = r'C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\sleek_main_menu.png'
subprocess.run([ADB, 'pull', '/sdcard/sleek_main_menu.png', dest])
print('Captured sleek_main_menu.png!')

# Open New Releases section to see movie cards wall
rpc('GUI.ActivateWindow', {'window': 'videos', 'parameters': ['plugin://plugin.video.30nama/?action=browse_section&section=new_releases']})
time.sleep(3)

subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/sleek_section_cards.png'])
dest2 = r'C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\sleek_section_cards.png'
subprocess.run([ADB, 'pull', '/sdcard/sleek_section_cards.png', dest2])
print('Captured sleek_section_cards.png!')
