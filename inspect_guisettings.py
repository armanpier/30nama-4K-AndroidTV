import re

with open('kodi_guisettings.xml', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'<setting id="[^"]*webserver[^"]*"[^>]*>.*?</setting>', text, re.IGNORECASE):
    print(m.group(0))

for m in re.finditer(r'<setting id="[^"]*control[^"]*"[^>]*>.*?</setting>', text, re.IGNORECASE):
    print(m.group(0))
