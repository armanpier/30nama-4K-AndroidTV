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
        print("Goto notice:", e)
        
    print("Waiting 6 seconds for page render...")
    time.sleep(6)
    
    title = page.title()
    print("Page title:", repr(title))
    print("Current URL:", page.url)
    page.screenshot(path="stealth_login_result.png")
    
    # Check if inputs exist
    inputs = page.query_selector_all('input')
    print(f"Found {len(inputs)} inputs:")
    for inp in inputs:
        print("  input:", inp.get_attribute('name'), inp.get_attribute('type'), inp.get_attribute('placeholder'))
        
    context.close()
