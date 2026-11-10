$ErrorActionPreference = "Stop"
$jhome = "C:\Program Files\Android\Android Studio\jbr"
$env:JAVA_HOME = $jhome
$env:PATH = "$jhome\bin;$env:PATH"

$buildTools = "$env:LOCALAPPDATA\Android\Sdk\build-tools\34.0.0"
$zipalign = "$buildTools\zipalign.exe"
$apksigner = "$buildTools\apksigner.bat"

Write-Host "=== 1. Repacking APK with patched bundle ==="
python repack_apk.py

Write-Host "=== 2. ZipAligning APK ==="
& $zipalign -p -f 4 "30tv-3.2.3-4k-mod-unsigned.apk" "30tv-3.2.3-4k-mod-aligned.apk"

Write-Host "=== 3. Signing APK with debug.keystore ==="
& $apksigner sign --ks "debug.keystore" --ks-pass "pass:android" --key-pass "pass:android" --ks-key-alias "androiddebugkey" --out "30tv-3.2.3-4k-mod.apk" "30tv-3.2.3-4k-mod-aligned.apk"

Write-Host "=== 4. Verifying APK signature ==="
& $apksigner verify --verbose "30tv-3.2.3-4k-mod.apk"

Write-Host "=== Done! Final APK: 30tv-3.2.3-4k-mod.apk ==="
