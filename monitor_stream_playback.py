import sys
import time
import subprocess
import json

sys.stdout.reconfigure(encoding='utf-8')
ADB = r"C:\Users\Arman\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def run_adb(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

print("1. Clearing logcat...")
run_adb("logcat -c")

print("2. Triggering Playback (DPAD_CENTER)...")
run_adb("shell input keyevent 23")

print("3. Waiting 4 seconds for VideoPlayer to initialize...")
time.sleep(4)

print("4. Capturing screenshot...")
run_adb("shell screencap -p /sdcard/s.png")
run_adb(r"pull /sdcard/s.png C:\Users\Arman\.gemini\antigravity\brain\5541959f-8acf-44a5-ab6c-42a6a9fe320f\videoplayer_active.png")

print("5. Inspecting logcat for stream / JWPlayer / ExoPlayer / OkHttp...")
res = subprocess.run(f'"{ADB}" logcat -d', shell=True, capture_output=True, text=True, errors='replace')
lines = res.stdout.splitlines()

stream_logs = [line for line in lines if any(k in line.lower() for k in ['stream', 'jwplayer', 'exoplayer', 'hana-api', '30nama', 'reactnativejs', 'medias'])]
print(f"\nFound {len(stream_logs)} matching log lines:\n")
for l in stream_logs[-40:]:
    print(l)

with open('playback_logs.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(stream_logs))
