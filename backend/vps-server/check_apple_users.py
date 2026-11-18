import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

cmd = '''python3 -c "
import urllib.request, urllib.parse, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

login_data = urllib.parse.urlencode({'username': 'P9502331E507', 'password': 'AB!8c9c8e207dxy9$'}).encode('utf-8')
headers = {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://pl.applemarket13.ir/api/admin/token', data=login_data, headers=headers)
with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
    tok_data = json.loads(r.read().decode())
    token = tok_data.get('access_token')

auth_headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'}
req_users = urllib.request.Request('https://pl.applemarket13.ir/api/users?offset=0&limit=100', headers=auth_headers)
with urllib.request.urlopen(req_users, timeout=10, context=ctx) as r:
    users_data = json.loads(r.read().decode())
    user_list = users_data.get('users', [])
    print(f'Total users in AppleMarket: {len(user_list)}')
    for u in user_list:
        sub = u.get('subscription_url') or ''
        uname = u.get('username') or ''
        status = u.get('status') or ''
        print(f'   User: {uname:25} | Status: {status} | Sub: {sub[:35]}...')
"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
