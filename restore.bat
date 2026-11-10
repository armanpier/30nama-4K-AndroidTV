@echo off
echo Restoring disabled packages...
for /f "tokens=2 delims=:" %%p in (backup\packages_disabled.txt) do (
    "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" connect 192.168.100.4:5555
    "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" shell pm enable %%p
)
echo Restore complete.
pause
