import io
import struct
import hashlib
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

orig_path = r'apk-extract\assets\index.android.bundle.orig'
with open(orig_path, 'rb') as f:
    bundle = bytearray(f.read())

reader = HBCReader()
reader.read_whole_file(io.BytesIO(bundle))

# 1. Patch Function 52673 (Action constructor)
fh = reader.function_headers[52673]
orig_52673 = bundle[fh.offset : fh.offset + fh.bytecodeSizeInBytes]

patch_52673 = bytearray(orig_52673[:6])

# 0x06: LoadParam <Reg8: 8, UInt8: 1> (actionUrl)
patch_52673 += bytes([0x6c, 0x08, 0x01])

# 0x09: LoadConstString <Reg8: 9, string_id: 29879> ('stream')
patch_52673 += bytes([0x73, 0x09, 0xb7, 0x74])

# 0x0d: JStrictEqual <Addr8: 18, Reg8: 8, Reg8: 9> -> target: 0x0d + 18 = 0x1f (DESKTOP)
patch_52673 += bytes([0xbc, 18, 0x08, 0x09])

# 0x11: LoadConstString <Reg8: 9, string_id: 29899> ('stream_servers')
patch_52673 += bytes([0x73, 0x09, 0xcb, 0x74])

# 0x15: JStrictEqual <Addr8: 10, Reg8: 8, Reg8: 9> -> target: 0x15 + 10 = 0x1f (DESKTOP)
patch_52673 += bytes([0xbc, 10, 0x08, 0x09])

# 0x19: LoadConstString <Reg8: 7, string_id: 13999> (TV key: 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX')
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x36])

# 0x1d: Jmp <Addr8: 6> -> target: 0x1d + 6 = 0x23 (PutById)
patch_52673 += bytes([0x8e, 6])

# 0x1f: LoadConstString <Reg8: 7, string_id: 687> (DESKTOP key: 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ')
patch_52673 += bytes([0x73, 0x07, 0xaf, 0x02])

# 0x23: PutById <Reg8: 2, Reg8: 7, UInt8: 1, string_id: 27083> (this.token = Reg8: 7)
patch_52673 += bytes([0x3b, 0x02, 0x07, 0x01, 0xcb, 0x69])

# 0x29: 2 bytes padding (1 x LoadConstUndefined <Reg8: 0>)
patch_52673 += bytes([0x76, 0x00])

# 0x2b: Original instructions up to 0x41
patch_52673 += orig_52673[0x2b:0x41]

# 0x41: 20 bytes padding (10 x LoadConstUndefined <Reg8: 0>)
patch_52673 += bytes([0x76, 0x00]) * 10

# 0x55: Original instructions to end
patch_52673 += orig_52673[0x55:]

assert len(patch_52673) == len(orig_52673) == 129, f"Size mismatch: {len(patch_52673)} vs {len(orig_52673)}"

bundle[fh.offset : fh.offset + len(patch_52673)] = patch_52673
print(f"Patched Function 52673 at {hex(fh.offset)} (129 bytes)")

# 2. Patch Function 4585 (increase QR check timeout from 60s to 1 hour = 3600000 ms)
fh_4585 = reader.function_headers[4585]
pos_60s = fh_4585.offset + 0x5c
bundle[pos_60s : pos_60s + 4] = struct.pack('<I', 3600000)
print(f"Patched Function 4585 timeout at {hex(pos_60s)} from 60000ms to 3600000ms (1 hour)")

# 3. Update Hermes footer SHA-1 hash
bundle[-20:] = hashlib.sha1(bundle[:-20]).digest()
print(f"Updated Hermes SHA-1 footer: {bundle[-20:].hex()}")

# 4. Verify modified bundle with HBCReader
verify_reader = HBCReader()
verify_reader.read_whole_file(io.BytesIO(bundle))
print("Verification: Patched bundle successfully verified by HBCReader!")

# 5. Write to output
output_bundle_path = r'apk-extract\assets\index.android.bundle'
with open(output_bundle_path, 'wb') as f:
    f.write(bundle)
print(f"Successfully wrote patched bundle to {output_bundle_path}")
