import struct

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# In Hermes v94:
# Header is at 0:
# struct BytecodeFileHeader {
#   uint64_t magic;
#   uint32_t version;
#   uint8_t sourceHash[20];
#   uint32_t fileLength;
#   uint32_t globalCodeIndex;
#   uint32_t functionCount;
#   uint32_t stringKindCount;
#   uint32_t identifierCount;
#   uint32_t stringCount;
#   uint32_t overflowStringCount;
#   uint32_t stringStorageSize;
#   ...
# }

# Let's search the data for the string "/* [wrapped with " and look at the bytes immediately before it
pos = data.find(b"/* [wrapped with ")
print(f"'/* [wrapped with ' at {pos}")
# Show 64 bytes before pos:
print("Before pos:")
print(data[pos-64:pos])
