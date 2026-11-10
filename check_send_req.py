with open("action_class_disasm.txt", "r", encoding="utf-16") as f:
    text = f.read()

idx = text.find("string_id: 33143")
print(text[idx:idx+300])
