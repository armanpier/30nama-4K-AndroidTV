import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()

c.execute('DELETE FROM client_traffics WHERE email LIKE ?', ('%arman8digit%',))
print('Deleted from client_traffics rows:', c.rowcount)
c.execute('SELECT id, settings FROM inbounds')
inbounds = c.fetchall()
for inb_id, raw_s in inbounds:
    if not raw_s: continue
    s = json.loads(raw_s)
    clients = s.get('clients', [])
    new_clients = [cl for cl in clients if 'arman8digit' not in cl.get('email', '')]
    if len(new_clients) != len(clients):
        s['clients'] = new_clients
        c.execute('UPDATE inbounds SET settings = ? WHERE id = ?', (json.dumps(s, ensure_ascii=False), inb_id))
        print(f'Cleaned test client from inbound {inb_id}')
conn.commit()
print('3X-UI cleanup done.')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
