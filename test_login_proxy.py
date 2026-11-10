import urllib.request
import urllib.parse
import ssl
import json

proxy_handler = urllib.request.ProxyHandler({
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808'
})
opener = urllib.request.build_opener(proxy_handler)

# Let's test action/login
url = 'https://world.hana-api.com/api/v2/action/login'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

payload = {'email': 'arman_pier@yahoo.com', 'password': 'Arman4237340'}
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
        res = r.read().decode('utf-8')
        print("Login response:", res)
except urllib.error.HTTPError as e:
    err = e.read().decode('utf-8')
    print(f"HTTPError {e.code}: {err[:500]}")
except Exception as e:
    print("Error:", e)
