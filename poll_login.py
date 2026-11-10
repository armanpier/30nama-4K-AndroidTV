import requests
import time
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
headers = {
    'User-Agent': 'tv30nama/3.2.3',
    'c-api-key': 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX',
    'c-version-number': '3.2.3',
    'c-language': 'fa'
}

code = '9c2602d8'
url = 'https://world.hana-api.com/api/v2/action/qrlogin_login'

print(f"Polling for code: {code}...")
for i in range(10):
    r = requests.post(url, data={'code': code}, headers=headers, proxies=proxies, verify=False)
    res = r.json()
    print(f"Attempt {i+1}: {res}")
    if res.get('success') and res.get('result', {}).get('token'):
        token = res['result']['token']
        print(f"\n[SUCCESS] Token: {token}")
        with open('c_token.txt', 'w') as f:
            f.write(token)
        break
    time.sleep(2)
