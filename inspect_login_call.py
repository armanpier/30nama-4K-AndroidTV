with open(r'apk-extract\assets\index.android.bundle.orig', 'rb') as f:
    data = f.read()

import re

# Find function or context around qrlogin_login
idx = data.find(b'qrlogin_login')
while idx != -1:
    print(f"--- MATCH AT {idx} ---")
    chunk = data[max(0, idx-200):min(len(data), idx+300)]
    words = re.findall(rb'[a-zA-Z0-9_\-\.]{3,}', chunk)
    print("Words:", [w.decode(errors='ignore') for w in words])
    idx = data.find(b'qrlogin_login', idx+1)
