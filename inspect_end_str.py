bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's inspect around 4575000 - 4576000
for i in range(4575350, 4575450, 16):
    hex_str = " ".join(f"{b:02x}" for b in data[i:i+16])
    asc_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[i:i+16])
    print(f"{i:06x}: {hex_str} |{asc_str}|")
