import io
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.disassembly.hbc_disassembler import disassemble_function

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
with open(bundle_path, "rb") as f:
    raw_file_bytes = f.read()

reader = HBCReader()
reader.read_whole_file(io.BytesIO(raw_file_bytes))

# Disassemble Function 58064 (VideoPlayerSettingsModal)
print("Disassembling function 58064...")
instructions, lines = disassemble_function(reader, 58064)
with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_58064_disasm.txt", "w", encoding="utf-8") as out:
    for line in lines:
        out.write(line + "\n")
print(f"Written {len(lines)} lines to func_58064_disasm.txt")

# Disassemble Function 56789 (VideoPlayerScreen)
print("Disassembling function 56789...")
instructions, lines = disassemble_function(reader, 56789)
with open(r"c:\Users\Arman\Documents\antigravity\quirky-turing\func_56789_disasm.txt", "w", encoding="utf-8") as out:
    for line in lines:
        out.write(line + "\n")
print(f"Written {len(lines)} lines to func_56789_disasm.txt")
