with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines[:960]):
    if "Reg8: 24" in line:
        print(f"Line {i:4d}: {line.strip()}")
