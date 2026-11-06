import os
import sys
import zipfile
import re
import subprocess
import shutil

SDK_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk")
BUILD_TOOLS_DIR = os.path.join(SDK_DIR, "build-tools", "34.0.0")
ZIPALIGN = os.path.join(BUILD_TOOLS_DIR, "zipalign.exe")
APKSIGNER = os.path.join(BUILD_TOOLS_DIR, "apksigner.bat")
KEYSTORE = "debug.keystore"
JAVA_HOME = r"C:\Program Files\Android\Android Studio\jbr"

def build_custom_apk(base_apk, output_apk, arch_label="x86"):
    print(f"\n========================================================")
    print(f"BUILDING 30NAMA 4K STANDALONE APK ({arch_label.upper()})")
    print(f"Base APK: {base_apk}")
    print(f"Output APK: {output_apk}")
    print(f"========================================================\n")

    if not os.path.exists(base_apk):
        raise FileNotFoundError(f"Base APK not found: {base_apk}")

    unaligned_apk = output_apk.replace(".apk", "-unaligned.apk")
    aligned_apk = output_apk.replace(".apk", "-aligned.apk")

    for f in [unaligned_apk, aligned_apk, output_apk]:
        if os.path.exists(f):
            try: os.remove(f)
            except OSError: pass

    # Read branding replacements
    banner_data = open(r"branding_assets\banner_320x180.png", "rb").read()
    splash_data = open(r"branding_assets\splash_1920x1080.jpg", "rb").read()
    icon_map = {
        "res/OK.png": open(r"branding_assets\OK.png", "rb").read(),
        "res/8X.png": open(r"branding_assets\8X.png", "rb").read(),
        "res/Dw.png": open(r"branding_assets\Dw.png", "rb").read(),
        "res/M2.png": open(r"branding_assets\M2.png", "rb").read(),
        "res/Gd.png": open(r"branding_assets\Gd.png", "rb").read(),
        "res/5p.png": open(r"branding_assets\5p.png", "rb").read(),
    }

    # Prepare plugin files
    addon_source_dir = "plugin.video.30nama"
    addon_files = {}
    for root, dirs, files in os.walk(addon_source_dir):
        if "__pycache__" in root: continue
        for fname in files:
            if fname.endswith(".pyc"): continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, addon_source_dir).replace("\\", "/")
            apk_entry = f"assets/addons/plugin.video.30nama/{rel_path}"
            with open(full_path, "rb") as af:
                addon_files[apk_entry] = af.read()
    print(f"Found {len(addon_files)} plugin.video.30nama addon files to inject.")

    # Prepare userdata files
    advancedsettings_data = open("advancedsettings.xml", "rb").read()
    autoexec_script = (
        "# -*- coding: utf-8 -*-\n"
        "import time, xbmc\n"
        "for _ in range(30):\n"
        "    if xbmc.getCondVisibility('Window.IsVisible(home)'):\n"
        "        time.sleep(0.5)\n"
        "        xbmc.executebuiltin('ActivateWindow(videos, plugin://plugin.video.30nama/, return)')\n"
        "        break\n"
        "    time.sleep(0.2)\n"
    ).encode("utf-8")
    
    vip_token = ""

    preconfigured_settings = (
        '<settings version="2">\n'
        f'    <setting id="c_token">{vip_token}</setting>\n'
        '    <setting id="proxy_url"></setting>\n'
        '    <setting id="tv_api_key">VdapnkLG9EHsSmF8yeKcb4253RAuN6YX</setting>\n'
        '    <setting id="desktop_api_key">et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ</setting>\n'
        '    <setting id="auto_fix_persian_encoding">true</setting>\n'
        '    <setting id="sub_priority">0</setting>\n'
        '    <setting id="auto_start_on_boot">true</setting>\n'
        '</settings>\n'
    ).encode("utf-8")

    userdata_files = {
        "assets/userdata/advancedsettings.xml": advancedsettings_data,
        "assets/userdata/autoexec.py": autoexec_script,
        "assets/userdata/addon_data/plugin.video.30nama/settings.xml": preconfigured_settings,
    }

    with zipfile.ZipFile(base_apk, "r") as zin, zipfile.ZipFile(unaligned_apk, "w", zipfile.ZIP_DEFLATED) as zout:
        infolist = zin.infolist()
        total = len(infolist)
        print(f"Processing {total} original APK entries...")

        for i, info in enumerate(infolist):
            uname = info.filename.upper()
            # 1. Skip signature files
            if uname.startswith("META-INF/") and (
                uname.endswith(".SF") or uname.endswith(".RSA") or uname.endswith(".DSA") or uname.endswith(".EC") or uname == "META-INF/MANIFEST.MF"
            ):
                continue

            # 2. Patch resources.arsc (Kodi -> 30TV)
            if info.filename == "resources.arsc":
                raw_arsc = bytearray(zin.read(info.filename))
                target = b"\x04\x04Kodi\x00"
                idx = raw_arsc.find(target)
                if idx != -1:
                    raw_arsc[idx:idx+len(target)] = b"\x04\x0430TV\x00"
                    print("Patched resources.arsc: app name -> '30TV'")
                # MUST BE STORED UNCOMPRESSED for Android 11+
                zout.writestr(info.filename, raw_arsc, compress_type=zipfile.ZIP_STORED)
                continue

            # 3. Patch assets/system/addon-manifest.xml (register 30nama addon)
            if info.filename == "assets/system/addon-manifest.xml":
                manifest_text = zin.read(info.filename).decode("utf-8")
                if "plugin.video.30nama" not in manifest_text:
                    manifest_text = manifest_text.replace("<addons>\n", "<addons>\n  <addon>plugin.video.30nama</addon>\n")
                    print("Patched assets/system/addon-manifest.xml: registered 'plugin.video.30nama'")
                zout.writestr(info.filename, manifest_text.encode("utf-8"))
                continue

            # 4. Patch assets/system/settings/settings.xml (Default -> Arial for font)
            if info.filename == "assets/system/settings/settings.xml":
                settings_text = zin.read(info.filename).decode("utf-8")
                # Replace font setting default with Arial
                patt = r'(<setting id="lookandfeel\.font"[^>]*>[\s\S]*?<default>)Default(</default>)'
                settings_text, count = re.subn(patt, r'\g<1>Arial\g<2>', settings_text)
                if count:
                    print("Patched assets/system/settings/settings.xml: default font -> 'Arial'")
                else:
                    print("Warning: lookandfeel.font pattern not matched, attempting fallback replace...")
                    settings_text = settings_text.replace('<default>Default</default>', '<default>Arial</default>', 1)
                zout.writestr(info.filename, settings_text.encode("utf-8"))
                continue

            # 5. Replace Leanback banner
            if info.filename == "res/OA.png":
                print("Replaced Leanback banner: res/OA.png (320x180)")
                zout.writestr(info.filename, banner_data)
                continue

            # 6. Replace App Splash
            if info.filename == "assets/media/splash.jpg":
                print("Replaced splash screen: assets/media/splash.jpg (1920x1080)")
                zout.writestr(info.filename, splash_data)
                continue

            # 7. Replace App Icons
            if info.filename in icon_map:
                zout.writestr(info.filename, icon_map[info.filename])
                continue

            # Copy unchanged file
            raw = zin.read(info.filename)
            zout.writestr(info, raw)

        # Inject 30nama addon files
        for apk_path, data in addon_files.items():
            zout.writestr(apk_path, data)

        # Inject userdata files
        for apk_path, data in userdata_files.items():
            zout.writestr(apk_path, data)

    print(f"\nRepacked unaligned APK created: {unaligned_apk} ({os.path.getsize(unaligned_apk)} bytes)")

    # Align APK using zipalign
    print("Aligning APK with zipalign...")
    res_align = subprocess.run([ZIPALIGN, "-p", "-f", "4", unaligned_apk, aligned_apk], capture_output=True, text=True)
    if res_align.returncode != 0:
        raise RuntimeError(f"zipalign failed: {res_align.stderr}")
    print(f"Aligned APK created: {aligned_apk} ({os.path.getsize(aligned_apk)} bytes)")

    res_chk = subprocess.run([ZIPALIGN, "-c", "4", aligned_apk], capture_output=True, text=True)
    print("Zipalign check:", "OK (Verification successful)" if res_chk.returncode == 0 else f"FAIL: {res_chk.stderr}")

    # Sign APK using apksigner
    print("Signing APK with debug.keystore...")
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA_HOME
    cmd_sign = [
        APKSIGNER, "sign",
        "--ks", KEYSTORE,
        "--ks-pass", "pass:android",
        "--key-pass", "pass:android",
        "--out", output_apk,
        aligned_apk
    ]
    res_sign = subprocess.run(cmd_sign, env=env, capture_output=True, text=True)
    if res_sign.returncode != 0:
        raise RuntimeError(f"apksigner failed: {res_sign.stderr}")

    print("Verifying APK signature...")
    cmd_verify = [APKSIGNER, "verify", "--verbose", output_apk]
    res_verify = subprocess.run(cmd_verify, env=env, capture_output=True, text=True)
    print(res_verify.stdout)
    if res_verify.returncode != 0:
        raise RuntimeError(f"apksigner verify failed: {res_verify.stderr}")

    # Cleanup temp files
    try: os.remove(unaligned_apk)
    except OSError: pass
    try: os.remove(aligned_apk)
    except OSError: pass

    final_size_mb = os.path.getsize(output_apk) / (1024 * 1024)
    print(f"SUCCESS: Built {output_apk} ({final_size_mb:.2f} MB)")
    return output_apk

if __name__ == "__main__":
    out = build_custom_apk("kodi-21.3-Omega-x86.apk", "30nama-4K-AndroidTV-x86.apk", "x86")
    print("\nDONE: Standalone APK is ready:", out)
