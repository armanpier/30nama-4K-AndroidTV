import os
import subprocess

TV_KEY = 'VdapnkLG9EHsSmF8yeKcb4253RAuN6YX'
DESKTOP_KEY = 'et7bRHdhmL468C5BcNrEMYTWGfz3a9vJ'

with open("tv_session_token.txt", "r") as f:
    token = f.read().strip()

settings_xml = f'''<settings version="2">
    <setting id="c_token">{token}</setting>
    <setting id="proxy_url">http://127.0.0.1:10808</setting>
    <setting id="tv_api_key">{TV_KEY}</setting>
    <setting id="desktop_api_key">{DESKTOP_KEY}</setting>
    <setting id="auto_fix_persian_encoding">true</setting>
    <setting id="sub_priority">0</setting>
</settings>'''

with open("settings.xml", "w", encoding="utf-8") as f:
    f.write(settings_xml)

adb = os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')
dest_dir = '/sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata/addon_data/plugin.video.30nama'
subprocess.run([adb, 'shell', f'mkdir -p {dest_dir}'])
subprocess.run([adb, 'push', 'settings.xml', f'{dest_dir}/settings.xml'])
print("Successfully pushed settings.xml to Kodi on emulator!")
