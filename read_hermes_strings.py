# In Hermes bytecode, let's find the String ID for "VideoSettingsQualityTitle"
# and then find functions that reference that String ID!

import struct

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Header:
# 0..8: Magic
# 8..12: Version
# 12..32: SHA1
# 32..36: FileLength
# 36..40: GlobalCodeIndex
# 40..44: FunctionCount
# 44..48: StringKindCount
# 48..52: IdentifierCount
# 52..56: StringCount
# 56..60: OverflowStringCount
# 60..64: StringStorageSize
(file_len, global_idx, func_count, string_kind_count, id_count, string_count, overflow_count, string_storage_size) = struct.unpack_from("<8I", data, 32)
print(f"Functions: {func_count}, Strings: {string_count}, StringStorage: {string_storage_size}")

# In Hermes v94:
# After header (offset 64):
# String Table starts at offset 64!
# Let's verify string table entry size.
# In SmallStringTableEntry: uint32 isUTF16:1, length:7, offset:24 -> size is 4 bytes per entry!
# Let's test reading String Table at offset 64:
str_table_offset = 64
# After string table is overflow string table (8 bytes per entry)
# Let's calculate where String Storage starts:
overflow_offset = str_table_offset + string_count * 4
string_storage_offset = overflow_offset + overflow_count * 8
print(f"String storage expected at: {string_storage_offset}")

# Let's verify string storage by decoding the first few strings:
def get_string(idx):
    entry_offset = str_table_offset + idx * 4
    val = struct.unpack_from("<I", data, entry_offset)[0]
    is_utf16 = (val >> 31) & 1
    length = (val >> 24) & 0x7F
    offset = val & 0xFFFFFF
    if length == 0x7F:
        # overflow entry
        pass
    raw = data[string_storage_offset + offset : string_storage_offset + offset + length]
    if is_utf16:
        return raw.decode("utf-16le", errors="ignore")
    else:
        return raw.decode("utf-8", errors="ignore")

# Test reading first 10 strings:
for i in range(min(15, string_count)):
    try:
        s = get_string(i)
        print(f"Str[{i}]: {repr(s)}")
    except Exception as e:
        print(f"Error reading str {i}: {e}")
        break
