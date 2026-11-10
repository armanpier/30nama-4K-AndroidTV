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

with open("tv_session_token.txt", "r") as f:
    TV_TOKEN = f.read().strip()

def call_api(action, params=None, api_key=TV_KEY, token=TV_TOKEN):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': api_key,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': 'tv30nama/3.2.3',
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

print("================================================================")
print("1. Verifying /action/user with TV Key and acquired TV Token")
print("================================================================")
res_user = call_api('user', api_key=TV_KEY)
print("User success:", res_user.get('success'))
if res_user.get('success'):
    user = res_user.get('result', {}).get('user', {})
    print(f"  User ID: {user.get('id')}")
    print(f"  Username: {user.get('username')}")
    print(f"  Email: {user.get('email')}")
    print(f"  Plan: {user.get('plan', {}).get('title')}")
    print(f"  Expire Date: {user.get('expire_date')}")
else:
    print("User response:", res_user)

print("\n================================================================")
print("2. Verifying /action/stream for Post 721725 (Poor Things) with DESKTOP KEY (4K)")
print("================================================================")
res_stream = call_api('stream', {'post_id': '721725', 'free_stream': 'false'}, api_key=DESKTOP_KEY)
print("Stream success:", res_stream.get('success'))
if res_stream.get('success'):
    medias = res_stream.get('result', {}).get('medias', [])
    print(f"Total media profiles: {len(medias)}")
    for m in medias:
        print(f"  Quality: {m.get('quality')}, Label: {m.get('label')}")
        f = m.get('file', {})
        print(f"    URL: {(f.get('m3u8') or f.get('url'))[:80]}...")
else:
    print("Stream response with Desktop key:", res_stream)
    print("Trying with TV Key...")
    res_stream_tv = call_api('stream', {'post_id': '721725', 'free_stream': 'false'}, api_key=TV_KEY)
    print("Stream success with TV key:", res_stream_tv.get('success'))
    if res_stream_tv.get('success'):
        for m in res_stream_tv.get('result', {}).get('medias', []):
            print(f"  Quality: {m.get('quality')}, Label: {m.get('label')}")

print("\n================================================================")
print("3. Verifying /action/download for Post 721725 (Direct 4K MKV / MP4)")
print("================================================================")
res_dl = call_api('download', {'post_id': '721725', 'free_download': 'false'}, api_key=DESKTOP_KEY)
print("Download success with Desktop key:", res_dl.get('success'))
if not res_dl.get('success'):
    res_dl = call_api('download', {'post_id': '721725', 'free_download': 'false'}, api_key=TV_KEY)
    print("Download success with TV key:", res_dl.get('success'))

if res_dl.get('success'):
    result = res_dl.get('result', {})
    print("Download result keys:", list(result.keys()) if isinstance(result, dict) else type(result))
    with open("download_api_result.json", "w", encoding="utf-8") as f:
        json.dump(res_dl, f, indent=2, ensure_ascii=False)
    print("Saved download_api_result.json!")
else:
    print("Download response:", res_dl)
