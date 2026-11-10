import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('clean_conversation.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('kodi_addon_code_dump.txt', 'w', encoding='utf-8') as out:
    for i in range(2040, len(lines)):
        out.write(f"[{i}] {lines[i]}")

print("Wrote kodi_addon_code_dump.txt")
