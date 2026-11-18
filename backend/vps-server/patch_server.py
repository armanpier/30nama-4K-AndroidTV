import re

with open('backend/vps-server/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace sync_3xui_sqlite
old_sync_3xui = """def sync_3xui_sqlite(user_data):
    \"\"\"
    Directly synchronizes user totalGB and expiryTime into local 3X-UI SQLite database (/etc/x-ui/x-ui.db).
    Guarantees sub-millisecond local update of 3X-UI clients without requiring external web session tokens.
    \"\"\"
    xui_db_path = "/etc/x-ui/x-ui.db"
    if not os.path.exists(xui_db_path):
        return
    try:
        if isinstance(user_data, str):
            user_data = json.loads(user_data)
        if not isinstance(user_data, dict):
            return

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

            if not matched_emails:
                return

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
                    if modified:
                        cur.execute(
                            "UPDATE inbounds SET settings = ? WHERE id = ?",
                            (json.dumps(inb_settings, ensure_ascii=False), inb_id)
                        )
                except Exception as json_err:
                    logging.warning(f"[3X-UI Sync] Failed to parse inbound {inb_id} settings: {json_err}")

            conn.commit()
            logging.info(f"[3X-UI Sync] Synced {matched_emails} in 3X-UI (Total: {total_bytes}, Expiry: {expiry_ms})")
    except Exception as e:
        logging.warning(f"[3X-UI Sync] Error synchronizing with /etc/x-ui/x-ui.db: {e}")"""

new_sync_3xui = """def sync_3xui_sqlite(user_data):
    \"\"\"
    Directly synchronizes user totalGB and expiryTime into local 3X-UI SQLite database (/etc/x-ui/x-ui.db).
    If client does not exist, automatically creates it in inbounds 1 & 9 and client_traffics.
    Returns (subId, email) tuple or (None, None).
    \"\"\"
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
        return (None, None)"""

assert old_sync_3xui in content, "old_sync_3xui not found!"
content = content.replace(old_sync_3xui, new_sync_3xui)

# 2. Update 3X-UI subUrl handling in sync_user_to_panels
old_sync_panels_3xui = """    # --- 2. 3X-UI ---
    try:
        sync_3xui_sqlite(user_data)
    except Exception as e:
        logging.warning(f"Error syncing user to 3X-UI: {e}")"""

new_sync_panels_3xui = """    # --- 2. 3X-UI ---
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
        logging.warning(f"Error syncing user to 3X-UI: {e}")"""

assert old_sync_panels_3xui in content, "old_sync_panels_3xui not found!"
content = content.replace(old_sync_panels_3xui, new_sync_panels_3xui)

# 3. Add delete_user_from_panels function before class Database
delete_func = """def delete_user_from_panels(pin: str, user_data: dict = None):
    \"\"\"Deletes user from both AppleMarket and local 3X-UI.\"\"\"
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

"""

content = content.replace("# ==========================================\n# DATABASE (SQLite with WAL Mode)", delete_func + "# ==========================================\n# DATABASE (SQLite with WAL Mode)")

# 4. Update /api/v1/admin/delete handler to call delete_user_from_panels
old_admin_delete = """            # ADMIN: Delete User (POST)
            if path == "/api/v1/admin/delete":
                pin = str(body.get("pin", "")).strip()
                if not pin:
                    return self.send_json(400, {"error": "Missing PIN"})
                raw_user = db.get(pin)
                if raw_user:
                    try:
                        u_del = json.loads(raw_user)
                        mappings = u_del.get("remote_panel_mappings", {})
                        if isinstance(mappings, dict) and "panel_pasarguard_applemarket" in mappings:
                            ap_uname = mappings["panel_pasarguard_applemarket"].get("username")
                            if ap_uname:
                                panels_json = db.get("__CONFIG_PANELS__")
                                panels = json.loads(panels_json) if panels_json else list(DEFAULT_INITIAL_PANELS)
                                apple_panel = next((p for p in panels if p.get("id") == "panel_pasarguard_applemarket"), None)
                                if apple_panel:
                                    p_url = apple_panel.get("url", "https://pl.applemarket13.ir").rstrip("/")
                                    tok = get_panel_jwt_token(p_url, apple_panel.get("username", "P9502331E507"), apple_panel.get("password", "AB!8c9c8e207dxy9$"))
                                    if tok:
                                        del_req = urllib.request.Request(f"{p_url}/api/user/{urllib.parse.quote(ap_uname)}", headers={"Authorization": f"Bearer {tok}"}, method="DELETE")
                                        with urllib.request.urlopen(del_req, timeout=6, context=INSECURE_SSL_CTX) as _:
                                            pass
                    except Exception as e:
                        logging.warning(f"Error deleting remote user from panel: {e}")
                db.delete(pin)
                return self.send_json(200, {"status": "success", "message": f"کاربر {pin} حذف شد."})"""

new_admin_delete = """            # ADMIN: Delete User (POST)
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
                return self.send_json(200, {"status": "success", "message": f"کاربر {pin} با موفقیت از سرور و تمامی پنل‌ها حذف شد."})"""

assert old_admin_delete in content, "old_admin_delete not found!"
content = content.replace(old_admin_delete, new_admin_delete)

with open('backend/vps-server/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("server.py updated successfully!")
