import paramiko
import os
import json
import shutil
import time

print("--- DEPLOYING ASANVPN v1.3.43 ---")

# 1. Copy locally to releases/v1.3.43
os.makedirs('releases/v1.3.43', exist_ok=True)
shutil.copy('android/app/build/outputs/apk/release/app-arm64-v8a-release.apk', 'releases/v1.3.43/AsanVPN-v1.3.43-arm64-v8a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-armeabi-v7a-release.apk', 'releases/v1.3.43/AsanVPN-v1.3.43-armeabi-v7a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-universal-release.apk', 'releases/v1.3.43/AsanVPN-v1.3.43-universal.apk')
print("1. Copied APKs to releases/v1.3.43/")

# 2. Upload APKs to VPS via SFTP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("2. Connecting to VPS (95.182.87.115)...")
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=20)
sftp = ssh.open_sftp()

print("3. Uploading APKs to /opt/asanvpn/...")
sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-v1.3.43-arm64-v8a.apk')
sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-arm64-v8a.apk')

sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-v1.3.43-armeabi-v7a.apk')
sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-armeabi-v7a.apk')

sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-universal.apk', '/opt/asanvpn/AsanVPN-v1.3.43-universal.apk')
sftp.put('releases/v1.3.43/AsanVPN-v1.3.43-universal.apk', '/opt/asanvpn/AsanVPN.apk')

version_data = {
    "versionName": "1.3.43",
    "versionCode": 49,
    "forceUpdate": False,
    "releaseNotes": "نمایش تست سرعت دانلود ۵ مگابایتی در کارت سرور متصل در صفحه اصلی و پنجره انتخاب سرور، اصلاح مسیر تست اتصال زنده گوگل جمینای (Google Gemini) از طریق پروکسی داخلی V2Ray جهت رفع خطای مسدودی کاذب، و بهینه‌سازی ذخیره‌سازی شاخص‌های سرور."
}

with open('version.json', 'w', encoding='utf-8') as f:
    json.dump(version_data, f, ensure_ascii=False, indent=2)

sftp.put('version.json', '/opt/asanvpn/version.json')
sftp.close()
print("4. SFTP upload complete!")

# 3. Update DB & restart service
print("5. Updating __CONFIG_APP_UPDATE__ and restarting asanvpn-api.service...")
raw_json = json.dumps(version_data, ensure_ascii=False)
update_py = f"""import sqlite3, time
conn = sqlite3.connect("/etc/asanvpn/asanvpn.db")
c = conn.cursor()
val = {repr(raw_json)}
c.execute("INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at", ("__CONFIG_APP_UPDATE__", val, int(time.time())))
conn.commit()
print("Updated __CONFIG_APP_UPDATE__ in DB to v1.3.43.")
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/update_v1343_db.py', 'w') as f:
    f.write(update_py)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/update_v1343_db.py')
print("DB UPDATE:", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('systemctl restart asanvpn-api.service && systemctl status asanvpn-api.service --no-pager')
print("SERVICE STATUS:\n", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8000/api/v1/app/version')
print("API VERSION RESPONSE:\n", stdout.read().decode())

ssh.close()
print("--- DEPLOYMENT COMPLETE ---")
