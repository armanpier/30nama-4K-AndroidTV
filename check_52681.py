import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

with open('apk-extract/assets/index.android.bundle.orig', 'rb') as f:
    bundle = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

fh = reader.function_headers[52681]
print('=== Function 52681 ===')
disassemble_function(reader, 52681, fh)
