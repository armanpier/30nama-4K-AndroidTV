import requests

proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
url_code = 'https://world.hana-api.com/api/v2/action/qrlogin_code'
url_login = 'https://world.hana-api.com/api/v2/action/qrlogin_login'
headers = {
    'User-Agent': 'tv30nama/3.2.3',
    'c-api-key': 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX',
    'c-version-number': '3.2.3',
    'c-language': 'fa'
}

# 1. Get fresh code
r1 = requests.post(url_code, headers=headers, proxies=proxies, verify=False).json()
print("qrlogin_code response:", r1)
code = r1.get('result', {}).get('code')

# 2. Test qrlogin_login with auth_code
r2 = requests.post(url_login, data={'auth_code': code}, headers=headers, proxies=proxies, verify=False).json()
print("qrlogin_login response with auth_code:", r2)
