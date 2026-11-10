import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

# Load original bundle
with open(r'apk-extract\assets\index.android.bundle.orig', 'rb') as f:
    bundle = bytearray(f.read())

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

fh = reader.function_headers[52673]
orig_52673 = bundle[fh.offset : fh.offset + fh.bytecodeSizeInBytes]
print(f"Function 52673 offset: {hex(fh.offset)}, size: {len(orig_52673)}")

# Construct the patched bytecode for 52673
# 0x00 to 0x06: original LoadParam instructions (6 bytes)
patch_52673 = bytearray(orig_52673[:6])

# 0x06: Start of our logic (replaces _classCallCheck which was 37 bytes, from 0x06 to 0x2b)
# Pos 0x06: LoadParam <Reg8: 8, UInt8: 1> (3 bytes)
pos_loadparam = len(patch_52673)
patch_52673 += bytes([0x6c, 0x08, 0x01])

# Pos 0x09: LoadConstZero <Reg8: 9> (2 bytes)
patch_52673 += bytes([0x7a, 0x09])

# Pos 0x0b: GetByVal <Reg8: 9, Reg8: 8, Reg8: 9> (4 bytes) -> actionUrl[0]
patch_52673 += bytes([0x49, 0x09, 0x08, 0x09])

# Pos 0x0f: LoadConstString <Reg8: 10, string_id: 27115> ('q') (4 bytes)
# 27115 = 0x69eb -> bytes [0xeb, 0x69]
patch_52673 += bytes([0x73, 0x0a, 0xeb, 0x69])

# Pos 0x13: JStrictNotEqual <Addr8: offset, Reg8: 9, Reg8: 10> (4 bytes)
# If not 'q', jump to DESKTOP branch.
# We will calculate the relative offset:
# JStrictNotEqual is 4 bytes (0x13 to 0x17).
# TV key branch:
# Pos 0x17: LoadConstString <Reg8: 7, string_id: 13999> (TV key) (4 bytes)
# Pos 0x1b: Jmp <Addr8: offset> (2 bytes)
# DESKTOP branch starts at 0x1d!
# So JStrictNotEqual jump offset from 0x13 to 0x1d is: 0x1d - 0x13 = 10 (0x0a)!
patch_52673 += bytes([0xbe, 0x0a, 0x09, 0x0a])

# Pos 0x17: LoadConstString <Reg8: 7, string_id: 13999> (4 bytes)
# 13999 = 0x36af -> bytes [0xaf, 0x36]
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x36])

# Pos 0x1b: Jmp <Addr8: offset> (2 bytes)
# Jump past DESKTOP branch (which is 4 bytes at 0x1d to 0x21).
# Target is 0x21.
# Relative offset from 0x1b to 0x21 is: 0x21 - 0x1b = 6 (0x06)!
patch_52673 += bytes([0x8e, 0x06])

# Pos 0x1d: LoadConstString <Reg8: 7, string_id: 687> (DESKTOP key) (4 bytes)
# 687 = 0x02af -> bytes [0xaf, 0x02]
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x02])

# Pos 0x21: PutById <Reg8: 2, Reg8: 7, UInt8: 1, string_id: 27083> (this.token = Reg8: 7) (6 bytes)
# 27083 = 0x69cb -> bytes [0xcb, 0x69]
patch_52673 += bytes([0x3b, 0x02, 0x07, 0x01, 0xcb, 0x69])

# Now we are at 0x27!
# 0x2b - 0x27 = 4 bytes remaining until 0x2b.
# Pad with 2 x LoadConstUndefined <Reg8: 0> (2 bytes each = 4 bytes)
patch_52673 += bytes([0x76, 0x00, 0x76, 0x00])

assert len(patch_52673) == 0x2b, f"Offset mismatch at 0x2b: {hex(len(patch_52673))}"

# 0x2b to 0x41: Original instructions (GetById config, emmiter, store, log) (22 bytes)
patch_52673 += orig_52673[0x2b:0x41]
assert len(patch_52673) == 0x41, f"Offset mismatch at 0x41: {hex(len(patch_52673))}"

# 0x41 to 0x55: Originally tokenMap lookup (20 bytes). We replace with 10 x LoadConstUndefined <Reg8: 0>
patch_52673 += bytes([0x76, 0x00]) * 10
assert len(patch_52673) == 0x55, f"Offset mismatch at 0x55: {hex(len(patch_52673))}"

# 0x55 to end: Original instructions (PutById config, actionUrl, overrideSession, etc.) (44 bytes)
patch_52673 += orig_52673[0x55:]
assert len(patch_52673) == len(orig_52673) == 129, f"Total size mismatch: {len(patch_52673)} vs {len(orig_52673)}"

print("Patch constructed successfully, length matches exactly 129 bytes!")

# Test disassemble the patch
bundle[fh.offset : fh.offset + len(patch_52673)] = patch_52673
import hashlib
bundle[-20:] = hashlib.sha1(bundle[:-20]).digest()

test_reader = HBCReader()
test_reader.read_whole_file(io.BytesIO(bundle))
print("\nDisassembly of patched Function 52673:")
disassemble_function(test_reader, 52673, test_reader.function_headers[52673])
