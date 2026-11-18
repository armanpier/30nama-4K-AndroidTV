#!/usr/bin/env python3
"""
AsanVPN Standalone Edge Backend API Server & SSOT (Single Source of Truth)
Runs on VPS (Port 80) providing persistent, sub-millisecond API for mobile clients,
Admin Dashboard, Telegram Bot, and ArvanCloud Edge Gateway.
Zero external pip dependencies (Python 3 standard library: http.server, sqlite3, json, urllib, ssl, threading).
"""

import sys
import os
import re
import json
import sqlite3
import time
import base64
import logging
import threading
import ssl
import uuid
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

# Configuration
PORT = 80
DB_PATH = "/etc/asanvpn/asanvpn.db"
BACKUP_PATH = "/etc/asanvpn/data.json"
DASHBOARD_HTML_PATH = "/etc/asanvpn/dashboard.html"
ADMIN_PASSWORD = "Arman4237340"
SUPPORT_PHONE = "+989120000000"
SUPPORT_TELEGRAM = "AsanSupport"
APP_VERSION = "1.3.25"
APP_VERSION_CODE = 31
GITHUB_APK_URL = "https://github.com/armanpier/AsanVPN/releases/download/v1.3.20/AsanVPN-v1.3.20-universal.apk"
EDGE_SECRET = "asanvpn-edge-internal-secret-2026"

DEFAULT_INITIAL_PANELS = [
    {
        "id": "panel_3xui_default",
        "name": "سرور ۳X-UI اصلی",
        "type": "3xui",
        "authType": "apiKey",
        "url": "https://95.182.87.115:14393/eX6Vvc2csV2GKtzmPF",
        "apiKey": "Wg6BrJKRiJzcNr4NKnjlxjZSAxMUIYkh7lzvWUDUQn3gxmW9",
        "subBaseUrl": "https://95.182.87.115:2016/xx11fs28c0ea3gr5/{subId}",
        "autoSync": True,
        "priority": 2,
        "userCount": 8,
        "createdAt": 1794227465
    },
    {
        "id": "panel_pasarguard_applemarket",
        "name": "اپل‌مارکت (AppleMarket)",
        "type": "pasarguard",
        "authType": "userPass",
        "url": "https://pl.applemarket13.ir",
        "username": "P9502331E507",
        "password": "AB!8c9c8e207dxy9$",
        "subBaseUrl": "https://cb13.farsistar.ir",
        "autoSync": True,
        "priority": 1,
        "userCount": 18,
        "createdAt": 1794900000
    },
    {
        "id": "panel_pasarguard_default",
        "name": "پاسارگاد (PasarGuard)",
        "type": "pasarguard",
        "authType": "apiKey",
        "url": "https://irtun.darklink.ir:8000",
        "apiKey": "pg_key_f85f5abb-13cc-4dc5-b3fc-8a77c2026e94",
        "subBaseUrl": "https://irsub.trafficfast.ir:9090",
        "autoSync": True,
        "priority": 2,
        "userCount": 11,
        "createdAt": 1794227484
    },
    {
        "id": "panel_goguard_default",
        "name": "سرور گوگارد (GoGuard Core)",
        "type": "goguard",
        "authType": "apiKey",
        "url": "https://core.erfjab.com",
        "apiKey": "7c704f070ae553721bfa91b4bcfeb84e2eaa8109d09e56d00b471e9001ed5206",
        "subBaseUrl": "https://versub.bertly.top",
        "autoSync": True,
        "priority": 3,
        "userCount": 12,
        "createdAt": 1792621000
    }
]

def resolve_panel_for_sub_url(url: str, panels: list):
    """
    Identifies the source panel for a subscription URL and returns (panel_id, panel_name, priority).
    Dynamically maps against live panels configuration so user dashboard priority changes are strictly honored.
    """
    if not url:
        return "panel_unknown", "External", 99

    url_lower = url.lower()

    # Precompute live priority and name map
    prio_map = {}
    name_map = {}
    for p in (panels or []):
        pid = p.get("id")
        if pid:
            prio_map[pid] = int(p.get("priority", 1))
            name_map[pid] = p.get("name")

    for p in (panels or []):
        p_sub = (p.get("subBaseUrl") or "").lower()
        p_url = (p.get("url") or "").lower()
        try:
            p_sub_host = urllib.parse.urlparse(p_sub).netloc.lower() if p_sub else ""
            p_url_host = urllib.parse.urlparse(p_url).netloc.lower() if p_url else ""
            u_host = urllib.parse.urlparse(url_lower).netloc.lower()
            if (p_sub_host and p_sub_host in u_host) or (p_url_host and p_url_host in u_host):
                pid = p.get("id", "")
                return pid, p.get("name", ""), prio_map.get(pid, int(p.get("priority", 1)))
        except Exception:
            pass
        if (p_sub and p_sub in url_lower) or (p_url and p_url in url_lower):
            pid = p.get("id", "")
            return pid, p.get("name", ""), prio_map.get(pid, int(p.get("priority", 1)))

    # Comprehensive fallback heuristics for all known domains
    if any(k in url_lower for k in ["bertly.top", "erfjab.com", "goguard", "fadaei.top", "sudopen.org", "hyperlink"]):
        pid = "panel_goguard_default"
        return pid, name_map.get(pid, "سرور گوگارد (GoGuard Core)"), prio_map.get(pid, 1)
    elif any(k in url_lower for k in ["farsistar.ir", "applemarket", "applemarket13.ir"]):
        pid = "panel_pasarguard_applemarket"
        return pid, name_map.get(pid, "اپل‌مارکت (AppleMarket)"), prio_map.get(pid, 2)
    elif any(k in url_lower for k in ["95.182.87.115", ":2016", "3x"]):
        pid = "panel_3xui_default"
        return pid, name_map.get(pid, "سرور ۳X-UI اصلی"), prio_map.get(pid, 2)
    elif any(k in url_lower for k in ["trafficfast.ir", "darklink.ir", "pasarguard"]):
        pid = "panel_pasarguard_default"
        return pid, name_map.get(pid, "پاسارگاد (PasarGuard)"), prio_map.get(pid, 3)

    return "custom_panel", "سرور پشتیبان", 99

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# SSL context that skips verification for remote self-signed or internal panel certs
INSECURE_SSL_CTX = ssl.create_default_context()
INSECURE_SSL_CTX.check_hostname = False
INSECURE_SSL_CTX.verify_mode = ssl.CERT_NONE

# Rate limiting storage for failed authentication attempts (IP and Device level)
RATE_LIMIT_STORE = {} # key -> {"count": int, "locked_until": int}
RATE_LIMIT_LOCK = threading.Lock()

def get_ip_subnet(ip: str) -> str:
    """Calculates IPv4 /24 subnet or returns clean IP. Excludes reverse proxy/internal addresses."""
    if not ip or ip in ("unknown", "127.0.0.1", "::1", "localhost"):
        return ""
    if ip.startswith("37.32.") or ip.startswith("185.143."):
        return ""
    if "." in ip:
        parts = ip.split(".")
        if len(parts) >= 3:
            return ".".join(parts[:3]) + ".0/24"
    return ip

def check_rate_limit(ip_key: str, dev_key: str) -> tuple:
    """Check if either IP or Device is locked out. Returns (is_locked, remaining_seconds)."""
    now = int(time.time())
    with RATE_LIMIT_LOCK:
        for k in [ip_key, dev_key]:
            if k and k in RATE_LIMIT_STORE:
                entry = RATE_LIMIT_STORE[k]
                if entry.get("locked_until", 0) > now:
                    return True, entry["locked_until"] - now
    return False, 0

def record_failed_attempt(ip_key: str, dev_key: str) -> tuple:
    """Record failure and lock out if threshold reached. Returns (locked, remaining_seconds, remaining_attempts)."""
    now = int(time.time())
    with RATE_LIMIT_LOCK:
        dev_entry = RATE_LIMIT_STORE.setdefault(dev_key, {"count": 0, "locked_until": 0}) if dev_key else None
        ip_entry = RATE_LIMIT_STORE.setdefault(ip_key, {"count": 0, "locked_until": 0}) if ip_key else None

        dev_count = (dev_entry["count"] + 1) if dev_entry else 1
        ip_count = (ip_entry["count"] + 1) if ip_entry else 1

        if dev_entry:
            dev_entry["count"] = dev_count
        if ip_entry:
            ip_entry["count"] = ip_count

        if (dev_entry and dev_count >= 3) or (ip_entry and ip_count >= 5):
            lock_until = now + 1800 # 30 min lockout
            if dev_entry:
                dev_entry["locked_until"] = lock_until
            if ip_entry:
                ip_entry["locked_until"] = lock_until
            return True, 1800, 0

        rem = max(0, 3 - dev_count) if dev_entry else max(0, 5 - ip_count)
        return False, 0, rem

def clear_rate_limit(ip_key: str = "", dev_key: str = "", clear_all: bool = False):
    """Clear failed attempts upon successful login or admin reset."""
    with RATE_LIMIT_LOCK:
        if clear_all:
            RATE_LIMIT_STORE.clear()
            return
        if ip_key and ip_key in RATE_LIMIT_STORE:
            del RATE_LIMIT_STORE[ip_key]
        if dev_key and dev_key in RATE_LIMIT_STORE:
            del RATE_LIMIT_STORE[dev_key]

def is_secure_10digit_pin(pin: str) -> bool:
    if not isinstance(pin, str) or len(pin) != 10 or not pin.isdigit():
        return False
    if len(set(pin)) < 6:
        return False
    for i in range(len(pin) - 2):
        if pin[i] == pin[i+1] == pin[i+2]:
            return False
    for i in range(len(pin) - 2):
        d1, d2, d3 = int(pin[i]), int(pin[i+1]), int(pin[i+2])
        if (d2 == d1 + 1 and d3 == d2 + 1) or (d2 == d1 - 1 and d3 == d2 - 1):
            return False
    if pin[:5] == pin[5:]:
        return False
    if pin[:2] * 5 == pin:
        return False
    if pin[0] == pin[1] and pin[2] == pin[3] and pin[4] == pin[5] and pin[6] == pin[7] and pin[8] == pin[9]:
        return False
    if pin == pin[::-1]:
        return False
    return True

def is_valid_pin_format(pin: str) -> bool:
    if not pin or not isinstance(pin, str):
        return False
    pin = pin.strip()
    return pin.isdigit() and len(pin) in (8, 10)

def generate_secure_10digit_pin(existing_checker) -> str:
    import random
    for _ in range(500):
        cand = str(random.randint(1000000000, 9999999999))
        if is_secure_10digit_pin(cand) and not existing_checker(cand):
            return cand
    while True:
        cand = str(random.randint(1000000000, 9999999999))
        if not existing_checker(cand):
            return cand

# ==========================================
# 3X-UI LOCAL SQLITE SYNCHRONIZATION
# ==========================================
def sync_3xui_sqlite(user_data):
    """
    Directly synchronizes user totalGB and expiryTime into local 3X-UI SQLite database (/etc/x-ui/x-ui.db).
    If client does not exist, automatically creates it in inbounds 1 & 9 and client_traffics.
    Returns (subId, email) tuple or (None, None).
    """
    xui_db_path = "/etc/x-ui/x-ui.db"
    if not os.path.exists(xui_db_path):
        return (None, None)
    try:
        if isinstance(user_data, str):
            user_data = json.loads(user_data)
        if not isinstance(user_data, dict):
            return (None, None)

        total_bytes = int(user_data.get("traffic_total_bytes", 0) or 0)
        expires_at = int(user_data.get("expires_at", 0) or 0)
        expiry_ms = expires_at * 1000 if expires_at > 0 else 0
        is_active = 1 if user_data.get("active", True) else 0

        possible_identifiers = set()
        mappings = user_data.get("remote_panel_mappings") or {}
        if isinstance(mappings, dict):
            for p_id, p_info in mappings.items():
                if isinstance(p_info, dict):
                    if p_info.get("username"):
                        possible_identifiers.add(str(p_info["username"]).strip())
                    if p_info.get("clientUuid"):
                        possible_identifiers.add(str(p_info["clientUuid"]).strip())

        name = str(user_data.get("name", "")).strip()
        pin = str(user_data.get("pin", "")).strip()
        if name:
            possible_identifiers.add(name)
            clean_tg = re.sub(r'[^a-zA-Z0-9_]', '', name.replace('@', ''))
            if clean_tg:
                possible_identifiers.add(clean_tg)
                if pin:
                    possible_identifiers.add(f"telegram{clean_tg}_{pin[-6:]}")
                    possible_identifiers.add(f"{clean_tg}_{pin[-6:]}")
        if pin:
            possible_identifiers.add(f"%_{pin[-6:]}")
            possible_identifiers.add(f"%{pin}%")
            possible_identifiers.add(f"user_{pin}")

        with sqlite3.connect(xui_db_path, timeout=5) as conn:
            cur = conn.cursor()
            matched_emails = set()
            for ident in possible_identifiers:
                if "%" in ident:
                    cur.execute("SELECT email FROM client_traffics WHERE email LIKE ?", (ident,))
                else:
                    cur.execute("SELECT email FROM client_traffics WHERE email = ?", (ident,))
                for row in cur.fetchall():
                    if row and row[0]:
                        matched_emails.add(row[0])

            if not matched_emails and pin:
                cur.execute("SELECT email FROM client_traffics WHERE email LIKE ?", (f"%{pin[-6:]}%",))
                for row in cur.fetchall():
                    if row and row[0]:
                        matched_emails.add(row[0])

            matched_sub_id = None
            primary_email = None

            if not matched_emails:
                # Client does not exist in 3X-UI: Create client in inbounds 1 and 9!
                new_uuid = str(uuid.uuid4())
                new_sub_id = secrets.token_hex(8)
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_')).strip('_')
                if not clean_name or clean_name.lower().startswith('telegram'):
                    new_email = f"user_{pin}" if pin else f"user_{secrets.token_hex(4)}"
                else:
                    new_email = f"{clean_name[:14]}_{pin[-6:]}" if pin else clean_name[:20]

                now_ms = int(time.time() * 1000)
                new_client = {
                    "id": new_uuid,
                    "email": new_email,
                    "totalGB": total_bytes,
                    "expiryTime": expiry_ms,
                    "enable": bool(is_active),
                    "subId": new_sub_id,
                    "comment": "",
                    "created_at": now_ms,
                    "updated_at": now_ms,
                    "limitIp": 0,
                    "reset": 0,
                    "resetDay": 0,
                    "resetMax": 0,
                    "resetWeekday": 0,
                    "security": "",
                    "tgId": 0,
                    "trafficReset": "never",
                    "trafficResetDay": 1
                }

                # Insert into clients table for direct 3X-UI subscription serving
                try:
                    cur.execute('''
                        INSERT INTO clients (
                            email, sub_id, uuid, password, auth, flow, security, reverse,
                            wg_private_key, wg_public_key, wg_allowed_ips, wg_pre_shared_key,
                            wg_keep_alive, wg_forwarded_ports, secret, ad_tag, limit_ip, limit_hwid,
                            total_gb, expiry_time, enable, tg_id, group_name, comment,
                            reset, reset_day, reset_weekday, reset_max, traffic_reset, traffic_reset_day,
                            created_at, updated_at, sync_orphaned_at
                        ) VALUES (
                            ?, ?, ?, '', '', '', '', '',
                            '', '', '', '',
                            0, '', '', '', 0, 0,
                            ?, ?, ?, 0, '', '',
                            0, 0, 0, 0, 'never', 1,
                            ?, ?, 0
                        )
                    ''', (new_email, new_sub_id, new_uuid, total_bytes, expiry_ms, is_active, now_ms, now_ms))
                    created_cid = cur.lastrowid
                    for inb_id in [1, 9]:
                        cur.execute('INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at) VALUES (?, ?, ?, ?)',
                                    (created_cid, inb_id, '', now_ms))
                except Exception as c_err:
                    logging.warning(f"[3X-UI Create] Error inserting into clients table: {c_err}")

                cur.execute("SELECT id, settings FROM inbounds WHERE id IN (1, 9)")
                inbounds = cur.fetchall()
                for inb_id, inb_settings_raw in inbounds:
                    if not inb_settings_raw:
                        continue
                    try:
                        inb_settings = json.loads(inb_settings_raw)
                        clients = inb_settings.setdefault("clients", [])
                        if not any(c.get("email") == new_email or c.get("id") == new_uuid for c in clients):
                            clients.append(new_client)
                            cur.execute(
                                "UPDATE inbounds SET settings = ? WHERE id = ?",
                                (json.dumps(inb_settings, ensure_ascii=False), inb_id)
                            )
                        cur.execute(
                            "INSERT OR REPLACE INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total) VALUES (?, ?, ?, 0, 0, ?, ?)",
                            (inb_id, is_active, new_email, expiry_ms, total_bytes)
                        )
                    except Exception as json_err:
                        logging.warning(f"[3X-UI Create] Inbound {inb_id} error: {json_err}")
                conn.commit()
                logging.info(f"[3X-UI Sync] Created new 3X-UI client {new_email} with subId {new_sub_id}")
                return (new_sub_id, new_email)

            # Update existing client(s)
            for email in matched_emails:
                cur.execute(
                    "UPDATE client_traffics SET total = ?, expiry_time = ?, enable = ? WHERE email = ?",
                    (total_bytes, expiry_ms, is_active, email)
                )

            cur.execute("SELECT id, settings FROM inbounds")
            inbounds = cur.fetchall()
            for inb_id, inb_settings_raw in inbounds:
                if not inb_settings_raw:
                    continue
                try:
                    inb_settings = json.loads(inb_settings_raw)
                    clients = inb_settings.get("clients", [])
                    modified = False
                    for c in clients:
                        c_email = c.get("email", "")
                        c_id = c.get("id", "")
                        if c_email in matched_emails or c_id in possible_identifiers:
                            c["totalGB"] = total_bytes
                            c["expiryTime"] = expiry_ms
                            c["enable"] = bool(is_active)
                            modified = True
                            if not matched_sub_id and c.get("subId"):
                                matched_sub_id = c.get("subId")
                                primary_email = c_email
                    if modified:
                        cur.execute(
                            "UPDATE inbounds SET settings = ? WHERE id = ?",
                            (json.dumps(inb_settings, ensure_ascii=False), inb_id)
                        )
                except Exception as json_err:
                    logging.warning(f"[3X-UI Sync] Failed to parse inbound {inb_id} settings: {json_err}")

            conn.commit()
            logging.info(f"[3X-UI Sync] Synced {matched_emails} in 3X-UI (Total: {total_bytes}, Expiry: {expiry_ms})")
            return (matched_sub_id, primary_email or next(iter(matched_emails), None))
    except Exception as e:
        logging.warning(f"[3X-UI Sync] Error synchronizing with /etc/x-ui/x-ui.db: {e}")
        return (None, None)

# ==========================================
# PARSE PROTOCOL NODES INTO JSON DICTS
# ==========================================
def parse_raw_proxy_link(link: str, panel_id: str = "", panel_name: str = "", priority: int = 1) -> dict:
    """Parses vless://, vmess://, trojan://, ss:// URIs into structured node objects."""
    link = link.strip()
    if not link:
        return None
    try:
        if link.startswith("vless://") or link.startswith("trojan://"):
            proto = "vless" if link.startswith("vless://") else "trojan"
            rest = link[len(proto) + 3:]
            user_part, host_part = rest.split("@", 1) if "@" in rest else ("", rest)
            host_port, query_part = host_part.split("?", 1) if "?" in host_part else (host_part, "")
            host, port = host_port.split(":", 1) if ":" in host_port else (host_port, "443")
            query, fragment = query_part.split("#", 1) if "#" in query_part else (query_part, "")
            params = urllib.parse.parse_qs(query)
            remark = urllib.parse.unquote(fragment) if fragment else f"{proto.upper()} Node"

            return {
                "protocol": proto,
                "remark": remark,
                "server": host,
                "port": int(port),
                "uuid": user_part,
                "type": params.get("type", ["tcp"])[0],
                "security": params.get("security", ["none"])[0],
                "sni": params.get("sni", [""])[0],
                "path": params.get("path", [""])[0],
                "hostHeader": params.get("host", [""])[0] or params.get("sni", [""])[0],
                "flow": params.get("flow", [""])[0],
                "pbk": params.get("pbk", [""])[0],
                "sid": params.get("sid", [""])[0],
                "spx": params.get("spx", [""])[0],
                "fingerprint": params.get("fp", ["chrome"])[0],
                "serviceName": params.get("serviceName", [""])[0],
                "encryption": params.get("encryption", ["none"])[0],
                "mode": params.get("mode", ["auto"])[0],
                "headerType": params.get("headerType", ["none"])[0],
                "raw_link": link,
                "panel_id": panel_id,
                "panel_name": panel_name,
                "panel_priority": priority
            }
        elif link.startswith("vmess://"):
            b64_str = link[8:]
            decoded = base64.b64decode(b64_str + "==").decode("utf-8", errors="ignore")
            cfg = json.loads(decoded)
            return {
                "protocol": "vmess",
                "remark": cfg.get("ps", "VMess Node"),
                "server": cfg.get("add", ""),
                "port": int(cfg.get("port", 443)),
                "uuid": cfg.get("id", ""),
                "alterId": int(cfg.get("aid", 0)),
                "type": cfg.get("net", "tcp"),
                "security": cfg.get("tls", "none"),
                "sni": cfg.get("sni", "") or cfg.get("host", ""),
                "path": cfg.get("path", ""),
                "hostHeader": cfg.get("host", ""),
                "cipher": "auto",
                "raw_link": link,
                "panel_id": panel_id,
                "panel_name": panel_name,
                "panel_priority": priority
            }
    except Exception as e:
        logging.debug(f"Failed to parse proxy link: {e}")
    return None

def fetch_subscription_data(url: str, timeout: int = 8) -> dict:
    """Fetches a subscription URL and extracts userinfo header + decoded node lines."""
    req = urllib.request.Request(url, headers={"User-Agent": "v2rayN/6.23 AsanVPN-Core/1.0"})
    res_data = {"user_info": None, "nodes_raw": []}
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=INSECURE_SSL_CTX) as res:
            sub_info = res.headers.get("Subscription-Userinfo") or res.headers.get("subscription-userinfo")
            if sub_info:
                info_dict = {}
                for part in sub_info.split(";"):
                    if "=" in part:
                        k, v = part.strip().split("=", 1)
                        try:
                            info_dict[k.strip().lower()] = int(v.strip())
                        except ValueError:
                            pass
                res_data["user_info"] = info_dict

            body = res.read().decode("utf-8", errors="ignore").strip()
            # If plain-text links are returned (e.g. GoGuard or unencoded subscriptions)
            if body.startswith("vless://") or body.startswith("vmess://") or body.startswith("trojan://") or body.startswith("ss://"):
                lines = [l.strip() for l in body.splitlines() if l.strip()]
            else:
                # Try base64 decoding
                try:
                    decoded = base64.b64decode(body + "==").decode("utf-8", errors="ignore")
                    lines = [l.strip() for l in decoded.splitlines() if l.strip()]
                except Exception:
                    lines = [l.strip() for l in body.splitlines() if l.strip()]
            res_data["nodes_raw"] = lines
    except Exception as e:
        logging.warning(f"Error fetching sub url {url}: {e}")
    return res_data

# ==========================================
# REMOTE PANEL API CLIENT & TOKEN CACHE
# ==========================================
PANEL_JWT_CACHE = {}

def normalize_panel_url(panel_url: str) -> str:
    url = (panel_url or "").strip().rstrip("/")
    if url.endswith("/dashboard"):
        url = url[:-10].rstrip("/")
    return url

def get_panel_jwt_token(panel_url: str, username: str, password: str, force_refresh: bool = False) -> str:
    """
    Retrieves or refreshes an OAuth2 JWT Bearer token for PasarGuard / Marzban / FastAPI panels.
    Caches token in memory for efficiency.
    """
    if not panel_url or not username or not password:
        return ""
    base_url = normalize_panel_url(panel_url)
    cache_key = f"{base_url}:{username}"
    now = time.time()
    if not force_refresh and cache_key in PANEL_JWT_CACHE:
        entry = PANEL_JWT_CACHE[cache_key]
        if now < entry.get("expires_at", 0):
            return entry.get("token", "")

    endpoints = [
        f"{base_url}/api/admin/token",
        f"{base_url}/dashboard/api/admin/token",
        f"{base_url}/api/token"
    ]
    data = urllib.parse.urlencode({"username": username, "password": password}).encode("utf-8")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    for ep in endpoints:
        try:
            req = urllib.request.Request(ep, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=7, context=INSECURE_SSL_CTX) as res:
                if res.status == 200:
                    resp = json.loads(res.read().decode("utf-8"))
                    tok = resp.get("access_token")
                    if tok:
                        PANEL_JWT_CACHE[cache_key] = {
                            "token": tok,
                            "expires_at": now + 1800 # 30 min cache
                        }
                        return tok
        except Exception as e:
            logging.debug(f"[PanelJWT] Failed on {ep}: {e}")
    return ""

def fetch_pasarguard_remote_users(panel_url: str, username: str, password: str, sub_base_url: str = "") -> list:
    """
    Fetches all users and their subscription URLs from a PasarGuard / Marzban panel using user/pass.
    """
    tok = get_panel_jwt_token(panel_url, username, password)
    if not tok:
        tok = get_panel_jwt_token(panel_url, username, password, force_refresh=True)
    if not tok:
        return []

    base_url = panel_url.rstrip("/")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN/1.0",
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json"
    }

    req = urllib.request.Request(f"{base_url}/api/users", headers=headers)
    users_list = []
    try:
        with urllib.request.urlopen(req, timeout=8, context=INSECURE_SSL_CTX) as res:
            if res.status == 200:
                body = json.loads(res.read().decode("utf-8"))
                users_list = body.get("users", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    except Exception as e:
        logging.warning(f"[fetch_pasarguard_remote_users] Error fetching user list: {e}")
        return []

    results = []
    for u in users_list:
        uname = u.get("username") if isinstance(u, dict) else str(u)
        if not uname:
            continue
        sub_url = u.get("subscription_url") or ""
        # If subscription_url is empty in summary, fetch full user detail
        if not sub_url:
            try:
                r_detail = urllib.request.Request(f"{base_url}/api/user/{urllib.parse.quote(uname)}", headers=headers)
                with urllib.request.urlopen(r_detail, timeout=6, context=INSECURE_SSL_CTX) as res_d:
                    if res_d.status == 200:
                        u_data = json.loads(res_d.read().decode("utf-8"))
                        sub_url = u_data.get("subscription_url") or ""
            except Exception as e:
                logging.debug(f"[fetch_pasarguard_remote_users] Detail fetch error for {uname}: {e}")

        # Ensure full URL if relative
        if sub_url and sub_url.startswith("/"):
            if sub_base_url:
                sub_url = sub_base_url.rstrip("/") + sub_url
            else:
                sub_url = base_url + sub_url

        results.append({
            "name": uname,
            "username": uname,
            "subUrl": sub_url,
            "status": u.get("status", "active") if isinstance(u, dict) else "active",
            "panelType": "pasarguard"
        })

    return results

def sync_user_to_panels(user_data):
    """
    Synchronizes user across all active panels:
    1. AppleMarket (PasarGuard panel with userPass JWT authentication)
    2. 3X-UI (Local SQLite database)
    Updates user_data with sub URLs and remote_panel_mappings.
    """
    if isinstance(user_data, str):
        try:
            user_data = json.loads(user_data)
        except Exception:
            return user_data
    if not isinstance(user_data, dict):
        return user_data

    pin = str(user_data.get("pin", "")).strip()
    raw_name = str(user_data.get("name") or user_data.get("username") or "").strip()
    if not raw_name:
        raw_name = f"user_{pin}"
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name.replace(' ', '_')).strip('_')
    if not safe_name or safe_name.lower().startswith('telegram'):
        safe_name = f"user_{pin}"
    safe_name = safe_name[:20]

    mappings = user_data.get("remote_panel_mappings")
    if not isinstance(mappings, dict):
        mappings = {}
    user_data["remote_panel_mappings"] = mappings

    sub_urls = list(user_data.get("upstream_sub_urls") or [])
    if user_data.get("upstream_sub_url") and not sub_urls:
        sub_urls = [u.strip() for u in str(user_data.get("upstream_sub_url")).split("\n") if u.strip()]

    # --- 1. AppleMarket (Priority 1) ---
    try:
        panels_json = db.get("__CONFIG_PANELS__")
        panels = json.loads(panels_json) if panels_json else list(DEFAULT_INITIAL_PANELS)
        apple_panel = next((p for p in panels if p.get("id") == "panel_pasarguard_applemarket"), None)
        if apple_panel and apple_panel.get("autoSync") is not False:
            p_url = apple_panel.get("url", "https://pl.applemarket13.ir").rstrip("/")
            p_user = apple_panel.get("username", "P9502331E507")
            p_pass = apple_panel.get("password", "AB!8c9c8e207dxy9$")
            tok = get_panel_jwt_token(p_url, p_user, p_pass)
            if tok:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN/1.0",
                    "Authorization": f"Bearer {tok}",
                    "Content-Type": "application/json"
                }

                matched_uname = None
                apple_sub = ""

                # Specific aliases for known accounts
                known_aliases = {
                    "admin": "Admin",
                    "tahoura": "Tah",
                    "mkhatab": "Mkhtab",
                    "abolfazl": "Abolfazl"
                }
                candidate_names = [safe_name]
                for k_alias, v_alias in known_aliases.items():
                    if k_alias in raw_name.lower():
                        candidate_names.insert(0, v_alias)

                for c_name in candidate_names:
                    try:
                        req_chk = urllib.request.Request(f"{p_url}/api/user/{urllib.parse.quote(c_name)}", headers=headers)
                        with urllib.request.urlopen(req_chk, timeout=6, context=INSECURE_SSL_CTX) as res_chk:
                            if res_chk.status == 200:
                                chk_data = json.loads(res_chk.read().decode("utf-8"))
                                matched_uname = chk_data.get("username")
                                apple_sub = chk_data.get("subscription_url") or ""
                                break
                    except Exception:
                        pass

                if not matched_uname:
                    # Create user on AppleMarket
                    expire_ts = user_data.get("expires_at")
                    if expire_ts and expire_ts < 1000000000:
                        expire_ts = None
                    data_limit = int(user_data.get("traffic_total_bytes") or 0)
                    create_payload = json.dumps({
                        "username": safe_name,
                        "expire": expire_ts,
                        "data_limit": data_limit,
                        "data_limit_reset_strategy": "no_reset",
                        "status": "active" if user_data.get("active", True) else "disabled",
                        "group_ids": [4],
                        "proxy_settings": {
                            "vless": {"id": str(uuid.uuid4())},
                            "vmess": {"id": str(uuid.uuid4())},
                            "trojan": {"password": secrets.token_hex(16)},
                            "shadowsocks": {"password": secrets.token_hex(16), "method": "chacha20-ietf-poly1305"}
                        }
                    }).encode("utf-8")
                    try:
                        req_cr = urllib.request.Request(f"{p_url}/api/user", data=create_payload, headers=headers, method="POST")
                        with urllib.request.urlopen(req_cr, timeout=8, context=INSECURE_SSL_CTX) as res_cr:
                            if res_cr.status in [200, 201]:
                                cr_data = json.loads(res_cr.read().decode("utf-8"))
                                matched_uname = cr_data.get("username")
                                apple_sub = cr_data.get("subscription_url") or ""
                    except Exception as cr_err:
                        logging.warning(f"[AppleMarket] Create error for {safe_name}: {cr_err}")

                if apple_sub:
                    mappings["panel_pasarguard_applemarket"] = {
                        "username": matched_uname or safe_name,
                        "subUrl": apple_sub,
                        "panelType": "pasarguard"
                    }
                    sub_urls = [u for u in sub_urls if not ("farsistar.ir" in u or "applemarket" in u)]
                    sub_urls.insert(0, apple_sub)
    except Exception as e:
        logging.warning(f"Error syncing user to AppleMarket: {e}")

    # --- 2. 3X-UI ---
    try:
        xui_sub_id, xui_email = sync_3xui_sqlite(user_data)
        if xui_sub_id:
            xui_sub_url = f"https://95.182.87.115:2016/xx11fs28c0ea3gr5/{xui_sub_id}"
            mappings["panel_3xui_default"] = {
                "username": xui_email or safe_name,
                "subUrl": xui_sub_url,
                "subId": xui_sub_id,
                "panelType": "3xui"
            }
            sub_urls = [u for u in sub_urls if not ("95.182.87.115:2016" in u)]
            sub_urls.append(xui_sub_url)
    except Exception as e:
        logging.warning(f"Error syncing user to 3X-UI: {e}")

    user_data["upstream_sub_urls"] = sub_urls
    user_data["upstream_sub_url"] = "\n".join(sub_urls)
    user_data["remote_panel_mappings"] = mappings
    return user_data

def delete_user_from_panels(pin: str, user_data: dict = None):
    """Deletes user from both AppleMarket and local 3X-UI."""
    # 1. AppleMarket deletion
    try:
        panels_json = db.get("__CONFIG_PANELS__")
        panels = json.loads(panels_json) if panels_json else list(DEFAULT_INITIAL_PANELS)
        apple_panel = next((p for p in panels if p.get("id") == "panel_pasarguard_applemarket"), None)
        if apple_panel and user_data:
            mappings = user_data.get("remote_panel_mappings", {})
            ap_uname = None
            if isinstance(mappings, dict) and "panel_pasarguard_applemarket" in mappings:
                ap_uname = mappings["panel_pasarguard_applemarket"].get("username")
            if not ap_uname:
                ap_uname = f"user_{pin}"
            if ap_uname:
                p_url = apple_panel.get("url", "https://pl.applemarket13.ir").rstrip("/")
                tok = get_panel_jwt_token(p_url, apple_panel.get("username", "P9502331E507"), apple_panel.get("password", "AB!8c9c8e207dxy9$"))
                if tok:
                    del_req = urllib.request.Request(f"{p_url}/api/user/{urllib.parse.quote(ap_uname)}", headers={"Authorization": f"Bearer {tok}"}, method="DELETE")
                    with urllib.request.urlopen(del_req, timeout=6, context=INSECURE_SSL_CTX) as _:
                        logging.info(f"[AppleMarket] Deleted remote user {ap_uname}")
    except Exception as e:
        logging.warning(f"Error deleting user from AppleMarket: {e}")

    # 2. 3X-UI deletion
    try:
        xui_db_path = "/etc/x-ui/x-ui.db"
        if os.path.exists(xui_db_path):
            with sqlite3.connect(xui_db_path, timeout=5) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM clients WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))
                for d_id, in cur.fetchall():
                    cur.execute("DELETE FROM client_inbounds WHERE client_id = ?", (d_id,))
                cur.execute("DELETE FROM clients WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))
                cur.execute("DELETE FROM client_traffics WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))
                cur.execute("SELECT id, settings FROM inbounds")
                for inb_id, raw_s in cur.fetchall():
                    if not raw_s: continue
                    s = json.loads(raw_s)
                    clients = s.get("clients", [])
                    new_clients = [c for c in clients if pin not in c.get("email", "") and (not pin or not c.get("email", "").endswith(pin[-6:]))]
                    if len(new_clients) != len(clients):
                        s["clients"] = new_clients
                        cur.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (json.dumps(s, ensure_ascii=False), inb_id))
                conn.commit()
                logging.info(f"[3X-UI] Deleted user clients for PIN {pin}")
    except Exception as e:
        logging.warning(f"Error deleting user from 3X-UI: {e}")

# ==========================================
# DATABASE (SQLite with WAL Mode)
# ==========================================
class Database:
    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, timeout=15.0, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=15000;")
        self.create_tables()

    def create_tables(self):
        with self._lock, self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at INTEGER
                )
            """)

    def get(self, key):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else None

    def put(self, key, value):
        with self._lock, self.conn:
            self.conn.execute("""
                INSERT INTO kv_store (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (key, value, int(time.time())))
        # Auto-sync to local 3X-UI if this is a user record
        if isinstance(key, str) and (len(key) == 8 or len(key) == 10) and key.isdigit():
            try:
                sync_3xui_sqlite(value)
            except Exception:
                pass

    def delete(self, key):
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))

    def get_all_users(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("SELECT key, value FROM kv_store")
            rows = cur.fetchall()
        users = []
        for key, val in rows:
            if key.startswith("__") or key == "apk_meta":
                continue
            try:
                data = json.loads(val)
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    # Explicit ultra-compact user summary without node cache arrays or multiline upstream URLs
                    users.append({
                        "pin": str(data.get("pin") or key),
                        "name": str(data.get("name") or ""),
                        "active": bool(data.get("active", True)),
                        "created_at": data.get("created_at"),
                        "expires_at": data.get("expires_at"),
                        "traffic_total_bytes": data.get("traffic_total_bytes", 0),
                        "traffic_remaining_bytes": data.get("traffic_remaining_bytes", 0),
                        "panel_ids": data.get("panel_ids") or ([] if not data.get("panel_id") else [data.get("panel_id")]),
                        "panel_type": data.get("panel_type") or "multi",
                        "max_devices": data.get("max_devices", 1),
                        "devices": data.get("devices") or ([] if not data.get("device_id") else [data.get("device_id")]),
                        "device_id": data.get("device_id"),
                        "bound_at": data.get("bound_at"),
                        "comment": data.get("comment") or "",
                        "telegram_id": data.get("telegram_id")
                    })
            except Exception:
                pass
        return users

    def get_all_full_users(self):
        """Returns complete raw user records with all upstream URLs and settings for background sync."""
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("SELECT key, value FROM kv_store")
            rows = cur.fetchall()
        users = []
        for key, val in rows:
            if key.startswith("__") or key == "apk_meta":
                continue
            try:
                data = json.loads(val)
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    data["pin"] = str(data.get("pin") or key)
                    users.append(data)
            except Exception:
                pass
        return users

    def get_all_kv(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("SELECT key, value FROM kv_store")
            rows = cur.fetchall()
        res = {}
        for key, val in rows:
            try:
                res[key] = json.loads(val)
            except Exception:
                res[key] = val
        return res

    def dump_to_backup_file(self):
        """Atomically dumps the entire database key-value store to BACKUP_PATH (data.json)."""
        try:
            all_kv = self.get_all_kv()
            tmp_path = BACKUP_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(all_kv, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, BACKUP_PATH)
        except Exception as e:
            logging.error(f"[Database] Failed to dump backup to {BACKUP_PATH}: {e}")

    def import_from_dict(self, data_dict):
        with self._lock, self.conn:
            for k, v in data_dict.items():
                val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                self.conn.execute("""
                    INSERT INTO kv_store (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """, (k, val_str, int(time.time())))
        self.dump_to_backup_file()

db = Database()

# Seed database from backup if empty
if not db.get("__ADMIN_CUSTOM_PASSWORD__") and os.path.exists(BACKUP_PATH):
    try:
        with open(BACKUP_PATH, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
            db.import_from_dict(backup_data)
            logging.info(f"Successfully seeded database from {BACKUP_PATH} ({len(backup_data)} keys)")
    except Exception as e:
        logging.error(f"Error seeding database: {e}")

if not db.get("__ADMIN_CUSTOM_PASSWORD__"):
    db.put("__ADMIN_CUSTOM_PASSWORD__", ADMIN_PASSWORD)

# Ensure panels configuration is seeded
if not db.get("__CONFIG_PANELS__"):
    db.put("__CONFIG_PANELS__", json.dumps(DEFAULT_INITIAL_PANELS, ensure_ascii=False))

# ==========================================
# BACKGROUND TRAFFIC & NODE SYNC ENGINE
# ==========================================
def run_traffic_sync_cycle():
    """
    Background worker cycle:
    1. Reads 3X-UI local SQLite client_traffics.
    2. Fetches active user subscription headers.
    3. Sums total traffic consumption and recalculates remaining bytes.
    4. Updates cached_nodes so mobile app connects in < 2ms without blocking.
    """
    try:
        users = db.get_all_full_users()
        active_users = [u for u in users if u.get("active", True) and u.get("pin")]
        if not active_users:
            return

        # 1. Map 3X-UI usage from local SQLite
        xui_usage = {}
        xui_db_path = "/etc/x-ui/x-ui.db"
        if os.path.exists(xui_db_path):
            try:
                with sqlite3.connect(xui_db_path, timeout=5) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT email, up, down, total FROM client_traffics")
                    for email, up, down, total in cur.fetchall():
                        if email:
                            xui_usage[email.lower()] = (up or 0) + (down or 0)
            except Exception as e:
                logging.warning(f"[BackgroundSync] Failed reading 3X-UI client_traffics: {e}")

        # Load configured panels once for matching
        panels_raw = db.get("__CONFIG_PANELS__")
        try:
            current_panels = json.loads(panels_raw) if panels_raw else DEFAULT_INITIAL_PANELS
        except Exception:
            current_panels = DEFAULT_INITIAL_PANELS

        # Map GoGuard remote user subscriptions dynamically
        goguard_map = {}
        try:
            g_panel = next((p for p in current_panels if p.get("id") == "panel_goguard_default" or p.get("type") == "goguard"), None)
            if g_panel and g_panel.get("autoSync") is not False:
                g_url = (g_panel.get("url") or "https://core.erfjab.com").rstrip("/")
                g_key = g_panel.get("apiKey") or "7c704f070ae553721bfa91b4bcfeb84e2eaa8109d09e56d00b471e9001ed5206"
                g_req = urllib.request.Request(f"{g_url}/api/subscriptions?limit=100", headers={"X-API-Key": g_key})
                with urllib.request.urlopen(g_req, timeout=6, context=INSECURE_SSL_CTX) as g_res:
                    if g_res.status == 200:
                        g_data = json.loads(g_res.read().decode("utf-8"))
                        for it in g_data.get("items", []):
                            uname = (it.get("username") or "").lower()
                            sub_link = it.get("subscription_link")
                            if uname and sub_link:
                                goguard_map[uname] = sub_link
        except Exception as ge:
            logging.warning(f"[BackgroundSync] Failed mapping GoGuard subscriptions: {ge}")

        # 2. Process each active user
        for u in active_users:
            pin = str(u.get("pin") or "").strip()
            name = (u.get("name") or "").lower()
            sub_urls = list(u.get("upstream_sub_urls") or [])
            if not sub_urls and u.get("upstream_sub_url"):
                sub_urls = [s.strip() for s in u["upstream_sub_url"].splitlines() if s.strip()]

            # Associate GoGuard subscription URL if matched
            if goguard_map:
                matched_g_sub = None
                for g_uname, g_sub in goguard_map.items():
                    if (pin and pin[-6:] in g_uname) or (name and name in g_uname):
                        matched_g_sub = g_sub
                        break
                if matched_g_sub and matched_g_sub not in sub_urls:
                    sub_urls.append(matched_g_sub)
                    u["upstream_sub_urls"] = sub_urls
                    if not u.get("remote_panel_mappings"):
                        u["remote_panel_mappings"] = {}
                    u["remote_panel_mappings"]["panel_goguard_default"] = {
                        "subUrl": matched_g_sub,
                        "panelType": "goguard"
                    }

            total_limit = int(u.get("traffic_total_bytes", 0) or 0)
            max_used = 0

            # Check 3X-UI usage
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace('@', ''))
            for ident, used in xui_usage.items():
                if (pin and pin in ident) or (clean_name and clean_name in ident):
                    max_used = max(max_used, used)

            # Group subscription URLs dynamically by panel priority
            sub_by_priority = {}
            seen_urls = set()
            for s_url in sub_urls:
                if not s_url or not s_url.startswith("http") or s_url in seen_urls:
                    continue
                seen_urls.add(s_url)
                p_id, p_name, p_priority = resolve_panel_for_sub_url(s_url, current_panels)
                sub_by_priority.setdefault(p_priority, []).append((s_url, p_id, p_name))

            tier_nodes_map = {}
            for p_priority in sorted(sub_by_priority.keys()):
                tier_nodes_map[p_priority] = []
                for s_url, p_id, p_name in sub_by_priority[p_priority]:
                    sub_data = fetch_subscription_data(s_url, timeout=7)
                    if sub_data["user_info"]:
                        ui = sub_data["user_info"]
                        used_sub = (ui.get("upload", 0) + ui.get("download", 0))
                        max_used = max(max_used, used_sub)
                        if ui.get("total", 0) > total_limit:
                            total_limit = ui["total"]

                    # Parse raw nodes strictly tagged with panel id, name, and waterfall priority
                    for r_line in sub_data["nodes_raw"]:
                        node_obj = parse_raw_proxy_link(r_line, panel_id=p_id, panel_name=p_name, priority=p_priority)
                        if not node_obj:
                            continue
                        if len(tier_nodes_map[p_priority]) < 150:
                            tier_nodes_map[p_priority].append(node_obj)

            # Recalculate remaining
            changed = False
            if total_limit > 0:
                calc_rem = max(0, total_limit - max_used)
                if u.get("traffic_remaining_bytes") != calc_rem or u.get("traffic_total_bytes") != total_limit:
                    u["traffic_remaining_bytes"] = calc_rem
                    u["traffic_total_bytes"] = total_limit
                    changed = True

            combined_nodes = []
            for p_priority in sorted(tier_nodes_map.keys()):
                combined_nodes.extend(tier_nodes_map[p_priority])

            if combined_nodes and len(combined_nodes) >= 1:
                u["cached_nodes"] = combined_nodes
                changed = True
                changed = True

            if changed:
                db.put(pin, json.dumps(u, ensure_ascii=False))

        # Sync database state to backup file
        db.dump_to_backup_file()

        logging.info(f"[BackgroundSync] Completed sync for {len(active_users)} active users.")
    except Exception as e:
        logging.error(f"[BackgroundSync] Error in sync cycle: {e}")

def background_sync_thread():
    # Initial delay on startup
    time.sleep(10)
    while True:
        run_traffic_sync_cycle()
        time.sleep(300) # Sync every 5 minutes

sync_thread = threading.Thread(target=background_sync_thread, daemon=True)
sync_thread.start()


# ==========================================
# APP VERSION & ABI SPLIT MANAGER
# ==========================================
def get_app_update_info(abi: str = None) -> dict:
    raw = db.get("__CONFIG_APP_UPDATE__")
    config = {}
    if raw:
        try:
            config = json.loads(raw)
        except Exception:
            config = {}

    ver_name = str(config.get("versionName") or config.get("version") or APP_VERSION).strip()
    try:
        ver_code = int(config.get("versionCode") or config.get("version_code") or APP_VERSION_CODE)
    except Exception:
        ver_code = APP_VERSION_CODE
    force_update = bool(config.get("forceUpdate", False))
    notes = str(config.get("releaseNotes") or config.get("changelog") or "بهینه‌سازی هوشمند سرعت دانلود در پس‌زمینه (در منوی چرخدنده)، رفع خطای اتصال کاربران جدید، فیلتر برنامه‌ها و پایداری شبکه").strip()

    base_opt = "/opt/asanvpn"

    def resolve_apk(abi_name):
        candidates = [
            os.path.join(base_opt, f"AsanVPN-v{ver_name}-{abi_name}.apk"),
            os.path.join(base_opt, f"AsanVPN-{abi_name}.apk"),
            os.path.join(base_opt, f"asanvpn-{abi_name}.apk"),
        ]
        if abi_name == "universal":
            candidates.extend([
                os.path.join(base_opt, f"AsanVPN-v{ver_name}-universal.apk"),
                os.path.join(base_opt, "AsanVPN-universal.apk"),
                os.path.join(base_opt, "AsanVPN.apk"),
                os.path.join(base_opt, "AsanVPN-latest.apk"),
                os.path.join(base_opt, "asanvpn.apk")
            ])
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]

    files = {
        "arm64-v8a": resolve_apk("arm64-v8a"),
        "armeabi-v7a": resolve_apk("armeabi-v7a"),
        "universal": resolve_apk("universal"),
    }

    sizes = {}
    for k, p in files.items():
        if os.path.exists(p):
            sizes[k] = os.path.getsize(p)
        else:
            sizes[k] = 21188373 if "64" in k else (21717012 if "v7" in k else 60844351)

    abis_info = {
        "arm64-v8a": {
            "url": "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download?abi=arm64-v8a",
            "fallbackUrl": "http://95.182.87.115/download?abi=arm64-v8a",
            "size": sizes["arm64-v8a"]
        },
        "armeabi-v7a": {
            "url": "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download?abi=armeabi-v7a",
            "fallbackUrl": "http://95.182.87.115/download?abi=armeabi-v7a",
            "size": sizes["armeabi-v7a"]
        },
        "universal": {
            "url": "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download",
            "fallbackUrl": "http://95.182.87.115/download",
            "size": sizes["universal"]
        }
    }

    target_dl = abis_info.get(abi, {}).get("url") if abi in abis_info else abis_info["universal"]["url"]
    target_fallback = abis_info.get(abi, {}).get("fallbackUrl") if abi in abis_info else abis_info["universal"]["fallbackUrl"]
    target_size = abis_info.get(abi, {}).get("size") if abi in abis_info else sizes["universal"]

    return {
        "success": True,
        "versionName": ver_name,
        "versionCode": ver_code,
        "forceUpdate": force_update,
        "totalSize": target_size,
        "downloadUrl": target_dl,
        "fallbackUrl": target_fallback,
        "githubUrl": f"https://github.com/armanpier/AsanVPN/releases/download/v{ver_name}/AsanVPN-v{ver_name}-universal.apk",
        "releaseNotes": notes,
        "abis": abis_info,
        "publishedAt": int(time.time())
    }


# ==========================================
# HTTP SERVER & API ROUTER
# ==========================================
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Token, X-Edge-Secret, Authorization")
        self.send_header("Connection", "close")
        self.send_header("Server", "AsanVPN-Edge-VPS/1.0")
        self.close_connection = True

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def is_authenticated_transit(self):
        client_host = self.client_address[0]
        if client_host in ("127.0.0.1", "::1", "localhost"):
            return True
        edge_secret = self.headers.get("X-Edge-Secret") or self.headers.get("x-edge-secret")
        if edge_secret and edge_secret == EDGE_SECRET:
            return True
        return False

    def check_admin_auth(self):
        token = self.headers.get("X-Admin-Token") or self.headers.get("x-admin-token") or ""
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            token = qs.get("token", [""])[0] or qs.get("admin_token", [""])[0] or qs.get("key", [""])[0]
        token = token.strip()
        custom_pwd = db.get("__ADMIN_CUSTOM_PASSWORD__") or ADMIN_PASSWORD
        valid_tokens = [custom_pwd.strip(), ADMIN_PASSWORD.strip()]
        if token and (token in valid_tokens or token.lower() in [vt.lower() for vt in valid_tokens]):
            return True

        # Check authorization cookie
        cookie_hdr = self.headers.get("Cookie") or self.headers.get("cookie") or ""
        if "asan_edge_auth=" in cookie_hdr:
            for part in cookie_hdr.split(";"):
                part = part.strip()
                if part.startswith("asan_edge_auth="):
                    cookie_token = part.split("asan_edge_auth=")[1].strip()
                    if cookie_token in valid_tokens or cookie_token.lower() in [vt.lower() for vt in valid_tokens]:
                        return True
        return False

    def send_json(self, status_code, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)
            try:
                self.wfile.flush()
            except Exception:
                pass

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw)
        except Exception:
            pass
        return {}

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Health
        if path in ["/health", "/ping"]:
            return self.send_json(200, {
                "status": "ok",
                "service": "AsanVPN VPS Core API",
                "time": int(time.time())
            })

        # Logout
        if path == "/logout":
            self.send_response(302)
            self.send_header("Set-Cookie", "asan_edge_auth=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly")
            self.send_header("Location", "/")
            self.send_cors_headers()
            self.end_headers()
            return

        # Admin Dashboard Frontend
        if path in ["/", "/admin", "/dashboard", "/panel", "/portal"]:
            if os.path.exists(DASHBOARD_HTML_PATH):
                with open(DASHBOARD_HTML_PATH, "rb") as f:
                    html_bytes = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_cors_headers()
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(html_bytes)
                    try:
                        self.wfile.flush()
                    except Exception:
                        pass
                return
            else:
                return self.send_json(404, {"error": "Dashboard template not found"})

        # Version check (supports ?abi=arm64-v8a or ?abi=armeabi-v7a)
        if path in ["/api/v1/app/version", "/api/v1/version", "/version"]:
            qs = urllib.parse.parse_qs(parsed.query)
            abi = qs.get("abi", [None])[0]
            info = get_app_update_info(abi)
            return self.send_json(200, info)

        # Direct APK Download (supports ?abi=arm64-v8a, ?abi=armeabi-v7a, /download/arm64-v8a, etc.)
        if path in ["/download", "/downloads", "/AsanVPN.apk", "/apk"] or path.startswith("/download/") or path.startswith("/downloads/"):
            qs = urllib.parse.parse_qs(parsed.query)
            abi = qs.get("abi", [None])[0]
            if not abi:
                if path.startswith("/download/"):
                    abi = path.removeprefix("/download/").strip("/")
                elif path.startswith("/downloads/"):
                    abi = path.removeprefix("/downloads/").strip("/")

            update_info = get_app_update_info(abi)
            ver_name = update_info.get("versionName") or APP_VERSION

            apk_path = None
            filename = f"AsanVPN-v{ver_name}-universal.apk"

            if abi and os.path.exists(os.path.join("/opt/asanvpn", abi)):
                apk_path = os.path.join("/opt/asanvpn", abi)
                filename = abi
            elif abi in ("arm64-v8a", "arm64"):
                for cand in [
                    f"/opt/asanvpn/AsanVPN-v{ver_name}-arm64-v8a.apk",
                    "/opt/asanvpn/AsanVPN-arm64-v8a.apk",
                    "/opt/asanvpn/asanvpn-arm64.apk"
                ]:
                    if os.path.exists(cand):
                        apk_path = cand
                        filename = f"AsanVPN-v{ver_name}-arm64-v8a.apk"
                        break
            elif abi in ("armeabi-v7a", "armeabi", "armv7"):
                for cand in [
                    f"/opt/asanvpn/AsanVPN-v{ver_name}-armeabi-v7a.apk",
                    "/opt/asanvpn/AsanVPN-armeabi-v7a.apk"
                ]:
                    if os.path.exists(cand):
                        apk_path = cand
                        filename = f"AsanVPN-v{ver_name}-armeabi-v7a.apk"
                        break

            if not apk_path:
                for candidate_name in [
                    f"AsanVPN-v{ver_name}-universal.apk",
                    "AsanVPN-universal.apk",
                    "AsanVPN.apk",
                    "AsanVPN-latest.apk",
                    "asanvpn.apk",
                    f"AsanVPN-v{ver_name}-arm64-v8a.apk",
                    "AsanVPN-arm64-v8a.apk"
                ]:
                    p = os.path.join("/opt/asanvpn", candidate_name)
                    if os.path.exists(p):
                        apk_path = p
                        filename = f"AsanVPN-v{ver_name}-universal.apk"
                        break

            if apk_path and os.path.exists(apk_path):
                file_size = os.path.getsize(apk_path)
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.android.package-archive")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_cors_headers()
                self.end_headers()
                if self.command != "HEAD":
                    with open(apk_path, "rb") as f:
                        while chunk := f.read(131072):
                            self.wfile.write(chunk)
                    try:
                        self.wfile.flush()
                    except Exception:
                        pass
                return
            else:
                self.send_response(302)
                self.send_header("Location", f"https://github.com/armanpier/AsanVPN/releases/download/v{ver_name}/AsanVPN-v{ver_name}-universal.apk")
                self.send_cors_headers()
                self.end_headers()
                return

        # ADMIN: Get App Update Configuration
        if path == "/api/v1/admin/config/update":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            qs = urllib.parse.parse_qs(parsed.query)
            abi = qs.get("abi", [None])[0]
            info = get_app_update_info(abi)
            return self.send_json(200, {"success": True, "config": info})

        # ADMIN: Get single user
        if path == "/api/v1/admin/user":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            qs = urllib.parse.parse_qs(parsed.query)
            pin = qs.get("pin", [""])[0].strip()
            raw = db.get(pin)
            if raw:
                try:
                    return self.send_json(200, {"success": True, "user": json.loads(raw)})
                except Exception:
                    pass
            return self.send_json(404, {"error": "User not found", "message": "کاربر یافت نشد."})

        # ADMIN: Get all users
        if path == "/api/v1/admin/users":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            users = db.get_all_users()
            return self.send_json(200, {
                "total": len(users),
                "users": users
            })

        # ADMIN: Get panels
        if path == "/api/v1/admin/panels":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            panels_json = db.get("__CONFIG_PANELS__")
            panels = json.loads(panels_json) if panels_json else DEFAULT_INITIAL_PANELS
            return self.send_json(200, {"panels": panels})

        # ADMIN: Download / Export Full System Backup
        if path in ["/api/v1/admin/backup/download", "/api/v1/admin/backup/export", "/api/v1/admin/backup"]:
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            all_kv = db.get_all_kv()
            timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
            backup_payload = {
                "_asanvpn_meta": {
                    "version": "2.0",
                    "backup_time": int(time.time()),
                    "backup_date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "server_ip": "95.182.87.115",
                    "key_count": len(all_kv)
                },
                "kv_data": all_kv
            }
            raw_bytes = json.dumps(backup_payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw_bytes)))
            self.send_header("Content-Disposition", f'attachment; filename="asanvpn-backup-{timestamp_str}.json"')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(raw_bytes)
            try:
                self.wfile.flush()
            except Exception:
                pass
            return

        # ADMIN: Remote Users from Panel
        if path == "/api/v1/admin/panels/remote_users":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            qs = urllib.parse.parse_qs(parsed.query)
            target_pid = qs.get("panel_id", [""])[0].strip()
            panels_json = db.get("__CONFIG_PANELS__")
            panels = json.loads(panels_json) if panels_json else DEFAULT_INITIAL_PANELS
            target_panel = next((p for p in panels if p.get("id") == target_pid), None)
            remote_users = []
            if target_panel:
                p_type = target_panel.get("type", "").lower()
                p_url = target_panel.get("url", "")
                p_key = target_panel.get("apiKey", "")
                p_sub = target_panel.get("subBaseUrl", "")
                p_auth = target_panel.get("authType", "apiKey")
                p_user = target_panel.get("username", "")
                p_pass = target_panel.get("password", "")

                if (p_auth == "userPass" or (p_user and p_pass)) and ("pasarguard" in p_type or "marzban" in p_type):
                    remote_users = fetch_pasarguard_remote_users(p_url, p_user, p_pass, p_sub)
                elif "3x" in p_type or p_type == "3xui":
                    xui_db_path = "/etc/x-ui/x-ui.db"
                    if os.path.exists(xui_db_path):
                        try:
                            with sqlite3.connect(xui_db_path, timeout=5) as conn:
                                cur = conn.cursor()
                                cur.execute("SELECT id, settings FROM inbounds")
                                for inb_id, inb_settings_raw in cur.fetchall():
                                    if inb_settings_raw:
                                        try:
                                            inb_cfg = json.loads(inb_settings_raw)
                                            for c in inb_cfg.get("clients", []):
                                                c_email = c.get("email", "")
                                                c_sub_id = c.get("subId") or c.get("id") or ""
                                                sub_link = p_sub.replace("{subId}", c_sub_id) if (p_sub and "{subId}" in p_sub) else f"https://95.182.87.115:2016/xx11fs28c0ea3gr5/{c_sub_id}"
                                                remote_users.append({
                                                    "name": c_email,
                                                    "username": c_email,
                                                    "subUrl": sub_link,
                                                    "panelType": "3xui"
                                                })
                                        except Exception:
                                            pass
                        except Exception as e:
                            logging.warning(f"Error reading 3X-UI remote users: {e}")
                elif "pasarguard" in p_type and p_key:
                    try:
                        req = urllib.request.Request(f"{p_url.rstrip('/')}/api/users", headers={"User-Agent": "Mozilla/5.0", "Authorization": f"ApiKey {p_key}", "X-API-KEY": p_key})
                        with urllib.request.urlopen(req, timeout=7, context=INSECURE_SSL_CTX) as res:
                            if res.status == 200:
                                u_data = json.loads(res.read().decode("utf-8"))
                                for u in u_data.get("users", []):
                                    uname = u.get("username", "")
                                    s_url = u.get("subscription_url") or ""
                                    if s_url and s_url.startswith("/") and p_sub:
                                        s_url = p_sub.rstrip("/") + s_url
                                    remote_users.append({
                                        "name": uname,
                                        "username": uname,
                                        "subUrl": s_url,
                                        "panelType": "pasarguard"
                                    })
                    except Exception as e:
                        logging.warning(f"Error reading PasarGuard remote users with API key: {e}")

            return self.send_json(200, {"success": True, "users": remote_users})

        # ADMIN: Get current password
        if path == "/api/v1/admin/password":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            pwd = db.get("__ADMIN_CUSTOM_PASSWORD__") or ADMIN_PASSWORD
            return self.send_json(200, {"password": pwd})

        self.send_json(404, {"error": "Not Found", "path": path})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        # ADMIN: Login
        if path == "/api/v1/admin/login":
            input_token = str(body.get("token") or body.get("password") or self.headers.get("X-Admin-Token") or "").strip()
            custom_pwd = (db.get("__ADMIN_CUSTOM_PASSWORD__") or ADMIN_PASSWORD).strip()
            if input_token == custom_pwd or input_token == ADMIN_PASSWORD:
                payload = json.dumps({
                    "success": True,
                    "message": "ورود با موفقیت انجام شد.",
                    "token": input_token
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Set-Cookie", f"asan_edge_auth={input_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(payload)
                try:
                    self.wfile.flush()
                except Exception:
                    pass
                return
            else:
                return self.send_json(401, {
                    "success": False,
                    "error": "رمز عبور وارد شده نادرست است."
                })

        # Check Admin Auth for all admin endpoints
        if path.startswith("/api/v1/admin/"):
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})

            # ADMIN: Extend User
            if path == "/api/v1/admin/extend":
                pin = str(body.get("pin", "")).strip()
                days = int(body.get("days", 30))
                traffic_gb = float(body.get("traffic_gb", 0))
                raw_user = db.get(pin)
                if not raw_user:
                    return self.send_json(404, {"error": "User not found", "message": "کاربر یافت نشد."})
                try:
                    user = json.loads(raw_user)
                    now = int(time.time())
                    current_exp = user.get("expires_at")
                    if current_exp and current_exp > now:
                        new_exp = current_exp + (days * 86400)
                    else:
                        new_exp = now + (days * 86400)
                    user["expires_at"] = new_exp
                    user["active"] = True

                    traffic_bytes_to_add = int(round(traffic_gb * (1024**3)))
                    current_total = int(user.get("traffic_total_bytes", 0) or 0)
                    current_rem = int(user.get("traffic_remaining_bytes", 0) or 0)
                    user["traffic_total_bytes"] = current_total + traffic_bytes_to_add
                    user["traffic_remaining_bytes"] = max(0, current_rem) + traffic_bytes_to_add

                    db.put(pin, json.dumps(user, ensure_ascii=False))
                    return self.send_json(200, {
                        "status": "success",
                        "pin": pin,
                        "new_expires_at": user["expires_at"],
                        "traffic_total_bytes": user["traffic_total_bytes"],
                        "traffic_remaining_bytes": user["traffic_remaining_bytes"]
                    })
                except Exception as e:
                    return self.send_json(500, {"error": str(e)})

            # ADMIN: Add/Edit User
            if path in ["/api/v1/admin/user", "/api/v1/admin/create", "/api/v1/admin/update"]:
                pin = str(body.get("pin", "")).strip()
                if not pin:
                    pin = generate_secure_10digit_pin(lambda p: db.get(p) is not None)
                    body["pin"] = pin
                if not is_valid_pin_format(pin):
                    return self.send_json(400, {"error": "Invalid PIN", "message": "کد اشتراک باید ۱۰ رقم (یا ۸ رقم برای کدهای قدیمی) باشد."})
                
                now = int(time.time())
                days = int(body.get("days", 30))
                traffic_gb = float(body.get("traffic_gb", 0))
                if traffic_gb > 0:
                    traffic_bytes = int(round(traffic_gb * (1024**3)))
                else:
                    traffic_bytes = int(body.get("traffic_total_bytes") or 0)
                if not body.get("created_at"):
                    body["created_at"] = now
                if not body.get("expires_at"):
                    body["expires_at"] = now + (days * 86400)
                if "traffic_total_bytes" not in body or body["traffic_total_bytes"] is None:
                    body["traffic_total_bytes"] = traffic_bytes
                if "traffic_remaining_bytes" not in body or body["traffic_remaining_bytes"] is None:
                    body["traffic_remaining_bytes"] = traffic_bytes if traffic_bytes > 0 else -1
                if traffic_bytes <= 0:
                    body["traffic_total_bytes"] = 0
                    body["traffic_remaining_bytes"] = -1
                if "active" not in body:
                    body["active"] = True

                # Synchronize user to all panels (AppleMarket, 3X-UI, etc.)
                try:
                    body = sync_user_to_panels(body)
                except Exception as sync_e:
                    logging.warning(f"Error during user panel sync: {sync_e}")

                db.put(pin, json.dumps(body, ensure_ascii=False))
                return self.send_json(200, {
                    "success": True,
                    "status": "created" if path == "/api/v1/admin/create" else "success",
                    "user": body,
                    "message": "کاربر با موفقیت ثبت شد."
                })

            # ADMIN: Delete User (POST)
            if path == "/api/v1/admin/delete":
                pin = str(body.get("pin", "")).strip()
                if not pin:
                    return self.send_json(400, {"error": "Missing PIN"})
                raw_user = db.get(pin)
                u_del = None
                if raw_user:
                    try:
                        u_del = json.loads(raw_user)
                    except Exception:
                        pass
                try:
                    delete_user_from_panels(pin, u_del)
                except Exception as e:
                    logging.warning(f"Error during panel user deletion: {e}")
                db.delete(pin)
                return self.send_json(200, {"status": "success", "message": f"کاربر {pin} با موفقیت از سرور و تمامی پنل‌ها حذف شد."})

            # ADMIN: Save Panels (Supports single panel update/add OR bulk list update)
            if path in ["/api/v1/admin/panels", "/api/v1/admin/panels/save"]:
                panels_raw = db.get("__CONFIG_PANELS__")
                try:
                    existing_panels = json.loads(panels_raw) if panels_raw else list(DEFAULT_INITIAL_PANELS)
                except Exception:
                    existing_panels = list(DEFAULT_INITIAL_PANELS)

                # Case A: Bulk list of panels
                if "panels" in body and isinstance(body.get("panels"), list):
                    new_panels = body["panels"]
                    if not new_panels and not body.get("allow_empty"):
                        return self.send_json(400, {"error": "Refusing to overwrite panels with empty list."})
                    db.put("__CONFIG_PANELS__", json.dumps(new_panels, ensure_ascii=False))
                    db.dump_to_backup_file()
                    return self.send_json(200, {"success": True, "message": "لیست پنل‌ها با موفقیت ذخیره گردید."})

                # Case B: Single panel save / edit (Sent from dashboard panel modal)
                target_id = body.get("id") or ""
                p_name = str(body.get("name", "")).strip()
                p_type = str(body.get("type", "3xui")).strip().lower()
                p_auth = str(body.get("authType", "apiKey")).strip()
                p_url = normalize_panel_url(str(body.get("url", "")))
                p_api_key = str(body.get("apiKey", "")).strip()
                p_user = str(body.get("username", "")).strip()
                p_pass = str(body.get("password", "")).strip()
                p_sub_base = str(body.get("subBaseUrl", "")).strip()
                p_priority = int(body.get("priority", 1) or 1)
                p_auto_sync = bool(body.get("autoSync", True))

                if not p_name or not p_url:
                    return self.send_json(400, {"error": "Missing required fields", "message": "نام و آدرس پنل الزامی هستند."})

                matched = False
                saved_panel = None
                for i, p in enumerate(existing_panels):
                    if target_id and p.get("id") == target_id:
                        existing_panels[i]["name"] = p_name
                        existing_panels[i]["type"] = p_type
                        existing_panels[i]["authType"] = p_auth
                        existing_panels[i]["url"] = p_url
                        existing_panels[i]["apiKey"] = p_api_key
                        existing_panels[i]["username"] = p_user
                        existing_panels[i]["password"] = p_pass
                        existing_panels[i]["subBaseUrl"] = p_sub_base
                        existing_panels[i]["priority"] = p_priority
                        existing_panels[i]["autoSync"] = p_auto_sync
                        saved_panel = existing_panels[i]
                        matched = True
                        break

                if not matched:
                    new_id = target_id or f"panel_{p_type}_{int(time.time())}"
                    saved_panel = {
                        "id": new_id,
                        "name": p_name,
                        "type": p_type,
                        "authType": p_auth,
                        "url": p_url,
                        "apiKey": p_api_key,
                        "username": p_user,
                        "password": p_pass,
                        "subBaseUrl": p_sub_base,
                        "priority": p_priority,
                        "autoSync": p_auto_sync,
                        "userCount": 0,
                        "createdAt": int(time.time()),
                        "lastSync": None,
                        "lastSyncStatus": None,
                        "lastSyncMessage": None
                    }
                    existing_panels.append(saved_panel)

                db.put("__CONFIG_PANELS__", json.dumps(existing_panels, ensure_ascii=False))
                db.dump_to_backup_file()
                # Trigger live background sync so nodes and priorities across all users reflect changes immediately
                try:
                    threading.Thread(target=run_traffic_sync_cycle, daemon=True).start()
                except Exception as te:
                    logging.warning(f"Failed to spawn background sync after panel update: {te}")
                return self.send_json(200, {
                    "success": True,
                    "panel": saved_panel,
                    "message": "مشخصات پنل با موفقیت ذخیره گردید."
                })

            # ADMIN: Delete Panel
            if path in ["/api/v1/admin/panels/delete", "/api/v1/admin/panel/delete"]:
                target_id = body.get("id") or body.get("panel_id")
                if not target_id:
                    return self.send_json(400, {"error": "Missing panel id"})
                panels_raw = db.get("__CONFIG_PANELS__")
                existing_panels = json.loads(panels_raw) if panels_raw else []
                new_panels = [p for p in existing_panels if p.get("id") != target_id]
                db.put("__CONFIG_PANELS__", json.dumps(new_panels, ensure_ascii=False))
                db.dump_to_backup_file()
                return self.send_json(200, {"success": True, "message": "پنل مورد نظر با موفقیت حذف گردید."})

            # ADMIN: Backup Restore / Import
            if path in ["/api/v1/admin/backup/restore", "/api/v1/admin/backup/import"]:
                if not body:
                    return self.send_json(400, {"error": "Empty backup payload"})
                kv_data = body.get("kv_data") if (isinstance(body, dict) and "kv_data" in body) else body
                if not isinstance(kv_data, dict):
                    return self.send_json(400, {"error": "Invalid backup format. Expected key-value dictionary."})
                db.import_from_dict(kv_data)
                db.dump_to_backup_file()
                # Also ensure all users in DB are synced to panels
                try:
                    for u_obj in db.get_all_users():
                        u_pin = u_obj.get("pin")
                        if u_pin:
                            synced_u = sync_user_to_panels(u_obj)
                            db.put(u_pin, json.dumps(synced_u, ensure_ascii=False))
                except Exception as sync_all_err:
                    logging.warning(f"Error syncing users across panels: {sync_all_err}")

                threading.Thread(target=run_traffic_sync_cycle, daemon=True).start()
                return self.send_json(200, {
                    "success": True,
                    "restored_keys": len(kv_data),
                    "message": f"بکاپ با موفقیت بازیابی شد ({len(kv_data)} رکورد بروزرسانی گردید)."
                })

            # ADMIN: Test Panel Latency & Auth
            if path == "/api/v1/admin/panels/test":
                p_id = body.get("panel_id") or body.get("id") or ""
                p_url = body.get("url", "").strip()
                p_type = body.get("type", "").lower()
                p_auth = body.get("authType", "apiKey")
                p_key = body.get("apiKey", "")
                p_user = body.get("username", "").strip()
                p_pass = body.get("password", "").strip()

                if (not p_url or (not p_key and not (p_user and p_pass))) and p_id:
                    panels_json = db.get("__CONFIG_PANELS__")
                    if panels_json:
                        try:
                            for p in json.loads(panels_json):
                                if p.get("id") == p_id:
                                    p_url = p.get("url", "").strip()
                                    p_type = p.get("type", "").lower()
                                    p_auth = p.get("authType", "apiKey")
                                    p_key = p.get("apiKey", "")
                                    p_user = p.get("username", "").strip()
                                    p_pass = p.get("password", "").strip()
                                    break
                        except Exception:
                            pass

                p_url = normalize_panel_url(p_url)
                start_t = time.time()
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AsanVPN/1.0"}
                    if (p_auth == "userPass" or (p_user and p_pass)) and ("pasarguard" in p_type or "marzban" in p_type):
                        tok = get_panel_jwt_token(p_url, p_user, p_pass, force_refresh=True)
                        if not tok:
                            return self.send_json(200, {"ok": False, "error": "احراز هویت ناموفق بود (نام کاربری یا رمز عبور اشتباه است)", "message": "خطا در لاگین به پنل"})
                        headers["Authorization"] = f"Bearer {tok}"
                        req = urllib.request.Request(f"{p_url.rstrip('/')}/api/users", headers=headers)
                        with urllib.request.urlopen(req, timeout=7, context=INSECURE_SSL_CTX) as res:
                            elapsed = int((time.time() - start_t) * 1000)
                            u_data = json.loads(res.read().decode("utf-8"))
                            cnt = len(u_data.get("users", [])) if isinstance(u_data, dict) else len(u_data)
                            return self.send_json(200, {
                                "ok": True,
                                "latency": elapsed,
                                "message": f"اتصال و لاگین موفق با اکانت {p_user} ({elapsed}ms - {cnt} کاربر در پنل)"
                            })
                    elif p_type == "pasarguard":
                        headers["Authorization"] = f"ApiKey {p_key}"
                        headers["X-API-KEY"] = p_key
                        req = urllib.request.Request(f"{p_url.rstrip('/')}/api/users", headers=headers)
                    elif p_type == "goguard":
                        headers["X-API-Key"] = p_key
                        req = urllib.request.Request(f"{p_url.rstrip('/')}/api/subscriptions", headers=headers)
                    elif p_type == "3xui" or "3x" in p_type:
                        xui_db = "/etc/x-ui/x-ui.db"
                        if os.path.exists(xui_db):
                            return self.send_json(200, {"ok": True, "latency": 1, "message": "اتصال محلی ۳X-UI فعال است (1ms)"})
                        req = urllib.request.Request(p_url, headers=headers)
                    else:
                        req = urllib.request.Request(p_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=7, context=INSECURE_SSL_CTX) as res:
                        elapsed = int((time.time() - start_t) * 1000)
                        return self.send_json(200, {"ok": True, "latency": elapsed, "message": f"اتصال موفق ({elapsed}ms)"})
                except Exception as e:
                    return self.send_json(200, {"ok": False, "error": str(e), "message": f"خطا در اتصال: {e}"})

            # ADMIN: Clear lockout for single user
            if path in ["/api/v1/admin/clear_lockout", "/api/v1/admin/reset_device"]:
                pin = str(body.get("pin", "")).strip()
                raw_user = db.get(pin)
                if raw_user:
                    try:
                        u = json.loads(raw_user)
                        old_dev = u.get("device_id")
                        old_devs = list(u.get("devices") or [])
                        u["device_id"] = None
                        u["devices"] = []
                        u["lockout_cleared"] = True
                        u["lockout_cleared_at"] = int(time.time())
                        if old_dev:
                            clear_rate_limit(dev_key=f"dev:{old_dev}")
                        for od in old_devs:
                            if od:
                                clear_rate_limit(dev_key=f"dev:{od}")
                        db.put(pin, json.dumps(u, ensure_ascii=False))
                        return self.send_json(200, {"success": True, "message": f"قفل دستگاه برای کاربر {pin} باز شد."})
                    except Exception as e:
                        return self.send_json(500, {"error": str(e)})
                return self.send_json(404, {"error": "User not found"})

            # ADMIN: Clear all lockouts
            if path in ["/api/v1/admin/clear_all_lockouts", "/api/v1/admin/unlock_rate_limit"]:
                users = db.get_all_users()
                count = 0
                for u in users:
                    pin = u.get("pin")
                    if pin:
                        old_dev = u.get("device_id")
                        old_devs = list(u.get("devices") or [])
                        u["device_id"] = None
                        u["devices"] = []
                        u["lockout_cleared"] = True
                        u["lockout_cleared_at"] = int(time.time())
                        if old_dev:
                            clear_rate_limit(dev_key=f"dev:{old_dev}")
                        for od in old_devs:
                            if od:
                                clear_rate_limit(dev_key=f"dev:{od}")
                        db.put(pin, json.dumps(u, ensure_ascii=False))
                        count += 1
                clear_rate_limit(clear_all=True)
                return self.send_json(200, {"success": True, "message": f"قفل دستگاه {count} کاربر باز شد."})

            # ADMIN: Change Password
            if path in ["/api/v1/admin/password", "/api/v1/admin/change_password"]:
                new_pwd = str(body.get("new_password") or body.get("password") or "").strip()
                if not new_pwd or len(new_pwd) < 4:
                    return self.send_json(400, {"error": "Invalid password", "message": "رمز عبور جدید باید حداقل ۴ نویسه باشد."})
                db.put("__ADMIN_CUSTOM_PASSWORD__", new_pwd)
                return self.send_json(200, {"success": True, "message": "رمز عبور با موفقیت به‌روزرسانی شد."})

            # ADMIN: Sync Panels (Manual trigger)
            if path in ["/api/v1/admin/sync_panels", "/api/v1/admin/panels/sync"]:
                p_id = body.get("id") or body.get("panel_id") or ""
                panels_json = db.get("__CONFIG_PANELS__")
                panels = json.loads(panels_json) if panels_json else list(DEFAULT_INITIAL_PANELS)
                target_panel = next((p for p in panels if p.get("id") == p_id), None) if p_id else None

                total_users = 0
                added_users = 0
                updated_users = 0

                if target_panel:
                    p_type = target_panel.get("type", "").lower()
                    p_url = target_panel.get("url", "")
                    p_sub = target_panel.get("subBaseUrl", "")
                    p_auth = target_panel.get("authType", "apiKey")
                    p_user = target_panel.get("username", "")
                    p_pass = target_panel.get("password", "")
                    rem_users = []
                    if (p_auth == "userPass" or (p_user and p_pass)) and ("pasarguard" in p_type or "marzban" in p_type):
                        rem_users = fetch_pasarguard_remote_users(p_url, p_user, p_pass, p_sub)
                    elif "3x" in p_type or p_type == "3xui":
                        xui_db_path = "/etc/x-ui/x-ui.db"
                        if os.path.exists(xui_db_path):
                            try:
                                with sqlite3.connect(xui_db_path, timeout=5) as conn:
                                    cur = conn.cursor()
                                    cur.execute("SELECT id, settings FROM inbounds")
                                    for inb_id, inb_settings_raw in cur.fetchall():
                                        if inb_settings_raw:
                                            try:
                                                inb_cfg = json.loads(inb_settings_raw)
                                                for c in inb_cfg.get("clients", []):
                                                    c_email = c.get("email", "")
                                                    c_sub_id = c.get("subId") or c.get("id") or ""
                                                    sub_link = p_sub.replace("{subId}", c_sub_id) if (p_sub and "{subId}" in p_sub) else f"https://95.182.87.115:2016/xx11fs28c0ea3gr5/{c_sub_id}"
                                                    rem_users.append({"name": c_email, "username": c_email, "subUrl": sub_link})
                                            except Exception:
                                                pass
                            except Exception as e:
                                logging.warning(f"Error reading 3X-UI: {e}")

                    total_users = len(rem_users)
                    for p in panels:
                        if p.get("id") == p_id:
                            p["userCount"] = total_users
                            p["lastSync"] = int(time.time())
                            p["lastSyncStatus"] = "success"
                            p["lastSyncMessage"] = f"همگام‌سازی موفق ({total_users} کاربر)"
                    db.put("__CONFIG_PANELS__", json.dumps(panels, ensure_ascii=False))
                    db.dump_to_backup_file()
                else:
                    for p in panels:
                        p_type = p.get("type", "").lower()
                        p_url = p.get("url", "")
                        p_sub = p.get("subBaseUrl", "")
                        p_auth = p.get("authType", "apiKey")
                        p_user = p.get("username", "")
                        p_pass = p.get("password", "")
                        rem_users = []
                        if (p_auth == "userPass" or (p_user and p_pass)) and ("pasarguard" in p_type or "marzban" in p_type):
                            rem_users = fetch_pasarguard_remote_users(p_url, p_user, p_pass, p_sub)
                        elif "3x" in p_type or p_type == "3xui":
                            xui_db_path = "/etc/x-ui/x-ui.db"
                            if os.path.exists(xui_db_path):
                                try:
                                    with sqlite3.connect(xui_db_path, timeout=5) as conn:
                                        cur = conn.cursor()
                                        cur.execute("SELECT id, settings FROM inbounds")
                                        for inb_id, inb_settings_raw in cur.fetchall():
                                            if inb_settings_raw:
                                                try:
                                                    inb_cfg = json.loads(inb_settings_raw)
                                                    for c in inb_cfg.get("clients", []):
                                                        c_email = c.get("email", "")
                                                        c_sub_id = c.get("subId") or c.get("id") or ""
                                                        sub_link = p_sub.replace("{subId}", c_sub_id) if (p_sub and "{subId}" in p_sub) else f"https://95.182.87.115:2016/xx11fs28c0ea3gr5/{c_sub_id}"
                                                        rem_users.append({"name": c_email, "username": c_email, "subUrl": sub_link})
                                                except Exception:
                                                    pass
                                except Exception:
                                    pass
                        if rem_users:
                            p["userCount"] = len(rem_users)
                            p["lastSync"] = int(time.time())
                            p["lastSyncStatus"] = "success"
                            p["lastSyncMessage"] = f"همگام‌سازی موفق ({len(rem_users)} کاربر)"
                            total_users += len(rem_users)
                    db.put("__CONFIG_PANELS__", json.dumps(panels, ensure_ascii=False))
                    db.dump_to_backup_file()

                # Also ensure all users in DB are synced to panels
                try:
                    for u_obj in db.get_all_users():
                        u_pin = u_obj.get("pin")
                        if u_pin:
                            synced_u = sync_user_to_panels(u_obj)
                            db.put(u_pin, json.dumps(synced_u, ensure_ascii=False))
                except Exception as sync_all_err:
                    logging.warning(f"Error syncing users across panels: {sync_all_err}")

                threading.Thread(target=run_traffic_sync_cycle, daemon=True).start()
                return self.send_json(200, {
                    "success": True,
                    "total": total_users,
                    "totalAdded": added_users,
                    "totalUpdated": updated_users,
                    "message": "عملیات همگام‌سازی ترافیک و سرورها انجام گردید."
                })

            # ADMIN: Update App Version & Force/Optional Settings
            if path in ["/api/v1/admin/config/update", "/api/v1/admin/app/version"]:
                existing_raw = db.get("__CONFIG_APP_UPDATE__")
                cfg = {}
                if existing_raw:
                    try:
                        cfg = json.loads(existing_raw)
                    except Exception:
                        cfg = {}
                if "versionName" in body and str(body["versionName"]).strip():
                    cfg["versionName"] = str(body["versionName"]).strip()
                if "versionCode" in body:
                    try:
                        cfg["versionCode"] = int(body["versionCode"])
                    except Exception:
                        pass
                if "forceUpdate" in body:
                    cfg["forceUpdate"] = bool(body["forceUpdate"])
                if "releaseNotes" in body and str(body["releaseNotes"]).strip():
                    cfg["releaseNotes"] = str(body["releaseNotes"]).strip()

                db.put("__CONFIG_APP_UPDATE__", json.dumps(cfg, ensure_ascii=False))
                updated_info = get_app_update_info()
                return self.send_json(200, {
                    "success": True,
                    "message": "تنظیمات نسخه و آپدیت با موفقیت ذخیره شد.",
                    "config": updated_info
                })

        # CLIENT: Lockout status check
        if path == "/api/v1/check_lockout":
            pin = str(body.get("pin", "")).strip()
            device_id = str(body.get("device_id", "")).strip()
            forwarded = self.headers.get("X-Forwarded-For") or ""
            cf_ip = self.headers.get("CF-Connecting-IP") or ""
            ar_ip = self.headers.get("AR-Real-IP") or ""
            client_ip = cf_ip or ar_ip or (forwarded.split(",")[0].strip() if forwarded else "") or self.client_address[0]
            ip_subnet = get_ip_subnet(client_ip)
            ip_key = f"ip:{ip_subnet}" if ip_subnet else ""
            dev_key = f"dev:{device_id}" if device_id else ""
            is_locked, rem_sec = check_rate_limit(ip_key, dev_key)
            return self.send_json(200, {
                "status": "success",
                "locked": is_locked,
                "remaining_seconds": rem_sec if is_locked else 0,
                "message_fa": "حساب مسدود است." if is_locked else "حساب فعال است."
            })

        # CLIENT: Connect endpoint (< 2ms instant response)
        if path == "/api/v1/connect":
            pin = str(body.get("pin", "")).strip()
            device_id = str(body.get("device_id", "")).strip()

            forwarded = self.headers.get("X-Forwarded-For") or ""
            cf_ip = self.headers.get("CF-Connecting-IP") or ""
            ar_ip = self.headers.get("AR-Real-IP") or ""
            client_ip = cf_ip or ar_ip or (forwarded.split(",")[0].strip() if forwarded else "") or self.client_address[0]
            ip_subnet = get_ip_subnet(client_ip)
            ip_key = f"ip:{ip_subnet}" if ip_subnet else ""
            dev_key = f"dev:{device_id}" if device_id else ""

            # Check rate limit lockout
            is_locked, rem_sec = check_rate_limit(ip_key, dev_key)
            if is_locked:
                return self.send_json(429, {
                    "status": "rate_limited",
                    "message_fa": f"تعداد تلاش‌های ناموفق بیش از ۳ بار بوده است. لطفاً {max(1, rem_sec // 60)} دقیقه دیگر تلاش کنید.",
                    "retry_after_seconds": rem_sec,
                    "locked_until_timestamp": (int(time.time()) + rem_sec) * 1000,
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            if not is_valid_pin_format(pin):
                locked, rem_sec, rem_attempts = record_failed_attempt(ip_key, dev_key)
                if locked:
                    return self.send_json(429, {
                        "status": "rate_limited",
                        "message_fa": "تعداد تلاش‌های ناموفق به ۳ بار رسید. ورود به مدت ۳۰ دقیقه مسدود شد.",
                        "retry_after_seconds": 1800,
                        "locked_until_timestamp": (int(time.time()) + 1800) * 1000,
                        "support_phone": SUPPORT_PHONE,
                        "support_telegram": SUPPORT_TELEGRAM
                    })
                return self.send_json(403, {
                    "status": "invalid_pin",
                    "message_fa": f"کد اشتراک باید ۱۰ رقم (یا ۸ رقم برای کدهای قدیمی) باشد. ({rem_attempts} فرصت باقی مانده)",
                    "remaining_attempts": rem_attempts,
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            raw_user = db.get(pin)
            if not raw_user:
                locked, rem_sec, rem_attempts = record_failed_attempt(ip_key, dev_key)
                if locked:
                    return self.send_json(429, {
                        "status": "rate_limited",
                        "message_fa": "تعداد تلاش‌های ناموفق به ۳ بار رسید. ورود به مدت ۳۰ دقیقه مسدود شد.",
                        "retry_after_seconds": 1800,
                        "locked_until_timestamp": (int(time.time()) + 1800) * 1000,
                        "support_phone": SUPPORT_PHONE,
                        "support_telegram": SUPPORT_TELEGRAM
                    })
                return self.send_json(403, {
                    "status": "invalid_pin",
                    "message_fa": f"کد اشتراک یافت نشد یا معتبر نمی‌باشد. ({rem_attempts} فرصت باقی مانده)",
                    "remaining_attempts": rem_attempts,
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            # Valid credentials - clear rate limit
            clear_rate_limit(ip_key, dev_key)

            user = json.loads(raw_user)
            now = int(time.time())

            if user.get("active") is False:
                return self.send_json(403, {
                    "status": "disabled",
                    "message_fa": "اشتراک شما غیرفعال شده است.",
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            if user.get("expires_at") and user["expires_at"] > 0 and user["expires_at"] < now:
                return self.send_json(403, {
                    "status": "expired",
                    "message_fa": "اعتبار زمانی اشتراک شما به پایان رسیده است.",
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            # Traffic exhaustion check (only applies if total quota is positive and finite)
            total_bytes = int(user.get("traffic_total_bytes", 0) or 0)
            rem_bytes = user.get("traffic_remaining_bytes")
            if total_bytes > 0 and rem_bytes is not None and rem_bytes != -1 and rem_bytes <= 0:
                return self.send_json(403, {
                    "status": "traffic_exhausted",
                    "message_fa": "حجم ترافیک اشتراک شما به پایان رسیده است. جهت شارژ مجدد با پشتیبانی تماس بگیرید.",
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM
                })

            # Device lock check
            raw_max = user.get("max_devices")
            try:
                max_dev = int(raw_max) if raw_max is not None and str(raw_max).strip() != "" else 1
            except Exception:
                max_dev = 1

            devices = list(user.get("devices") or ([] if not user.get("device_id") else [user.get("device_id")]))
            if device_id:
                if max_dev > 0:
                    if device_id not in devices:
                        if len(devices) >= max_dev:
                            return self.send_json(403, {
                                "status": "device_locked",
                                "message_fa": f"این اشتراک روی دستگاه دیگری فعال است (حداکثر {max_dev} دستگاه).",
                                "support_phone": SUPPORT_PHONE,
                                "support_telegram": SUPPORT_TELEGRAM
                            })
                        devices.append(device_id)
                        user["devices"] = devices
                        user["device_id"] = devices[0]
                        db.put(pin, json.dumps(user, ensure_ascii=False))
                else:
                    # Unlimited devices (max_dev <= 0)
                    if device_id not in devices:
                        devices.append(device_id)
                        user["devices"] = devices
                        if not user.get("device_id"):
                            user["device_id"] = device_id
                        db.put(pin, json.dumps(user, ensure_ascii=False))

            nodes = user.get("cached_nodes") or []
            if not nodes:
                try:
                    for cand_pin in ["22858950", "21825611", "33438704", "37600714", "15188776"]:
                        cand_raw = db.get(cand_pin)
                        if cand_raw:
                            c_data = json.loads(cand_raw)
                            c_nodes = c_data.get("cached_nodes")
                            if c_nodes and len(c_nodes) > 0:
                                nodes = c_nodes
                                break
                except Exception:
                    pass

            # If user has specific panel_ids assigned, filter nodes to those panels if available
            user_panel_ids = user.get("panel_ids") or []
            if user_panel_ids and nodes:
                filtered_nodes = [n for n in nodes if n.get("panel_id") in user_panel_ids]
                if filtered_nodes:
                    nodes = filtered_nodes

            # Strictly guarantee waterfall priority assignment and sorting based on LIVE __CONFIG_PANELS__
            panels_raw = db.get("__CONFIG_PANELS__")
            try:
                live_panels = json.loads(panels_raw) if panels_raw else DEFAULT_INITIAL_PANELS
            except Exception:
                live_panels = DEFAULT_INITIAL_PANELS

            panel_prio_map = {}
            panel_name_map = {}
            for p in live_panels:
                pid = p.get("id")
                if pid:
                    panel_prio_map[pid] = int(p.get("priority", 1))
                    panel_name_map[pid] = p.get("name")

            def get_node_live_info(n):
                pid = n.get("panel_id")
                raw_l = (n.get("raw_link") or "").lower()
                srv = (n.get("server") or "").lower()
                rem = (n.get("remark") or "").lower()
                p_name = (n.get("panel_name") or "").lower()

                if not pid or pid == "custom_panel" or pid not in panel_prio_map:
                    if any(k in raw_l for k in ["bertly.top", "erfjab.com", "fadaei.top", "sudopen.org", "hyperlink"]) or "goguard" in p_name or "go guard" in p_name:
                        pid = "panel_goguard_default"
                    elif "95.182.87.115" in srv or "fastly" in rem or "3x" in p_name:
                        pid = "panel_3xui_default"
                    elif "94.183.166.44" in srv or "94.139.179.53" in srv or "farsistar" in raw_l or "apple" in p_name:
                        pid = "panel_pasarguard_applemarket"
                    elif "trafficfast" in raw_l or "darklink" in raw_l or "pasarguard" in p_name:
                        pid = "panel_pasarguard_default"
                    else:
                        pid = "panel_3xui_default"

                prio = panel_prio_map.get(pid, int(n.get("panel_priority", 2)))
                name = panel_name_map.get(pid, n.get("panel_name") or "سرور")
                return pid, name, prio

            for n in nodes:
                pid, pname, prio = get_node_live_info(n)
                n["panel_id"] = pid
                n["panel_name"] = pname
                n["panel_priority"] = prio

            nodes = sorted(nodes, key=lambda x: int(x.get("panel_priority", 1)))
            days_left = max(0, (user["expires_at"] - now) // 86400) if user.get("expires_at") else "نامحدود"
            remaining_bytes = user.get("traffic_remaining_bytes")
            if remaining_bytes is None or (total_bytes <= 0 and remaining_bytes == 0):
                remaining_bytes = -1
            total_bytes = user.get("traffic_total_bytes", 26843545600)

            return self.send_json(200, {
                "status": "success",
                "user_info": {
                    "name": user.get("name") or "کاربر گرامی",
                    "days_left": days_left,
                    "traffic_remaining_bytes": remaining_bytes,
                    "traffic_total_bytes": total_bytes,
                    "max_devices": max_dev,
                    "active_devices_count": len(devices),
                    "support_phone": SUPPORT_PHONE,
                    "support_telegram": SUPPORT_TELEGRAM,
                    "is_admin": pin in ["22858950", "Arman4237340"]
                },
                "nodes": nodes
            })

        self.send_json(404, {"error": "Not Found", "path": path})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/v1/admin/user":
            if not self.check_admin_auth():
                return self.send_json(401, {"error": "Unauthorized", "message": "رمز عبور یا توکن مدیریت نامعتبر است"})
            params = urllib.parse.parse_qs(parsed.query)
            pin = params.get("pin", [""])[0]
            if not pin:
                body = self.read_json_body()
                pin = body.get("pin", "")
            if pin:
                db.delete(pin)
                return self.send_json(200, {"success": True, "message": f"کاربر {pin} با موفقیت حذف گردید."})
            return self.send_json(400, {"error": "Missing PIN"})
        self.send_json(404, {"error": "Not Found"})


def run():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), RequestHandler)
    logging.info(f"AsanVPN Standalone Core API Server (SSOT) running on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run()
