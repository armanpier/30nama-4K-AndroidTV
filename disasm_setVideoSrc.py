import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

for fid in [56797, 56798]:
    print(f"\n==================== Function {fid} ====================")
    orig_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    disassemble_function(reader, fid, reader.function_headers[fid])
    sys.stdout = orig_stdout
    print(buf.getvalue())
