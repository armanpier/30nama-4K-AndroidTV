import urllib.request
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
proxy_handler = urllib.request.ProxyHandler(PROXIES)
opener = urllib.request.build_opener(proxy_handler)

url = 'https://world.hana-api.com/api/v2/action/movies'
headers = {
    'c-api-key': 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX',
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}
req = urllib.request.Request(url, headers=headers)
with opener.open(req) as r:
    data = json.loads(r.read().decode('utf-8'))

for item in data.get('result', {}).get('movies', [])[:10]:
    mid = item.get('id')
    t_fa = item.get('title_fa')
    t_en = item.get('title_en')
    y = item.get('year')
    print(f"ID: {mid} | Title: {t_fa} ({t_en}) | Year: {y}")
