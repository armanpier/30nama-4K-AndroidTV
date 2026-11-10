import re

with open(r'apk-extract\assets\index.android.bundle.orig', 'rb') as f:
    data = f.read()

# find endpoints
matches = re.findall(rb'https://[a-zA-Z0-9.-]+\.30nama\.[a-zA-Z]+', data)
print('30nama domains:', set(m.decode() for m in matches))

for fid in [52655, 52658, 52661]:
    pass
