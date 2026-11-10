$dir1 = 'c:\Users\Arman\Documents\antigravity\quirky-turing\android'
$dir2 = 'C:\Users\Arman\Documents\antigravity\AsanVPN\android'

$files1 = Get-ChildItem -Recurse -File $dir1 | Where-Object { $_.FullName -notmatch '\\(\.gradle|build|\.idea|captures|\.kotlin)\\' }
$files2 = Get-ChildItem -Recurse -File $dir2 | Where-Object { $_.FullName -notmatch '\\(\.gradle|build|\.idea|captures|\.kotlin)\\' }

$rel1 = $files1 | ForEach-Object { $_.FullName.Substring($dir1.Length) }
$rel2 = $files2 | ForEach-Object { $_.FullName.Substring($dir2.Length) }

$onlyIn1 = $rel1 | Where-Object { $_ -notin $rel2 }
$onlyIn2 = $rel2 | Where-Object { $_ -notin $rel1 }

$diffs = @()
foreach ($f in ($rel1 | Where-Object { $_ -in $rel2 })) {
    $h1 = (Get-FileHash ($dir1 + $f)).Hash
    $h2 = (Get-FileHash ($dir2 + $f)).Hash
    if ($h1 -ne $h2) {
        $diffs += [PSCustomObject]@{ File = $f; Hash1 = $h1; Hash2 = $h2 }
    }
}

Write-Host "=== PARITY CHECK RESULTS ==="
Write-Host "Total tracked files in Repo 1: $($rel1.Count)"
Write-Host "Total tracked files in Repo 2: $($rel2.Count)"
Write-Host "Only in Repo 1 count: $($onlyIn1.Count)"
if ($onlyIn1.Count -gt 0) { $onlyIn1 | ForEach-Object { Write-Host "  + $_" } }
Write-Host "Only in Repo 2 count: $($onlyIn2.Count)"
if ($onlyIn2.Count -gt 0) { $onlyIn2 | ForEach-Object { Write-Host "  - $_" } }
Write-Host "Content differences count: $($diffs.Count)"
if ($diffs.Count -gt 0) { $diffs | ForEach-Object { Write-Host "  DIFF: $($_.File)" } }
