from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

import io
reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

# Search for the string ID of "Running action: stream" or "stream_servers"
targets = ["Running action: stream", "Running action: stream_servers", "stream_servers", "stream_server"]
for t in targets:
    try:
        idx = reader.strings.index(t)
        print(f"String '{t}' has ID {idx}")
    except ValueError:
        print(f"String '{t}' not in reader.strings")
