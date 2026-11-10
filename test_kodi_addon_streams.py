import urllib.request
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

def rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        payload['params'] = params
    req = urllib.request.Request('http://127.0.0.1:8080/jsonrpc', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

print("--- 1. Testing Main Menu ---")
res = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/'})
for item in res.get('result', {}).get('files', []):
    print("  Menu:", item.get('label'), "->", item.get('file'))

print("\n--- 2. Testing 4K Movie Stream List: Apocalypse Z (ID 722170) ---")
res_4k = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=722170&title=Apocalypse+Z'})
files = res_4k.get('result', {}).get('files', [])
print(f"Total stream items found: {len(files)}")
for f in files:
    print("  Stream item:", f.get('label'))
    print("    File URL:", f.get('file')[:90] + "...")

print("\n--- 3. Testing Movie Stream List: Sigma (ID 722177) ---")
res_sigma = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=722177&title=Sigma'})
files_s = res_sigma.get('result', {}).get('files', [])
print(f"Total stream items found: {len(files_s)}")
for f in files_s:
    print("  Stream item:", f.get('label'))

print("\n--- 4. Testing Series Stream List: 4 Blocks Zero (ID 721725) ---")
res_series = rpc('Files.GetDirectory', {'directory': 'plugin://plugin.video.30nama/?action=list_streams&id=721725&title=4+Blocks+Zero'})
files_ser = res_series.get('result', {}).get('files', [])
print(f"Total stream items found: {len(files_ser)}")
for f in files_ser[:4]:
    print("  Series item:", f.get('label'))
