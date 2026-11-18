import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT id, settings FROM inbounds WHERE id = 1')
row = c.fetchone()
s = json.loads(row[1])
for cl in s.get('clients', []):
    sid = cl.get('subId')
    em = cl.get('email')
    url = f'https://95.182.87.115:2016/xx11fs28c0ea3gr5/{sid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'v2rayN/6.23'})
    try:
        with urllib.request.urlopen(req, timeout=3, context=ctx) as r:
            print(f'Inbound 1: {em} -> {r.status} OK (len {len(r.read())})')
    except Exception as e:
        print(f'Inbound 1: {em} -> ERR {e}')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
