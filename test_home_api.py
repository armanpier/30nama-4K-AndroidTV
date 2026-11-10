import urllib.request
import ssl
import json

proxy_handler = urllib.request.ProxyHandler({
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808'
})
opener = urllib.request.build_opener(proxy_handler)

url = 'https://world.hana-api.com/api/v2/action/home'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

headers = {
    'c-api-key': TV_KEY,
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}

req = urllib.request.Request(url, headers=headers)
try:
    with opener.open(req, timeout=10) as r:
        raw = r.read().decode('utf-8')
        data = json.loads(raw)
        print("Success:", data.get('success'))
        print("Keys in result:", list(data.get('result', {}).keys()))
        rows = data.get('result', {}).get('rows') or []
        print(f"Total rows in home: {len(rows)}")
        for row in rows[:3]:
            print("Row title:", row.get('title'), f"items: {len(row.get('items', []))}")
            if row.get('items'):
                first = row.get('items')[0]
                print("   First item:", first.get('title'), "id:", first.get('id'), "imdb:", first.get('imdb'))
except Exception as e:
    print("Error:", e)
