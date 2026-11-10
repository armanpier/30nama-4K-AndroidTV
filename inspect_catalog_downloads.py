import urllib.request
import urllib.parse
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
proxy_handler = urllib.request.ProxyHandler(PROXIES)
opener = urllib.request.build_opener(proxy_handler)

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

# 1. Get home movies
req = urllib.request.Request(f'{BASE_URL}/home', headers=headers)
with opener.open(req) as r:
    home_data = json.loads(r.read().decode('utf-8'))

posts = home_data.get('result', {}).get('movies', {}).get('posts', [])[:6]
posts += home_data.get('result', {}).get('new_releases', {}).get('posts', [])[:4]

headers['Content-Type'] = 'application/x-www-form-urlencoded'

for p in posts:
    pid = str(p.get('id'))
    title = p.get('title', {}).get('english') or f"Post {pid}"
    print(f"\n================ Post {pid}: {title} ================")
    
    data_dl = urllib.parse.urlencode({'post_id': pid, 'free_download': 'false'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/download', data=data_dl, headers=headers)
    try:
        with opener.open(req) as r:
            dl_data = json.loads(r.read().decode('utf-8'))
        if not dl_data.get('success'):
            print("  Download not allowed / failed:", dl_data.get('msg'))
            continue
            
        res_dl = dl_data.get('result', {}).get('download', {})
        if isinstance(res_dl, list):
            print(f"  [Movie] Available qualities ({len(res_dl)}):")
            for item in res_dl:
                q = item.get('quality')
                sz = item.get('size')
                res = item.get('resolution')
                dl = item.get('dl') or ''
                is_4k = '2160' in str(res) or '4k' in str(q).lower() or '2160' in str(q).lower()
                tag = '>>> 4K ULTRA HD <<<' if is_4k else ''
                print(f"    - {q} | {res} | {sz} | {item.get('encoder')} {tag}")
                if dl:
                    print(f"      URL: {dl[:85]}...")
        elif isinstance(res_dl, dict):
            print(f"  [Series] Seasons: {list(res_dl.keys())}")
            for s_key, s_items in res_dl.items():
                print(f"    Season {s_key} has {len(s_items)} quality releases")
                for item in s_items[:2]:
                    q = item.get('quality')
                    print(f"      - Quality: {q}, Size: {item.get('size')}")
    except Exception as e:
        print("  Error:", e)
