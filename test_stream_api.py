import urllib.request, json

url = 'https://world.hana-api.com/api/v2/action/stream'

for platform, key in [('ANDROIDTV', 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'), ('DESKTOP', 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ')]:
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': key,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': 'Mozilla/5.0'
    }
    data = 'post_id=461612&free_stream=false'.encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        content = res.read().decode('utf-8')
        print(f'{platform}: Status {res.status}, response: {content[:300]}')
    except urllib.error.HTTPError as e:
        err_content = e.read().decode('utf-8')
        print(f'{platform}: HTTPError {e.code}: {err_content[:300]}')
    except Exception as e:
        print(f'{platform}: Error {e}')
