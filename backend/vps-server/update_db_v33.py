import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

version_data = {
    "versionName": "1.3.33",
    "versionCode": 39,
    "forceUpdate": False,
    "releaseNotes": "احترام کامل به حالت انتخاب دستی سرورها بدون سوییچ ناخواسته، اندازه‌گیری و نمایش زنده تاخیر (پینگ) سرور هر ۱۰ ثانیه، جلوگیری از نمایش رنگ سبز پیش از برقراری قطعی ارتباط، جستجو و سوییچ هوشمند آبشاری به سایر پنل‌ها در پس‌زمینه برای حالت هوش مصنوعی Gemini و تماس صوتی، و همگام‌سازی کامل کاربران میان تمامی پنل‌ها."
}

val_str = json.dumps(version_data, ensure_ascii=False)

sftp = ssh.open_sftp()
with sftp.open('/tmp/ver_update.json', 'w') as f:
    f.write(val_str)
sftp.close()

cmd = """python3 -c "
import sqlite3, time
with open('/tmp/ver_update.json', 'r', encoding='utf-8') as f:
    val = f.read()

conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
c = conn.cursor()
c.execute('INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at', ('__CONFIG_APP_UPDATE__', val, int(time.time())))
conn.commit()
print('__CONFIG_APP_UPDATE__ successfully written to DB!')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:\n", stdout.read().decode())
print("ERR:\n", stderr.read().decode())
ssh.close()
