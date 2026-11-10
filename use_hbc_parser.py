from hermes_dec.parsers.hbc_file_parser import parse_file

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
print("Parsing bundle...")
hbc = parse_file(bundle_path)
print("Parsed successfully!")
print(f"Total string kinds: {len(hbc.string_kinds)}")
print(f"Total strings: {len(hbc.string_table)}")

# Find target strings in string_table
targets = ["VideoSettingsQualityTitle", "selectedQualityObject", "VideoSettingsTitle", "getQualityLevel", "setCurrentQuality"]
target_map = {}
for i, s in enumerate(hbc.string_table):
    val = s.val
    for t in targets:
        if val == t:
            target_map[t] = i
            print(f"Target '{t}' -> String ID: {i}")

print("Target map:", target_map)
