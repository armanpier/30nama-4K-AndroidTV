$ErrorActionPreference = "Stop"

$dir1 = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
$dir2 = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"

$excludePatterns = @("\\\.gradle\\", "\\build\\", "\\\.kotlin\\", "\\\.idea\\", "\\captures\\", "\\local\.properties$")

function Get-TrackedFiles($baseDir) {
    $files = Get-ChildItem -Path $baseDir -Recurse -File | Where-Object {
        $rel = $_.FullName.Substring($baseDir.Length)
        $skip = $false
        foreach ($pattern in $excludePatterns) {
            if ($rel -match $pattern) {
                $skip = $true
                break
            }
        }
        -not $skip
    }
    return $files
}

$files1 = Get-TrackedFiles $dir1
$files2 = Get-TrackedFiles $dir2

Write-Host "Tracked Files in quirky-turing\android: $($files1.Count)"
Write-Host "Tracked Files in AsanVPN\android:       $($files2.Count)"

$map1 = @{}
foreach ($f in $files1) {
    $rel = $f.FullName.Substring($dir1.Length).TrimStart("\/")
    $map1[$rel] = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
}

$map2 = @{}
foreach ($f in $files2) {
    $rel = $f.FullName.Substring($dir2.Length).TrimStart("\/")
    $map2[$rel] = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
}

$onlyIn1 = @()
$onlyIn2 = @()
$mismatched = @()

foreach ($key in $map1.Keys) {
    if (-not $map2.ContainsKey($key)) {
        $onlyIn1 += $key
    } elseif ($map1[$key] -ne $map2[$key]) {
        $mismatched += "$key (Repo1: $($map1[$key]) vs Repo2: $($map2[$key]))"
    }
}

foreach ($key in $map2.Keys) {
    if (-not $map1.ContainsKey($key)) {
        $onlyIn2 += $key
    }
}

Write-Host "================ PARITY RESULTS ================"
Write-Host "Only in quirky-turing: $($onlyIn1.Count)"
if ($onlyIn1.Count -gt 0) { $onlyIn1 | ForEach-Object { Write-Host "  $_" } }

Write-Host "Only in AsanVPN:       $($onlyIn2.Count)"
if ($onlyIn2.Count -gt 0) { $onlyIn2 | ForEach-Object { Write-Host "  $_" } }

Write-Host "Hash Mismatches:       $($mismatched.Count)"
if ($mismatched.Count -gt 0) { $mismatched | ForEach-Object { Write-Host "  $_" } }

if ($onlyIn1.Count -eq 0 -and $onlyIn2.Count -eq 0 -and $mismatched.Count -eq 0) {
    Write-Host "PARITY VERIFICATION: 100% BIT-FOR-BIT MATCH ACROSS ALL $($map1.Count) FILES!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "PARITY VERIFICATION FAILED!" -ForegroundColor Red
    exit 1
}
