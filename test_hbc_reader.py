from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    reader = HBCReader(f)

print("HBCReader initialized!")
print(f"Header: version={reader.header.version}, funcCount={reader.header.function_count}")
print(f"String count: {len(reader.strings)}")

# Look for targets in reader.strings
targets = ["VideoSettingsQualityTitle", "selectedQualityObject", "VideoSettingsTitle", "getQualityLevel", "setCurrentQuality"]
target_map = {}
for i, s in enumerate(reader.strings):
    for t in targets:
        if s == t:
            target_map[t] = i
            print(f"Target '{t}' -> String ID: {i}")

print("Target map:", target_map)
