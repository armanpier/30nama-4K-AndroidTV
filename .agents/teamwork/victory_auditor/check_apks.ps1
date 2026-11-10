Add-Type -AssemblyName System.IO.Compression.FileSystem

$apks = @(
    "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\outputs\apk\debug\app-debug.apk",
    "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\outputs\apk\release\app-release.apk",
    "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\build\outputs\apk\debug\app-debug.apk",
    "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\build\outputs\apk\release\app-release.apk"
)

foreach ($path in $apks) {
    if (Test-Path $path) {
        $item = Get-Item $path
        $zip = [System.IO.Compression.ZipFile]::OpenRead($path)
        $entryCount = $zip.Entries.Count
        $dexCount = ($zip.Entries | Where-Object { $_.FullName -like "*.dex" }).Count
        $geoCount = ($zip.Entries | Where-Object { $_.FullName -like "assets/*.dat" }).Count
        $zip.Dispose()
        Write-Host ("[OK] {0} ({1}) - {2} bytes, entries: {3}, dex: {4}, geo assets: {5}" -f $item.Name, $item.Directory.Parent.Name, $item.Length, $entryCount, $dexCount, $geoCount)
    } else {
        Write-Host ("[FAIL] Missing: {0}" -f $path)
    }
}
