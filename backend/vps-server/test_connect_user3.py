import urllib.request, json

req = urllib.request.Request(
    'https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/api/v1/connect',
    method='POST',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'pin': '36329986', 'deviceId': '340f058cd4f7278f'}).encode()
)
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read().decode())
    nodes = data.get('nodes', [])
    print(f"Total nodes: {len(nodes)}")
    tiers = {}
    for n in nodes:
        p = n.get('panel_priority', 1)
        tiers.setdefault(p, []).append(n)
    for p, n_list in sorted(tiers.items()):
        first = n_list[0]
        print(f"Tier {p} ({first.get('panel_name')}): {len(n_list)} nodes")
        print(f"  First: {first.get('remark')}")
        print(f"    proto={first.get('protocol')} host={first.get('server')}:{first.get('port')} net={first.get('type')} sec={first.get('security')} pbk={first.get('pbk')}")
        if len(n_list) > 1:
            second = n_list[1]
            print(f"  Second: {second.get('remark')}")
            print(f"    proto={second.get('protocol')} host={second.get('server')}:{second.get('port')} net={second.get('type')} sec={second.get('security')} pbk={second.get('pbk')}")
