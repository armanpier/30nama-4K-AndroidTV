import sys
import time
import json
import os
import subprocess
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import speech_recognition as sr

user_data = r"C:\Users\Arman\AppData\Local\Temp\stealth_test_profile"
FFMPEG = r"C:\Users\Arman\AppData\Local\CapCut\Apps\7.3.0.2974\ffmpeg.exe"

def solve_audio(audio_url, page):
    print("Downloading audio from:", audio_url)
    # Download audio through page context or request
    mp3_path = "captcha.mp3"
    wav_path = "captcha.wav"
    
    # Download via urllib with proxy
    proxy_handler = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(audio_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with opener.open(req, timeout=15) as r, open(mp3_path, "wb") as f:
        f.write(r.read())
        
    print(f"Downloaded mp3 ({os.path.getsize(mp3_path)} bytes). Converting to wav via ffmpeg...")
    res = subprocess.run([FFMPEG, "-y", "-i", mp3_path, wav_path], capture_output=True)
    if res.returncode != 0:
        print("FFMPEG error:", res.stderr.decode('utf-8', errors='ignore'))
        return None
        
    print("Transcribing with Google Speech Recognition...")
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        print("Recognized text:", repr(text))
        return text
    except Exception as e:
        print("Recognition error:", e)
        return None

def main():
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
        
        print("Submitting form...")
        page.locator('div[type="submit"]').click()
        time.sleep(3)
        
        # Check if reCAPTCHA appeared
        bframe = None
        for f in page.frames:
            if "bframe" in f.url:
                bframe = f
                break
                
        if bframe:
            print("Found reCAPTCHA frame! Clicking audio button...")
            bframe.click('#recaptcha-audio-button', timeout=5000)
            time.sleep(3)
            
            audio_source = bframe.locator('#audio-source')
            if audio_source.count() > 0:
                audio_url = audio_source.get_attribute('src')
                text = solve_audio(audio_url, page)
                if text:
                    print("Typing response into captcha...")
                    bframe.fill('#audio-response', text)
                    time.sleep(1)
                    print("Clicking verify...")
                    bframe.click('#recaptcha-verify-button')
                    time.sleep(5)
            else:
                print("No audio source found on bframe.")
                
        # Wait for potential redirect or token
        print("Waiting 6 seconds for login processing...")
        time.sleep(6)
        print("Current URL:", page.url)
        page.screenshot(path="login_result.png")
        
        cookies = context.cookies()
        print(f"\nCaptured {len(cookies)} cookies:")
        for c in cookies:
            print(f"  {c['name']} = {c['value'][:40]} (domain: {c['domain']})")
            
        with open("cookies_result.json", "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
            
        context.close()

if __name__ == '__main__':
    main()
