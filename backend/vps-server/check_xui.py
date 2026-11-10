import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json
conn = sqlite3.connect('/etc/x-ui/x-ui.db')
inbounds = conn.execute('SELECT id, port, protocol, settings, stream_settings, remark, enable FROM inbounds').fetchall()
for ib in inbounds:
    print('ID:', ib[0], 'PORT:', ib[1], 'PROTO:', ib[2], 'REMARK:', ib[5], 'ENABLE:', ib[6])
    stream = json.loads(ib[4])
    print('  NET:', stream.get('network'), 'SEC:', stream.get('security'))
    if stream.get('realitySettings'):
        print('  REALITY dest:', stream.get('realitySettings').get('dest'), 'serverNames:', stream.get('realitySettings').get('serverNames'))
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
