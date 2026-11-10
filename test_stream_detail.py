import urllib.request
import urllib.parse
import ssl
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

proxy_handler = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'})
opener = urllib.request.build_opener(proxy_handler)

url = 'https://world.hana-api.com/api/v2/action/stream'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

payload = {'post_id': '721725', 'free_stream': 'false'}
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'c-api-key': TV_KEY,
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}

encoded = urllib.parse.urlencode(payload).encode('utf-8')
req = urllib.request.Request(url, data=encoded, headers=headers)

try:
    with opener.open(req, timeout=10) as r:
        res = json.loads(r.read().decode('utf-8'))
        print("Success:", res.get('success'))
        print("Msg:", repr(res.get('msg')))
        result = res.get('result', {})
        print("Result keys:", list(result.keys()))
        medias = result.get('medias', [])
        print(f"Total medias: {len(medias)}")
        for m in medias:
            print(f"  Quality: {m.get('quality')}, label: {m.get('label')}")
            files = m.get('file', {})
            print(f"    File keys: {list(files.keys())}")
        subtitles = result.get('subtitles', [])
        print("Subtitles:", subtitles)
except Exception as e:
    print("Error:", e)
