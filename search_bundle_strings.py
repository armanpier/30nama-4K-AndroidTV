bundle_path = r"apk-extract\assets\index.android.bundle.orig"
with open(bundle_path, "rb") as f:
    data = f.read()

import re

# Find ASCII strings length 3 to 60
pattern = re.compile(rb'[A-Za-z0-9_\-\.\/]{3,60}')
matches = pattern.findall(data)

found = set()
for m in matches:
    try:
        s = m.decode('ascii')
        if any(w in s.lower() for w in ['login', 'auth', 'stream', 'qrlogin', 'signin', 'password', 'token']):
            found.add(s)
    except:
        pass

for s in sorted(found):
    if not s.startswith('node_modules') and not s.startswith('react-native') and len(s) < 30:
        print(s)
