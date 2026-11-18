import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = """python3 -c "
import sqlite3, json, urllib.request, ssl, time

time.sleep(2)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('/etc/x-ui/x-ui.db')
c = conn.cursor()
c.execute('SELECT email, sub_id FROM clients')
rows = c.fetchall()
ok_count = 0
fail_count = 0
for em, sid in rows:
    url = f'https://95.182.87.115:2016/xx11fs28c0ea3gr5/{sid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'v2rayN/6.23'})
    try:
        with urllib.request.urlopen(req, timeout=3, context=ctx) as r:
            if r.status == 200:
                ok_count += 1
            else:
                print(f'FAIL {em}: {r.status}')
                fail_count += 1
    except Exception as e:
        print(f'FAIL {em}: {e}')
        fail_count += 1

print(f'3X-UI Sub Results: {ok_count} OK, {fail_count} Failed (Total: {len(rows)})')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
