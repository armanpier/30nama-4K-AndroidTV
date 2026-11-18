import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, email, sub_id, uuid FROM clients')
rows = c.fetchall()
print(f'Total in clients table: {len(rows)}')
for r in rows:
    print(f'ID: {r[0]:2} | Email: {r[1]:30} | sub_id: {r[2]} | uuid: {r[3]}')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
