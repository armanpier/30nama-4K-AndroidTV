bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    data = f.read()

# Let's scan backwards from 1226915 until we see non-printable bytes or zeroes!
pos = 1226915
while pos > 0 and (32 <= data[pos] <= 126 or data[pos] in (10, 13, 9)):
    pos -= 1

print(f"Text began at: {pos + 1}")
print(f"Bytes before: {[hex(b) for b in data[pos-10:pos+1]]}")
print(f"First 50 chars: {data[pos+1:pos+51]}")
