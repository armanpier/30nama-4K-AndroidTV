import os
import sys
import ssl
import urllib.request
from build_standalone_apk import build_custom_apk

def download_file(url, output):
    if os.path.exists(output) and os.path.getsize(output) > 50 * 1024 * 1024:
        print(f"{output} already exists ({os.path.getsize(output) / (1024*1024):.1f} MB). Skipping download.")
        return output

    print(f"Downloading {url} to {output}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req, context=ctx) as resp, open(output, "wb") as out_f:
        total = int(resp.headers.get("content-length", 0))
        done = 0
        chunk_sz = 1024 * 1024
        while True:
            chunk = resp.read(chunk_sz)
            if not chunk:
                break
            out_f.write(chunk)
            done += len(chunk)
            if total:
                pct = (done / total) * 100
                print(f"Downloaded: {done / (1024*1024):.1f}MB / {total / (1024*1024):.1f}MB ({pct:.1f}%)", end="\r")

    print(f"\nSaved {output} ({os.path.getsize(output) / (1024*1024):.1f} MB)")
    return output

if __name__ == "__main__":
    targets = [
        (
            "https://mirrors.kodi.tv/releases/android/arm64-v8a/kodi-21.3-Omega-arm64-v8a.apk",
            "kodi-21.3-Omega-arm64-v8a.apk",
            "30nama-4K-AndroidTV-arm64-v8a.apk",
            "ARM64 (Modern Android TVs & Google TV Sticks)"
        ),
        (
            "https://mirrors.kodi.tv/releases/android/arm/kodi-21.3-Omega-armeabi-v7a.apk",
            "kodi-21.3-Omega-armeabi-v7a.apk",
            "30nama-4K-AndroidTV-armeabi-v7a.apk",
            "ARM 32-bit (Legacy Android TV Sticks & Boxes)"
        ),
    ]

    for url, base_apk, out_apk, desc in targets:
        print(f"\n==================================================")
        print(f"PROCESSING: {desc}")
        print(f"==================================================")
        download_file(url, base_apk)
        build_custom_apk(base_apk, out_apk, desc)
        print(f"FINISHED: {out_apk}")
