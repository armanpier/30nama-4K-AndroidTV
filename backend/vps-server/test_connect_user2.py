import urllib.request, json

req = urllib.request.Request(
    'https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/api/v1/connect',
    method='POST',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'pin': '36329986', 'deviceId': '340f058cd4f7278f'}).encode()
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode()
        print('Status:', r.status)
        print('Raw response (first 500 chars):', raw[:500])
except urllib.error.HTTPError as e:
    print('HTTPError:', e.code, e.read().decode())
except Exception as e:
    print('Error:', e)
