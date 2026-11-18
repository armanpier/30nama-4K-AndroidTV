import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c '
import urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://irtun.darklink.ir/api/v1/ping", headers={"X-API-Key": "pg_key_f85f5abb-13cc-4dc5-b3fc-8a77c2026e94"})
try:
    with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
        print("irtun.darklink.ir status:", r.status, r.read().decode())
except Exception as e:
    print("irtun.darklink.ir err:", e)

req2 = urllib.request.Request("https://core.erfjab.com/api/v1/ping", headers={"X-API-Key": "7c704f070ae553721bfa91b4bcfeb84e2eaa8109d09e56d00b471e9001ed5206"})
try:
    with urllib.request.urlopen(req2, timeout=5, context=ctx) as r:
        print("core.erfjab.com status:", r.status, r.read().decode())
except Exception as e:
    print("core.erfjab.com err:", e)
'
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
