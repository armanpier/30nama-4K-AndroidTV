# -*- coding: utf-8 -*-
import time
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon("plugin.video.30nama")

def log(msg):
    xbmc.log(f"[plugin.video.30nama.service] {msg}", xbmc.LOGINFO)

if __name__ == "__main__":
    log("Startup service initialized.")
    auto_start = ADDON.getSetting("auto_start_on_boot")
    if auto_start.lower() != "false":
        monitor = xbmc.Monitor()
        for _ in range(60):
            if monitor.abortRequested():
                break
            if xbmc.getCondVisibility("Window.IsVisible(home)"):
                time.sleep(0.5)
                log("Auto-launching 30nama 4K main menu...")
                xbmc.executebuiltin("ActivateWindow(videos, plugin://plugin.video.30nama/, return)")
                break
            time.sleep(0.2)
