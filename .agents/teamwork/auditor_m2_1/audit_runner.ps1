# Milestone 2 Forensic Integrity Audit Script
# Executes all integrity checks with strict empirical verification

$ErrorActionPreference = "Stop"
$failures = 0
$passes = 0

function Assert-Check {
    param(
        [string]$Name,
        [bool]$Condition,
        [string]$Details
    )
    if ($Condition) {
        Write-Host "[PASS] $Name - $Details" -ForegroundColor Green
        $script:passes++
    } else {
        Write-Host "[FAIL] $Name - $Details" -ForegroundColor Red
        $script:failures++
    }
}

Write-Host "================================================================="
Write-Host " STARTING FORENSIC INTEGRITY AUDIT - MILESTONE 2 (R2)"
Write-Host "================================================================="

# --- CHECK 1: IranAppBypassHelper.kt Source & Genuine Logic ---
Write-Host "`n--- CHECK 1: IranAppBypassHelper.kt Genuine Implementation ---"
$bypassPath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\util\IranAppBypassHelper.kt"
$bypassContent = Get-Content -Path $bypassPath -Raw

Assert-Check "FileExists_IranAppBypassHelper" (Test-Path $bypassPath) "IranAppBypassHelper.kt exists at expected path"

# Check required Iranian packages per ORIGINAL_REQUEST.md
$hasNobitex = $bypassContent.Contains("app.nobitex") -and $bypassContent.Contains("market.nobitex") -and $bypassContent.Contains("ir.nobitex")
Assert-Check "RequiredPackages_Nobitex" $hasNobitex "Contains Nobitex packages (app.nobitex, market.nobitex, ir.nobitex)"

$hasUp = $bypassContent.Contains("com.sibche.aspardproject.app") -and $bypassContent.Contains("ir.nasimpay.app") -and $bypassContent.Contains("com.asanpardakht.app")
Assert-Check "RequiredPackages_Up" $hasUp "Contains Up / Asan Pardakht packages (com.sibche.aspardproject.app, ir.nasimpay.app, com.asanpardakht.app)"

$hasBazaar = $bypassContent.Contains("com.farsitel.bazaar")
Assert-Check "RequiredPackages_CafeBazaar" $hasBazaar "Contains Cafe Bazaar package (com.farsitel.bazaar)"

# Count package list size
$packageMatches = [regex]::Matches($bypassContent, '"([a-zA-Z0-9_\.]+)"')
$uniquePackages = ($packageMatches | ForEach-Object { $_.Groups[1].Value } | Where-Object { $_ -match '\.' -and $_ -notlike 'com.asanvpn*' } | Select-Object -Unique)
Assert-Check "PackageCount_Sufficient" ($uniquePackages.Count -ge 50) "Comprehensive catalog contains $($uniquePackages.Count) packages (>= 50 required)"

# Check genuine addDisallowedApplication invocation
$callsAddDisallowed = $bypassContent -match 'builder\.addDisallowedApplication\(pkg\)'
Assert-Check "Calls_addDisallowedApplication" $callsAddDisallowed "builder.addDisallowedApplication(pkg) is genuinely called"

# Check NameNotFoundException handling
$handlesNotFound = $bypassContent -match 'catch\s*\(\s*e:\s*PackageManager\.NameNotFoundException\s*\)'
Assert-Check "Handles_NameNotFoundException" $handlesNotFound "Catches PackageManager.NameNotFoundException for uninstalled apps"

# Check genuine dynamic counter return (not a facade return 0 or return constant)
$dynamicCounter = $bypassContent -match 'var\s+bypassedCount\s*=\s*0' -and $bypassContent -match 'bypassedCount\+\+' -and $bypassContent -match 'return\s+bypassedCount'
Assert-Check "Dynamic_BypassCounter" $dynamicCounter "Returns dynamic bypassedCount (not a hardcoded facade)"


# --- CHECK 2: AsanVpnService.kt Integration ---
Write-Host "`n--- CHECK 2: AsanVpnService.kt Integration ---"
$vpnServicePath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\service\AsanVpnService.kt"
$vpnServiceContent = Get-Content -Path $vpnServicePath -Raw

$importsHelper = $vpnServiceContent -match 'import\s+com\.asanvpn\.app\.util\.IranAppBypassHelper'
Assert-Check "Imports_IranAppBypassHelper" $importsHelper "Imports com.asanvpn.app.util.IranAppBypassHelper"

$callsHelper = $vpnServiceContent -match 'IranAppBypassHelper\.applyDisallowedApplications\(\s*builder\s*,\s*this\s*\)'
Assert-Check "Calls_applyDisallowedApplications" $callsHelper "Calls IranAppBypassHelper.applyDisallowedApplications(builder, this)"

# Ensure it's called BEFORE builder.establish()
$helperIndex = $vpnServiceContent.IndexOf("IranAppBypassHelper.applyDisallowedApplications")
$establishIndex = $vpnServiceContent.IndexOf("builder.establish()")
$isBeforeEstablish = ($helperIndex -gt 0) -and ($establishIndex -gt 0) -and ($helperIndex -lt $establishIndex)
Assert-Check "Called_Before_Establish" $isBeforeEstablish "Called before builder.establish() (Android VpnService lifecycle requirement)"


# --- CHECK 3: V2RayConfigBuilder.kt Direct Routing Rules ---
Write-Host "`n--- CHECK 3: V2RayConfigBuilder.kt Direct Routing Rules ---"
$configBuilderPath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\service\v2ray\V2RayConfigBuilder.kt"
$configContent = Get-Content -Path $configBuilderPath -Raw

$hasStrategy = $configContent -match 'addProperty\("domainStrategy",\s*"IPIfNonMatch"\)'
Assert-Check "Routing_DomainStrategy" $hasStrategy "Routing domainStrategy set to 'IPIfNonMatch'"

# Check direct domain rule contents
$hasGeositeCatIr = $configContent.Contains('"geosite:category-ir"')
$hasGeositeIr = $configContent.Contains('"geosite:ir"')
$hasDomainIr = $configContent.Contains('"domain:ir"')
Assert-Check "DirectDomains_GeositeCatIr" $hasGeositeCatIr "Direct rule contains 'geosite:category-ir'"
Assert-Check "DirectDomains_GeositeIr" $hasGeositeIr "Direct rule contains 'geosite:ir'"
Assert-Check "DirectDomains_DomainIr" $hasDomainIr "Direct rule contains 'domain:ir'"

# Check direct IP rule contents
$hasGeoipPrivate = $configContent.Contains('"geoip:private"')
$hasGeoipIr = $configContent.Contains('"geoip:ir"')
Assert-Check "DirectIPs_GeoipPrivate" $hasGeoipPrivate "Direct IP rule contains 'geoip:private'"
Assert-Check "DirectIPs_GeoipIr" $hasGeoipIr "Direct IP rule contains 'geoip:ir'"

# Check outbound tag is direct
$hasOutboundDirect = $configContent -match 'addProperty\("outboundTag",\s*"direct"\)'
Assert-Check "Outbound_Tag_Direct" $hasOutboundDirect "Outbound tag set to 'direct' for Iran rules"


# --- CHECK 4: GeoAssetManager.kt Auto-Update Mechanism ---
Write-Host "`n--- CHECK 4: GeoAssetManager.kt Auto-Update Mechanism ---"
$geoPath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt"
$geoContent = Get-Content -Path $geoPath -Raw

Assert-Check "FileExists_GeoAssetManager" (Test-Path $geoPath) "GeoAssetManager.kt exists"

# Check mirrors
$hasJsdelivr = $geoContent.Contains("https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release")
$hasGithubRaw = $geoContent.Contains("https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release")
Assert-Check "Mirrors_Configured" ($hasJsdelivr -and $hasGithubRaw) "jsDelivr and GitHub Raw mirrors configured"

# Check 24-hour throttle
$hasThrottle = $geoContent -match 'CHECK_INTERVAL_MS\s*=\s*24L\s*\*\s*60L\s*\*\s*60L\s*\*\s*1000L'
Assert-Check "Throttle_Interval" $hasThrottle "CHECK_INTERVAL_MS configured for 24 hours"

# Check APK asset copy fallback
$hasEnsureAssets = $geoContent -match 'context\.assets\.open\(fileName\)'
Assert-Check "EnsureAssets_FromApk" $hasEnsureAssets "ensureAssetsInitialized copies missing assets from APK assets"

# Check SHA256 computation via MessageDigest
$hasMessageDigest = $geoContent -match 'MessageDigest\.getInstance\("SHA-256"\)'
Assert-Check "Uses_MessageDigest_SHA256" $hasMessageDigest "computeSha256 uses genuine MessageDigest.getInstance('SHA-256')"

# Check atomic rename logic
$hasAtomicRename = $geoContent -match 'tempFile\.renameTo\(finalFile\)'
Assert-Check "Atomic_File_Rename" $hasAtomicRename "Atomic replacement via tempFile.renameTo(finalFile)"

# Check hash mismatch deletion logic
$hasMismatchDelete = $geoContent -match 'tempFile\.delete\(\)'
Assert-Check "Mismatch_Delete_Temp" $hasMismatchDelete "Deletes temporary file on hash mismatch or failure"

# Check preference timestamp persistence
$hasPrefTimestamp = $geoContent -match 'prefs\.lastGeoRulesCheckTime\s*=\s*now'
Assert-Check "Preferences_Timestamp_Update" $hasPrefTimestamp "Updates prefs.lastGeoRulesCheckTime on check"


# --- CHECK 5: MainActivity.kt Startup Integration ---
Write-Host "`n--- CHECK 5: MainActivity.kt Startup Integration ---"
$mainActivityPath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\MainActivity.kt"
$mainContent = Get-Content -Path $mainActivityPath -Raw

$hasMainEnsureAssets = $mainContent -match 'GeoAssetManager\.ensureAssetsInitialized\(applicationContext\)'
Assert-Check "MainActivity_EnsureAssets" $hasMainEnsureAssets "MainActivity calls GeoAssetManager.ensureAssetsInitialized on launch"

$hasMainBgCheck = $mainContent -match 'GeoAssetManager\.checkAndUpdateRules\(applicationContext,\s*force\s*=\s*false\)'
Assert-Check "MainActivity_BgCheck" $hasMainBgCheck "MainActivity launches background checkAndUpdateRules after delay"


# --- CHECK 6: Bundled Asset Files Check ---
Write-Host "`n--- CHECK 6: Bundled Asset Files Check ---"
$geoipPath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\assets\geoip.dat"
$geositePath = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\assets\geosite.dat"

$geoipExists = (Test-Path $geoipPath) -and ((Get-Item $geoipPath).Length -gt 1000000)
$geositeExists = (Test-Path $geositePath) -and ((Get-Item $geositePath).Length -gt 1000000)

Assert-Check "Bundled_geoip.dat" $geoipExists "geoip.dat exists in assets with size $((Get-Item $geoipPath).Length) bytes"
Assert-Check "Bundled_geosite.dat" $geositeExists "geosite.dat exists in assets with size $((Get-Item $geositePath).Length) bytes"


# --- CHECK 7: Prohibited Patterns & Facade Detection ---
Write-Host "`n--- CHECK 7: Prohibited Patterns & Facade Detection ---"
# Check if any methods in newly added/modified M2 files return fake static mocks
$noDummyBypass = -not ($bypassContent -match 'return\s+0\s*;' -or $bypassContent -match 'TODO\(')
Assert-Check "NoDummy_IranAppBypass" $noDummyBypass "IranAppBypassHelper contains no TODOs or dummy zero-returns"

$noDummyGeo = -not ($geoContent -match 'return\s+Result\.success\(true\)\s*;' -or $geoContent -match 'TODO\(')
Assert-Check "NoDummy_GeoAssetManager" $noDummyGeo "GeoAssetManager contains no unconditional dummy success returns"


# --- SUMMARY ---
Write-Host "`n================================================================="
Write-Host " FORENSIC AUDIT SUMMARY: $passes PASSED, $failures FAILED"
Write-Host "================================================================="

if ($failures -gt 0) {
    Write-Host "`nVERDICT: INTEGRITY VIOLATION ($failures failed checks)" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nVERDICT: CLEAN (All $passes checks passed)" -ForegroundColor Green
    exit 0
}
