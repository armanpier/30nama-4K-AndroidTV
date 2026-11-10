import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
url = 'https://mirrors.kodi.tv/releases/android/x86/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        html = r.read().decode('utf-8')
        apks = re.findall(r'href=[\'"]([^\'"]+\.apk)[\'"]', html)
        print('Available x86 APKs:', apks[-5:])
except Exception as e:
    print('Error:', e)
