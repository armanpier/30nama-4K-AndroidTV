import urllib.request
import urllib.error
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://world.hana-api.com/api/v2/action/login'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

payloads = [
    {'email': 'arman_pier@yahoo.com', 'password': 'Arman4237340'},
    {'username': 'arman_pier@yahoo.com', 'password': 'Arman4237340'},
    {'login': 'arman_pier@yahoo.com', 'password': 'Arman4237340'},
    {'user': 'arman_pier@yahoo.com', 'pass': 'Arman4237340'},
]

for p in payloads:
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': TV_KEY,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': 'tv30nama/3.2.3'
    }
    encoded = '&'.join(f"{k}={urllib.parse.quote(v)}" for k, v in p.items()).encode('utf-8')
    req = urllib.request.Request(url, data=encoded, headers=headers)
    print(f"Testing with fields: {list(p.keys())}")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            res = r.read().decode('utf-8')
            print("Response:", res)
            break
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8')
        print(f"HTTPError {e.code}: {err}")
    except Exception as e:
        print("Error:", e)
