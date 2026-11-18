import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', 22, 'root', 'Arman4237340')

sftp = ssh.open_sftp()
print("Uploading updated main.py to VPS /root/asanvpn-bot/main.py ...")
sftp.put('backend/telegram-bot/main.py', '/root/asanvpn-bot/main.py')
print("Done.")

# Clear any cached animation file id and ensure video is fresh
cmd_db = """python3 -c "
import sqlite3
c = sqlite3.connect('/root/asanvpn-bot/bot_data.db')
c.execute(\"DELETE FROM settings WHERE key='welcome_animation_file_id'\")
c.execute(\"UPDATE settings SET value='' WHERE key='welcome_video_file_id'\")
c.commit()
print('Reset welcome media file_id in DB')
" """
_, stdout_db, _ = ssh.exec_command(cmd_db)
print(stdout_db.read().decode())

# Check if welcome_loop.mp4 exists, link welcome_ffd3c6.mp4 to welcome_loop.mp4 so it's super fast 1.6MB
cmd_link = "cd /root/asanvpn-bot && cp welcome_loop.mp4 welcome_ffd3c6.mp4"
_, stdout_lk, _ = ssh.exec_command(cmd_link)

print("Restarting asanvpn-bot systemd service...")
_, stdout_srv, stderr_srv = ssh.exec_command("systemctl restart asanvpn-bot && sleep 2 && systemctl status asanvpn-bot")
print("SERVICE STATUS:\n" + stdout_srv.read().decode())
print("ERR:\n" + stderr_srv.read().decode())

sftp.close()
ssh.close()
print("Deployment of Bot Updates Complete!")
