import struct

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's search for "selectedQualityObject" byte offset in the entire file
s_bytes = b"selectedQualityObject"
pos = data.find(s_bytes)
print(f"'{s_bytes.decode()}' is at offset: {pos}")

# In Hermes, where does string storage start?
# Let's find out what points to this offset or offsets within string storage!
# StringStorageSize is 3348424 (0x3317c8).
# Notice pos is 4491270.
# 4491270 - 3348424 = 1142846.
# That means string storage is roughly in the range [1142846, 4491270 + len]!
# Let's find the start of string storage:
# Let's look for "/* [wrapped with " which was the first string found earlier at 1143000 approx!
print("Searching for string storage start...")
# Earlier: /* [wrapped with ...
first_str = b"/* [wrapped with "
pos_first = data.find(first_str)
print(f"First string at: {pos_first}")
