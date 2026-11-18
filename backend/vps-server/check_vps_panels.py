import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json
conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
c = conn.cursor()
c.execute('SELECT key, value FROM kv_store')
users = []
for k, v in c.fetchall():
    if not k.startswith('__') and k != 'apk_meta':
        try:
            d = json.loads(v)
            users.append((k, d.get('name'), d.get('upstream_sub_urls'), d.get('panel_ids'), d.get('remote_panel_mappings')))
        except:
            pass
print('Found users count:', len(users))
for u in users:
    urls = u[2] or []
    mappings = u[4] or {}
    print(f'PIN: {u[0]} | Name: {u[1]} | SubURLs: {len(urls)} | Mappings: {list(mappings.keys())}')
    for sub in urls:
        print(f'   -> {sub}')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERR:", err)

ssh.close()
