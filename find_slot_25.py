import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

for fid in range(56789, min(56920, len(reader.function_headers))):
    fh = reader.function_headers[fid]
    buf = io.StringIO()
    orig_stdout = sys.stdout
    sys.stdout = buf
    disassemble_function(reader, fid, fh)
    sys.stdout = orig_stdout
    text = buf.getvalue()
    if "UInt8: 25" in text and fid != 56789:
        print(f"Function {fid} (name='{reader.strings[fh.functionName]}') references slot 25!")
        for line in text.splitlines():
            if "UInt8: 25" in line:
                print("  " + line.strip())
