import json

node = {
    "protocol": "vless",
    "remark": "index-telegram93795023_329986|📊8.47GB|⏳28D",
    "server": "95.182.87.115",
    "port": 443,
    "uuid": "ed37a1a4-ac92-414d-b782-06422774af5c",
    "type": "xhttp",
    "security": "reality",
    "sni": "shop-ca-en.amd.com",
    "path": "/index/main/",
    "pbk": "4vmBU0kTyD8belV4uorbundNHjDF6DyLwQCHUgL1zA4",
    "sid": "ca3256a6"
}

# Simulate V2RayConfigBuilder.buildConfig(node)
root = {
    "stats": {},
    "log": {"loglevel": "warning"},
    "policy": {
        "levels": {
            "8": {
                "handshake": 4,
                "connIdle": 300,
                "uplinkOnly": 1,
                "downlinkOnly": 1
            }
        },
        "system": {
            "statsOutboundUplink": True,
            "statsOutboundDownlink": True
        }
    },
    "inbounds": [
        {
            "tag": "tun",
            "protocol": "tun",
            "settings": {
                "name": "xray0",
                "MTU": 1500,
                "userLevel": 8
            },
            "sniffing": {
                "enabled": True,
                "routeOnly": True,
                "destOverride": ["http", "tls", "quic"]
            }
        },
        {
            "tag": "socks-in",
            "port": 10808,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": True, "userLevel": 8},
            "sniffing": {"enabled": True, "routeOnly": True, "destOverride": ["http", "tls", "quic"]}
        },
        {
            "tag": "http-in",
            "port": 10809,
            "listen": "127.0.0.1",
            "protocol": "http",
            "settings": {"auth": "noauth"}
        }
    ],
    "outbounds": [
        {
            "tag": "proxy",
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": node["server"],
                    "port": node["port"],
                    "users": [{
                        "id": node["uuid"],
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": {
                "network": "xhttp",
                "security": "reality",
                "realitySettings": {
                    "serverName": node["sni"],
                    "fingerprint": "chrome",
                    "publicKey": node["pbk"],
                    "shortId": node["sid"],
                    "spiderX": ""
                },
                "xhttpSettings": {
                    "path": node["path"],
                    "host": node["sni"],
                    "mode": "auto"
                }
            }
        },
        {"tag": "dns-out", "protocol": "dns"},
        {
            "tag": "direct",
            "protocol": "freedom",
            "settings": {"domainStrategy": "UseIP"},
            "streamSettings": {"sockopt": {"domainStrategy": "UseIP"}}
        },
        {
            "tag": "block",
            "protocol": "blackhole",
            "settings": {"response": {"type": "http"}}
        }
    ],
    "dns": {
        "queryStrategy": "UseIPv4",
        "servers": ["1.1.1.1", "8.8.8.8"]
    },
    "routing": {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {
                "type": "field",
                "outboundTag": "dns-out",
                "inboundTag": ["tun", "socks-in"],
                "port": "53"
            },
            {
                "type": "field",
                "outboundTag": "proxy",
                "ip": ["1.1.1.1", "8.8.8.8"]
            },
            {
                "type": "field",
                "outboundTag": "direct",
                "domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]
            },
            {
                "type": "field",
                "outboundTag": "direct",
                "ip": ["geoip:private", "geoip:ir"]
            },
            {
                "type": "field",
                "outboundTag": "proxy",
                "network": "tcp,udp"
            }
        ]
    }
}

print(json.dumps(root, indent=2))
with open('simulated_vpn_config.json', 'w') as f:
    json.dump(root, f, indent=2)
