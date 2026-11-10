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
    
    print("Navigating...")
    page.goto('https://30nama.com/login', wait_until='commit', timeout=30000)
    print("Waiting for selector input[name='userlogin']...")
    page.wait_for_selector('input[name="userlogin"]', timeout=30000)
    print("Input found!")
    
    # Dump form HTML
    form_html = page.evaluate("""() => {
        const form = document.querySelector('form') || document.body;
        return form.innerHTML;
    }""")
    
    with open('login_form_inner.html', 'w', encoding='utf-8') as f:
        f.write(form_html)
    print("Saved login_form_inner.html!")
    
    context.close()
