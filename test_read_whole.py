from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    parsed = reader.read_whole_file(f)

print("Parsed successfully!")
# inspect parsed attributes
print([a for a in dir(parsed) if not a.startswith("_")])
