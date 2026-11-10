import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('clean_conversation.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
# Write lines 1700 to the end
with open('kodi_addon_spec.txt', 'w', encoding='utf-8') as out:
    for i in range(1650, len(lines)):
        out.write(f"[{i}] {lines[i]}")

print("Wrote kodi_addon_spec.txt from line 1650 onwards")
