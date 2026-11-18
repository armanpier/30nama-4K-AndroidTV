import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c "
import sqlite3, json

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT email, total, enable FROM client_traffics')
rows = c.fetchall()
print(f'Total client_traffics in 3X-UI: {len(rows)}')
for r in rows:
    print(f'   Email: {r[0]:35} | Enable: {r[2]} | Total: {r[1]}')
"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
