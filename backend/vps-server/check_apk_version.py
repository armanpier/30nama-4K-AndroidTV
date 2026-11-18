import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

try:
    with open('/opt/asanvpn/version.json', 'r') as f:
        print('version.json:', f.read())
except Exception as e:
    print('version.json err:', e)

conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
c = conn.cursor()
c.execute('SELECT value FROM kv_store WHERE key = \"__CONFIG_APP_UPDATE__\"')
row = c.fetchone()
print('__CONFIG_APP_UPDATE__:', row[0] if row else 'None')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
