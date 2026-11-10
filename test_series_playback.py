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

print("1. Opening Series: 4 Blocks Zero S01E01...")
res_series = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=721725&title=4+Blocks+Zero'})
files = res_series.get('result', {}).get('files', [])
if files:
    ep1 = files[0]
    print("Playing:", ep1.get('label'))
    rpc('Player.Open', {'item': {'file': ep1.get('file')}})
    time.sleep(5)
    
    players = rpc('Player.GetActivePlayers').get('result', [])
    if players:
        pid = players[0]['playerid']
        rpc('Input.ShowOSD')
        time.sleep(1)
        subprocess.run([ADB, 'shell', 'screencap', '-p', '/sdcard/series_screen.png'])
        dest = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\kodi_series_playback_verified.png"
        subprocess.run([ADB, 'pull', '/sdcard/series_screen.png', dest])
        print("Pulled kodi_series_playback_verified.png!")
        
        props = rpc('Player.GetProperties', {'playerid': pid, 'properties': ['time', 'totaltime', 'speed', 'subtitles']})
        print("Series playback props:", json.dumps(props.get('result', {}), indent=2))
