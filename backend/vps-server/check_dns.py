import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

commands = [
    "cat /etc/resolv.conf",
    "systemctl status systemd-resolved --no-pager",
    "python3 -c \"import json; print(json.dumps(json.load(open('/usr/local/x-ui/bin/config.json')).get('dns'), indent=2))\"",
    "journalctl -u x-ui -n 30 --no-pager"
]

for cmd in commands:
    print(f"=== {cmd} ===")
    _, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)

ssh.close()
