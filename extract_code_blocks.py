import sys
import re
from html.parser import HTMLParser
import html

sys.stdout.reconfigure(encoding='utf-8')

with open('chrome_dump.html', 'r', encoding='utf-8', errors='ignore') as f:
    raw_html = f.read()

# Let's find all code blocks: <pre ...><code>...</code></pre> or <code-block ...>
# Or <pre>...</pre>
code_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', raw_html, re.DOTALL)
print(f"Total <pre> code blocks found: {len(code_blocks)}")

for i, cb in enumerate(code_blocks):
    # strip tags
    clean = re.sub(r'<[^>]+>', '', cb)
    clean = html.unescape(clean)
    print(f"\n================ CODE BLOCK {i} (len {len(clean)}) ================")
    print('\n'.join(clean.split('\n')[:15]))
    with open(f'code_block_{i}.txt', 'w', encoding='utf-8') as out:
        out.write(clean)

print("\nDone extracting all code blocks!")
