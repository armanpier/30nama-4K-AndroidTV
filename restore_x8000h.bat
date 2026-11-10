@echo off
set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
set TV_IP=192.168.100.7:5555

echo Connecting to Sony 65X8000H at %TV_IP%...
%ADB% connect %TV_IP%

echo.
echo ========================================================
echo Re-enabling debloated packages on 65X8000H...
echo ========================================================

%ADB% -s %TV_IP% shell pm enable com.sony.dtv.demosupport
%ADB% -s %TV_IP% shell pm enable com.sony.dtv.demosystemsupport
%ADB% -s %TV_IP% shell pm enable com.sony.dtv.multiscreendemo
%ADB% -s %TV_IP% shell pm enable com.sony.dtv.sonybugreportsys
%ADB% -s %TV_IP% shell pm enable com.sony.dtv.sonyloglevelsettingsys
%ADB% -s %TV_IP% shell pm enable com.sony.dtv.sonyselect
%ADB% -s %TV_IP% shell pm enable com.google.android.feedback
%ADB% -s %TV_IP% shell pm enable com.google.android.partnersetup
%ADB% -s %TV_IP% shell pm enable com.google.android.tv.bugreportsender
%ADB% -s %TV_IP% shell pm enable com.google.android.tungsten.setupwraith
%ADB% -s %TV_IP% shell pm enable com.android.printspooler

echo.
echo Resetting animation speeds back to 1.0x (standard)...
%ADB% -s %TV_IP% shell settings put global window_animation_scale 1.0
%ADB% -s %TV_IP% shell settings put global transition_animation_scale 1.0
%ADB% -s %TV_IP% shell settings put global animator_duration_scale 1.0

echo.
echo ========================================================
echo All changes reverted successfully on Sony 65X8000H!
echo ========================================================
pause
