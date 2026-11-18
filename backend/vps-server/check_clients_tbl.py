import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
for t in ['clients', 'client_inbounds']:
    c.execute(f'PRAGMA table_info({t})')
    print(f'Columns in {t}:', [r[1] for r in c.fetchall()])

c.execute('SELECT * FROM clients LIMIT 2')
print('Sample clients:', c.fetchall())
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
