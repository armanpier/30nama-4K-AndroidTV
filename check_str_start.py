bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's find stringStorageSize = 3348424
# If stringStorageSize is 3348424, and the strings end around 4575350:
# 4575350 - 3348424 = 1226926!
# Look at 1226926:
# 1226926 + 3348424 = 4575350!
# That means 1226926 IS the start of string storage!
# Let's check data[1226920:1226940]!
print(f"Data around 1226926:")
for i in range(1226915, 1226940):
    print(f"  {i}: {hex(data[i])} '{chr(data[i]) if 32 <= data[i] <= 126 else '.'}'")
