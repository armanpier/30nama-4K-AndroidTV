import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c "
import sqlite3, json

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, settings FROM inbounds WHERE id = 1')
row = c.fetchone()
if row:
    s = json.loads(row[1])
    clients = s.get('clients', [])
    print(f'Inbound 1 has {len(clients)} clients')
    if clients:
        print('Sample client:', json.dumps(clients[0], indent=2))
"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
