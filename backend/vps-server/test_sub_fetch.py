import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c '
import sqlite3, json

conn = sqlite3.connect("/etc/asanvpn/asanvpn.db")
c = conn.cursor()
c.execute("SELECT value FROM kv_store WHERE key = \\"7053923325\\"")
row = c.fetchone()
if row:
    data = json.loads(row[0])
    nodes = data.get("cached_nodes", [])
    print("Found nodes count:", len(nodes))
    for n in nodes:
        print("Node:", n.get("remark"), "| Panel:", n.get("panel_name"), "| Server:", n.get("server"))
else:
    print("Not found")
'
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
