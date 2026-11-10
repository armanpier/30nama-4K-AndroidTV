$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
$androidDir = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
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
$cp = @(
    "$androidDir\app\build\intermediates\javac\debugUnitTest\compileDebugUnitTestJavaWithJavac\classes",
    "$androidDir\app\build\tmp\kotlin-classes\debugUnitTest",
    "$androidDir\app\build\intermediates\javac\debug\compileDebugJavaWithJavac\classes",
    "$androidDir\app\build\tmp\kotlin-classes\debug"
) + $neededJars
$fullCp = $cp -join ";"
Set-Location $androidDir
& "$env:JAVA_HOME\bin\java.exe" -cp $fullCp com.asanvpn.app.GeoAssetManagerAdversarialTest
