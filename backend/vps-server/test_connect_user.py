import urllib.request, json

req = urllib.request.Request(
    'https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/api/v1/connect',
    method='POST',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'pin': '36329986', 'deviceId': '340f058cd4f7278f'}).encode()
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
        print('Success:', data.get('success'))
        servers = data.get('servers', [])
        print('Total servers:', len(servers))
        tiers = {}
        for s in servers:
            p = s.get('panelPriority', 1)
            tiers.setdefault(p, []).append(s)
        for p, srvs in tiers.items():
            first = srvs[0]
            print(f"Tier {p} ({first.get('panelName')}): {len(srvs)} servers")
            print(f"  First server: {first.get('remark')} - {first.get('protocol')}://{first.get('server')}:{first.get('port')} (net={first.get('type')}, sec={first.get('security')}, pbk={first.get('pbk')})")
except Exception as e:
    print('Error:', e)
