import urllib.request
import urllib.parse
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}))
with open('tv_session_token.txt') as f:
    token = f.read().strip()

BASE_URL = 'https://world.hana-api.com/api/v2/action'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

headers = {
    'c-api-key': TV_KEY,
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3',
    'c-token': token
}

for param in ['q', 'search', 'query', 'keyword', 'title']:
    url = f"{BASE_URL}/search?{param}=batman"
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req) as r:
            res = json.loads(r.read().decode())
        success = res.get('success')
        rk = list(res.get('result', {}).keys()) if res.get('result') else None
        print(f"GET with {param}: success={success} | keys={rk}")
    except Exception as e:
        print(f"GET with {param} err: {e}")

headers['Content-Type'] = 'application/x-www-form-urlencoded'
for param in ['q', 'search', 'query', 'keyword', 'title']:
    data = urllib.parse.urlencode({param: 'batman'}).encode()
    req = urllib.request.Request(f"{BASE_URL}/search", data=data, headers=headers)
    try:
        with opener.open(req) as r:
            res = json.loads(r.read().decode())
        success = res.get('success')
        rk = list(res.get('result', {}).keys()) if res.get('result') else None
        print(f"POST with {param}: success={success} | keys={rk}")
    except Exception as e:
        print(f"POST with {param} err: {e}")
