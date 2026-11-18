import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, inbound_id, enable, email, up, down, expiry_time, total FROM client_traffics WHERE email = ?', ('mkhatab',))
print('mkhatab rows:', c.fetchall())
c.execute('SELECT id, inbound_id, enable, email, up, down, expiry_time, total FROM client_traffics WHERE email = ?', ('user_15188776',))
print('user_15188776 rows:', c.fetchall())
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
