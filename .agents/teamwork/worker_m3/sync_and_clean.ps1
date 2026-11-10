$src = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
$dst = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"

Write-Host "Copying modified source files..."
$filesToCopy = @(
    "app\src\main\java\com\asanvpn\app\util\AppLogger.kt",
    "app\src\main\java\com\asanvpn\app\data\VpnRepository.kt",
    "app\src\main\java\com\asanvpn\app\service\PingTester.kt",
    "app\src\main\java\com\asanvpn\app\MainActivity.kt",
    "app\src\main\java\com\asanvpn\app\util\IranAppBypassHelper.kt",
    "app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt",
    "app\src\main\java\com\asanvpn\app\service\v2ray\V2RayConfigBuilder.kt",
    "app\src\main\java\com\asanvpn\app\service\AsanVpnService.kt",
    "app\src\main\java\com\asanvpn\app\data\PreferencesManager.kt"
)

foreach ($rel in $filesToCopy) {
    $sourcePath = Join-Path $src $rel
    $destPath = Join-Path $dst $rel
    $destDir = Split-Path -Parent $destPath
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Path $sourcePath -Destination $destPath -Force
    Write-Host "Copied $rel to AsanVPN"
}

Write-Host "Copying test tree..."
$testSrc = Join-Path $src "app\src\test"
$testDst = Join-Path $dst "app\src\test"
if (Test-Path $testSrc) {
    Copy-Item -Path $testSrc -Destination (Split-Path -Parent $testDst) -Recurse -Force
    Write-Host "Copied app\src\test tree to AsanVPN"
}

Write-Host "Copying .gitignore from AsanVPN to quirky-turing..."
$gitignoreSrc = Join-Path $dst ".gitignore"
$gitignoreDst = Join-Path $src ".gitignore"
if (Test-Path $gitignoreSrc) {
    Copy-Item -Path $gitignoreSrc -Destination $gitignoreDst -Force
    Write-Host "Copied .gitignore to quirky-turing"
}

Write-Host "Deleting transient compiler dumps..."
$errDir1 = Join-Path $src ".kotlin\errors"
if (Test-Path $errDir1) {
    Remove-Item -Path $errDir1 -Recurse -Force
    Write-Host "Removed $errDir1"
}
$errDir2 = Join-Path $dst ".kotlin\errors"
if (Test-Path $errDir2) {
    Remove-Item -Path $errDir2 -Recurse -Force
    Write-Host "Removed $errDir2"
}

Write-Host "Sync and clean complete."
