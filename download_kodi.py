import urllib.request
import ssl
import sys
import os

url = 'https://mirrors.kodi.tv/releases/android/x86/kodi-21.3-Omega-x86.apk'
output = 'kodi-21.3-Omega-x86.apk'

if os.path.exists(output) and os.path.getsize(output) > 50 * 1024 * 1024:
    print(f"{output} already exists, size: {os.path.getsize(output)} bytes")
    sys.exit(0)

print(f"Downloading {url} to {output}...")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

with urllib.request.urlopen(req, context=ctx) as resp, open(output, 'wb') as out_file:
    total_size = int(resp.headers.get('content-length', 0))
    downloaded = 0
    chunk_size = 1024 * 1024  # 1MB
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        out_file.write(chunk)
        downloaded += len(chunk)
        if total_size:
            percent = (downloaded / total_size) * 100
            print(f"Progress: {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB ({percent:.1f}%)", end='\r')

print(f"\nDownload finished! Total size: {os.path.getsize(output)} bytes")
