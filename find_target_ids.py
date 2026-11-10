from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    reader.read_whole_file(f)

print(f"Total strings: {len(reader.strings)}")
targets = ["VideoSettingsQualityTitle", "selectedQualityObject", "VideoSettingsTitle", "getQualityLevel", "setCurrentQuality", "stream_server"]
for t in targets:
    try:
        idx = reader.strings.index(t)
        print(f"Target '{t}' -> String ID: {idx}")
    except ValueError:
        print(f"Target '{t}' not found in reader.strings")
