@echo off
set "JAVA_HOME=C:\Users\Arman\.jdks\jdk-17"
set "PATH=%JAVA_HOME%\bin;%PATH%"
echo === VERIFYING JAVA RUNTIME ===
java -version
echo === RUNNING testDebugUnitTest with --rerun-tasks on quirky-turing\android ===
cd /d "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
call gradlew.bat testDebugUnitTest --rerun-tasks --no-daemon
if errorlevel 1 exit /b 1
echo === TEST EXECUTION FINISHED SUCCESSFULLY ===
