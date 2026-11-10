with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "UInt8: 66" in line:
        start = max(0, i - 5)
        end = min(len(lines), i + 10)
        print(f"--- Line {i} ---")
        for j in range(start, end):
            print(f"{j:4d}: {lines[j].strip()}")
