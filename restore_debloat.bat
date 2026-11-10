@echo off
set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
set TV_IP=192.168.100.4:5555

echo Connecting to TV at %TV_IP%...
%ADB% connect %TV_IP%

echo.
echo ========================================================
echo Re-enabling debloated packages...
echo ========================================================

%ADB% shell pm enable com.sony.dtv.demosupport
%ADB% shell pm enable com.sony.dtv.demosystemsupport
%ADB% shell pm enable com.sony.dtv.multiscreendemo
%ADB% shell pm enable tv.samba.ssm
%ADB% shell pm enable tv.samba.ssm.ui
%ADB% shell pm enable com.sony.dtv.sonybugreportsys
%ADB% shell pm enable com.sony.dtv.sonyloglevelsettingsys
%ADB% shell pm enable com.google.android.feedback
%ADB% shell pm enable com.google.android.partnersetup
%ADB% shell pm enable com.android.printspooler

echo.
echo Resetting animation speeds back to 1.0x (standard)...
%ADB% shell settings put global window_animation_scale 1.0
%ADB% shell settings put global transition_animation_scale 1.0
%ADB% shell settings put global animator_duration_scale 1.0

echo.
echo ========================================================
echo All changes reverted successfully!
echo ========================================================
pause
