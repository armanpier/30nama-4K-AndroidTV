from hermes_dec.parsers.hbc_file_parser import HBCReader

bundle_path = r"C:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
reader = HBCReader()
with open(bundle_path, "rb") as f:
    reader.read_whole_file(f)

target_ids = {
    34482: "VideoSettingsQualityTitle",
    35480: "selectedQualityObject",
    34483: "VideoSettingsTitle",
    29914: "setCurrentQuality"
}

import struct

targets_bytes = {
    struct.pack("<H", k): v for k, v in target_ids.items()
}

found_funcs = {}
for i, fh in enumerate(reader.function_headers):
    offset = fh.offset
    size = fh.bytecodeSizeInBytes
    bc = reader.file_buffer[offset : offset + size]
    for b_pat, name in targets_bytes.items():
        if b_pat in bc:
            if i not in found_funcs:
                found_funcs[i] = []
            found_funcs[i].append(name)

print(f"Found matches in {len(found_funcs)} functions:")
for f_idx, names in found_funcs.items():
    fh = reader.function_headers[f_idx]
    func_name = reader.strings[fh.functionName] if fh.functionName < len(reader.strings) else "unnamed"
    print(f"  Function [{f_idx}] (name='{func_name}', size={fh.bytecodeSizeInBytes}, offset={fh.offset}): {names}")
