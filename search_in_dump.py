with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\video_player_strings.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r"(VideoSettings|Quality|QualityLevel|currentLevel|audioTrack|subtitles|sources|bitrate)", text, re.IGNORECASE)]
for pos in matches:
    start = max(0, pos - 60)
    end = min(len(text), pos + 100)
    print("--------------------")
    print(text[start:end])
