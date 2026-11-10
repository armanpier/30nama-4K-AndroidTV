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
    
    api_requests = []
    def on_req(req):
        if "action" in req.url or "api" in req.url or "download" in req.url or "stream" in req.url:
            api_requests.append({
                "url": req.url,
                "method": req.method,
                "headers": req.headers,
                "post_data": req.post_data
            })
            
    page.on("request", on_req)
    
    print("Navigating to https://30nama.com/ ...")
    page.goto('https://30nama.com/', wait_until='networkidle', timeout=30000)
    time.sleep(3)
    
    # Also navigate to a movie page (e.g. poor things / 721725)
    print("Navigating to movie page...")
    page.goto('https://30nama.com/movies/721725', wait_until='networkidle', timeout=30000)
    time.sleep(4)
    
    with open("web_api_requests.json", "w", encoding="utf-8") as f:
        json.dump(api_requests, f, indent=2, ensure_ascii=False)
        
    print(f"Captured {len(api_requests)} API requests!")
    for r in api_requests:
        print(f"[{r['method']}] {r['url']}")
        for h, v in r['headers'].items():
            if 'key' in h or 'token' in h or 'auth' in h or 'user' in h or 'cookie' in h:
                print(f"    {h}: {v[:80]}")
                
    context.close()
