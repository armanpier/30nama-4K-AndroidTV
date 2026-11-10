# Verification of Test Suite & Integrity
$ErrorActionPreference = "Stop"

$repo1 = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
$repo2 = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"

Write-Host "=== 1. Inspecting Test Files in Repo 1 ==="
$testFiles = Get-ChildItem -Recurse -File "$repo1\app\src\test"
Write-Host "Test files found: $($testFiles.Count)"
foreach ($tf in $testFiles) {
    Write-Host "  $($tf.FullName.Substring($repo1.Length)) ($($tf.Length) bytes)"
}

Write-Host "`n=== 2. Running Gradle Unit Tests in quirky-turing ==="
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"

Push-Location $repo1
try {
    Write-Host "Running .\gradlew.bat test --no-daemon in $repo1..."
    $testOut1 = .\gradlew.bat test --no-daemon 2>&1
    Write-Host "Exit Code: $LASTEXITCODE"
    $testOut1 | Select-String -Pattern "BUILD|Task|Passed|failed|FAILED" | Select-Object -First 30
} finally {
    Pop-Location
}

Write-Host "`n=== 3. Running Gradle Unit Tests in AsanVPN ==="
Push-Location $repo2
try {
    Write-Host "Running .\gradlew.bat test --no-daemon in $repo2..."
    $testOut2 = .\gradlew.bat test --no-daemon 2>&1
    Write-Host "Exit Code: $LASTEXITCODE"
    $testOut2 | Select-String -Pattern "BUILD|Task|Passed|failed|FAILED" | Select-Object -First 30
} finally {
    Pop-Location
}
