import urllib.request
import urllib.parse
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
proxy_handler = urllib.request.ProxyHandler(PROXIES)
opener = urllib.request.build_opener(proxy_handler)

BASE_URL = 'https://world.hana-api.com/api/v2/action'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'
DESKTOP_KEY = 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ'
USER_TOKEN = '7de0b48a8c8ed59d926d33fccf136348ca3e1518'

def call_api(action, params=None, api_key=DESKTOP_KEY, token=USER_TOKEN, ua='tv30nama/3.2.3'):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': api_key,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': ua,
        'c-token': token,
        'Authorization': f"Bearer {token}"
    }
    encoded = urllib.parse.urlencode(params or {}).encode('utf-8')
    url = f"{BASE_URL}/{action}"
    req = urllib.request.Request(url, data=encoded, headers=headers)
    try:
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'exception': str(e)}

print("--- 1. Testing /action/user with Desktop Key ---")
res_user = call_api('user', api_key=DESKTOP_KEY)
print("User response:", json.dumps(res_user, ensure_ascii=False, indent=2)[:500])

print("\n--- 2. Testing /action/user with TV Key ---")
res_user_tv = call_api('user', api_key=TV_KEY)
print("User TV response:", json.dumps(res_user_tv, ensure_ascii=False, indent=2)[:500])

print("\n--- 3. Testing /action/stream for Post 721725 (Poor Things) with Desktop Key ---")
res_stream = call_api('stream', {'post_id': '721725', 'free_stream': 'false'}, api_key=DESKTOP_KEY)
print("Stream success:", res_stream.get('success'))
if res_stream.get('success'):
    medias = res_stream.get('result', {}).get('medias', [])
    print(f"Total media profiles: {len(medias)}")
    for m in medias:
        print(f"  Quality: {m.get('quality')}, Label: {m.get('label')}")
else:
    print("Stream msg:", res_stream.get('msg'), res_stream)

print("\n--- 4. Testing /action/download for Post 721725 with Desktop Key ---")
res_dl = call_api('download', {'post_id': '721725', 'free_download': 'false'}, api_key=DESKTOP_KEY)
print("Download success:", res_dl.get('success'))
if res_dl.get('success'):
    result = res_dl.get('result', {})
    print("Download result keys:", list(result.keys()) if isinstance(result, dict) else type(result))
    if isinstance(result, list):
        print(f"Total download items: {len(result)}")
        for item in result[:3]:
            print(f"  Quality: {item.get('quality')}, Size: {item.get('size')}, Link: {item.get('link')[:60]}...")
    elif isinstance(result, dict):
        for k, v in list(result.items())[:3]:
            print(f"  {k}: {str(v)[:100]}")
else:
    print("Download msg:", res_dl.get('msg'), res_dl)
