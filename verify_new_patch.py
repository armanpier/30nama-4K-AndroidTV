import io
import struct
import hashlib
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

# 0x2b to 0x41: Original instructions (config, emmiter, store, log)
patch_52673 += orig_52673[0x2b:0x41]

# Now, 0x41 to 0x6d (44 bytes):
block_41_to_6d = bytearray()
# 0x41: PutById config (this.config = config) (6 bytes)
block_41_to_6d += orig_52673[0x55:0x5b]

# 0x47: LoadParam actionUrl (3 bytes)
# 0x4a: PutById actionUrl (this.actionUrl = actionUrl) (6 bytes)
block_41_to_6d += orig_52673[0x5b:0x64]

# 0x50: LoadParam <Reg8: 5, UInt8: 3> (param3 overrideSession) (3 bytes)
block_41_to_6d += bytes([0x6c, 0x05, 0x03])

# 0x53: LoadConstString <Reg8: 10, string_id: 13999> (TV key) (4 bytes)
block_41_to_6d += bytes([0x73, 0x0a, 0xaf, 0x36])

# 0x57: JStrictNotEqual <Addr8: 6, Reg8: 7, Reg8: 10> -> if this.token != TV_KEY, jump to PutById (4 bytes)
# (Offset 6 from 0x57 jumps to 0x5d: 0x57 + 6 = 0x5d)
block_41_to_6d += bytes([0xbe, 0x06, 0x07, 0x0a])

# 0x5b: LoadConstTrue <Reg8: 5> (overrideSession = true) (2 bytes)
block_41_to_6d += bytes([0x78, 0x05])

# 0x5d: PutById <Reg8: 2, Reg8: 5, UInt8: 4, string_id: 31037> (this.overrideSession = Reg8: 5) (6 bytes)
block_41_to_6d += bytes([0x3b, 0x02, 0x05, 0x04, 0x3d, 0x79])

# 0x63 to 0x6d: 10 bytes padding (5 x LoadConstUndefined <Reg8: 0>)
block_41_to_6d += bytes([0x76, 0x00]) * 5

assert len(block_41_to_6d) == 44, f"Block len is {len(block_41_to_6d)}, expected 44"
patch_52673 += block_41_to_6d

# 0x6d to end: Original instructions (emmiter, store, log, ret)
patch_52673 += orig_52673[0x6d:]

assert len(patch_52673) == len(orig_52673) == 129, f"Size mismatch: {len(patch_52673)} vs {len(orig_52673)}"

bundle[fh.offset : fh.offset + len(patch_52673)] = patch_52673

# Update Hermes SHA-1 footer
bundle[-20:] = hashlib.sha1(bundle[:-20]).digest()

# Verify modified bundle with HBCReader
verify_reader = HBCReader()
verify_reader.read_whole_file(io.BytesIO(bundle))
print("Verification: Modified bundle successfully loaded by HBCReader!")

dis = disassemble_function(verify_reader, 52673, verify_reader.function_headers[52673])
