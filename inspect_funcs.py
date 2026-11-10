import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle.orig"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

funcs_to_disasm = [52664, 52673, 52677, 53302, 53327]

for fid in funcs_to_disasm:
    print(f"\n==================== Function {fid} ====================")
    hdr = reader.function_headers[fid]
    print(f"offset: {hex(hdr.offset)}, bytecodeSize: {hdr.bytecodeSizeInBytes}")
    disassemble_function(reader, fid, hdr)
