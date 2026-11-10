import sqlite3
import shutil
import tempfile
import os

src = r'C:\Users\Arman\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies'
tmp = os.path.join(tempfile.gettempdir(), 'chrome_cookies.db')
shutil.copy2(src, tmp)

conn = sqlite3.connect(tmp)
cur = conn.cursor()
cur.execute("SELECT host_key, name, path FROM cookies WHERE host_key LIKE '%30nama%' OR host_key LIKE '%hana%'")
rows = cur.fetchall()
print('Found cookies:', len(rows))
for r in rows:
    print(' ', r)
conn.close()
os.remove(tmp)
