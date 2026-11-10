import struct

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's find String Table in Hermes v94:
# In Hermes v94, the header has:
# 32: file_len
# 36: global_code_idx
# 40: func_count
# 44: string_kind_count
# 48: id_count
# 52: string_count
# 56: overflow_count
# 60: string_storage_size

(file_len, global_idx, func_count, string_kind_count, id_count, string_count, overflow_count, string_storage_size) = struct.unpack_from("<8I", data, 32)

# Where does string storage start?
# In find_string_storage.py, we found the first string at offset 1226963 (or 0x12b8d3)
# Let's locate the string table entries!
# String count is 36097.
# If each entry is 4 bytes, 36097 * 4 = 144,388 bytes.
# Overflow string count is 4939 * 8 bytes = 39,512 bytes.
# Notice: 1226963 - (144388 + 39512) = 1,043,063.
# Let's scan for a 4-byte entry pointing to 0 (the start of string storage)!

target_offset = data.find(b"VideoSettingsQualityTitle")
rel_offset = target_offset - 1226963  # relative to string storage
print(f"Target rel_offset: {rel_offset} (0x{rel_offset:x})")

# Let's search data for entries pointing to rel_offset
# In Hermes SmallStringTableEntry:
# offset is lower 24 bits (or 23 bits)!
# length is 7 bits or 8 bits!
# Let's search for (rel_offset & 0xFFFFFF) in data before 1226963:
target_bytes_24 = struct.pack("<I", rel_offset & 0xFFFFFF)[:3]
matches = []
for i in range(0, 1226963 - 4):
    val = struct.unpack_from("<I", data, i)[0]
    # Check if offset matches rel_offset
    if (val & 0xFFFFFF) == rel_offset:
        matches.append((i, val))

print(f"Matches for rel_offset: {len(matches)}")
for offset, val in matches:
    print(f"  Entry at {offset} (0x{offset:x}): val = 0x{val:08x}, length = {(val >> 24) & 0x7f}")
