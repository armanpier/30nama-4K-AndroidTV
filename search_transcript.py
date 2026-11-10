import json

transcript_path = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\.system_generated\logs\transcript.jsonl"

tokens_found = set()

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'c-token' in line or 'qrlogin' in line or 'token' in line:
            import re
            m = re.findall(r'[a-zA-Z0-9_-]{25,60}', line)
            for tok in m:
                if any(c.isupper() for c in tok) and any(c.islower() for c in tok) and any(c.isdigit() for c in tok):
                    if len(tok) == 32 or len(tok) == 40 or len(tok) == 44:
                        tokens_found.add(tok)

print("Potential tokens found in transcript:")
for t in tokens_found:
    print(" ", t)
