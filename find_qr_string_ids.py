from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"apk-extract\assets\index.android.bundle.orig"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    reader.read_whole_file(f)

targets = ["qrlogin_code", "qrlogin_login", "qrlogin_auth_code"]
target_ids = {}
for i, s in enumerate(reader.strings):
    for t in targets:
        if s == t:
            print(f"String '{t}' -> ID: {i}")
            target_ids[t] = i
