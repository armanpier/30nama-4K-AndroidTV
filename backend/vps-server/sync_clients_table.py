import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json, time, subprocess

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()

# 1. Delete arman8digittest from clients, client_inbounds, client_traffics
c.execute('SELECT id FROM clients WHERE email LIKE ?', ('%arman8digit%',))
del_rows = c.fetchall()
for d_id, in del_rows:
    c.execute('DELETE FROM client_inbounds WHERE client_id = ?', (d_id,))
c.execute('DELETE FROM clients WHERE email LIKE ?', ('%arman8digit%',))
c.execute('DELETE FROM client_traffics WHERE email LIKE ?', ('%arman8digit%',))

# 2. Get all clients from Inbound 1
c.execute('SELECT settings FROM inbounds WHERE id = 1')
s1 = json.loads(c.fetchone()[0])
clients_in_1 = s1.get('clients', [])

now_ms = int(time.time() * 1000)

for cl in clients_in_1:
    em = cl.get('email', '')
    uuid_val = cl.get('id', '')
    sub_id = cl.get('subId', '')
    total = cl.get('totalGB', 0)
    expiry = cl.get('expiryTime', 0)
    enable = 1 if cl.get('enable', True) else 0

    if not em or not sub_id:
        continue

    # Check if in clients table
    c.execute('SELECT id, sub_id FROM clients WHERE email = ?', (em,))
    row = c.fetchone()
    if not row:
        c.execute('''
            INSERT INTO clients (
                email, sub_id, uuid, password, auth, flow, security, reverse,
                wg_private_key, wg_public_key, wg_allowed_ips, wg_pre_shared_key,
                wg_keep_alive, wg_forwarded_ports, secret, ad_tag, limit_ip, limit_hwid,
                total_gb, expiry_time, enable, tg_id, group_name, comment,
                reset, reset_day, reset_weekday, reset_max, traffic_reset, traffic_reset_day,
                created_at, updated_at, sync_orphaned_at
            ) VALUES (
                ?, ?, ?, '', '', '', '', '',
                '', '', '', '',
                0, '', '', '', 0, 0,
                ?, ?, ?, 0, '', '',
                0, 0, 0, 0, 'never', 1,
                ?, ?, 0
            )
        ''', (em, sub_id, uuid_val, total, expiry, enable, now_ms, now_ms))
        client_id = c.lastrowid
        print(f'Inserted into clients: {em} (id={client_id}, sub_id={sub_id})')
    else:
        client_id = row[0]
        c.execute('UPDATE clients SET sub_id = ?, uuid = ?, total_gb = ?, expiry_time = ?, enable = ?, updated_at = ? WHERE id = ?',
                  (sub_id, uuid_val, total, expiry, enable, now_ms, client_id))

    # Link to inbounds 1 and 9 in client_inbounds
    for inb_id in [1, 9]:
        c.execute('SELECT 1 FROM client_inbounds WHERE client_id = ? AND inbound_id = ?', (client_id, inb_id))
        if not c.fetchone():
            c.execute('INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at) VALUES (?, ?, ?, ?)',
                      (client_id, inb_id, '', now_ms))
            print(f'Linked client {client_id} to inbound {inb_id}')

conn.commit()
print('All clients synced to clients and client_inbounds!')

subprocess.run(['systemctl', 'restart', 'x-ui'])
print('Restarted x-ui.')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
