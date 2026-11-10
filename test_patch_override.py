import io
import struct
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

with open(r'apk-extract\assets\index.android.bundle.orig', 'rb') as f:
    bundle = bytearray(f.read())

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

fh = reader.function_headers[52673]
orig_52673 = bundle[fh.offset : fh.offset + fh.bytecodeSizeInBytes]

patch_52673 = bytearray(orig_52673[:6])

# 0x06: LoadParam <Reg8: 8, UInt8: 1> (actionUrl)
patch_52673 += bytes([0x6c, 0x08, 0x01])

# 0x09: LoadConstZero <Reg8: 9> (index 0)
patch_52673 += bytes([0x7a, 0x09])

# 0x0b: GetByVal <Reg8: 9, Reg8: 8, Reg8: 9> (actionUrl[0])
patch_52673 += bytes([0x49, 0x09, 0x08, 0x09])

# 0x0f: LoadConstString <Reg8: 10, string_id: 27115> ('q')
patch_52673 += bytes([0x73, 0x0a, 0xeb, 0x69])

# 0x13: JStrictNotEqual <Addr8: 10, Reg8: 9, Reg8: 10> -> jump to 0x1d (DESKTOP)
patch_52673 += bytes([0xbe, 0x0a, 0x09, 0x0a])

# 0x17: LoadConstString <Reg8: 7, string_id: 13999> (TV key: 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX')
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x36])

# 0x1b: Jmp <Addr8: 6> -> jump to 0x21 (PutById)
patch_52673 += bytes([0x8e, 0x06])

# 0x1d: LoadConstString <Reg8: 7, string_id: 687> (DESKTOP key: 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ')
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x02])

# 0x21: PutById <Reg8: 2, Reg8: 7, UInt8: 1, string_id: 27083> (this.token = Reg8: 7)
patch_52673 += bytes([0x3b, 0x02, 0x07, 0x01, 0xcb, 0x69])

# 0x27: 4 bytes padding (2 x LoadConstUndefined <Reg8: 0>)
patch_52673 += bytes([0x76, 0x00, 0x76, 0x00])

# 0x2b: Original instructions up to 0x41
patch_52673 += orig_52673[0x2b:0x41]

# 0x41: 20 bytes block for overrideSession logic:
# LoadParam <Reg8: 11, UInt8: 3> (3 bytes: param3)
# LoadConstString <Reg8: 10, string_id: 13999> (4 bytes: TV key)
# JStrictNotEqual <Addr8: 4, Reg8: 7, Reg8: 10> (4 bytes: jump over LoadConstTrue if not TV key)
# LoadConstTrue <Reg8: 11> (2 bytes: overrideSession = true)
# PutById <Reg8: 2, Reg8: 11, UInt8: 4, string_id: 31037> (6 bytes: this.overrideSession = Reg8: 11)
# Nop (1 byte: 0x00)
block_41 = bytearray()
block_41 += bytes([0x6c, 0x0b, 0x03])              # LoadParam <Reg8: 11, UInt8: 3>
block_41 += bytes([0x73, 0x0a, 0xaf, 0x36])        # LoadConstString <Reg8: 10, string_id: 13999>
block_41 += bytes([0xbe, 0x04, 0x07, 0x0a])        # JStrictNotEqual <Addr8: 4, Reg8: 7, Reg8: 10> -> jumps +4 bytes (over LoadConstTrue)
block_41 += bytes([0x78, 0x0b])                    # LoadConstTrue <Reg8: 11>
block_41 += bytes([0x3b, 0x02, 0x0b, 0x04, 0x3d, 0x79]) # PutById <Reg8: 2, Reg8: 11, UInt8: 4, string_id: 31037>
block_41 += bytes([0x00])                          # Nop (1 byte)
assert len(block_41) == 20, f"Block 41 len is {len(block_41)}"
patch_52673 += block_41

# 0x55 to 0x64: Original instructions (config, actionUrl)
patch_52673 += orig_52673[0x55:0x64]

# 0x64 to 0x6d: Original overrideSession setting (9 bytes) -> replace with 4 x LoadConstUndefined (8 bytes) + 1 Nop
block_64 = bytes([0x76, 0x00, 0x76, 0x00, 0x76, 0x00, 0x76, 0x00, 0x00])
assert len(block_64) == 9
patch_52673 += block_64

# 0x6d to end: Original instructions (emmiter, store, log, ret)
patch_52673 += orig_52673[0x6d:]

assert len(patch_52673) == len(orig_52673) == 129, f"Size mismatch: {len(patch_52673)} vs {len(orig_52673)}"

bundle[fh.offset : fh.offset + len(patch_52673)] = patch_52673

# Update SHA-1 footer
import hashlib
bundle[-20:] = hashlib.sha1(bundle[:-20]).digest()

# Test disassembling with HBCReader
test_reader = HBCReader()
test_reader.read_whole_file(io.BytesIO(bundle))
print("Successfully parsed by HBCReader!")
dis = disassemble_function(test_reader, 52673, test_reader.function_headers[52673])
