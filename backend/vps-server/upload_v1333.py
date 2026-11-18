import paramiko
import os
import json
import shutil

# 1. Copy locally to releases/v1.3.33
os.makedirs('releases/v1.3.33', exist_ok=True)
shutil.copy('android/app/build/outputs/apk/release/app-arm64-v8a-release.apk', 'releases/v1.3.33/AsanVPN-v1.3.33-arm64-v8a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-armeabi-v7a-release.apk', 'releases/v1.3.33/AsanVPN-v1.3.33-armeabi-v7a.apk')
shutil.copy('android/app/build/outputs/apk/release/app-universal-release.apk', 'releases/v1.3.33/AsanVPN-v1.3.33-universal.apk')
print("Copied APKs to releases/v1.3.33/")

# 2. Upload to VPS via SFTP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to VPS...")
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)
sftp = ssh.open_sftp()

print("Uploading AsanVPN-v1.3.33-arm64-v8a.apk...")
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-v1.3.33-arm64-v8a.apk')
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-arm64-v8a.apk', '/opt/asanvpn/AsanVPN-arm64-v8a.apk')

print("Uploading AsanVPN-v1.3.33-armeabi-v7a.apk...")
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-v1.3.33-armeabi-v7a.apk')
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-armeabi-v7a.apk', '/opt/asanvpn/AsanVPN-armeabi-v7a.apk')

print("Uploading AsanVPN-v1.3.33-universal.apk...")
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-universal.apk', '/opt/asanvpn/AsanVPN-v1.3.33-universal.apk')
sftp.put('releases/v1.3.33/AsanVPN-v1.3.33-universal.apk', '/opt/asanvpn/AsanVPN.apk')

version_data = {
    "versionName": "1.3.33",
    "versionCode": 39,
    "forceUpdate": False,
    "releaseNotes": "احترام کامل به حالت انتخاب دستی سرورها بدون سوییچ ناخواسته، اندازه‌گیری و نمایش زنده تاخیر (پینگ) سرور هر ۱۰ ثانیه، جلوگیری از نمایش رنگ سبز پیش از برقراری قطعی ارتباط، جستجو و سوییچ هوشمند آبشاری به سایر پنل‌ها در پس‌زمینه برای حالت هوش مصنوعی Gemini و تماس صوتی، و همگام‌سازی کامل کاربران میان تمامی پنل‌ها."
}

with open('version.json', 'w', encoding='utf-8') as f:
    json.dump(version_data, f, ensure_ascii=False, indent=2)

sftp.put('version.json', '/opt/asanvpn/version.json')
sftp.close()
print("Uploaded APKs and version.json to VPS!")

# 3. Update DB on VPS
update_script = f"""python3 -c '
import sqlite3, json, time
conn = sqlite3.connect("/etc/asanvpn/asanvpn.db")
c = conn.cursor()
val = json.dumps({json.dumps(version_data, ensure_ascii=False)}, ensure_ascii=False)
c.execute("INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at", ("__CONFIG_APP_UPDATE__", val, int(time.time())))
conn.commit()
print("Updated __CONFIG_APP_UPDATE__ in DB.")
'"""

stdin, stdout, stderr = ssh.exec_command(update_script)
print("DB UPDATE:\n", stdout.read().decode())
err = stderr.read().decode()
if err:
    print("DB ERR:\n", err)

ssh.close()
print("Deployment of v1.3.33 COMPLETE!")
