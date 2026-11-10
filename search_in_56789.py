with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

import re
terms = ["qualityObject", "selectedQuality", "quality", "stream", "levels", "sources", "m3u8"]

found_lines = []
for i, line in enumerate(lines):
    for t in terms:
        if re.search(r"\b" + t, line, re.IGNORECASE):
            found_lines.append((i, line.strip()))
            break

print(f"Found {len(found_lines)} matching lines in func_56789_disasm.txt:")
for line_num, text in found_lines[:40]:
    print(f"Line {line_num}: {text}")
