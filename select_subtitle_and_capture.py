import urllib.request
import json
import time
import subprocess
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

ADB = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')

def rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        payload['params'] = params
    req = urllib.request.Request('http://127.0.0.1:8080/jsonrpc', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

players = rpc('Player.GetActivePlayers').get('result', [])
if players:
    pid = players[0]['playerid']
    # Turn subtitles on
    print("Enabling subtitle display...")
    res = rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': 'on'})
    print("SetSubtitle 'on' result:", res)
    
    # Select subtitle index 0 (the external subtitle fetched from SubSource)
    res_idx = rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': 0})
    print("SetSubtitle index 0 result:", res_idx)
    
    time.sleep(2)
    # Check current subtitle
    props = rpc('Player.GetProperties', {'playerid': pid, 'properties': ['currentsubtitle', 'subtitleenabled']})
    print("Subtitle properties:", json.dumps(props.get('result', {}), indent=2))
    
    # Hide OSD if open so subtitles are visible clearly
    subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/sub_screen.png'])
    dest = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\kodi_subtitles_verified.png"
    subprocess.run([ADB, 'pull', '/sdcard/sub_screen.png', dest])
    print("Pulled kodi_subtitles_verified.png!")
