import sys
import time
import json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"

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
    
    responses = []
    page.on("response", lambda res: responses.append({
        "url": res.url,
        "status": res.status,
    }))

    print("Navigating to https://30nama.com/login ...")
    page.goto('https://30nama.com/login', wait_until='commit', timeout=30000)
    page.wait_for_selector('input[name="userlogin"]', timeout=30000)
    time.sleep(1)
    
    print("Clicking 'ورود با رمز عبور / پسورد'...")
    pwd_btn = page.locator("text='ورود با رمز عبور / پسورد'")
    pwd_btn.click()
    time.sleep(1)
    
    print("Filling credentials...")
    page.fill('input[name="userlogin"]', 'arman_pier@yahoo.com')
    time.sleep(0.5)
    page.fill('input[name="password"]', 'Arman4237340')
    time.sleep(1)
    
    print("Clicking submit button...")
    # Find submit button
    submit_btn = page.locator('div[type="submit"]')
    submit_btn.click()
    
    print("Waiting 5 seconds for network activity...")
    time.sleep(5)
    
    print("Current URL:", page.url)
    page.screenshot(path="login_after_submit.png")
    
    print("\nNetwork responses captured:")
    for r in responses:
        if "api" in r["url"] or "login" in r["url"] or "action" in r["url"] or "turnstile" in r["url"]:
            print(f"  {r['status']} {r['url']}")
            
    cookies = context.cookies()
    print(f"\nCookies captured ({len(cookies)}):")
    c_tokens = []
    for c in cookies:
        print(f"  {c['name']} = {c['value'][:30]}... domain={c['domain']}")
        if "token" in c['name'].lower() or "auth" in c['name'].lower() or "c-token" in c['name'].lower():
            c_tokens.append(c)
            
    with open('cookies_dump.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
        
    context.close()
