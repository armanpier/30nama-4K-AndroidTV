transcript_path = r"C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if 'DpJjksP5NbyUqVAeUUCReR4RvSU2t2WY' in line:
            print(f"Found in line {i}:")
            # print surrounding 300 chars
            idx = line.find('DpJjksP5NbyUqVAeUUCReR4RvSU2t2WY')
            print(line[max(0, idx-100):min(len(line), idx+200)])
