import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

with open('simulated_vpn_config.json') as f:
    cfg = json.load(f)

test_variants = [
    ("With regexp only", [{"type": "field", "outboundTag": "direct", "domain": ["regexp:.*\\.ir$"]}]),
    ("With domain:ir", [{"type": "field", "outboundTag": "direct", "domain": ["domain:ir"]}]),
    ("With geosite:category-ir", [{"type": "field", "outboundTag": "direct", "domain": ["geosite:category-ir"]}]),
    ("With geoip:ir", [{"type": "field", "outboundTag": "direct", "ip": ["geoip:ir"]}]),
    ("With geoip:private", [{"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]}])
]

sftp = ssh.open_sftp()
for name, test_rules in test_variants:
    cfg["routing"]["rules"] = [
        {"type": "field", "outboundTag": "dns-out", "inboundTag": ["tun", "socks-in"], "port": "53"},
        {"type": "field", "outboundTag": "proxy", "ip": ["1.1.1.1", "8.8.8.8"]}
    ] + test_rules + [
        {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"}
    ]
    with sftp.open('/tmp/test_rule.json', 'w') as f:
        f.write(json.dumps(cfg))
    _, stdout, stderr = ssh.exec_command('cd /usr/local/x-ui/bin && ./xray-linux-amd64 run -c /tmp/test_rule.json -test')
    res = stdout.read().decode()
    if "Failed to start" in res:
        print(f"FAILED: {name} -> {res.strip().splitlines()[-1]}")
    else:
        print(f"PASSED: {name}")

sftp.close()
ssh.close()
