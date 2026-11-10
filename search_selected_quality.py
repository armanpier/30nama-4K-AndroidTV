bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

import re
matches = [m.start() for m in re.finditer(rb"selectedQualityObject", data)]
print(f"Matches for selectedQualityObject: {len(matches)}")
for pos in matches:
    print(f"Position: {pos}")
    start = max(0, pos - 200)
    end = min(len(data), pos + 200)
    print("".join(chr(b) if 32 <= b <= 126 else "." for b in data[start:end]))
