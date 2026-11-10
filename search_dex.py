import os
import re

dex_files = [f"C:\\Users\\Arman\\Documents\\antigravity\\quirky-turing\\apk-extract\\classes{i}.dex" if i > 1 
             else "C:\\Users\\Arman\\Documents\\antigravity\\quirky-turing\\apk-extract\\classes.dex" 
             for i in range(1, 5)]

terms = [b"RNJWPlayer", b"setCurrentQuality", b"quality", b"Quality", b"maxVideoWidth", b"maxVideoHeight"]

for dex in dex_files:
    if not os.path.exists(dex):
        continue
    print(f"\n=== Searching {os.path.basename(dex)} ===")
    with open(dex, "rb") as f:
        data = f.read()
    for t in terms:
        matches = [m.start() for m in re.finditer(re.escape(t), data)]
        if matches:
            print(f"  Term {t.decode(errors='ignore')}: {len(matches)} matches")
            for pos in matches[:3]:
                start = max(0, pos - 40)
                end = min(len(data), pos + len(t) + 40)
                chunk = data[start:end]
                safe = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                print(f"    @{pos}: {safe}")
