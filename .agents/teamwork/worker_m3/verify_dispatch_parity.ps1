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
    if ((Get-FileHash ($dir1 + $f)).Hash -ne (Get-FileHash ($dir2 + $f)).Hash) { $diffs += $f }
}
Write-Host "Only in 1: $($onlyIn1.Count), Only in 2: $($onlyIn2.Count), Content diffs: $($diffs.Count)"
