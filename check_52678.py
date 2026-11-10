import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

with open('apk-extract/assets/index.android.bundle.orig', 'rb') as f:
    bundle = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

for fid in [52678, 52679, 52680]:
    fh = reader.function_headers[fid]
    print(f'=== Function {fid} ===')
    disassemble_function(reader, fid, fh)
