import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

# Disassemble Function 56791
orig_stdout = sys.stdout
with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56791_disasm.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    disassemble_function(reader, 56791, reader.function_headers[56791])
    sys.stdout = orig_stdout

with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56791_disasm.txt", "r", encoding="utf-8") as f:
    print(f.read())
