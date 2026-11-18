import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c '
import sqlite3, json

conn = sqlite3.connect("/etc/asanvpn/asanvpn.db")
c = conn.cursor()
c.execute("SELECT key, value FROM kv_store")
users = []
for k, v in c.fetchall():
    if not k.startswith("__") and k != "apk_meta":
        try:
            d = json.loads(v)
            users.append((k, d.get("name"), d.get("panel_ids"), d.get("remote_panel_mappings", {})))
        except:
            pass

print(f"Total users in DB: {len(users)}")
for pin, name, pids, mappings in users:
    print(f"PIN: {pin:10} | Name: {name:25} | panel_ids: {pids} | Mapped: {list(mappings.keys())}")
'
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
