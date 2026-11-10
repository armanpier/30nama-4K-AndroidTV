bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's inspect the layout before 1226963
# What is at 1226900 - 1226963?
for i in range(1226900, 1226970, 16):
    hex_str = " ".join(f"{b:02x}" for b in data[i:i+16])
    asc_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[i:i+16])
    print(f"{i:06x}: {hex_str} |{asc_str}|")
