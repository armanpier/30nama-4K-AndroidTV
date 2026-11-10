import sys
import time
import json
import os
import subprocess
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"
FFMPEG = r"C:\Users\Arman\AppData\Local\CapCut\Apps\7.3.0.2974\ffmpeg.exe"

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
    time.sleep(1)
    
    print("Switching to password mode...")
    pwd_btn = page.locator("text='ورود با رمز عبور / پسورد'")
    pwd_btn.click()
    time.sleep(1)
    
    print("Filling credentials...")
    page.fill('input[name="userlogin"]', 'arman_pier@yahoo.com')
    time.sleep(0.5)
    page.fill('input[name="password"]', 'Arman4237340')
    time.sleep(1)
    
    print("Submitting form...")
    page.locator('div[type="submit"]').click()
    time.sleep(3)
    
    # Find reCAPTCHA bframe
    print("Looking for reCAPTCHA bframe...")
    bframe = None
    for f in page.frames:
        if "bframe" in f.url:
            bframe = f
            break
            
    if not bframe:
        print("No bframe found. Checking if logged in directly...")
        print("URL:", page.url)
    else:
        print("Found bframe! Clicking audio button...")
        try:
            bframe.click('#recaptcha-audio-button', timeout=5000)
            time.sleep(3)
            # Check for error or audio source
            audio_source = bframe.locator('#audio-source')
            if audio_source.count() > 0:
                audio_url = audio_source.get_attribute('src')
                print("Audio URL found:", audio_url)
            else:
                # Check for "Your computer or network may be sending automated queries"
                err = bframe.locator('.rc-doscaptcha-body-text')
                if err.count() > 0:
                    print("reCAPTCHA blocked automated queries:", err.inner_text())
                else:
                    print("No audio source found, dumping bframe content...")
                    print(bframe.content()[:500])
        except Exception as e:
            print("Error interacting with bframe:", e)
            
    page.screenshot(path="after_audio_attempt.png")
    context.close()
