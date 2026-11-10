bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Inspect strings from 4475000 to 4495000
chunk = data[4475000:4495000]
strings = []
curr = []
for b in chunk:
    if 32 <= b <= 126:
        curr.append(chr(b))
    else:
        if len(curr) >= 4:
            strings.append("".join(curr))
        curr = []
if len(curr) >= 4:
    strings.append("".join(curr))

with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\video_player_strings.txt", "w", encoding="utf-8") as out:
    for s in strings:
        out.write(s + "\n")

print(f"Dumped {len(strings)} strings to video_player_strings.txt")
