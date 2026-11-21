import paramiko
import os
import json
import shutil
import time
from upload_virustotal import scan_file_virustotal

print("=== DEPLOYING ASANVPN v1.3.45 (versionCode 51) ===")

# 1. Update version.json locally
version_data = {
    "versionName": "1.3.45",
    "versionCode": 51,
    "forceUpdate": False,
    "releaseNotes": "پشتیبانی کامل از پروتکل نسل جدید هیستریا (Hysteria 2 UDP)، الگوریتم هوشمند انتخاب سرور با اولویت‌بندی پیشرفته و آبشاری (تست ۵ سرور سریع اولویت ۱ به صورت نوبتی و انتقال خودکار به اولویت ۲ در صورت اختلال)، قابلیت جدید سنجش سرعت دانلود و آپلود دستی سرورها با حجم قابل تنظیم."
}

with open('version.json', 'w', encoding='utf-8') as f:
    json.dump(version_data, f, ensure_ascii=False, indent=2)
print("1. Updated version.json locally.")

# 2. Copy APKs to releases/v1.3.45
os.makedirs('releases/v1.3.45', exist_ok=True)
arm64_apk = 'releases/v1.3.45/AsanVPN-v1.3.45-arm64-v8a.apk'
armv7_apk = 'releases/v1.3.45/AsanVPN-v1.3.45-armeabi-v7a.apk'
univ_apk = 'releases/v1.3.45/AsanVPN-v1.3.45-universal.apk'

shutil.copy('android/app/build/outputs/apk/release/app-arm64-v8a-release.apk', arm64_apk)
shutil.copy('android/app/build/outputs/apk/release/app-armeabi-v7a-release.apk', armv7_apk)
shutil.copy('android/app/build/outputs/apk/release/app-universal-release.apk', univ_apk)
print("2. Copied APKs to releases/v1.3.45/")

# 3. Connect to VPS and upload
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("3. Connecting to VPS (95.182.87.115)...")
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=20)
sftp = ssh.open_sftp()

print("4. Uploading APKs to /opt/asanvpn/...")
sftp.put(arm64_apk, '/opt/asanvpn/AsanVPN-v1.3.45-arm64-v8a.apk')
sftp.put(arm64_apk, '/opt/asanvpn/AsanVPN-arm64-v8a.apk')

sftp.put(armv7_apk, '/opt/asanvpn/AsanVPN-v1.3.45-armeabi-v7a.apk')
sftp.put(armv7_apk, '/opt/asanvpn/AsanVPN-armeabi-v7a.apk')

sftp.put(univ_apk, '/opt/asanvpn/AsanVPN-v1.3.45-universal.apk')
sftp.put(univ_apk, '/opt/asanvpn/AsanVPN.apk')

sftp.put('version.json', '/opt/asanvpn/version.json')
sftp.close()
print("5. SFTP upload complete!")

# 4. Update DB & restart service
print("6. Updating __CONFIG_APP_UPDATE__ and restarting asanvpn-api.service...")
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
print("DB stdout:", stdout.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command("systemctl restart asanvpn-api.service")
print("Restart stdout:", stdout.read().decode('utf-8'))

ssh.close()
print("7. VPS Deployment Complete!")

# 5. Submit all 3 APKs to VirusTotal
print("\n=== SUBMITTING RELEASES TO VIRUSTOTAL ===")
results = {}
for name, path in [("arm64-v8a", arm64_apk), ("armeabi-v7a", armv7_apk), ("universal", univ_apk)]:
    print(f"\nScanning {name}...")
    res = scan_file_virustotal(path)
    results[name] = res

print("\n=== VIRUSTOTAL SUMMARY ===")
for name, res in results.items():
    if res:
        print(f"[{name}] Stats: {res.get('stats')} | Report: {res.get('gui_url')}")
    else:
        print(f"[{name}] Failed to scan.")
