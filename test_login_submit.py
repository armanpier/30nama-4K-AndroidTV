import time
import sys
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
    
    print("Navigating to https://30nama.com/login ...")
    page.goto('https://30nama.com/login', wait_until='commit', timeout=30000)
    page.wait_for_selector('input[name="userlogin"]', timeout=30000)
    
    print("Typing userlogin...")
    page.click('input[name="userlogin"]')
    page.fill('input[name="userlogin"]', 'arman_pier@yahoo.com')
    time.sleep(1)
    
    print("Pressing Enter...")
    page.keyboard.press('Enter')
    time.sleep(4)
    
    print("Current URL:", page.url)
    page.screenshot(path="login_after_enter.png")
    
    inputs = page.query_selector_all('input')
    print(f"Inputs found ({len(inputs)}):")
    for inp in inputs:
        print("  input:", inp.get_attribute('name'), inp.get_attribute('type'))
        
    context.close()
