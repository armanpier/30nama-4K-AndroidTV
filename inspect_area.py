import struct
import re

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's inspect regions around:
# 1) VideoSettingsQualityTitle (@4477711)
# 2) setCurrentQuality (@3675239)
# 3) stream_server (@3674588)

targets = [
    ("VideoSettingsQualityTitle", 4477711),
    ("setCurrentQuality", 3675239),
    ("stream_server", 3674588),
]

for name, pos in targets:
    print(f"\n==================== {name} @ {pos} ====================")
    start = max(0, pos - 500)
    end = min(len(data), pos + 500)
    chunk = data[start:end]
    # Extract all ASCII/printable string runs >= 3 chars
    strings = []
    curr = []
    for b in chunk:
        if 32 <= b <= 126:
            curr.append(chr(b))
        else:
            if len(curr) >= 3:
                strings.append("".join(curr))
            curr = []
    if len(curr) >= 3:
        strings.append("".join(curr))
    print("Found strings around this area:")
    for s in strings:
        print(f"  - {s}")
