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

# Check if player is still active
players = rpc('Player.GetActivePlayers').get('result', [])
if not players:
    print("Player stopped, restarting playback...")
    res_4k = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=722170&title=Apocalypse+Z'})
    files = res_4k.get('result', {}).get('files', [])
    rpc('Player.Open', {'item': {'file': files[0]['file']}})
    time.sleep(3)

# Bring up Kodi OSD
print("Showing Kodi Player OSD...")
rpc('Input.ShowOSD')
time.sleep(0.5)

# Capture screen
subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/osd_screen.png'])
dest = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\kodi_osd_playback_verified.png"
subprocess.run([ADB, 'pull', '/sdcard/osd_screen.png', dest])
print("Pulled kodi_osd_playback_verified.png!")

# Get current properties
players = rpc('Player.GetActivePlayers').get('result', [])
if players:
    pid = players[0]['playerid']
    props = rpc('Player.GetProperties', {'playerid': pid, 'properties': ['time', 'totaltime', 'speed', 'subtitles', 'currentsubtitle']})
    print("Player props:", json.dumps(props.get('result', {}), indent=2))
