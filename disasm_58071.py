import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

orig_stdout = sys.stdout
buf = io.StringIO()
sys.stdout = buf
disassemble_function(reader, 58071, reader.function_headers[58071])
sys.stdout = orig_stdout

with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_58071_disasm.txt", "w", encoding="utf-8") as out:
    out.write(buf.getvalue())

print("Disassembled 58071:")
print(buf.getvalue()[:2500])
