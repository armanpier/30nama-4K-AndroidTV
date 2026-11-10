import os
import subprocess
import tkinter as tk
from tkinter import ttk

ADB_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")

def send_key(code):
    try:
        subprocess.run([ADB_PATH, "shell", "input", "keyevent", str(code)], 
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except Exception as e:
        print(f"Error sending key {code}: {e}")

root = tk.Tk()
root.title("Android TV Remote")
root.geometry("260x420")
root.attributes("-topmost", True)
root.configure(bg="#1e1e24")

# Styling
style = ttk.Style()
style.theme_use("clam")

btn_bg = "#2b2d42"
btn_fg = "#ffffff"
btn_active = "#8d99ae"
accent_bg = "#e63946"

title_lbl = tk.Label(root, text="30TV D-PAD REMOTE", font=("Segoe UI", 12, "bold"), fg="#edf2f4", bg="#1e1e24")
title_lbl.pack(pady=10)

# D-pad Frame
dpad_frame = tk.Frame(root, bg="#1e1e24")
dpad_frame.pack(pady=10)

def make_btn(parent, text, cmd, bg=btn_bg, fg=btn_fg, width=6, height=2):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=btn_active,
                     font=("Segoe UI", 10, "bold"), relief="flat", bd=0, width=width, height=height, cursor="hand2")

btn_up = make_btn(dpad_frame, "▲\nUP", lambda: send_key(19))
btn_up.grid(row=0, column=1, padx=4, pady=4)

btn_left = make_btn(dpad_frame, "◄ LEFT", lambda: send_key(21))
btn_left.grid(row=1, column=0, padx=4, pady=4)

btn_ok = make_btn(dpad_frame, "OK", lambda: send_key(23), bg=accent_bg, width=6, height=2)
btn_ok.grid(row=1, column=1, padx=4, pady=4)

btn_right = make_btn(dpad_frame, "RIGHT ►", lambda: send_key(22))
btn_right.grid(row=1, column=2, padx=4, pady=4)

btn_down = make_btn(dpad_frame, "▼\nDOWN", lambda: send_key(20))
btn_down.grid(row=2, column=1, padx=4, pady=4)

# Control Buttons Frame
ctrl_frame = tk.Frame(root, bg="#1e1e24")
ctrl_frame.pack(pady=15, fill="x", padx=20)

btn_back = make_btn(ctrl_frame, "BACK", lambda: send_key(4), width=8, height=1)
btn_back.grid(row=0, column=0, padx=5, pady=4)

btn_home = make_btn(ctrl_frame, "HOME", lambda: send_key(3), width=8, height=1)
btn_home.grid(row=0, column=1, padx=5, pady=4)

btn_play = make_btn(ctrl_frame, "PLAY / PAUSE", lambda: send_key(85), bg="#457b9d", width=18, height=1)
btn_play.grid(row=1, column=0, columnspan=2, padx=5, pady=6)

# Keyboard bindings on the remote window
root.bind("<Up>", lambda e: send_key(19))
root.bind("<Down>", lambda e: send_key(20))
root.bind("<Left>", lambda e: send_key(21))
root.bind("<Right>", lambda e: send_key(22))
root.bind("<Return>", lambda e: send_key(23))
root.bind("<space>", lambda e: send_key(85))
root.bind("<BackSpace>", lambda e: send_key(4))
root.bind("<Escape>", lambda e: send_key(4))

hint_lbl = tk.Label(root, text="Arrow Keys: Navigate | Enter: OK\nBackSpace: Back | Space: Play/Pause", 
                    font=("Segoe UI", 8), fg="#8d99ae", bg="#1e1e24")
hint_lbl.pack(side="bottom", pady=8)

root.mainloop()
