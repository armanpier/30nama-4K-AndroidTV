import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

for fid in [56803, 56819]:
    fh = reader.function_headers[fid]
    buf = io.StringIO()
    orig_stdout = sys.stdout
    sys.stdout = buf
    disassemble_function(reader, fid, fh)
    sys.stdout = orig_stdout
    print(f"\n==================== Function {fid} (name='{reader.strings[fh.functionName]}') ====================")
    lines = buf.getvalue().splitlines()
    for l in lines[:100]:
        print(l)
