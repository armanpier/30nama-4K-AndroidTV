import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"apk-extract\assets\index.android.bundle.orig"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

for fid in range(52664, 52682):
    hdr = reader.function_headers[fid]
    print(f"\n==================== Function {fid} (offset: {hex(hdr.offset)}, size: {hdr.bytecodeSizeInBytes}) ====================")
    disassemble_function(reader, fid, hdr)
