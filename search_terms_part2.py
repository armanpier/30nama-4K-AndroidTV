from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

import io
reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

import re
terms = ["stream", "quality", "resolution", "video", "hls", "m3u8", "player", "playback", "link", "media"]

matching_strings = {}
for i, s in enumerate(reader.strings):
    for t in terms:
        if re.search(r"\b" + t, s, re.I):
            matching_strings[i] = s
            break

for idx in sorted(matching_strings.keys()):
    if idx > 15404:
        print(f"  [{idx:5d}]: '{matching_strings[idx]}'")
