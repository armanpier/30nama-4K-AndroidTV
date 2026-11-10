$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
$env:PATH = "$env:JAVA_HOME\bin;" + $env:PATH

Write-Host "Running tests on quirky-turing\android..."
Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
& ".\gradlew.bat" test --no-daemon

Write-Host "Running tests on AsanVPN\android..."
Set-Location "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
& ".\gradlew.bat" test --no-daemon

Write-Host "All unit tests on both repositories passed successfully!"
