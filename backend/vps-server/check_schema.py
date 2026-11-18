import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute(\\"SELECT name FROM sqlite_master WHERE type = 'table'\\")
print('TABLES in x-ui.db:', c.fetchall())

for t in ['inbounds', 'client_traffics', 'settings']:
    c.execute(f'PRAGMA table_info({t})')
    print(f'Columns in {t}:', [r[1] for r in c.fetchall()])
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
