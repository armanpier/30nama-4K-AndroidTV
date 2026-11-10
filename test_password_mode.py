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
    time.sleep(1)
    
    # Click "ورود با رمز عبور / پسورد"
    print("Clicking 'ورود با رمز عبور / پسورد'...")
    # Find element containing text "ورود با رمز عبور"
    pwd_btn = page.locator("text='ورود با رمز عبور / پسورد'")
    pwd_btn.click()
    time.sleep(2)
    
    inputs = page.query_selector_all('input')
    print(f"Inputs found after switching ({len(inputs)}):")
    for inp in inputs:
        print("  input:", inp.get_attribute('name'), inp.get_attribute('type'))
        
    page.screenshot(path="login_password_mode.png")
    
    # Save the updated DOM
    with open('login_password_dom.html', 'w', encoding='utf-8') as f:
        f.write(page.content())
    print("Saved login_password_dom.html")
    context.close()
