import urllib.request, json

url = 'https://world.hana-api.com/api/v2/action/home'
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'c-api-key': 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX',
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}

req = urllib.request.Request(url, data=b'', headers=headers)
res = urllib.request.urlopen(req, timeout=10)
data = json.loads(res.read().decode('utf-8'))

def scan(obj):
    if isinstance(obj, dict):
        if 'free_stream' in obj:
            print('Key free_stream:', obj['free_stream'], 'title:', obj.get('title') or obj.get('name') or obj.get('id'))
        for v in obj.values():
            scan(v)
    elif isinstance(obj, list):
        for v in obj:
            scan(v)

scan(data)
