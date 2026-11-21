import sys
import os
import hashlib
import time
import requests

API_KEY = "3e315c57ebbe18769caf133945b41dcff0ab2587e907237eefb0ee8357a07735"

def get_file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()

def scan_file_virustotal(filepath):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return None
    
    filesize = os.path.getsize(filepath)
    sha256 = get_file_sha256(filepath)
    filename = os.path.basename(filepath)
    print(f"\n--- Scanning {filename} ({filesize / (1024*1024):.2f} MB, SHA256: {sha256}) ---")
    
    headers = {
        "x-apikey": API_KEY,
        "Accept": "application/json"
    }

    # 1. Check if already analyzed
    check_url = f"https://www.virustotal.com/api/v3/files/{sha256}"
    res = requests.get(check_url, headers=headers)
    if res.status_code == 200:
        data = res.json().get("data", {})
        attr = data.get("attributes", {})
        stats = attr.get("last_analysis_stats", {})
        print(f"File already known on VirusTotal! Stats: {stats}")
        gui_url = f"https://www.virustotal.com/gui/file/{sha256}"
        print(f"Report: {gui_url}")
        return {"sha256": sha256, "stats": stats, "gui_url": gui_url}

    # 2. Upload file
    if filesize > 32 * 1024 * 1024:
        print("File > 32MB, requesting large file upload URL...")
        up_res = requests.get("https://www.virustotal.com/api/v3/files/upload_url", headers=headers)
        if up_res.status_code != 200:
            print(f"Failed to get upload URL: {up_res.status_code} {up_res.text}")
            return None
        upload_url = up_res.json().get("data")
    else:
        upload_url = "https://www.virustotal.com/api/v3/files"

    print(f"Uploading {filename} to VirusTotal...")
    with open(filepath, 'rb') as f:
        files = {"file": (filename, f, "application/vnd.android.package-archive")}
        up_resp = requests.post(upload_url, headers={"x-apikey": API_KEY}, files=files)

    if up_resp.status_code not in (200, 201):
        print(f"Upload failed: {up_resp.status_code} {up_resp.text}")
        return None

    analysis_id = up_resp.json().get("data", {}).get("id")
    print(f"Upload succeeded! Analysis ID: {analysis_id}")

    gui_url = f"https://www.virustotal.com/gui/file/{sha256}"
    print(f"VirusTotal Report URL: {gui_url}")

    # Wait for analysis results (up to 45 seconds)
    print("Waiting for scan results...")
    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    for i in range(9):
        time.sleep(5)
        a_resp = requests.get(analysis_url, headers=headers)
        if a_resp.status_code == 200:
            a_data = a_resp.json().get("data", {})
            status = a_data.get("attributes", {}).get("status")
            stats = a_data.get("attributes", {}).get("stats", {})
            print(f"  [{i*5 + 5}s] Status: {status}, Stats: {stats}")
            if status == "completed":
                return {"sha256": sha256, "stats": stats, "gui_url": gui_url}

    return {"sha256": sha256, "stats": "queued", "gui_url": gui_url}

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "android/app/build/outputs/apk/release/app-universal-release.apk"
    scan_file_virustotal(target)
