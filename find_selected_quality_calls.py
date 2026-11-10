with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "selectedQualityObject" in line:
        start = max(0, i - 10)
        end = min(len(lines), i + 10)
        print(f"--- Around line {i} ---")
        for j in range(start, end):
            print(f"{j:4d}: {lines[j].strip()}")
