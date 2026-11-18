import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, settings FROM inbounds')
inbounds = c.fetchall()
found_subids = set()
for inb_id, raw_s in inbounds:
    if not raw_s: continue
    s = json.loads(raw_s)
    for cl in s.get('clients', []):
        sid = cl.get('subId')
        em = cl.get('email')
        if sid:
            found_subids.add((sid, em, inb_id))

print(f'Total clients with subId: {len(found_subids)}')
for sid, em, inb_id in list(found_subids)[:15]:
    print(f'Inbound {inb_id}: {em} -> subId: {sid}')

# Check 7e9f381e3b1e7923
c.execute('SELECT * FROM client_traffics WHERE email LIKE \"%15188776%\"')
print('Client traffics for 15188776:', c.fetchall())
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
