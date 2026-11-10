with open('30nama_login_dom.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = re.findall(r'(?:turnstile|sitekey|recaptcha|cf-turnstile)[^"\'><\s]{0,80}', text, re.I)
print(f"Total matches: {len(matches)}")
for m in set(matches):
    print(" ", m)
