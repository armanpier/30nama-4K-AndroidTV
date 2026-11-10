import os
import sys
import zipfile

def repack_apk(orig_apk_path, patched_bundle_path, out_apk_path):
    print(f"Repacking {orig_apk_path} -> {out_apk_path}")
    print(f"Using patched bundle: {patched_bundle_path}")
    
    with open(patched_bundle_path, "rb") as f:
        patched_bundle_data = f.read()
    print(f"Patched bundle size: {len(patched_bundle_data)} bytes")
    
    class AlignedZipFile(zipfile.ZipFile):
        def _open_to_write(self, zinfo, force_zip64=False):
            if zinfo.compress_type == 0:  # ZIP_STORED
                cur_pos = self.fp.tell()
                fname_bytes, _ = zinfo._encodeFilenameFlags()
                extra_len = len(zinfo.extra or b"")
                hdr_len = 30 + len(fname_bytes) + extra_len
                data_offset = cur_pos + hdr_len
                pad = (4 - (data_offset % 4)) % 4
                if pad > 0:
                    zinfo.extra = (zinfo.extra or b"") + b"\x00" * pad
            return super()._open_to_write(zinfo, force_zip64=force_zip64)

    sig_extensions = (".SF", ".RSA", ".DSA", ".EC")
    
    with zipfile.ZipFile(orig_apk_path, "r") as zin:
        infolist = zin.infolist()
        total = len(infolist)
        print(f"Total entries in original APK: {total}")
        
        with AlignedZipFile(out_apk_path, "w") as zout:
            written_count = 0
            for i, info in enumerate(infolist):
                # Skip signature files
                upper_name = info.filename.upper()
                if upper_name.startswith("META-INF/") and (
                    upper_name.endswith(".SF")
                    or upper_name.endswith(".RSA")
                    or upper_name.endswith(".DSA")
                    or upper_name.endswith(".EC")
                    or upper_name == "META-INF/MANIFEST.MF"
                ):
                    continue
                
                # Create a clean zinfo
                new_info = zipfile.ZipInfo(info.filename, info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                # Strip previous zero-padding from extra if stored
                if info.compress_type == 0:
                    new_info.extra = (info.extra or b"").rstrip(b"\x00")
                else:
                    new_info.extra = info.extra or b""
                
                if info.filename == "assets/index.android.bundle":
                    print(f"Replacing {info.filename} with patched bundle ({len(patched_bundle_data)} bytes)")
                    zout.writestr(new_info, patched_bundle_data, compress_type=zipfile.ZIP_DEFLATED)
                else:
                    data = zin.read(info.filename)
                    zout.writestr(new_info, data, compress_type=info.compress_type)
                
                written_count += 1
                if written_count % 500 == 0:
                    print(f"Processed {written_count} / {total} entries...")

    print(f"Repack complete! Total written entries: {written_count}")
    print(f"Output APK size: {os.path.getsize(out_apk_path)} bytes")

if __name__ == "__main__":
    orig = r"c:\Users\Arman\Downloads\30tv-3.2.3.apk"
    bundle = r"c:\Users\Arman\Documents\antigravity\quirky-turing\apk-extract\assets\index.android.bundle"
    out = r"c:\Users\Arman\Documents\antigravity\quirky-turing\30tv-3.2.3-4k-mod-unsigned.apk"
    repack_apk(orig, bundle, out)
