import re

with open('android/app/build/reports/tests/testDebugUnitTest/index.html', encoding='utf-8') as f:
    html = f.read()

failures = re.findall(r'<li class="failures">\s*<a href="([^"]+)">([^<]+)</a>', html)
print("Failures:", failures)

classes = re.findall(r'<tr>\s*<td class="failures"><a href="([^"]+)">([^<]+)</a></td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>', html)
print("Classes with failures:", classes)
