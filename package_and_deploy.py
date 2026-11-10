import os
import zipfile
import subprocess

addon_dir = 'plugin.video.30nama'
zip_filename = 'plugin.video.30nama.zip'

if os.path.exists(zip_filename):
    os.remove(zip_filename)

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(addon_dir):
        if '__pycache__' in root:
            continue
        for f in files:
            if f.endswith('.pyc'): continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, '.')
            zf.write(full_path, rel_path)

print(f"Packaged {zip_filename} ({os.path.getsize(zip_filename)} bytes)")

adb = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')
subprocess.run([adb, 'push', zip_filename, f'/sdcard/Download/{zip_filename}'])

# Push updated files directly into Kodi installed addon directory
dest_addon_dir = '/sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/plugin.video.30nama'
subprocess.run([adb, 'push', 'plugin.video.30nama/default.py', f'{dest_addon_dir}/default.py'])
subprocess.run([adb, 'push', 'plugin.video.30nama/addon.xml', f'{dest_addon_dir}/addon.xml'])
subprocess.run([adb, 'push', 'plugin.video.30nama/icon.png', f'{dest_addon_dir}/icon.png'])

# Push resources/art
subprocess.run([adb, 'shell', f'mkdir -p {dest_addon_dir}/resources/art'])
subprocess.run([adb, 'push', 'plugin.video.30nama/resources/art', f'{dest_addon_dir}/resources/'])
print("Successfully pushed all files and artwork to Kodi!")
