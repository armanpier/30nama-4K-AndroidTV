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
try:
    res = urllib.request.urlopen(req, timeout=10)
    data = json.loads(res.read().decode('utf-8'))
    print('Home success:', data.get('success'))
    raw = json.dumps(data)
    print('Occurrences of free_stream:', raw.count('free_stream'))
    # search for items where free_stream is truthy
    def scan(obj):
        if isinstance(obj, dict):
            if obj.get('options', {}).get('free_stream'):
                print('Found free stream item:', obj.get('id'), obj.get('title'))
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
    scan(data)
except Exception as e:
    print('Error:', e)
