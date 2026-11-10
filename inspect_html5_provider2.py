with open(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\jwplayer\html5_provider_mobile.js", "r", encoding="utf-8") as f:
    content = f.read()

# Let's inspect getQualityLevels and setCurrentQuality in html5_provider_mobile.js
import re
for term in ["getQualityLevels", "setCurrentQuality", "setVideoSource", "exoPlayer"]:
    print(f"=== Matches for {term} ===")
    matches = [m.start() for m in re.finditer(re.escape(term), content)]
    for pos in matches[:5]:
        start = max(0, pos - 100)
        end = min(len(content), pos + 250)
        print("---")
        print(content[start:end])
