from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    res = reader.read_whole_file(f)

print("res:", type(res), res)
print("reader attrs:", [a for a in dir(reader) if not a.startswith("_") and not callable(getattr(reader, a))])
