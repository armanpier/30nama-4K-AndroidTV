import urllib.request
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXIES))
url = 'https://subsource.net/subtitles/apocalypse-z-new-world-2026/farsi_persian'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with opener.open(req, timeout=10) as r:
        html = r.read().decode('utf-8')
    print('Subsource status 200, length:', len(html))
    links = re.findall(r'href=["\']([^"\']*subtitles[^"\']*)["\']', html)
    print('Subtitle links found:', links[:5])
except Exception as e:
    print('Error:', e)
