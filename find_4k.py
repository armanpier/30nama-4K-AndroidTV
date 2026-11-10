import urllib.request
import urllib.parse
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXIES))

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

req = urllib.request.Request(f'{BASE_URL}/home', headers=headers)
with opener.open(req) as r:
    home_data = json.loads(r.read().decode('utf-8'))

all_posts = []
res = home_data.get('result', {})
for k in ['new_releases', 'suggested', 'top_10', 'movies']:
    for p in res.get(k, {}).get('posts', []):
        all_posts.append(p)

print(f"Total posts collected from home: {len(all_posts)}")
headers['Content-Type'] = 'application/x-www-form-urlencoded'

found_4k = []
for p in all_posts:
    pid = str(p.get('id'))
    title = p.get('title', {}).get('english') or f"Post {pid}"
    data_dl = urllib.parse.urlencode({'post_id': pid, 'free_download': 'false'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/download', data=data_dl, headers=headers)
    try:
        with opener.open(req) as r:
            dl_data = json.loads(r.read().decode('utf-8'))
        res_dl = dl_data.get('result', {}).get('download', {})
        if isinstance(res_dl, list):
            for item in res_dl:
                q = str(item.get('quality') or '')
                res_str = str(item.get('resolution') or '')
                if '2160' in res_str or '4k' in q.lower() or '2160' in q.lower() or 'remux' in q.lower():
                    dl_url = item.get('dl')
                    print(f"MATCH: {title} (ID {pid}) -> {q} ({res_str}) {item.get('size')}")
                    print(f"  DL: {dl_url[:80]}...")
                    found_4k.append((title, pid, q, res_str, item.get('size'), dl_url))
        elif isinstance(res_dl, dict):
            for s_key, s_items in res_dl.items():
                for item in s_items:
                    q = str(item.get('quality') or '')
                    if '2160' in q.lower() or '4k' in q.lower():
                        print(f"MATCH (Series): {title} (ID {pid}) Season {s_key} -> {q}")
    except Exception as e:
        pass

print(f"\nDone! Found {len(found_4k)} 4K releases!")
