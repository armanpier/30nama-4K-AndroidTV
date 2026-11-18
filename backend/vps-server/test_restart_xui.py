import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://95.182.87.115:2016/xx11fs28c0ea3gr5/7e9f381e3b1e7923'
req = urllib.request.Request(url, headers={'User-Agent': 'v2rayN/6.23'})
try:
    with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
        print('Status:', r.status, 'Length:', len(r.read()))
except Exception as e:
    print('Error:', e)
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
