$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
$env:PATH = "$env:JAVA_HOME\bin;" + $env:PATH

Write-Host "=== JDK 17 Verification ==="
& "$env:JAVA_HOME\bin\java.exe" -version

$androidJar = "C:\Users\Arman\AppData\Local\Android\Sdk\platforms\android-34\android.jar"
$modulesPath = "$env:USERPROFILE\.gradle\caches\modules-2\files-2.1"
$neededJars = @(
    $androidJar,
    (Get-ChildItem -Recurse -Filter "gson-2.10.1.jar" $modulesPath | Select-Object -First 1 -ExpandProperty FullName),
    (Get-ChildItem -Recurse -Filter "kotlin-stdlib-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources" } | Select-Object -First 1 -ExpandProperty FullName),
    (Get-ChildItem -Recurse -Filter "okhttp-4.12.0.jar" $modulesPath | Select-Object -First 1 -ExpandProperty FullName),
    (Get-ChildItem -Recurse -Filter "okio-jvm-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources" } | Select-Object -First 1 -ExpandProperty FullName),
    (Get-ChildItem -Recurse -Filter "kotlinx-coroutines-core-jvm-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources" } | Select-Object -First 1 -ExpandProperty FullName),
    (Get-ChildItem -Recurse -Filter "kotlinx-coroutines-android-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources" } | Select-Object -First 1 -ExpandProperty FullName)
)

Write-Host "Located dependency jars:"
$neededJars | ForEach-Object { Write-Host "  $_" }

function Run-Repo-Tests($repoRoot, $repoName) {
    $androidDir = "$repoRoot\android"
    Write-Host "`n========================================================"
    Write-Host "Testing $repoName at $androidDir"
    Write-Host "========================================================"

    Set-Location $androidDir
    Write-Host "1. Running Gradle testDebugUnitTest..."
    & ".\gradlew.bat" testDebugUnitTest --no-daemon
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle test failed on $repoName"
    }

    $cp = @(
        "$androidDir\app\build\intermediates\javac\debugUnitTest\compileDebugUnitTestJavaWithJavac\classes",
        "$androidDir\app\build\tmp\kotlin-classes\debugUnitTest",
        "$androidDir\app\build\intermediates\javac\debug\compileDebugJavaWithJavac\classes",
        "$androidDir\app\build\tmp\kotlin-classes\debug"
    ) + $neededJars

    $fullCp = $cp -join ";"

    $mainClasses = @(
        "com.asanvpn.app.util.AppLoggerStressTest",
        "com.asanvpn.app.AppLoggerEmpiricalTest",
        "com.asanvpn.app.M1RemediationAdversarialTest",
        "com.asanvpn.app.M2RoutingAndBypassEmpiricalTest",
        "com.asanvpn.app.GeoAssetManagerAdversarialTest"
    )

    foreach ($cls in $mainClasses) {
        Write-Host "`n--- Executing $cls on $repoName ---"
        if ($cls -eq "com.asanvpn.app.M1RemediationAdversarialTest") {
            # M1RemediationAdversarialTest expects working directory to be repo root so android/app/... resolves
            Set-Location $repoRoot
        } else {
            Set-Location $androidDir
        }
        & "$env:JAVA_HOME\bin\java.exe" -cp $fullCp $cls
        if ($LASTEXITCODE -ne 0) {
            throw "$cls failed with exit code $LASTEXITCODE on $repoName"
        }
    }
}

Run-Repo-Tests "c:\Users\Arman\Documents\antigravity\quirky-turing" "Repo 1 (quirky-turing)"
Run-Repo-Tests "C:\Users\Arman\Documents\antigravity\AsanVPN" "Repo 2 (AsanVPN)"

Write-Host "`n========================================================"
Write-Host "ALL EMPIRICAL TESTS PASSED ACROSS BOTH REPOSITORIES!"
Write-Host "========================================================"
