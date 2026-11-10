import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

with open('simulated_vpn_config.json') as f:
    cfg = json.load(f)

cfg["routing"]["rules"] = [
    {"type": "field", "outboundTag": "dns-out", "inboundTag": ["tun", "socks-in"], "port": "53"},
    {"type": "field", "outboundTag": "direct", "domain": ["geosite:category-ir", "domain:ir"]},
    {"type": "field", "outboundTag": "direct", "ip": ["geoip:private", "geoip:ir"]},
    {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"}
]

sftp = ssh.open_sftp()
with sftp.open('/tmp/test_clean_cfg.json', 'w') as f:
    f.write(json.dumps(cfg, indent=2))
sftp.close()

_, stdout, stderr = ssh.exec_command('cd /usr/local/x-ui/bin && ./xray-linux-amd64 run -c /tmp/test_clean_cfg.json -test')
res = stdout.read().decode()
print("Xray test output:\n", res)
ssh.close()
