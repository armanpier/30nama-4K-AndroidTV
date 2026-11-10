import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import json
with open('/usr/local/x-ui/bin/config.json') as f:
    cfg = json.load(f)
for ib in cfg.get('inbounds', []):
    if ib.get('port') == 443:
        print('INBOUND 443:')
        stream = ib.get('streamSettings', {})
        print('  network:', stream.get('network'))
        print('  security:', stream.get('security'))
        print('  realitySettings:', stream.get('realitySettings'))
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
