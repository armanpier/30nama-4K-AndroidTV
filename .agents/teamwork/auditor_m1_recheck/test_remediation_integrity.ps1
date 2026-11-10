# Independent Empirical Test Suite for Milestone 1 Remediations
$ErrorActionPreference = "Stop"

Write-Output "=== TEST 1: PIN Masking Threshold Logic ==="
$pinCases = @("", "1", "12", "123", "12345", "22858950", "Arman4237340")
foreach ($p in $pinCases) {
    $masked = if ($p.Length -gt 2) { "***" + $p.Substring($p.Length - 2) } else { "***" }
    Write-Output "PIN '$p' (len=$($p.Length)) -> Masked: '$masked'"
    if ($p.Length -le 2 -and $masked -ne "***") {
        throw "VULNERABILITY: Short PIN $p leaked in $masked"
    }
    if ($p.Length -gt 2 -and !$masked.StartsWith("***")) {
        throw "VULNERABILITY: PIN $p not masked"
    }
}
Write-Output "PASS: PIN masking threshold verified."

Write-Output "`n=== TEST 2: Device ID Masking Threshold Logic ==="
$devCases = @("", "a", "dev", "1234", "12345", "a1b2c3d4e5f6", "UNKNOWN_DEVICE")
foreach ($d in $devCases) {
    $masked = if ($d.Length -gt 4) { "***" + $d.Substring($d.Length - 4) } else { "***" }
    Write-Output "DEV '$d' (len=$($d.Length)) -> Masked: '$masked'"
    if ($d.Length -le 4 -and $masked -ne "***") {
        throw "VULNERABILITY: Short Device ID $d leaked in $masked"
    }
    if ($d.Length -gt 4 -and !$masked.StartsWith("***")) {
        throw "VULNERABILITY: Device ID $d not masked"
    }
}
Write-Output "PASS: Device ID masking threshold verified."

Write-Output "`n=== TEST 3: Base URL Masking Regex ==="
$urlCases = @(
    "https://worker1.spareone.icu/api/v1/connect",
    "http://sub.worker.spareone.icu:8080/api/v1/check_lockout",
    "https://162.159.153.4:8443/api/v1/connect",
    "https://user:pass@secret.workers.dev/api/v1/connect"
)
foreach ($u in $urlCases) {
    $masked = $u -replace '://[^/]+', '://***'
    Write-Output "URL '$u' -> Masked: '$masked'"
    if ($masked -match 'spareone' -or $masked -match '162\.159' -or $masked -match 'workers\.dev') {
        throw "VULNERABILITY: URL domain leaked in $masked"
    }
    if (!$masked.Contains("://***")) {
        throw "VULNERABILITY: URL replacement failed in $masked"
    }
}
Write-Output "PASS: Base URL masking verified."

Write-Output "`n=== TEST 4: IPv4 Redaction Regex in Exception Messages ==="
$msgCases = @(
    "Failed to connect to 162.159.153.4:443 after 500ms",
    "Connection refused: /127.0.0.1:8080",
    "timeout connecting to 10.0.0.1",
    "UnknownHostException: worker.dev",
    "SSL handshake failed with 141.101.121.1:8443"
)
foreach ($m in $msgCases) {
    $sanitized = $m -replace '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', '***'
    Write-Output "MSG '$m' -> Sanitized: '$sanitized'"
    if ($sanitized -match '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+') {
        throw "VULNERABILITY: IP address leaked in $sanitized"
    }
}
Write-Output "PASS: IPv4 redaction in exception messages verified."

Write-Output "`n=== ALL 4 REMEDIATION LOGIC TESTS EMPIRICALLY PASSED ==="
