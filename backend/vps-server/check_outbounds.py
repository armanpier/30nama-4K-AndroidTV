import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import json
with open('/usr/local/x-ui/bin/config.json') as f:
    cfg = json.load(f)
for ob in cfg.get('outbounds', []):
    print('OUTBOUND:', ob.get('tag'), ob.get('protocol'), ob.get('settings'))
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
