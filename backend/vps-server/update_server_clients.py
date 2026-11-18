with open('backend/vps-server/server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '                cur.execute("SELECT id, settings FROM inbounds WHERE id IN (1, 9)")'
assert target in text, 'target not found'

addition = """                # Insert into clients table for direct 3X-UI subscription serving
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

"""

text = text.replace(target, addition + target, 1)

del_target = 'cur.execute("DELETE FROM client_traffics WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))'
del_addition = """cur.execute("SELECT id FROM clients WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))
                for d_id, in cur.fetchall():
                    cur.execute("DELETE FROM client_inbounds WHERE client_id = ?", (d_id,))
                cur.execute("DELETE FROM clients WHERE email LIKE ? OR email = ?", (f"%{pin[-6:]}%", f"user_{pin}"))
                """
assert del_target in text, 'del_target not found'
text = text.replace(del_target, del_addition + del_target, 1)

with open('backend/vps-server/server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated server.py successfully!')
