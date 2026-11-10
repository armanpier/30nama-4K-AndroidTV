import sys
import time
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
    page.goto('https://30nama.com/login', wait_until='commit', timeout=30000)
    page.wait_for_selector('input[name="userlogin"]', timeout=30000)
    time.sleep(2)
    
    html = page.content()
    with open('current_login_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved current_login_page.html, length:", len(html))
    context.close()
