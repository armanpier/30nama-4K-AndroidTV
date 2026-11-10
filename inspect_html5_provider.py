with open(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\jwplayer\html5_provider_mobile.js", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r"qualityLevels", content)]
for pos in matches:
    start = max(0, pos - 150)
    end = min(len(content), pos + 350)
    print("---------------------------------")
    print(content[start:end])
