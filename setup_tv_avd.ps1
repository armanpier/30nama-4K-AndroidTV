$jhome = "C:\Program Files\Android\Android Studio\jbr"
$env:JAVA_HOME = $jhome
$env:PATH = "$jhome\bin;$env:PATH"
$avdmanager = "$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin\avdmanager.bat"

Write-Host "=== Creating AVD Android_TV_4K ==="
& $avdmanager create avd --name "Android_TV_4K" --package "system-images;android-34;google-tv;x86" --device "tv_4k" --force

Write-Host "=== Listing AVDs ==="
& $avdmanager list avd
