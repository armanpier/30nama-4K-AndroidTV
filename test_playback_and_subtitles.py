import os
import urllib.request
import json
import time
import subprocess
import sys
sys.stdout.reconfigure(encoding='utf-8')

ADB = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')

def rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        payload['params'] = params
    req = urllib.request.Request('http://127.0.0.1:8080/jsonrpc', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

def capture_screen(name):
    subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/screen.png'])
    dest = f"C:\\Users\\Arman\\.gemini\\antigravity\\brain\\5541959f-8acf-44a5-ab6c-42a6a9fe320f\\{name}.png"
    subprocess.run([ADB, 'pull', '/sdcard/screen.png', dest])
    print(f"Captured screen -> {name}.png")

print("1. Querying stream list for Apocalypse Z (ID 722170)...")
res_4k = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=722170&title=Apocalypse+Z'})
files = res_4k.get('result', {}).get('files', [])
if not files:
    print("No streams found:", res_4k)
    sys.exit(1)

target_item = files[0] # The 4K ULTRA HD release
print("Selected target:", target_item.get('label'))
play_url = target_item.get('file')

print(f"\n2. Calling Player.Open on: {play_url[:90]}...")
open_res = rpc('Player.Open', {'item': {'file': play_url}})
print("Player.Open response:", open_res)

print("\n3. Monitoring playback on emulator for 25 seconds...")
for i in range(12):
    time.sleep(2)
    players = rpc('Player.GetActivePlayers')
    p_list = players.get('result', [])
    print(f"  [T+{i*2}s] Active players: {len(p_list)}")
    if p_list:
        pid = p_list[0].get('playerid')
        props = rpc('Player.GetProperties', {'playerid': pid, 'properties': ['time', 'totaltime', 'speed', 'subtitles', 'currentsubtitle']})
        res_prop = props.get('result', {})
        t = res_prop.get('time', {})
        tot = res_prop.get('totaltime', {})
        spd = res_prop.get('speed')
        subs = res_prop.get('subtitles', [])
        cur_sub = res_prop.get('currentsubtitle', {})
        print(f"    Playback Time: {t.get('hours',0):02d}:{t.get('minutes',0):02d}:{t.get('seconds',0):02d} / {tot.get('hours',0):02d}:{tot.get('minutes',0):02d}:{tot.get('seconds',0):02d} | Speed: {spd}")
        print(f"    Subtitles attached ({len(subs)}): {subs}")
        print(f"    Current Subtitle: {cur_sub}")

capture_screen("kodi_4k_playing_verified")
print("\nPlayback verification finished!")
