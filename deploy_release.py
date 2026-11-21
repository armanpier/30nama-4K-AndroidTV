import os
import sys
import json
import shutil
import time
import requests
import paramiko

VT_API_KEY = "3e315c57ebbe18769caf133945b41dcff0ab2587e907237eefb0ee8357a07735"

def deploy():
    with open('version.json', 'r', encoding='utf-8') as f:
        version_data = json.load(f)

    v_name = version_data.get('versionName')
    v_code = version_data.get('versionCode')
    print(f"==================================================")
    print(f"  DEPLOYING ASANVPN v{v_name} (versionCode {v_code})")
    print(f"==================================================")

    # 1. Local copy
    rel_dir = f"releases/v{v_name}"
    os.makedirs(rel_dir, exist_ok=True)
    apk_arm64 = f"{rel_dir}/AsanVPN-v{v_name}-arm64-v8a.apk"
    apk_armv7 = f"{rel_dir}/AsanVPN-v{v_name}-armeabi-v7a.apk"
    apk_univ = f"{rel_dir}/AsanVPN-v{v_name}-universal.apk"

    shutil.copy('android/app/build/outputs/apk/release/app-arm64-v8a-release.apk', apk_arm64)
    shutil.copy('android/app/build/outputs/apk/release/app-armeabi-v7a-release.apk', apk_armv7)
    shutil.copy('android/app/build/outputs/apk/release/app-universal-release.apk', apk_univ)
    print("1. Local APKs copied to", rel_dir)

    # 2. VPS Upload
    print("2. Connecting to VPS (95.182.87.115)...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=20)
    sftp = ssh.open_sftp()

    print("3. Uploading APKs to VPS /opt/asanvpn/...")
    sftp.put(apk_arm64, f"/opt/asanvpn/AsanVPN-v{v_name}-arm64-v8a.apk")
    sftp.put(apk_arm64, f"/opt/asanvpn/AsanVPN-arm64-v8a.apk")

    sftp.put(apk_armv7, f"/opt/asanvpn/AsanVPN-v{v_name}-armeabi-v7a.apk")
    sftp.put(apk_armv7, f"/opt/asanvpn/AsanVPN-armeabi-v7a.apk")

    sftp.put(apk_univ, f"/opt/asanvpn/AsanVPN-v{v_name}-universal.apk")
    sftp.put(apk_univ, f"/opt/asanvpn/AsanVPN.apk")

    sftp.put('version.json', '/opt/asanvpn/version.json')

    # Update DB via temp script
    payload_str = json.dumps(version_data, ensure_ascii=False)
    remote_script_content = f"""import sqlite3, json, time
conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
c = conn.cursor()
val = {json.dumps(payload_str)}
c.execute("INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at", ("__CONFIG_APP_UPDATE__", val, int(time.time())))
conn.commit()
print("Updated __CONFIG_APP_UPDATE__ in DB successfully.")
"""
    with sftp.file('/tmp/update_version.py', 'w') as rf:
        rf.write(remote_script_content)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command("python3 /tmp/update_version.py")
    print("DB:", stdout.read().decode('utf-8').strip())

    stdin, stdout, stderr = ssh.exec_command("systemctl restart asanvpn-api.service")
    ssh.close()
    print("4. VPS deployment completed successfully!")

    # 3. VirusTotal Automated Submission
    print("5. Submitting APKs to VirusTotal (Cloud Scan Pre-Indexing)...")
    import virustotal_uploader
    for apk_path in [apk_arm64, apk_armv7, apk_univ]:
        fname = os.path.basename(apk_path)
        print(f"--> Uploading {fname} to VirusTotal...")
        aid = virustotal_uploader.upload_to_virustotal(apk_path)
        if aid:
            res = virustotal_uploader.check_analysis(aid)
            if res:
                print(f"    Verdict for {fname}: {res['stats']}")
                if res.get('gui_url'):
                    print(f"    VirusTotal URL: {res['gui_url']}")

    print("==================================================")
    print("  ALL DEPLOYMENT & SCAN ACTIONS COMPLETED!")
    print("==================================================")

if __name__ == '__main__':
    deploy()
