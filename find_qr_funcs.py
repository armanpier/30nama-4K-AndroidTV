from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"apk-extract\assets\index.android.bundle.orig"
with open(bundle_path, "rb") as f:
    bundle_bytes = f.read()

import io
reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle_bytes))

s_code = 29895
s_login = 29896

print(f"Searching functions referencing {s_code} or {s_login}...")

for fid in range(reader.header.functionCount):
    hdr = reader.function_headers[fid]
    offset = hdr.offset
    size = hdr.bytecodeSizeInBytes
    bc = bundle_bytes[offset:offset+size]
    if s_code.to_bytes(2, 'little') in bc:
        print(f"Function {fid} references qrlogin_code (29895)")
    if s_login.to_bytes(2, 'little') in bc:
        print(f"Function {fid} references qrlogin_login (29896)")
