import os
import sys
import time
import requests

VT_API_KEY = "3e315c57ebbe18769caf133945b41dcff0ab2587e907237eefb0ee8357a07735"

def upload_to_virustotal(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None

    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    print(f"Uploading {file_name} ({file_size / (1024*1024):.2f} MB) to VirusTotal...")

    headers = {
        "x-apikey": VT_API_KEY
    }

    if file_size < 32 * 1024 * 1024:
        # Standard upload endpoint (<32MB)
        url = "https://www.virustotal.com/api/v3/files"
    else:
        # Request special upload URL for large files (>32MB)
        print("Requesting large file upload URL...")
        resp = requests.get("https://www.virustotal.com/api/v3/files/upload_url", headers=headers)
        if resp.status_code != 200:
            print(f"Failed to get upload URL: {resp.status_code} {resp.text}")
            return None
        url = resp.json().get("data")

    with open(file_path, "rb") as f:
        files = {"file": (file_name, f, "application/vnd.android.package-archive")}
        resp = requests.post(url, headers=headers, files=files)

    if resp.status_code not in (200, 201):
        print(f"Upload failed: {resp.status_code} {resp.text}")
        return None

    analysis_data = resp.json().get("data", {})
    analysis_id = analysis_data.get("id")
    print(f"Upload successful! Analysis ID: {analysis_id}")
    return analysis_id

def check_analysis(analysis_id):
    headers = {"x-apikey": VT_API_KEY}
    url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"

    print("Waiting for VirusTotal analysis to complete...")
    for _ in range(12):  # Poll up to 60 seconds
        time.sleep(5)
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            status = data.get("attributes", {}).get("status")
            print(f"Status: {status}")
            if status == "completed":
                stats = data.get("attributes", {}).get("stats", {})
                results = data.get("attributes", {}).get("results", {})
                google_result = results.get("Google", {}) or results.get("Google Play Protect", {})
                meta = data.get("meta", {}).get("file_info", {})
                sha256 = meta.get("sha256")
                return {
                    "stats": stats,
                    "sha256": sha256,
                    "google": google_result,
                    "gui_url": f"https://www.virustotal.com/gui/file/{sha256}" if sha256 else None
                }
    return None

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "releases/v1.3.44/AsanVPN-v1.3.44-arm64-v8a.apk"
    aid = upload_to_virustotal(target_file)
    if aid:
        report = check_analysis(aid)
        if report:
            print("--- VIRUSTOTAL REPORT ---")
            print(f"Stats: {report['stats']}")
            if report.get('gui_url'):
                print(f"View Report: {report['gui_url']}")
