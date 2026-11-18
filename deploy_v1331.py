import os
import sys
import paramiko
import json

VPS_HOST = '95.182.87.115'
VPS_USER = 'root'
VPS_PASS = 'Arman4237340'
TARGET_DIR = '/opt/asanvpn'
VERSION_NAME = '1.3.31'
VERSION_CODE = 37

LOCAL_RELEASE_DIR = r'c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\outputs\apk\release'

arm64_apk = os.path.join(LOCAL_RELEASE_DIR, 'app-arm64-v8a-release.apk')
armv7_apk = os.path.join(LOCAL_RELEASE_DIR, 'app-armeabi-v7a-release.apk')
universal_apk = os.path.join(LOCAL_RELEASE_DIR, 'app-universal-release.apk')

for path, name in [(arm64_apk, 'arm64'), (armv7_apk, 'armeabi-v7a'), (universal_apk, 'universal')]:
    if not os.path.exists(path):
        print(f"ERROR: Missing local APK: {path}")
        sys.exit(1)
    print(f"Found {name} APK: {path} ({os.path.getsize(path):,} bytes)")

print("Connecting to VPS via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, port=22, username=VPS_USER, password=VPS_PASS, timeout=30)
sftp = ssh.open_sftp()

def upload_with_progress(local_path, remote_path):
    print(f"Uploading {os.path.basename(local_path)} -> {remote_path} ...")
    sftp.put(local_path, remote_path)
    print("Done.")

# Upload main versioned files
upload_with_progress(arm64_apk, f'{TARGET_DIR}/AsanVPN-v{VERSION_NAME}-arm64-v8a.apk')
upload_with_progress(armv7_apk, f'{TARGET_DIR}/AsanVPN-v{VERSION_NAME}-armeabi-v7a.apk')
upload_with_progress(universal_apk, f'{TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk')

# Copy to common fallback symlinks / targets
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-arm64-v8a.apk {TARGET_DIR}/AsanVPN-arm64-v8a.apk')
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-arm64-v8a.apk {TARGET_DIR}/asanvpn-arm64.apk')

ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-armeabi-v7a.apk {TARGET_DIR}/AsanVPN-armeabi-v7a.apk')

ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk {TARGET_DIR}/AsanVPN-universal.apk')
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk {TARGET_DIR}/AsanVPN.apk')
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk {TARGET_DIR}/AsanVPN-latest.apk')
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk {TARGET_DIR}/asanvpn-universal.apk')
ssh.exec_command(f'cp {TARGET_DIR}/AsanVPN-v{VERSION_NAME}-universal.apk {TARGET_DIR}/asanvpn.apk')

# Update __CONFIG_APP_UPDATE__ in sqlite
update_payload = {
    "versionName": VERSION_NAME,
    "versionCode": VERSION_CODE,
    "forceUpdate": False,
    "releaseNotes": "افزودن حالت اختصاصی تماس صوتی، کلاب‌هاوس و بازی‌های آنلاین (Voice Call & WebRTC) با فیلتر خودکار لینک‌های فاقد UDP، تست زنده اتصال UDP در تنظیمات و بهینه‌سازی ترافیک Realtime."
}

vps_script = f'''
import sqlite3, json

conn = sqlite3.connect("/etc/asanvpn/asanvpn.db")
c = conn.cursor()
val = {json.dumps(json.dumps(update_payload, ensure_ascii=False))}
c.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES ('__CONFIG_APP_UPDATE__', ?)", (val,))
conn.commit()
conn.close()
print("Updated __CONFIG_APP_UPDATE__ to v{VERSION_NAME}")
'''

with sftp.file('/tmp/update_version_db.py', 'w') as f:
    f.write(vps_script)

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/update_version_db.py')
print("DB UPDATE:\n" + stdout.read().decode())

# Update version.json on disk
version_json = {
    "versionName": VERSION_NAME,
    "versionCode": VERSION_CODE,
    "forceUpdate": False,
    "releaseNotes": update_payload["releaseNotes"]
}
with sftp.file(f'{TARGET_DIR}/version.json', 'w') as f:
    json.dump(version_json, f, indent=2, ensure_ascii=False)
print("Updated /opt/asanvpn/version.json")

sftp.close()
ssh.close()
print(f"v{VERSION_NAME} Deployment Complete!")
