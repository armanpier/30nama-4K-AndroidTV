# AsanVPN Unified Server & Disaster Recovery Suite

An automated, interactive installer and orchestrator for **AsanVPN Edge Backend Server** with multi-panel failover cascades (3X-UI, PasarGuard, GoGuard), domestic Iranian routing, SQLite SSOT with atomic JSON backups, and direct Android APK distribution.

---

## 🌟 Key Features

1. **Self-Contained Edge API & Web Dashboard**: Zero external pip dependencies. Powered by Python 3 standard library (`http.server`, `sqlite3`, `threading`, `urllib`).
2. **Priority-Based Waterfall Routing**:
   - **Priority 1 (Primary)**: Local/Direct 3X-UI nodes (`vless`, `fastly-xhttp`).
   - **Priority 2 (Secondary Failover)**: PasarGuard encrypted tunnel network (`darklink`, `trafficfast`).
   - **Priority 3 (Tertiary Failover)**: GoGuard Core network.
   - Mobile clients strictly query and lock onto Priority 1 first. Secondary tiers are engaged *only* during censorship outages.
3. **Disaster Recovery & Zero-Data-Loss Architecture**:
   - SQLite WAL database (`/etc/asanvpn/asanvpn.db`) with automatic real-time mirror dump to `/etc/asanvpn/data.json`.
   - 1-Click web backup download (`.json`) directly from the admin dashboard.
   - Instant disaster recovery: point the installer to any backup `.json` file to restore all 30+ users, device locks, and panels in seconds.
4. **Android APK Hosting**: Hosts `AsanVPN-universal.apk`, `arm64-v8a`, and `armeabi-v7a` directly on `/opt/asanvpn/` for instantaneous in-app updates and QR code sharing.

---

## 🚀 Quick Installation (New or Existing VPS)

### Requirements
- **OS**: Ubuntu 20.04 / 22.04 / 24.04 LTS or Debian 11 / 12 (x86_64 or arm64)
- **Privileges**: Root access (`sudo -i`)

### Run the Interactive Installer

Clone or download this repository on your VPS:

```bash
git clone https://github.com/armanpier/AsanVPN.git /tmp/asanvpn-repo
cd /tmp/asanvpn-repo/asanvpn-installer
sudo bash install.sh
```

Or upload this `asanvpn-installer` directory to your VPS and run:
```bash
chmod +x install.sh
sudo bash install.sh
```

---

## 📋 Interactive Installation Steps (English Guided Wizard)

During installation, the script will interactively guide you through:

| Step | Setting | Default Value | Description |
|---|---|---|---|
| **1** | Server IP / Domain | *Auto-detected* | Public IPv4 or domain pointing to this server |
| **2** | Web Dashboard Port | `80` | HTTP port for mobile API and admin web interface |
| **3** | Admin Password | `Arman4237340` | Secret password to log into the web dashboard |
| **4** | 3X-UI Integration | Priority 1 | Checks for local 3X-UI (or installs official 3X-UI automatically) |
| **5** | Secondary Panels | PasarGuard & GoGuard | Automated failover credentials and subscription URLs |
| **6** | Disaster Recovery | Optional | Restore all users and settings from an existing backup `.json` file |
| **7** | APK Download | `v1.3.16` | Fetches latest APKs into `/opt/asanvpn/` |

---

## 🔄 Disaster Recovery Workflow (Complete Restoration)

If your server was lost, re-installed, or corrupted:

1. **Option A: Restore During Installation**:
   When `install.sh` asks:
   ```text
   Do you want to restore from an existing backup file? [y/N]: y
   Enter absolute path to your backup .json file: /root/asanvpn-backup-2026-11-16.json
   ```
   The installer automatically imports all users, pins, device bindings, and panels into the fresh SQLite database.

2. **Option B: Restore on a Running System via Web Dashboard**:
   - Log into your dashboard (`http://YOUR_SERVER_IP/`).
   - Go to **Proxy Panels** or header menu.
   - Click **بازیابی بکاپ (Restore Backup)**.
   - Select your `.json` backup file. The dashboard will parse and confirm the number of records, restore the database, and trigger an immediate node sync.

3. **Option C: Manual CLI Restore**:
   ```bash
   cp /path/to/your-backup.json /etc/asanvpn/data.json
   systemctl restart asanvpn-api
   ```
   Upon restart, `server.py` detects the backup and seeds the database automatically.

---

## 🛠 Useful Service Management Commands

```bash
# Check API server status
systemctl status asanvpn-api

# View realtime server logs
journalctl -u asanvpn-api -f

# Restart API server
systemctl restart asanvpn-api

# Test server health locally
curl -s http://127.0.0.1/health

# Trigger background traffic & node synchronization manually
curl -s -X POST -H "X-Admin-Token: YOUR_PASSWORD" http://127.0.0.1/api/v1/admin/sync_panels
```

---

## 📁 Files & Directory Layout

```
/etc/asanvpn/
├── server.py              # Core API Server (Python standard library)
├── dashboard.html         # Single Page Admin Application
├── asanvpn.db             # Primary SQLite Database (WAL mode)
└── data.json              # Atomic Real-Time Persistence Backup

/opt/asanvpn/
├── AsanVPN.apk            # Direct download symlink
├── AsanVPN-universal.apk  # Universal APK
├── AsanVPN-arm64-v8a.apk  # 64-bit ARM APK
└── AsanVPN-armeabi-v7a.apk# 32-bit ARM APK

/etc/systemd/system/
└── asanvpn-api.service    # Auto-restart Systemd Service
```

---

## 🔒 Security & Firewall Ports

The installer automatically configures UFW rules for:
- `22/tcp`: SSH Management
- `80/tcp`: AsanVPN Web Dashboard & Mobile API
- `443/tcp`: Primary VLESS Inbound
- `2016/tcp`: 3X-UI Subscription Port
- `14393/tcp`: 3X-UI Web Administration Panel
- `2082/tcp`: Fastly-XHTTP Inbound
