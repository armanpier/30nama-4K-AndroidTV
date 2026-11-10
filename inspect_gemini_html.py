import sys
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('gemini_share_bot.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's search for "Android TV 4K Streaming Fix" in the html
idx = html.find('Android TV 4K Streaming Fix')
print("Index of title:", idx)
if idx != -1:
    print("Surrounding 500 chars:")
    print(repr(html[idx-100:idx+400]))

# Look for data arrays or JSON in script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    if 'Streaming' in s or 'Android' in s or 'Kodi' in s or '4k' in s.lower():
        print(f"Script {i} has keywords! Length: {len(s)}")
        # let's see if there are strings or json
        matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', s)
        print(f"  Total quoted strings: {len(matches)}")
        long_strings = [m for m in matches if len(m) > 100]
        print(f"  Long strings (>100 chars): {len(long_strings)}")
        for ls in long_strings[:5]:
            print("   --- SAMPLE:", ls[:150].replace('\\n', '\n'))

