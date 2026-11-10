import re

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Search for RNJWPlayer occurrences in bundle
matches = [m.start() for m in re.finditer(rb"RNJWPlayer", data)]
print(f"RNJWPlayer matches: {len(matches)}")
for pos in matches:
    start = max(0, pos - 200)
    end = min(len(data), pos + 300)
    chunk = data[start:end]
    safe = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
    print(f"@{pos}: {safe}")
