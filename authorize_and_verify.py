import urllib.request
import urllib.parse
import json
import time
import os
import subprocess
import webbrowser
import sys

sys.stdout.reconfigure(encoding='utf-8')

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
proxy_handler = urllib.request.ProxyHandler(PROXIES)
opener = urllib.request.build_opener(proxy_handler)

BASE_URL = 'https://world.hana-api.com/api/v2/action'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'
DESKTOP_KEY = 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ'

HEADERS_BASE = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'c-api-key': TV_KEY,
    'c-version-number': '3.2.3',
    'c-language': 'fa',
    'user-agent': 'tv30nama/3.2.3'
}

def api_call(action, data=None, api_key=TV_KEY, token=None):
    headers = dict(HEADERS_BASE)
    headers['c-api-key'] = api_key
    if token:
        headers['c-token'] = token
        headers['Authorization'] = f"Bearer {token}"
    
    encoded = urllib.parse.urlencode(data or {}).encode('utf-8') if data is not None else b''
    url = f"{BASE_URL}/{action.lstrip('/')}"
    req = urllib.request.Request(url, data=encoded, headers=headers)
    try:
        with opener.open(req, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

def save_token_to_kodi(token):
    settings_xml = f'''<settings version="2">
    <setting id="c_token">{token}</setting>
    <setting id="proxy_url">http://127.0.0.1:10808</setting>
    <setting id="tv_api_key">{TV_KEY}</setting>
    <setting id="desktop_api_key">{DESKTOP_KEY}</setting>
    <setting id="auto_fix_persian_encoding">true</setting>
    <setting id="sub_priority">0</setting>
</settings>'''
    
    local_path = 'temp_settings.xml'
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(settings_xml)
    
    adb = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')
    dest_dir = '/sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata/addon_data/plugin.video.30nama'
    subprocess.run([adb, 'shell', f'mkdir -p {dest_dir}'])
    subprocess.run([adb, 'push', local_path, f'{dest_dir}/settings.xml'])
    print(f"Token saved to Kodi settings on emulator!")

def run():
    print("=" * 60)
    print("30nama Kodi 4K Addon Authorization & Verification Pipeline")
    print("=" * 60)
    
    # 1. Request QR code
    print("\n[Step 1] Requesting fresh TV activation code...")
    res = api_call('qrlogin_code', {})
    if not res.get('success'):
        print("Failed to get QR code:", res)
        return
    
    code = res['result']['code']
    auth_url = res['result']['url']
    print(f"\n========================================================")
    print(f"  TV ACTIVATION CODE : {code}")
    print(f"  ACTIVATION URL     : {auth_url}")
    print(f"========================================================\n")
    
    # 2. Open browser for authorization
    print("Opening activation page in browser...")
    webbrowser.open(auth_url)
    
    print("\nWaiting for confirmation in browser (timeout: 180s)...")
    print("Please click 'Confirm / تأیید' on the webpage.")
    
    start = time.time()
    token = None
    while time.time() - start < 180:
        login_res = api_call('qrlogin_login', {'auth_code': code})
        if login_res.get('success') and login_res.get('result', {}).get('token'):
            token = login_res['result']['token']
            print(f"\n[SUCCESS] Token acquired: {token}")
            break
        time.sleep(2)
        print(".", end="", flush=True)
        
    if not token:
        print("\nTimed out waiting for approval.")
        return
        
    # 3. Save to Kodi
    print("\n[Step 2] Injecting token into Kodi addon settings...")
    save_token_to_kodi(token)
    
    # 4. Verify account info
    print("\n[Step 3] Verifying authenticated user profile...")
    user_res = api_call('user', {}, TV_KEY, token)
    if user_res.get('success'):
        u = user_res.get('result', {}).get('user', {})
        print(f"  Username: {u.get('username')}")
        print(f"  Email: {u.get('email')}")
        print(f"  Subscription Plan: {u.get('plan', {}).get('title')}")
        print(f"  Expiration Date: {u.get('expire_date')}")
    else:
        print("  User verification response:", user_res)
        
    # 5. Verify /action/stream (4K profile)
    post_id = '721725'  # Poor Things / 4 Blocks Zero
    print(f"\n[Step 4] Verifying /action/stream for Post ID {post_id} with DESKTOP KEY (4K)...")
    stream_res = api_call('stream', {'post_id': post_id, 'free_stream': 'false'}, DESKTOP_KEY, token)
    if stream_res.get('success'):
        medias = stream_res.get('result', {}).get('medias', [])
        print(f"  Total stream profiles available: {len(medias)}")
        for m in medias:
            print(f"    Quality: {m.get('quality')}, Label: {m.get('label')}")
            file_obj = m.get('file', {})
            m3u8 = file_obj.get('m3u8') or file_obj.get('url')
            if m3u8:
                print(f"      URL: {m3u8[:80]}...")
    else:
        print("  Stream error:", stream_res)
        
    # 6. Verify /action/download (Direct 4K MKV)
    print(f"\n[Step 5] Verifying /action/download for Post ID {post_id} (Direct 4K MKV)...")
    dl_res = api_call('download', {'post_id': post_id, 'free_download': 'false'}, DESKTOP_KEY, token)
    print("  Download response:", json.dumps(dl_res, indent=2, ensure_ascii=False)[:500])
    
    print("\n[Step 6] Verification Pipeline Complete!")

if __name__ == '__main__':
    run()
