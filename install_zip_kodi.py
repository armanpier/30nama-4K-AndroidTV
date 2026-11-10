import urllib.request
import json
import time

def call(method, params=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        payload['params'] = params
    req = urllib.request.Request('http://127.0.0.1:8080/jsonrpc', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.loads(r.read().decode('utf-8'))

# Open addon browser
call('GUI.ActivateWindow', {'window': 'addonbrowser'})
time.sleep(1)

# Navigate down to "Install from zip file"
for _ in range(5):
    res = call('GUI.GetProperties', {'properties': ['currentcontrol']})
    lbl = res.get('result', {}).get('currentcontrol', {}).get('label', '')
    if 'zip' in lbl.lower():
        break
    call('Input.Down')
    time.sleep(0.2)

call('Input.Select')
time.sleep(1)

# Inside File browser, find External storage
for _ in range(5):
    res = call('GUI.GetProperties', {'properties': ['currentcontrol']})
    lbl = res.get('result', {}).get('currentcontrol', {}).get('label', '')
    if 'external' in lbl.lower():
        break
    call('Input.Down')
    time.sleep(0.2)

call('Input.Select')
time.sleep(0.5)

# Find Download
for _ in range(10):
    res = call('GUI.GetProperties', {'properties': ['currentcontrol']})
    lbl = res.get('result', {}).get('currentcontrol', {}).get('label', '')
    if 'download' in lbl.lower():
        break
    call('Input.Down')
    time.sleep(0.2)

call('Input.Select')
time.sleep(0.5)

# Find plugin.video.30nama.zip
for _ in range(5):
    res = call('GUI.GetProperties', {'properties': ['currentcontrol']})
    lbl = res.get('result', {}).get('currentcontrol', {}).get('label', '')
    if '30nama' in lbl.lower():
        break
    call('Input.Down')
    time.sleep(0.2)

print("Selecting zip file to update...")
call('Input.Select')
time.sleep(3)

print("Check addon update status:")
res = call('Addons.GetAddons', {'properties': ['name', 'enabled', 'version']})
for a in res.get('result', {}).get('addons', []):
    if '30nama' in a.get('addonid', '').lower():
        print("Updated Addon:", a)
