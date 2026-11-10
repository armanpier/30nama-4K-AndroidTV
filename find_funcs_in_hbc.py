from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    reader.read_whole_file(f)

target_ids = {
    34482: "VideoSettingsQualityTitle",
    35480: "selectedQualityObject",
    34483: "VideoSettingsTitle",
    29914: "setCurrentQuality"
}

print(f"Total function headers: {len(reader.function_headers)}")

# Each function header has offset, info, etc.
# Let's inspect function_headers[0]
fh0 = reader.function_headers[0]
print("FunctionHeader[0] fields:", [f for f in dir(fh0) if not f.startswith("_")])

# Search bytecode for our target_ids
# In Hermes instructions:
# Opcode is 1 byte, operands can be uint8, uint16, uint32.
# 34482 in uint16 LE is \xb2\x86
# 35480 in uint16 LE is \x98\x8a
# 34483 in uint16 LE is \xb3\x86
# 29914 in uint16 LE is \xda\x74
import struct

targets_bytes = {
    struct.pack("<H", k): v for k, v in target_ids.items()
}

found_funcs = {}
for i, fh in enumerate(reader.function_headers):
    # read bytecode for this function
    offset = fh.offset
    size = fh.bytecode_size_in_bytes
    bc = reader.file_buffer[offset : offset + size]
    for b_pat, name in targets_bytes.items():
        if b_pat in bc:
            if i not in found_funcs:
                found_funcs[i] = []
            found_funcs[i].append(name)

print(f"Found matches in {len(found_funcs)} functions:")
for f_idx, names in found_funcs.items():
    print(f"  Function {f_idx}: {names}")
