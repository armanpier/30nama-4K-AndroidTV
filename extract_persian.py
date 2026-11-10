# Dump Persian strings from the Hermes bundle
import re

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Match runs of UTF-8 encoded Arabic/Persian characters
# Arabic/Persian UTF-8 bytes typically start with \xd8..\xdb followed by \x80..\xbf
persian_pattern = re.compile(rb'([\xd8-\xdb][\x80-\xbf](\s|[\xd8-\xdb][\x80-\xbf]|[a-zA-Z0-9_:\.\-\/])*)')

matches = persian_pattern.findall(data)
unique_persian = set()
for m in matches:
    raw = m[0]
    try:
        text = raw.decode('utf-8', errors='ignore').strip()
        if len(text) >= 4 and any('\u0600' <= c <= '\u06ff' for c in text):
            unique_persian.add(text)
    except:
        pass

with open("c:\\Users\\Arman\\Documents\\antigravity\\quirky-turing\\persian_strings.txt", "w", encoding="utf-8") as out:
    for s in sorted(unique_persian):
        out.write(s + "\n")

print(f"Extracted {len(unique_persian)} Persian strings to persian_strings.txt")
