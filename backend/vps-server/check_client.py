import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json
conn = sqlite3.connect('/etc/x-ui/x-ui.db')
rows = conn.execute('SELECT settings FROM inbounds WHERE id = 1').fetchone()
settings = json.loads(rows[0])
clients = settings.get('clients', [])
print('Total clients in inbound 1:', len(clients))
target = 'ed37a1a4-ac92-414d-b782-06422774af5c'
found = False
for c in clients:
    if c.get('id') == target:
        found = True
        print('CLIENT FOUND:', c.get('email'), 'enable:', c.get('enable'))
        break
if not found:
    print('CLIENT NOT FOUND! Looking for email telegram93795023_329986...')
    for c in clients:
        if 'telegram93795023' in c.get('email', ''):
            print('Email match:', c.get('email'), 'id:', c.get('id'), 'enable:', c.get('enable'))
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
