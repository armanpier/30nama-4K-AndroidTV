import requests

proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
url_auth = 'https://world.hana-api.com/api/v2/action/qrlogin_auth'
headers = {
    'User-Agent': 'tv30nama/3.2.3',
    'c-api-key': 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX',
    'c-version-number': '3.2.3',
    'c-language': 'fa'
}

r = requests.post(url_auth, data={'auth_code': 'e4393e85'}, headers=headers, proxies=proxies, verify=False).json()
print("qrlogin_auth response:", r)
