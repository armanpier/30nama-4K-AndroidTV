$ErrorActionPreference = "Stop"

$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
$env:PATH = "$env:JAVA_HOME\bin;" + $env:PATH

Write-Host "Using Java Home: $env:JAVA_HOME"
& "$env:JAVA_HOME\bin\java.exe" -version

# Target 1: quirky-turing\android
Write-Host "`n=========================================="
Write-Host "BUILDING 1: quirky-turing\android"
Write-Host "=========================================="
Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
& ".\gradlew.bat" assembleDebug assembleRelease --no-daemon
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gradle build failed on quirky-turing\android with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Build quirky-turing\android SUCCEEDED with exit code 0."

$apks1 = Get-ChildItem -Recurse -Filter "*.apk" "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\outputs\apk"
Write-Host "Generated APKs for quirky-turing:"
$apks1 | ForEach-Object { Write-Host " - $($_.FullName) ($($_.Length) bytes)" }

# Target 2: AsanVPN\android
Write-Host "`n=========================================="
Write-Host "BUILDING 2: AsanVPN\android"
Write-Host "=========================================="
Set-Location "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
& ".\gradlew.bat" assembleDebug assembleRelease --no-daemon
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gradle build failed on AsanVPN\android with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Build AsanVPN\android SUCCEEDED with exit code 0."

$apks2 = Get-ChildItem -Recurse -Filter "*.apk" "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\build\outputs\apk"
Write-Host "Generated APKs for AsanVPN:"
$apks2 | ForEach-Object { Write-Host " - $($_.FullName) ($($_.Length) bytes)" }

Write-Host "`n=========================================="
Write-Host "ALL BUILDS AND VERIFICATIONS SUCCEEDED"
Write-Host "=========================================="
