import io
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"apk-extract\assets\index.android.bundle.orig"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

orig_stdout = sys.stdout
with open("qr_endpoints_disasm.txt", "w", encoding="utf-8") as out:
    for fid in [53271, 53272, 53273, 53302, 53318]:
        out.write(f"\n================ FUNCTION {fid} ================\n")
        sys.stdout = out
        disassemble_function(reader, fid, reader.function_headers[fid])
sys.stdout = orig_stdout

print("Disassembled QR and stream functions!")
