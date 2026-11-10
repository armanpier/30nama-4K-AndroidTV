# Independent Parity and Integrity Audit Script
$ErrorActionPreference = "Stop"

$repo1 = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
$repo2 = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"

Write-Host "=== 1. Checking Directory Existence ==="
Write-Host "Repo 1 ($repo1): $(Test-Path $repo1)"
Write-Host "Repo 2 ($repo2): $(Test-Path $repo2)"

Write-Host "`n=== 2. Root Directory Listing (including hidden) ==="
Write-Host "Repo 1 Root Items:"
Get-ChildItem -Force $repo1 | Select-Object Name, Mode, Length | Format-Table -AutoSize
Write-Host "Repo 2 Root Items:"
Get-ChildItem -Force $repo2 | Select-Object Name, Mode, Length | Format-Table -AutoSize

Write-Host "`n=== 3. Ephemeral Directories & Scraps Detection ==="
$ephemeralRegex = '\\(\.gradle|build|\.idea|captures|\.kotlin)\\'
$scrapsRegex = '(\.log$|\.tmp$|\.bak$|\.swp$|error|dump)'

$allFiles1 = Get-ChildItem -Recurse -Force -File $repo1
$allFiles2 = Get-ChildItem -Recurse -Force -File $repo2

Write-Host "Total raw files in Repo 1 (including all caches/build): $($allFiles1.Count)"
Write-Host "Total raw files in Repo 2 (including all caches/build): $($allFiles2.Count)"

$scraps1 = $allFiles1 | Where-Object { $_.FullName -notmatch $ephemeralRegex -and $_.Name -match $scrapsRegex }
$scraps2 = $allFiles2 | Where-Object { $_.FullName -notmatch $ephemeralRegex -and $_.Name -match $scrapsRegex }

Write-Host "`nPotential non-ephemeral scrap files in Repo 1:"
if ($scraps1) { $scraps1 | Select-Object FullName | Format-Table -AutoSize } else { Write-Host "None" }

Write-Host "`nPotential non-ephemeral scrap files in Repo 2:"
if ($scraps2) { $scraps2 | Select-Object FullName | Format-Table -AutoSize } else { Write-Host "None" }

Write-Host "`n=== 4. Checking Ephemeral Directory Contents ==="
$transientDirs1 = Get-ChildItem -Force $repo1 | Where-Object { $_.Name -match '^\.gradle$|^build$|^\.idea$|^captures$|^\.kotlin$' }
$transientDirs2 = Get-ChildItem -Force $repo2 | Where-Object { $_.Name -match '^\.gradle$|^build$|^\.idea$|^captures$|^\.kotlin$' }

Write-Host "Ephemeral dirs in Repo 1: $($transientDirs1.Name -join ', ')"
Write-Host "Ephemeral dirs in Repo 2: $($transientDirs2.Name -join ', ')"

# Check if .kotlin exists and has anything in it
if (Test-Path "$repo1\.kotlin") {
    Write-Host "Repo 1 has .kotlin directory. Contents:"
    Get-ChildItem -Recurse -Force "$repo1\.kotlin" | Select-Object FullName
}
if (Test-Path "$repo2\.kotlin") {
    Write-Host "Repo 2 has .kotlin directory. Contents:"
    Get-ChildItem -Recurse -Force "$repo2\.kotlin" | Select-Object FullName
}

Write-Host "`n=== 5. Non-Ephemeral Tracked File Parity & SHA-256 Audit ==="
$trackedFiles1 = $allFiles1 | Where-Object { $_.FullName -notmatch $ephemeralRegex }
$trackedFiles2 = $allFiles2 | Where-Object { $_.FullName -notmatch $ephemeralRegex }

Write-Host "Tracked file count in Repo 1: $($trackedFiles1.Count)"
Write-Host "Tracked file count in Repo 2: $($trackedFiles2.Count)"

$relMap1 = @{}
foreach ($f in $trackedFiles1) {
    $rel = $f.FullName.Substring($repo1.Length).TrimStart('\', '/')
    $relMap1[$rel] = $f
}

$relMap2 = @{}
foreach ($f in $trackedFiles2) {
    $rel = $f.FullName.Substring($repo2.Length).TrimStart('\', '/')
    $relMap2[$rel] = $f
}

$onlyIn1 = $relMap1.Keys | Where-Object { -not $relMap2.ContainsKey($_) }
$onlyIn2 = $relMap2.Keys | Where-Object { -not $relMap1.ContainsKey($_) }

Write-Host "`nFiles ONLY in Repo 1 ($($onlyIn1.Count)):"
if ($onlyIn1) { $onlyIn1 | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  (None)" }

Write-Host "`nFiles ONLY in Repo 2 ($($onlyIn2.Count)):"
if ($onlyIn2) { $onlyIn2 | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  (None)" }

Write-Host "`n=== 6. Computing SHA-256 Hashes for All Common Tracked Files ==="
$commonFiles = $relMap1.Keys | Where-Object { $relMap2.ContainsKey($_) } | Sort-Object
Write-Host "Common tracked files to hash: $($commonFiles.Count)"

$hashMismatches = @()
$hashMatches = 0

foreach ($rel in $commonFiles) {
    $path1 = $relMap1[$rel].FullName
    $path2 = $relMap2[$rel].FullName
    
    $hash1 = (Get-FileHash -Algorithm SHA256 -Path $path1).Hash
    $hash2 = (Get-FileHash -Algorithm SHA256 -Path $path2).Hash
    
    if ($hash1 -ne $hash2) {
        $hashMismatches += [PSCustomObject]@{
            File = $rel
            Hash1 = $hash1
            Hash2 = $hash2
            Size1 = $relMap1[$rel].Length
            Size2 = $relMap2[$rel].Length
        }
    } else {
        $hashMatches++
    }
}

Write-Host "`nHash Match Count: $hashMatches"
Write-Host "Hash Mismatch Count: $($hashMismatches.Count)"

if ($hashMismatches.Count -gt 0) {
    Write-Host "`nMismatched Files:"
    $hashMismatches | Format-Table -AutoSize
}

Write-Host "`n=== 7. Detailed Audit of Key Modified/Added Files ==="
$keyFiles = @(
    "app\src\main\java\com\asanvpn\app\util\AppLogger.kt",
    "app\src\main\java\com\asanvpn\app\util\IranAppBypassHelper.kt",
    "app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt",
    "app\src\main\java\com\asanvpn\app\data\PreferencesManager.kt",
    "app\src\main\java\com\asanvpn\app\data\VpnRepository.kt",
    "app\src\main\java\com\asanvpn\app\service\AsanVpnService.kt",
    "app\src\main\java\com\asanvpn\app\service\PingTester.kt",
    "app\src\main\java\com\asanvpn\app\service\v2ray\V2RayConfigBuilder.kt",
    "app\src\main\java\com\asanvpn\app\MainActivity.kt",
    ".gitignore",
    "build.gradle",
    "settings.gradle",
    "gradle.properties",
    "app\build.gradle",
    "gradle\wrapper\gradle-wrapper.properties",
    "gradle\libs.versions.toml"
)

foreach ($kf in $keyFiles) {
    $p1 = Join-Path $repo1 $kf
    $p2 = Join-Path $repo2 $kf
    $e1 = Test-Path $p1
    $e2 = Test-Path $p2
    if ($e1 -and $e2) {
        $h1 = (Get-FileHash -Algorithm SHA256 -Path $p1).Hash
        $h2 = (Get-FileHash -Algorithm SHA256 -Path $p2).Hash
        $eq = ($h1 -eq $h2)
        Write-Host "$kf : Match=$eq ($h1)"
    } else {
        Write-Host "$kf : Missing! (p1=$e1, p2=$e2)"
    }
}
