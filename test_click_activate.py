import sys
import time
import json
import urllib.request
import urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"

PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
proxy_handler = urllib.request.ProxyHandler(PROXIES)
opener = urllib.request.build_opener(proxy_handler)

BASE_URL = 'https://world.hana-api.com/api/v2/action'
TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'

def api_call(action, data=None):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'c-api-key': TV_KEY,
        'c-version-number': '3.2.3',
        'c-language': 'fa',
        'user-agent': 'tv30nama/3.2.3'
    }
    encoded = urllib.parse.urlencode(data or {}).encode('utf-8') if data is not None else b''
    url = f"{BASE_URL}/{action}"
    req = urllib.request.Request(url, data=encoded, headers=headers)
    try:
        with opener.open(req, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

def main():
    print("1. Requesting fresh QR code from backend...")
    res = api_call('qrlogin_code', {})
    if not res.get('success'):
        print("Failed to get QR code:", res)
        return
        
    code = res['result']['code']
    auth_url = res['result']['url']
    print(f"Got TV activation code: {code}, URL: {auth_url}")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            proxy={'server': 'http://127.0.0.1:10808'},
            viewport={'width': 1280, 'height': 800}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        print(f"2. Navigating in logged-in Chrome to {auth_url} ...")
        page.goto(auth_url, wait_until='commit', timeout=30000)
        time.sleep(3)
        
        print("Locating 'فعال سازی' button...")
        act_btn = page.locator("text='فعال سازی'")
        if act_btn.count() > 0:
            print("Found 'فعال سازی' button! Clicking it...")
            act_btn.first.click()
            time.sleep(3)
            page.screenshot(path="after_activate_click.png")
        else:
            print("Button 'فعال سازی' not found directly by text, searching buttons...")
            buttons = page.query_selector_all('button, .btn-control, [type="submit"]')
            for idx, b in enumerate(buttons):
                t = b.inner_text().strip()
                if "فعال" in t:
                    print(f"Clicking button {idx}: {t}")
                    b.click()
                    time.sleep(3)
                    break
                    
        page.screenshot(path="after_activation.png")
        
        print("\n3. Polling qrlogin_login for TV token...")
        token = None
        for i in range(15):
            chk = api_call('qrlogin_login', {'auth_code': code})
            print(f"  Poll {i+1}: {chk.get('msg')} | success={chk.get('success')}")
            if chk.get('success') and chk.get('result', {}).get('token'):
                token = chk['result']['token']
                print(f"\n========================================================")
                print(f">>> [SUCCESS] TV SESSION TOKEN: {token} <<<")
                print(f"========================================================\n")
                break
            time.sleep(2)
            
        context.close()
        
        if token:
            with open("tv_session_token.txt", "w") as f:
                f.write(token)
            print("Successfully written tv_session_token.txt!")

if __name__ == '__main__':
    main()
