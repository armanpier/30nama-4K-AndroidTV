import hermes_dec
from hermes_dec.hbc.HBCFile import HBCFile

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
print("Loading HBC file...")
hbc = HBCFile(bundle_path)
print("HBC loaded!")

print(f"Total functions: {len(hbc.functions)}")
print(f"Total strings: {len(hbc.strings)}")

# Let's find string IDs for our target strings
targets = ["VideoSettingsQualityTitle", "selectedQualityObject", "VideoSettingsTitle", "getQualityLevel", "setCurrentQuality"]
target_ids = {}
for i, s in enumerate(hbc.strings):
    if s in targets:
        target_ids[s] = i
        print(f"String '{s}' has ID {i}")

# Now let's scan all functions to find which functions reference these string IDs in their instructions!
for name, sid in target_ids.items():
    print(f"\nSearching for references to '{name}' (ID {sid})...")
    for f_idx, func in enumerate(hbc.functions):
        # Check bytecode of func
        # In hermes instructions, string/id operands are uint16 or uint32
        for inst in func.instructions:
            # check operands
            for op in inst.operands:
                if op == sid:
                    print(f"  Found in Function [{f_idx}] (name: {getattr(func, 'name', 'unnamed')}): {inst}")
                    break
