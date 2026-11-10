import re

with open('auth_page_dom.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

print('Length:', len(text))
titles = re.findall(r'<title>(.*?)</title>', text, re.I)
print('Title:', titles)
forms = re.findall(r'<form.*?</form>', text, re.I | re.DOTALL)
print('Forms found:', len(forms))
for form in forms:
    print('FORM:', form[:300])
buttons = re.findall(r'<button.*?</button>', text, re.I | re.DOTALL)
print('Buttons found:', len(buttons))
for btn in buttons:
    print('BTN:', btn)
