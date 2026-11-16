#!/usr/bin/env bash
# ==============================================================================
#  AsanVPN Complete Interactive System Installer & Disaster Recovery Suite
#  Platform: Ubuntu 20.04 / 22.04 / 24.04 & Debian 11 / 12
#  Architecture: x86_64 / arm64
# ==============================================================================

set -e

# ANSI Color Codes for Clean CLI Presentation
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

clear
cat << "EOF"
  █████╗ ███████╗ █████╗ ███╗   ██╗██╗   ██╗██████╗ ███╗   ██╗
 ██╔══██╗██╔════╝██╔══██╗████╗  ██║██║   ██║██╔══██╗████╗  ██║
 ███████║███████╗███████║██╔██╗ ██║██║   ██║██████╔╝██╔██╗ ██║
 ██╔══██║╚════██║██╔══██║██║╚██╗██║╚██╗ ██╔╝██╔═══╝ ██║╚██╗██║
 ██║  ██║███████║██║  ██║██║ ╚████║ ╚████╔╝ ██║     ██║ ╚████║
 ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═══╝  ╚═╝     ╚═╝  ╚═══╝
    Enterprise Edge Backend & Multi-Panel Orchestrator Installer
EOF

echo -e "${CYAN}==============================================================================${NC}"
echo -e "${BOLD} Welcome to the AsanVPN Unified Server Interactive Installer${NC}"
echo -e " This wizard will guide you through setting up or restoring the entire"
echo -e " AsanVPN ecosystem: Core API Server, Web Dashboard, 3X-UI integration,"
echo -e " secondary panel waterfalls, backup restoration, and APK distribution."
echo -e "${CYAN}==============================================================================${NC}\n"

# 1. Privilege Check
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This installer must be executed as root.${NC}"
   echo -e "Please re-run using: ${YELLOW}sudo bash install.sh${NC}"
   exit 1
fi

# 2. OS Compatibility Check
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_NAME=$ID
    OS_VER=$VERSION_ID
    echo -e "${GREEN}[OK] Operating System detected:${NC} ${BOLD}$PRETTY_NAME${NC}"
else
    echo -e "${YELLOW}[WARNING] Could not identify OS from /etc/os-release. Assuming Debian/Ubuntu compatible.${NC}"
    OS_NAME="ubuntu"
fi

# 3. Detect Public IPv4
DEFAULT_IP=$(curl -s -m 5 https://api.ipify.org || curl -s -m 5 https://icanhazip.com || hostname -I | awk '{print $1}')
echo -e "${GREEN}[OK] Detected Server Public IP:${NC} ${BOLD}${DEFAULT_IP}${NC}\n"

echo -e "${BOLD}${BLUE}--- STEP 1: Core Network & Domain Settings ---${NC}"
read -rp "Enter Server Domain or Public IP [default: ${DEFAULT_IP}]: " INPUT_IP
SERVER_IP="${INPUT_IP:-$DEFAULT_IP}"
echo -e "  -> Using Server Address: ${CYAN}${SERVER_IP}${NC}\n"

read -rp "Enter Web Dashboard & API Port [default: 80]: " INPUT_PORT
SERVER_PORT="${INPUT_PORT:-80}"
echo -e "  -> Using API Port: ${CYAN}${SERVER_PORT}${NC}\n"

echo -e "${BOLD}${BLUE}--- STEP 2: Administrative Security Credentials ---${NC}"
echo -e "The Admin Password is required to log into the web dashboard and manage users."
read -rp "Enter Admin Password [default: Arman4237340]: " INPUT_PASS
ADMIN_PASSWORD="${INPUT_PASS:-Arman4237340}"
echo -e "  -> Admin Password set.\n"

echo -e "${BOLD}${BLUE}--- STEP 3: Primary Panel Integration (3X-UI - Priority 1) ---${NC}"
echo -e "Priority 1 is reserved for the primary 3X-UI server. Mobile clients always"
echo -e "connect to Priority 1 first as long as it is responsive."

XUI_INSTALLED=false
if systemctl is-active --quiet x-ui 2>/dev/null || [[ -d /etc/x-ui ]]; then
    XUI_INSTALLED=true
    echo -e "  -> Detected existing 3X-UI service on this server!"
fi

if [[ "$XUI_INSTALLED" == "false" ]]; then
    read -rp "Would you like to install official 3X-UI on this server now? [Y/n]: " INSTALL_XUI_CHOICE
    INSTALL_XUI_CHOICE="${INSTALL_XUI_CHOICE:-Y}"
    if [[ "$INSTALL_XUI_CHOICE" =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Installing official 3X-UI server...${NC}"
        bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh) || true
        XUI_INSTALLED=true
    fi
fi

read -rp "3X-UI Web Admin Port [default: 14393]: " INPUT_XUI_PORT
XUI_PORT="${INPUT_XUI_PORT:-14393}"

read -rp "3X-UI Web Secret Path [default: /eX6Vvc2csV2GKtzmPF]: " INPUT_XUI_PATH
XUI_PATH="${INPUT_XUI_PATH:-/eX6Vvc2csV2GKtzmPF}"

read -rp "3X-UI Subscription Port [default: 2016]: " INPUT_SUB_PORT
XUI_SUB_PORT="${INPUT_SUB_PORT:-2016}"

read -rp "3X-UI Subscription Secret Path [default: /xx11fs28c0ea3gr5]: " INPUT_SUB_PATH
XUI_SUB_PATH="${INPUT_SUB_PATH:-/xx11fs28c0ea3gr5}"

read -rp "3X-UI API / Session Key [default: Wg6BrJKRiJzcNr4NKnjlxjZSAxMUIYkh7lzvWUDUQn3gxmW9]: " INPUT_XUI_KEY
XUI_API_KEY="${INPUT_XUI_KEY:-Wg6BrJKRiJzcNr4NKnjlxjZSAxMUIYkh7lzvWUDUQn3gxmW9}"

XUI_URL="https://${SERVER_IP}:${XUI_PORT}${XUI_PATH}"
XUI_SUB_BASE="https://${SERVER_IP}:${XUI_SUB_PORT}${XUI_SUB_PATH}/{subId}"
echo -e "  -> 3X-UI URL: ${CYAN}${XUI_URL}${NC}"
echo -e "  -> 3X-UI Subscription Base: ${CYAN}${XUI_SUB_BASE}${NC}\n"

echo -e "${BOLD}${BLUE}--- STEP 4: Secondary Failover Panels (PasarGuard & GoGuard) ---${NC}"
echo -e "Secondary panels serve as automated failover tiers (Priority 2 & 3) if Priority 1"
echo -e "is ever unreachable or blocked by censorship."
read -rp "Configure secondary failover panels? [Y/n]: " SECONDARY_CHOICE
SECONDARY_CHOICE="${SECONDARY_CHOICE:-Y}"

PASARGUARD_ENABLED=false
GOGUARD_ENABLED=false

if [[ "$SECONDARY_CHOICE" =~ ^[Yy]$ ]]; then
    PASARGUARD_ENABLED=true
    read -rp "PasarGuard Panel API URL [default: https://irtun.darklink.ir:8000]: " INPUT_PG_URL
    PG_URL="${INPUT_PG_URL:-https://irtun.darklink.ir:8000}"

    read -rp "PasarGuard API Key [default: pg_key_f85f5abb-13cc-4dc5-b3fc-8a77c2026e94]: " INPUT_PG_KEY
    PG_KEY="${INPUT_PG_KEY:-pg_key_f85f5abb-13cc-4dc5-b3fc-8a77c2026e94}"

    read -rp "PasarGuard Sub Base URL [default: https://irsub.trafficfast.ir:9090]: " INPUT_PG_SUB
    PG_SUB="${INPUT_PG_SUB:-https://irsub.trafficfast.ir:9090}"

    GOGUARD_ENABLED=true
    read -rp "GoGuard Core API URL [default: https://core.erfjab.com]: " INPUT_GG_URL
    GG_URL="${INPUT_GG_URL:-https://core.erfjab.com}"

    read -rp "GoGuard API Key [default: 7c704f070ae553721bfa91b4bcfeb84e2eaa8109d09e56d00b471e9001ed5206]: " INPUT_GG_KEY
    GG_KEY="${INPUT_GG_KEY:-7c704f070ae553721bfa91b4bcfeb84e2eaa8109d09e56d00b471e9001ed5206}"
fi
echo -e ""

echo -e "${BOLD}${BLUE}--- STEP 5: Disaster Recovery & Backup Restoration ---${NC}"
echo -e "If you have an existing backup JSON file (e.g. data.json or asanvpn-backup-*.json),"
echo -e "we can restore all previous users, device locks, and panels immediately."
read -rp "Do you want to restore from an existing backup file? [y/N]: " RESTORE_CHOICE
RESTORE_CHOICE="${RESTORE_CHOICE:-N}"

BACKUP_FILE_TO_RESTORE=""
if [[ "$RESTORE_CHOICE" =~ ^[Yy]$ ]]; then
    read -rp "Enter absolute path to your backup .json file: " INPUT_BKP_PATH
    if [[ -f "$INPUT_BKP_PATH" ]]; then
        BACKUP_FILE_TO_RESTORE="$INPUT_BKP_PATH"
        echo -e "${GREEN}[OK] Valid backup file found:${NC} $BACKUP_FILE_TO_RESTORE"
    else
        echo -e "${RED}[ERROR] File not found at $INPUT_BKP_PATH! Will proceed with fresh initialization.${NC}"
    fi
fi
echo -e ""

echo -e "${BOLD}${BLUE}--- STEP 6: Android Mobile APK Distribution ---${NC}"
echo -e "Hosts universal and ABI-specific APKs in /opt/asanvpn/ for direct in-app updates"
echo -e "and QR code camera downloads without requiring external store access."
read -rp "Download latest AsanVPN Android APKs (v1.3.16) to /opt/asanvpn/? [Y/n]: " DOWNLOAD_APK_CHOICE
DOWNLOAD_APK_CHOICE="${DOWNLOAD_APK_CHOICE:-Y}"
echo -e ""

# ==============================================================================
# EXECUTION PHASE
# ==============================================================================
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD} Starting Installation & Deployment...${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}\n"

# 1. Install System Dependencies
echo -e "${CYAN}[1/6] Installing required system packages...${NC}"
apt-get update -qq
apt-get install -y -qq python3 python3-pip sqlite3 curl wget ufw libsqlite3-dev psmisc >/dev/null
echo -e "${GREEN}[OK] System dependencies installed.${NC}\n"

# 2. Setup Directories
echo -e "${CYAN}[2/6] Configuring directories...${NC}"
mkdir -p /etc/asanvpn
mkdir -p /opt/asanvpn
echo -e "${GREEN}[OK] Directories ready (/etc/asanvpn, /opt/asanvpn).${NC}\n"

# 3. Deploy Core Files
echo -e "${CYAN}[3/6] Deploying AsanVPN Core Server and Web Dashboard...${NC}"
if [[ -f "${SCRIPT_DIR}/core/server.py" ]]; then
    cp "${SCRIPT_DIR}/core/server.py" /etc/asanvpn/server.py
    cp "${SCRIPT_DIR}/core/dashboard.html" /etc/asanvpn/dashboard.html
else
    echo -e "${RED}[ERROR] Source files not found in ${SCRIPT_DIR}/core!${NC}"
    exit 1
fi
chmod +x /etc/asanvpn/server.py
echo -e "${GREEN}[OK] Server files deployed successfully.${NC}\n"

# 4. Initialize Database / Restore Backup
echo -e "${CYAN}[4/6] Initializing database & configuration SSOT...${NC}"
if [[ -n "$BACKUP_FILE_TO_RESTORE" ]]; then
    echo -e "${YELLOW}Restoring database from backup: ${BACKUP_FILE_TO_RESTORE}...${NC}"
    cp "$BACKUP_FILE_TO_RESTORE" /etc/asanvpn/data.json
    # Import into SQLite
    python3 -c "
import sqlite3, json, time, os
data = json.load(open('/etc/asanvpn/data.json', 'r', encoding='utf-8'))
if 'kv_data' in data:
    data = data['kv_data']
conn = sqlite3.connect('/etc/asanvpn/asanvpn.db')
conn.execute('CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER)')
for k, v in data.items():
    val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
    conn.execute('INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (k, val_str, int(time.time())))
conn.commit()
print('Successfully restored', len(data), 'records into /etc/asanvpn/asanvpn.db')
"
else
    # Build initial data.json
    python3 -c "
import json, time
panels = [
    {
        'id': 'panel_3xui_default',
        'name': 'سرور ۳X-UI اصلی',
        'type': '3xui',
        'url': '${XUI_URL}',
        'apiKey': '${XUI_API_KEY}',
        'subBaseUrl': '${XUI_SUB_BASE}',
        'priority': 1,
        'autoSync': True,
        'createdAt': int(time.time()),
        'userCount': 0
    }
]

if '${PASARGUARD_ENABLED}' == 'true':
    panels.append({
        'id': 'panel_pasarguard_default',
        'name': 'سرور پاسارگاد (PasarGuard)',
        'type': 'pasarguard',
        'url': '${PG_URL}',
        'apiKey': '${PG_KEY}',
        'subBaseUrl': '${PG_SUB}',
        'priority': 2,
        'autoSync': True,
        'createdAt': int(time.time()),
        'userCount': 0
    })

if '${GOGUARD_ENABLED}' == 'true':
    panels.append({
        'id': 'panel_goguard_default',
        'name': 'سرور گوگارد (GoGuard Core)',
        'type': 'goguard',
        'url': '${GG_URL}',
        'apiKey': '${GG_KEY}',
        'subBaseUrl': '',
        'priority': 3,
        'autoSync': True,
        'createdAt': int(time.time()),
        'userCount': 0
    })

init_data = {
    '__ADMIN_CUSTOM_PASSWORD__': '${ADMIN_PASSWORD}',
    '__CONFIG_APP_UPDATE__': {
        'versionName': '1.3.16',
        'versionCode': 22,
        'forceUpdate': False,
        'releaseNotes': 'قابلیت سوییچ خودکار ۵ ثانیه‌ای به سریع‌ترین سرور و اولویت‌بندی آبشاری پنل‌ها'
    },
    '__CONFIG_PANELS__': panels
}

with open('/etc/asanvpn/data.json', 'w', encoding='utf-8') as f:
    json.dump(init_data, f, ensure_ascii=False, indent=2)
print('Initialized /etc/asanvpn/data.json with', len(panels), 'panels.')
"
fi
echo -e "${GREEN}[OK] Database initialized.${NC}\n"

# 5. Fetch APKs if requested
if [[ "$DOWNLOAD_APK_CHOICE" =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}[5/6] Downloading latest Android APKs into /opt/asanvpn/...${NC}"
    RELEASE_TAG="v1.3.16"
    BASE_GH="https://github.com/armanpier/AsanVPN/releases/download/${RELEASE_TAG}"
    wget -q -O /opt/asanvpn/AsanVPN-universal.apk "${BASE_GH}/AsanVPN-${RELEASE_TAG}-universal.apk" || true
    wget -q -O /opt/asanvpn/AsanVPN-arm64-v8a.apk "${BASE_GH}/AsanVPN-${RELEASE_TAG}-arm64-v8a.apk" || true
    wget -q -O /opt/asanvpn/AsanVPN-armeabi-v7a.apk "${BASE_GH}/AsanVPN-${RELEASE_TAG}-armeabi-v7a.apk" || true
    cp /opt/asanvpn/AsanVPN-universal.apk /opt/asanvpn/AsanVPN.apk 2>/dev/null || true
    echo -e "${GREEN}[OK] APK files ready in /opt/asanvpn/.${NC}\n"
else
    echo -e "${YELLOW}[5/6] Skipping APK download.${NC}\n"
fi

# 6. Setup Systemd Service & Firewall
echo -e "${CYAN}[6/6] Installing systemd service & setting up firewall...${NC}"
cp "${SCRIPT_DIR}/systemd/asanvpn-api.service" /etc/systemd/system/asanvpn-api.service

# Stop anything blocking the port
fuser -k "${SERVER_PORT}/tcp" 2>/dev/null || true

systemctl daemon-reload
systemctl enable asanvpn-api
systemctl restart asanvpn-api

# Configure Firewall (UFW)
if command -v ufw >/dev/null 2>&1; then
    ufw allow 22/tcp >/dev/null 2>&1 || true
    ufw allow "${SERVER_PORT}/tcp" >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
    ufw allow "${XUI_SUB_PORT}/tcp" >/dev/null 2>&1 || true
    ufw allow "${XUI_PORT}/tcp" >/dev/null 2>&1 || true
    ufw allow 2082/tcp >/dev/null 2>&1 || true
fi

sleep 2

# Verification Health Check
HEALTH_CHECK=$(curl -s -m 5 "http://127.0.0.1:${SERVER_PORT}/health" || echo "FAILED")

if [[ "$HEALTH_CHECK" =~ "ok" ]]; then
    echo -e "${GREEN}[SUCCESS] AsanVPN API Service is running and healthy!${NC}\n"
else
    echo -e "${RED}[WARNING] Health check response: ${HEALTH_CHECK}${NC}"
    echo -e "Check service logs with: ${YELLOW}journalctl -u asanvpn-api -e --no-pager${NC}\n"
fi

# ==============================================================================
# SUMMARY & USAGE INFORMATION
# ==============================================================================
echo -e "${BOLD}${GREEN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}               ASANVPN INSTALLATION COMPLETED SUCCESSFULLY!                  ${NC}"
echo -e "${BOLD}${GREEN}==============================================================================${NC}"
echo -e ""
echo -e "  ${BOLD}Web Admin Dashboard:${NC}    ${CYAN}http://${SERVER_IP}:${SERVER_PORT}/${NC}"
echo -e "  ${BOLD}Admin Password:${NC}          ${YELLOW}${ADMIN_PASSWORD}${NC}"
echo -e "  ${BOLD}Client Connect Endpoint:${NC} ${CYAN}http://${SERVER_IP}:${SERVER_PORT}/api/v1/connect${NC}"
echo -e "  ${BOLD}Health Check Endpoint:${NC}   ${CYAN}http://${SERVER_IP}:${SERVER_PORT}/health${NC}"
echo -e "  ${BOLD}APK Download URL:${NC}        ${CYAN}http://${SERVER_IP}:${SERVER_PORT}/download${NC}"
echo -e ""
echo -e "  ${BOLD}3X-UI Admin Panel:${NC}       ${CYAN}${XUI_URL}${NC}"
echo -e "  ${BOLD}3X-UI Subscription:${NC}      ${CYAN}${XUI_SUB_BASE}${NC}"
echo -e ""
echo -e "  ${BOLD}Service Management Commands:${NC}"
echo -e "    • Status:   ${YELLOW}systemctl status asanvpn-api${NC}"
echo -e "    • Restart:  ${YELLOW}systemctl restart asanvpn-api${NC}"
echo -e "    • Logs:     ${YELLOW}journalctl -u asanvpn-api -f${NC}"
echo -e ""
echo -e "  ${BOLD}Backup & Disaster Recovery:${NC}"
echo -e "    • Auto-backup location: ${YELLOW}/etc/asanvpn/data.json${NC}"
echo -e "    • Web download backup:   Navigate to Settings / Panels -> 'Download Backup'"
echo -e "    • Manual restore:        Copy your backup .json to ${YELLOW}/etc/asanvpn/data.json${NC}"
echo -e "                             and restart service."
echo -e "${BOLD}${GREEN}==============================================================================${NC}\n"
