import re

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

keywords = ["1080", "720", "480", "2160", "4k", "4K", "FHD", "HD", "UHD", "SD", "Auto", "auto", "کیفیت", "رزولوشن", "سرعت", "کیفیت پخش"]

for kw in keywords:
    # search UTF-8
    kw_u8 = kw.encode('utf-8')
    matches_u8 = [m.start() for m in re.finditer(re.escape(kw_u8), data)]
    if matches_u8:
        print(f"UTF-8 match for '{kw}': {len(matches_u8)} times")
        for pos in matches_u8[:3]:
            start = max(0, pos - 40)
            end = min(len(data), pos + len(kw_u8) + 40)
            chunk = data[start:end]
            safe_str = "".join(chr(b) if 32 <= b <= 126 else f"\\x{b:02x}" for b in chunk)
            print(f"  @{pos}: {safe_str}")

    # search UTF-16LE
    kw_u16 = kw.encode('utf-16le')
    matches_u16 = [m.start() for m in re.finditer(re.escape(kw_u16), data)]
    if matches_u16:
        print(f"UTF-16LE match for '{kw}': {len(matches_u16)} times")
        for pos in matches_u16[:3]:
            start = max(0, pos - 40)
            end = min(len(data), pos + len(kw_u16) + 40)
            chunk = data[start:end]
            safe_str = "".join(chr(b) if 32 <= b <= 126 else f"\\x{b:02x}" for b in chunk)
            print(f"  @{pos}: {safe_str}")
