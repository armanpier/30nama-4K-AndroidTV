import struct
import re

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

magic = data[:8]
version = struct.unpack_from("<I", data, 8)[0]
print(f"Magic: {magic.hex()}, version: {version}")

# Header unpacking
(file_len, global_idx, func_count, string_kind_count, id_count, string_count, overflow_count, string_storage_size) = struct.unpack_from("<8I", data, 32)
print(f"FileLen: {file_len}, FuncCount: {func_count}, IDCount: {id_count}, StringCount: {string_count}, StringStorageSize: {string_storage_size}")

# Find where string storage is located
# Let's inspect the layout of Hermes Bytecode v94:
# After header (offset 64 or 72?):
# Function table header / ArrayBuffer / etc.
# Or we can scan the data for all UTF-8 and UTF-16 strings
print("Scanning strings...")

# Look for quality keywords
keywords = [b"1080", b"720", b"480", b"2160", b"4K", b"4k", b"quality", b"Quality", b"resolution", b"Resolution", b"stream", b"stream_link", b"m3u8", b"abrkocholo", b"divyacamilla", b"30nama", b"30tv", b"exoplayer", b"jwplayer"]

for kw in keywords:
    matches = [m.start() for m in re.finditer(re.escape(kw), data)]
    print(f"Keyword {kw.decode(errors='ignore')}: found {len(matches)} occurrences")
    for pos in matches[:5]:
        start = max(0, pos - 40)
        end = min(len(data), pos + len(kw) + 40)
        chunk = data[start:end]
        # print printable
        printable = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"  @{pos}: {printable}")
