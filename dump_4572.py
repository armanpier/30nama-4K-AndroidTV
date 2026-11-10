import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

with open('apk-extract/assets/index.android.bundle.orig', 'rb') as f:
    bundle = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

fh = reader.function_headers[4572]
dis = disassemble_function(reader, 4572, fh)
with open('func_4572_full.txt', 'w', encoding='utf-8') as out:
    out.write(dis if dis else '')
print('Written func_4572_full.txt')
