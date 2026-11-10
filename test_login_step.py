import time
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-infobars'
        ],
        proxy={'server': 'http://127.0.0.1:10808'},
        viewport={'width': 1280, 'height': 800}
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    
    print("Navigating to https://30nama.com/login ...")
    try:
        page.goto('https://30nama.com/login', timeout=25000, wait_until='domcontentloaded')
    except Exception as e:
        pass
        
    time.sleep(3)
    print("Page title:", repr(page.title()))
    
    # 1. Fill userlogin
    print("Filling userlogin...")
    page.fill('input[name="userlogin"]', 'arman_pier@yahoo.com')
    time.sleep(1)
    page.screenshot(path="login_step1.png")
    
    # Click submit / next button
    # Find button
    buttons = page.query_selector_all('button')
    print(f"Found {len(buttons)} buttons:")
    for b in buttons:
        print("  button text:", repr(b.inner_text()))
        
    # Click the primary button
    if buttons:
        buttons[0].click()
        print("Clicked button 0!")
        
    time.sleep(4)
    print("After click URL:", page.url)
    page.screenshot(path="login_step2.png")
    
    inputs = page.query_selector_all('input')
    print(f"Inputs after step 1 ({len(inputs)}):")
    for inp in inputs:
        print("  input:", inp.get_attribute('name'), inp.get_attribute('type'))
        
    context.close()
