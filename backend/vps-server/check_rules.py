import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import json
with open('/usr/local/x-ui/bin/config.json') as f:
    cfg = json.load(f)
rules = cfg.get('routing', {}).get('rules', [])
for i, r in enumerate(rules):
    print(f'Rule {i}: outbound={r.get(\\\"outboundTag\\\")} domain={r.get(\\\"domain\\\")}')
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
