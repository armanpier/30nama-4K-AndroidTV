import re
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

brain_dir = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f"
for fname in ['orig_logcat.txt', 'logcat_movie.txt', 'pt_logcat.txt']:
    p = os.path.join(brain_dir, fname)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            t = f.read()
        print(f"=== {fname} ===")
        found = set()
        for u in re.findall(r'https?://[^\s\"\'<>]+', t):
            if any(k in u for k in ['stream', 'm3u8', 'download', 'action', 'post']):
                if u not in found:
                    found.add(u)
                    print(" ", u[:120])
