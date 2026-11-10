import sys
import time
import json
import os
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from faster_whisper import WhisperModel

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"

def solve_audio(audio_url, model):
    print("Downloading audio from:", audio_url)
    mp3_path = "captcha_current.mp3"
    
    proxy_handler = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(audio_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with opener.open(req, timeout=15) as r, open(mp3_path, "wb") as f:
        f.write(r.read())
        
    print(f"Downloaded mp3 ({os.path.getsize(mp3_path)} bytes). Transcribing with faster-whisper...")
    segments, info = model.transcribe(mp3_path)
    text = ' '.join([s.text for s in segments]).strip()
    print("Transcribed text:", repr(text))
    return text

def main():
    print("Loading whisper model...")
    model = WhisperModel('tiny', device='cpu', compute_type='int8')
    
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
        page.locator("text='ورود با رمز عبور / پسورد'").click()
        time.sleep(1)
        
        print("Filling credentials...")
        page.fill('input[name="userlogin"]', 'arman_pier@yahoo.com')
        time.sleep(0.5)
        page.fill('input[name="password"]', 'Arman4237340')
        time.sleep(1)
        
        print("Submitting login form...")
        page.locator('div[type="submit"]').click()
        time.sleep(3)
        
        # Look for reCAPTCHA bframe
        for attempt in range(3):
            bframe = None
            for f in page.frames:
                if "bframe" in f.url:
                    bframe = f
                    break
                    
            if not bframe:
                print("No bframe detected.")
                break
                
            print(f"[Attempt {attempt+1}] Checking for audio button or audio source...")
            try:
                audio_btn = bframe.locator('#recaptcha-audio-button')
                if audio_btn.is_visible():
                    print("Clicking audio button...")
                    audio_btn.click()
                    time.sleep(2)
                    
                audio_source = bframe.locator('#audio-source')
                if audio_source.is_visible() or audio_source.count() > 0:
                    audio_url = audio_source.get_attribute('src')
                    text = solve_audio(audio_url, model)
                    if text:
                        print("Typing answer:", repr(text))
                        bframe.fill('#audio-response', text)
                        time.sleep(1)
                        print("Clicking verify button...")
                        bframe.click('#recaptcha-verify-button')
                        time.sleep(4)
                else:
                    # Maybe it's already solved or blocked
                    print("Audio source not visible.")
            except Exception as e:
                print("Captcha interaction exception:", e)
                
            # Check if login succeeded or redirected
            if "/login" not in page.url or "profile" in page.url:
                print("Redirect detected! Page URL:", page.url)
                break
                
        print("Waiting 5s for session settlement...")
        time.sleep(5)
        print("Final Page URL:", page.url)
        page.screenshot(path="login_whisper_result.png")
        
        cookies = context.cookies()
        print(f"\nCaptured {len(cookies)} cookies:")
        found_token = None
        for c in cookies:
            print(f"  {c['name']} = {c['value'][:35]}... (domain: {c['domain']})")
            if "c-token" in c['name'].lower() or "token" in c['name'].lower():
                found_token = c['value']
                
        with open("cookies_whisper.json", "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
            
        # Check localStorage and sessionStorage
        try:
            storage = page.evaluate("() => ({ local: {...localStorage}, session: {...sessionStorage} })")
            print("\nStorage keys:")
            print("  Local:", list(storage.get('local', {}).keys()))
            print("  Session:", list(storage.get('session', {}).keys()))
            with open("storage_dump.json", "w", encoding="utf-8") as f:
                json.dump(storage, f, indent=2)
                
            for k, v in storage.get('local', {}).items():
                if "token" in k.lower() or "auth" in k.lower() or "user" in k.lower():
                    print(f"  LocalStorage '{k}': {str(v)[:80]}")
        except Exception as e:
            print("Storage eval error:", e)
            
        context.close()

if __name__ == '__main__':
    main()
