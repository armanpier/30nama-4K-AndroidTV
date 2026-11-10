import urllib.request
import ssl
import json
import re

ctx = ssl.create_default_context()

urls_to_test = [
    'https://gemini.google.com/share/bce5a150ca57',
    'https://gemini.google.com/share/bce5a150ca57?social_preview=true',
    'https://gemini.google.com/share/bce5a150ca57?hl=en',
]

for url in urls_to_test:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f"URL: {url}")
            print(f"Length: {len(data)}")
            with open('gemini_share_bot.html', 'w', encoding='utf-8') as out:
                out.write(data)
            
            # Check og:description or title
            og_title = re.findall(r'<meta property="og:title" content="([^"]+)"', data)
            og_desc = re.findall(r'<meta property="og:description" content="([^"]+)"', data)
            print("OG Title:", og_title)
            print("OG Desc:", og_desc)
            break
    except Exception as e:
        print(f"Error {url}: {e}")
