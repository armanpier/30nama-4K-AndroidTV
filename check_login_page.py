import subprocess

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
cmd = [
    chrome,
    "--headless=new",
    "--disable-gpu",
    "--proxy-server=http://127.0.0.1:10808",
    "--dump-dom",
    "https://30nama.com/login"
]

res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
print("DOM len:", len(res.stdout))
with open("30nama_login_dom.html", "w", encoding="utf-8") as f:
    f.write(res.stdout)
