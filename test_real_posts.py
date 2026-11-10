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
DESKTOP_KEY = 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ'

for pid in ['722177', '689848']:
    print(f"\n================ Post {pid} ================")
    
    # 1. Stream with TV key
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': TV_KEY,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': 'tv30nama/3.2.3',
        'c-token': token
    }
    data = urllib.parse.urlencode({'post_id': pid, 'free_stream': 'false'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/stream', data=data, headers=headers)
    with opener.open(req) as r:
        s_data = json.loads(r.read().decode('utf-8'))
    print('Stream (TV Key) success:', s_data.get('success'), 'msg:', s_data.get('msg'))
    if s_data.get('success'):
        for m in s_data.get('result', {}).get('medias', []):
            print('  Stream:', m.get('quality'), m.get('label'))
            
    # 2. Stream with Desktop key (4K!)
    headers['c-api-key'] = DESKTOP_KEY
    req = urllib.request.Request(f'{BASE_URL}/stream', data=data, headers=headers)
    with opener.open(req) as r:
        s_desk = json.loads(r.read().decode('utf-8'))
    print('Stream (Desktop Key) success:', s_desk.get('success'), 'msg:', s_desk.get('msg'))
    if s_desk.get('success'):
        for m in s_desk.get('result', {}).get('medias', []):
            print('  4K Stream:', m.get('quality'), m.get('label'))
            
    # 3. Download
    headers['c-api-key'] = TV_KEY
    data_dl = urllib.parse.urlencode({'post_id': pid, 'free_download': 'false'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/download', data=data_dl, headers=headers)
    with opener.open(req) as r:
        dl_data = json.loads(r.read().decode('utf-8'))
    print('Download success:', dl_data.get('success'))
    if dl_data.get('success'):
        dl_res = dl_data.get('result', {}).get('download', {})
        print('  Download categories:', list(dl_res.keys()))
        for cat, items in dl_res.items():
            for item in items[:2]:
                q = item.get('quality')
                sz = item.get('size')
                print(f"    [{cat}] Quality: {q}, Size: {sz}")
                links = item.get('link', [])
                if links:
                    dl_url = links[0].get('dl')
                    print(f"      Link: {dl_url[:80]}...")
