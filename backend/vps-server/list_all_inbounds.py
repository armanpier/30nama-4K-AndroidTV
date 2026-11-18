import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, user_id, up, down, total, remark, enable, port, protocol, settings, stream_settings, tag, sniffing FROM inbounds')
for r in c.fetchall():
    print(f'Inbound ID: {r[0]} | Port: {r[7]} | Proto: {r[8]} | Remark: {r[5]} | Enable: {r[6]}')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
