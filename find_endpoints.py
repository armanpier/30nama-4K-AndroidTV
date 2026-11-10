import re

with open(r'apk-extract\assets\index.android.bundle.orig', 'rb') as f:
    data = f.read()

# Find all action words
# In React Native API calls, they might be like "action/xxx" or just "login", "register", "auth", "token"
words = set()
for m in re.finditer(rb'["\']([a-zA-Z0-9_\-\/]{3,50})["\']', data):
    w = m.group(1).decode('utf-8', errors='ignore')
    if any(k in w.lower() for k in ['login', 'auth', 'signin', 'token', 'user', 'stream', 'home', 'comment', 'movie', 'series']):
        words.add(w)

for w in sorted(words):
    if len(w) < 40 and not w.startswith('node_modules'):
        print(w)
