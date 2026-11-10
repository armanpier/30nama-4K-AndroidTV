param(
    [string]$dir1 = "c:\Users\Arman\Documents\antigravity\quirky-turing\android",
    [string]$dir2 = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
)

$files1 = Get-ChildItem -Recurse -File $dir1 | Where-Object { $_.FullName -notmatch '\\(\.gradle|build|\.idea|captures|\.kotlin)\\' }
$files2 = Get-ChildItem -Recurse -File $dir2 | Where-Object { $_.FullName -notmatch '\\(\.gradle|build|\.idea|captures|\.kotlin)\\' }

$rel1 = $files1 | ForEach-Object { $_.FullName.Substring($dir1.Length) }
$rel2 = $files2 | ForEach-Object { $_.FullName.Substring($dir2.Length) }

$onlyIn1 = $rel1 | Where-Object { $_ -notin $rel2 }
$onlyIn2 = $rel2 | Where-Object { $_ -notin $rel1 }

$diffs = @()
foreach ($f in ($rel1 | Where-Object { $_ -in $rel2 })) {
    $hash1 = (Get-FileHash ($dir1 + $f)).Hash
    $hash2 = (Get-FileHash ($dir2 + $f)).Hash
    if ($hash1 -ne $hash2) {
        $diffs += $f
    }
}

Write-Host "=== COMPARISON SUMMARY ==="
Write-Host "Only in 1 (quirky-turing): $($onlyIn1.Count)"
$onlyIn1 | ForEach-Object { Write-Host "  +$_" }

Write-Host "Only in 2 (AsanVPN): $($onlyIn2.Count)"
$onlyIn2 | ForEach-Object { Write-Host "  -$_" }

Write-Host "Content differences: $($diffs.Count)"
$diffs | ForEach-Object { Write-Host "  ~$_" }
