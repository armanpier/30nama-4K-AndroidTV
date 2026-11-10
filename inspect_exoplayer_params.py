with open(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\classes2.dex", "rb") as f:
    data = f.read()

pos = 8069303
start = max(0, pos - 200)
end = min(len(data), pos + 200)
chunk = data[start:end]
print("".join(chr(b) if 32 <= b <= 126 else "." for b in chunk))
