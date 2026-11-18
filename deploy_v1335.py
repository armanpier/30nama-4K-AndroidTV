import paramiko
import os
import json
import shutil
import time

print("--- DEPLOYING ASANVPN v1.3.35 ---")

# 1. Copy locally to releases/v1.3.35
os.makedirs('releases/v1.3.35', exist_ok=True)
shutil.copy('android/app/build/outputs/apk/release/app-arm64-v8a-release.apk', 'releases/v1.3.35/AsanVPN-v1.3.35-arm64-v8a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-armeabi-v7a-release.apk', 'releases/v1.3.35/AsanVPN-v1.3.35-armeabi-v7a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-universal-release.apk', 'releases/v1.3.35/AsanVPN-v1.3.35-universal.apk')
print("1. Copied APKs to releases/v1.3.35/")

# 2. Upload APKs to VPS via SFTP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("2. Connecting to VPS (95.182.87.115)...")
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=20)
sftp = ssh.open_sftp()

print("3. Uploading APKs to /opt/asanvpn/...")
sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-v1.3.35-arm64-v8a.apk')
sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-arm64-v8a.apk')

sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-v1.3.35-armeabi-v7a.apk')
sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-armeabi-v7a.apk')

sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-universal.apk', '/opt/asanvpn/AsanVPN-v1.3.35-universal.apk')
sftp.put('releases/v1.3.35/AsanVPN-v1.3.35-universal.apk', '/opt/asanvpn/AsanVPN.apk')

version_data = {
    "versionName": "1.3.35",
    "versionCode": 41,
    "forceUpdate": False,
    "releaseNotes": "سوییچ زنده و خودکار به پنل با اولویت بالاتر به محض تغییر اولویت در داشبورد بدون نیاز به خاموش/روشن کردن وی‌پی‌ان، افزایش تایم‌اوت تست کانکشن سرورها در حین اتصال فعال، و بررسی دوره‌ای اولویت‌ها هر ۶۰ ثانیه."
}

raw_json = json.dumps(version_data, ensure_ascii=False)

with sftp.file('/opt/asanvpn/version.json', 'w') as f:
    f.write(json.dumps(version_data, ensure_ascii=False, indent=2))

# Update DB
script_content = f"""import sqlite3, time
conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
c = conn.cursor()
val = {repr(raw_json)}
c.execute("INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at", ("__CONFIG_APP_UPDATE__", val, int(time.time())))
conn.commit()
conn.close()
print("SUCCESS: Updated __CONFIG_APP_UPDATE__ to v1.3.35 (code 41)")
"""

with sftp.file('/tmp/update_version_kv.py', 'w') as f:
    f.write(script_content)

sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/update_version_kv.py')
print("DB UPDATE:", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('systemctl restart asanvpn-api.service')
print("SERVICE RESTARTED:", stdout.read().decode())

ssh.close()
print("--- DEPLOYMENT COMPLETE ---")
