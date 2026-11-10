import json

transcript_path = r'C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\.system_generated\logs\transcript.jsonl'
with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        for c in data.get('tool_calls', []):
            if c.get('name') in ['write_file', 'edit_file']:
                path = c.get('arguments', {}).get('Path', '')
                if any(k in path.lower() for k in ['patch', 'bundle', 'repack', 'mod']):
                    print(f"Line {i}: {c.get('name')} -> {path}")
