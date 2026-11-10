import re

def search_in_file(path):
    print(f"=== Searching in {path} ===")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Search for quality related properties and methods
    terms = ["getQualityLevels", "setCurrentQuality", "currentQuality", "quality", "levels", "setQuality", "qualityLabel", "qualityLabels"]
    for t in terms:
        matches = [m.start() for m in re.finditer(re.escape(t), content, re.IGNORECASE)]
        print(f"  Term '{t}': {len(matches)} occurrences")
        for pos in matches[:3]:
            start = max(0, pos - 60)
            end = min(len(content), pos + len(t) + 60)
            print(f"    @{pos}: {content[start:end]}")

search_in_file(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\jwplayer\jwplayer.core.js")
search_in_file(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\jwplayer\jwplayer.js")
search_in_file(r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\jwplayer\html5_provider_mobile.js")
