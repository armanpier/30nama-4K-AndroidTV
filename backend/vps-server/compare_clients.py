import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT settings FROM inbounds WHERE id = 1')
s = json.loads(c.fetchone()[0])
clients = s.get('clients', [])
c_good = next(cl for cl in clients if cl.get('email') == 'mkhatab')
c_bad = next(cl for cl in clients if cl.get('email') == 'user_15188776')
print('GOOD CLIENT (200 OK):')
print(json.dumps(c_good, indent=2))
print('BAD CLIENT (404):')
print(json.dumps(c_bad, indent=2))
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
