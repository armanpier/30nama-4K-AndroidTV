with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

for j in range(930, 970):
    print(f"{j:4d}: {lines[j].strip()}")
