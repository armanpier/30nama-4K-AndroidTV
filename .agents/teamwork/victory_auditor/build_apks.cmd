@echo off
set "JAVA_HOME=C:\Users\Arman\.jdks\jdk-17"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo === BUILDING APKs ON quirky-turing\android ===
cd /d "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
call gradlew.bat assembleDebug assembleRelease --no-daemon
if errorlevel 1 (
    echo BUILD FAILED ON quirky-turing\android
    exit /b 1
)

echo === BUILDING APKs ON AsanVPN\android ===
cd /d "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
call gradlew.bat assembleDebug assembleRelease --no-daemon
if errorlevel 1 (
    echo BUILD FAILED ON AsanVPN\android
    exit /b 1
)

echo === ALL BUILDS FINISHED SUCCESSFULLY ===
