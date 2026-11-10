import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

test_script = r"""
import json, subprocess, time

client_config = {
    "log": {"loglevel": "debug"},
    "inbounds": [{
        "tag": "socks-in",
        "port": 20808,
        "listen": "127.0.0.1",
        "protocol": "socks",
        "settings": {"auth": "noauth", "udp": True}
    }],
    "outbounds": [{
        "tag": "proxy",
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": "127.0.0.1",
                "port": 443,
                "users": [{
                    "id": "ed37a1a4-ac92-414d-b782-06422774af5c",
                    "encryption": "none"
                }]
            }]
        },
        "streamSettings": {
            "network": "xhttp",
            "security": "reality",
            "realitySettings": {
                "serverName": "creators.radeon.com",
                "fingerprint": "chrome",
                "show": False,
                "publicKey": "4vmBU0kTyD8belV4uorbundNHjDF6DyLwQCHUgL1zA4",
                "shortId": "ca3256a6",
                "spiderX": ""
            },
            "xhttpSettings": {
                "path": "/index/main/",
                "host": "creators.radeon.com",
                "mode": "auto"
            }
        }
    }]
}

with open('/tmp/test_xray_client.json', 'w') as f:
    json.dump(client_config, f, indent=2)

print("Starting test xray client...")
proc = subprocess.Popen(['/usr/local/x-ui/bin/xray-linux-amd64', 'run', '-c', '/tmp/test_xray_client.json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)

print("Testing curl through socks5://127.0.0.1:20808...")
res = subprocess.run(['curl', '-x', 'socks5h://127.0.0.1:20808', '-I', '--connect-timeout', '5', 'https://cp.cloudflare.com/generate_204'], capture_output=True, text=True)
print("Curl generate_204 returncode:", res.returncode)
print("Curl stdout:\n" + res.stdout)
print("Curl stderr:\n" + res.stderr)

res2 = subprocess.run(['curl', '-x', 'socks5h://127.0.0.1:20808', '-I', '--connect-timeout', '5', 'https://www.google.com'], capture_output=True, text=True)
print("Curl google returncode:", res2.returncode)
print("Curl stdout:\n" + res2.stdout)
print("Curl stderr:\n" + res2.stderr)

proc.terminate()
time.sleep(1)
out, err = proc.communicate(timeout=2)
print("--- Xray client log snippet ---")
print(out[:1000] if out else "")
print(err[:1000] if err else "")
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/run_test.py', 'w') as f:
    f.write(test_script)
sftp.close()

_, stdout, stderr = ssh.exec_command('python3 /tmp/run_test.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
