# Codebase Architecture, Repository Parity & Build Environment Survey Report

## 1. Observation

### 1.1 Project Structure & File System Mapping
Surveyed target directories:
- `c:\Users\Arman\Documents\antigravity\quirky-turing\android`
- `C:\Users\Arman\Documents\antigravity\AsanVPN\android`

Both directories contain an Android Gradle application project organized as follows:
```
android/
├── build.gradle.kts                          # Root build script (AGP 8.5.0, Kotlin 2.0.0, Compose 2.0.0)
├── settings.gradle.kts                       # Root project name 'AsanVPN', module ':app'
├── gradle.properties                         # Gradle JVM & Android properties
├── gradlew, gradlew.bat                      # Gradle wrapper executables (Gradle 8.12)
├── local.properties                          # sdk.dir=C\:\\Users\\Arman\\AppData\\Local\\Android\\Sdk
├── gradle/wrapper/
│   ├── gradle-wrapper.jar
│   └── gradle-wrapper.properties             # distributionUrl: gradle-8.12-bin.zip
├── ui_backup_original_dark/                  # Historical UI backup files
│   ├── screens/ (ConnectScreen.kt, ExpiredScreen.kt, PinScreen.kt)
│   └── theme/ (Color.kt, Theme.kt)
└── app/
    ├── build.gradle.kts                      # Module build script (compileSdk 34, minSdk 24, targetSdk 34)
    ├── proguard-rules.pro                    # Obfuscation, keep rules for libv2ray, models, okhttp
    ├── libs/
    │   └── libv2ray.aar                      # Precompiled Xray-core / GoMobile native library (SHA-256: CF71680B...)
    └── src/main/
        ├── AndroidManifest.xml               # Permissions, FileProvider, MainActivity, AsanVpnService
        ├── assets/
        │   ├── custom_routing_black          # Blacklist routing definitions (3,019 bytes)
        │   ├── custom_routing_global         # Global routing definitions (464 bytes)
        │   ├── custom_routing_white          # Whitelist routing definitions (1,917 bytes)
        │   ├── custom_routing_white_iran     # Iran routing rules (631 bytes)
        │   ├── custom_routing_white_russia   # Russia routing rules (739 bytes)
        │   ├── geoip.dat                     # GeoIP database (18,534,419 bytes)
        │   ├── geosite.dat                   # GeoSite domain database (8,659,692 bytes)
        │   ├── open_source_licenses.html     # Open source attribution (52,538 bytes)
        │   ├── proxy_package_name            # Package whitelist/filter asset (9,899 bytes)
        │   ├── translators.json              # Localization metadata (2,754 bytes)
        │   ├── v2ray_config.json             # Static template config (1,553 bytes)
        │   └── v2ray_config_with_tun.json    # Template TUN config (1,867 bytes)
        ├── java/com/asanvpn/app/
        │   ├── MainActivity.kt               # Jetpack Compose Host, PIN navigation, system bar setup
        │   ├── data/
        │   │   ├── PreferencesManager.kt     # Hardware-bound AES-CBC encrypted SharedPreferences
        │   │   ├── VpnRepository.kt          # Worker API sync, failover routing, cache management
        │   │   └── models/
        │   │       └── VpnConfig.kt          # ConnectRequest, ConnectResponse, UserInfo, VpnNode
        │   ├── service/
        │   │   ├── AsanVpnService.kt         # VpnService implementation, TUN fd provider, session watcher
        │   │   ├── PingTester.kt             # Multi-tier priority waterfall latency engine
        │   │   └── v2ray/
        │   │       ├── V2RayConfigBuilder.kt # JSON generator for Xray Core inbound/outbound/routing
        │   │       └── V2RayCoreManager.kt   # JNI bridge controller & asset unpacker
        │   ├── ui/
        │   │   ├── components/
        │   │   │   └── UpdateDialog.kt       # In-app update modal with APK downloader
        │   │   ├── screens/
        │   │   │   ├── ConnectScreen.kt      # Dial button, latency badge, usage bars, server picker
        │   │   │   ├── ExpiredScreen.kt      # Subscription expiration / renewal view
        │   │   │   └── PinScreen.kt          # 8-digit keypad entry, lockout UI, admin log sheet
        │   │   └── theme/
        │   │       ├── Color.kt              # Color palette definitions
        │   │       └── Theme.kt              # Material3 Theme configuration
        │   └── util/
        │       ├── AppLogger.kt              # Dual-tier user/admin in-memory log buffer (currently max 200)
        │       └── AppUpdateManager.kt       # APK fetcher and PackageInstaller Intent trigger
        └── res/                              # Drawables, mipmaps, strings.xml, colors.xml, network_security_config.xml
```

### 1.2 Repository Comparison & Parity State
1. **Git Repository Status**:
   - `c:\Users\Arman\Documents\antigravity\quirky-turing`:
     - Remote: `origin https://github.com/armanpier/30nama-4K-AndroidTV.git (fetch & push)`
     - Current Branch: `main`, commit `e853b1c` (`fix(sync): optimize cross-panel sync, eliminate redundant remote fetches and fix socket read timeout`)
     - Android code is tracked directly under `android/`. `git status -s android/` is completely clean.
   - `C:\Users\Arman\Documents\antigravity\AsanVPN`:
     - Remote: `origin https://github.com/armanpier/AsanVPN.git (fetch & push)`
     - Current Branch: `main`, commit `cc2f31b` (`fix(sync): optimize cross-panel sync, eliminate redundant remote fetches and fix socket read timeout`)
     - Android code is tracked directly under `android/`. `git status -s android/` is completely clean.
   - **Submodules**: Neither repository uses git submodules for `android/`. Both maintain direct tracking.

2. **File Tree Diff**:
   - Total source/resource files surveyed in `quirky-turing\android`: 68 files.
   - Total source/resource files surveyed in `AsanVPN\android`: 68 files.
   - File differences identified:
     - `Only in quirky-turing\android`: `\.kotlin\errors\errors-1792793529735.log` (transient compiler error dump).
     - `Only in AsanVPN\android`: `\.gitignore` (12 lines containing ignore patterns: `*.iml`, `.gradle`, `.kotlin`, `/local.properties`, `/.idea/`, `.DS_Store`, `/build`, `/captures`, `.externalNativeBuild`, `.cxx`, `local.properties`).
     - Content differences among common files: **0 files differ**. All 67 shared files (including `libv2ray.aar`, `app/build.gradle.kts`, `V2RayCoreManager.kt`, `AsanVpnService.kt`, all Kotlin code, and all binary asset files) have 100% identical SHA-256 hashes.
   - Keystore:
     - Release keystore `asanvpn-release.jks` exists at the root of both repositories:
       - `c:\Users\Arman\Documents\antigravity\quirky-turing\asanvpn-release.jks`
       - `C:\Users\Arman\Documents\antigravity\AsanVPN\asanvpn-release.jks`
     - In `app/build.gradle.kts`, it is referenced as `storeFile = file("../../asanvpn-release.jks")`.
   - Local properties:
     - Both contain identical `local.properties`: `sdk.dir=C\:\\Users\\Arman\\AppData\\Local\\Android\\Sdk`.

### 1.3 Build Environment & Verification Results
1. **JDK 17 Setup**:
   - Location: `C:\Users\Arman\.jdks\jdk-17`
   - Command: `& "$env:JAVA_HOME\bin\java.exe" -version`
   - Output:
     ```
     openjdk version "17.0.21" 2026-10-20
     OpenJDK Runtime Environment Temurin-17.0.21+9 (build 17.0.21+9)
     OpenJDK 64-Bit Server VM Temurin-17.0.21+9 (build 17.0.21+9, mixed mode, sharing)
     ```
   - Invocation configuration: `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"` works properly.

2. **Gradle Invocations & Performance**:
   - Gradle wrapper version: Gradle 8.12 (Kotlin 2.0.21, Groovy 3.0.22, Ant 1.10.15).
   - **`quirky-turing\android`**:
     - `./gradlew assembleDebug`:
       - Result: `BUILD SUCCESSFUL in 2m 2s` (36 actionable tasks executed).
       - Output binary: `app/build/outputs/apk/debug/app-debug.apk` (81,937,180 bytes).
     - `./gradlew assembleRelease`:
       - Result: `BUILD SUCCESSFUL in 26s` (42 actionable tasks executed, minified with R8, signed with release keystore).
       - Output binary: `app/build/outputs/apk/release/app-release.apk` (60,637,185 bytes).
   - **`AsanVPN\android`**:
     - `./gradlew assembleDebug assembleRelease`:
       - Result: `BUILD SUCCESSFUL in 3m 47s` (78 actionable tasks: 56 executed, 22 up-to-date).
       - Output binaries:
         - `app/build/outputs/apk/debug/app-debug.apk` (81,937,156 bytes).
         - `app/build/outputs/apk/release/app-release.apk` (60,637,183 bytes).
   - Test suites:
     - Directories `app/src/test` and `app/src/androidTest` do not exist in either repository.


### 1.4 Native Library & JNI Architecture
- Precompiled AAR: `app/libs/libv2ray.aar` (SHA-256: `CF71680B776B9CA583747BA652F816B047A655EAB875D8951E6141636D88BBD6`).
- Archive inspection revealed:
  - `jni/arm64-v8a/libgojni.so` (35,995,824 bytes)
  - `jni/armeabi-v7a/libgojni.so` (34,825,460 bytes)
  - `jni/x86/libgojni.so` (34,872,196 bytes)
  - `jni/x86_64/libgojni.so` (38,412,304 bytes)
  - `classes.jar` (13,426 bytes) with classes: `libv2ray.Libv2ray`, `libv2ray.CoreController`, `libv2ray.CoreCallbackHandler`, `go.Seq`
  - `assets/geoip.dat`, `assets/geosite.dat`, `assets/geoip-only-cn-private.dat`
- No CMake or NDK build scripts (`CMakeLists.txt` or `Android.mk`) are present or required because the native core is completely prebuilt into `libv2ray.aar`.

### 1.5 Architecture Layers & Component Catalog
1. **Core / JNI Layer**:
   - `libv2ray.aar`: Go runtime bridged via GoMobile.
   - `V2RayCoreManager.kt`:
     - Calls `Libv2ray.initCoreEnv(...)` pointing to app's internal private files directory (`context.getDir("assets", Context.MODE_PRIVATE)`).
     - Copies `geoip.dat` and `geosite.dat` from APK assets on first run.
     - Controls core lifecycle via `coreController.startLoop(configJson, tunFd)` and `coreController.stopLoop()`.
     - Queries traffic stats via `coreController.queryAllOutboundTrafficStats()`.
2. **Service & Background Layer**:
   - `AsanVpnService.kt`:
     - Subclasses `android.net.VpnService`.
     - Binds OS TUN interface (`172.19.0.1/30`, MTU 1500, Route `0.0.0.0/0`, DNS `1.1.1.1`/`8.8.8.8`).
     - Calls `builder.addDisallowedApplication(packageName)` to prevent self-loop.
     - Hands file descriptor `tunFd` to `V2RayCoreManager`.
     - Spawns coroutine `sessionValidatorJob` that runs every 25 seconds against `VpnRepository.syncWithWorker` to immediately kill the tunnel if the user's PIN is deleted, invalid, or revoked.
3. **Configuration Generator**:
   - `V2RayConfigBuilder.kt`:
     - Builds complete Xray JSON with `tun`, `socks-in` (port 10808), `http-in` (port 10809), and outbounds (`proxy`, `dns-out`, `direct`, `block`).
     - Generates lightweight `buildTestConfig` for `Libv2ray.measureOutboundDelay`.
4. **Latency & Probing Engine**:
   - `PingTester.kt`:
     - Multi-tier priority waterfall cascade (`connectFastAndOptimize`, `findFastestNode`).
     - Stage 1: Parallel TCP prescan (`testTcpLatency`) to reject unresponsive hosts.
     - Stage 2: Real tunnel delay (`measureRealDelay`) via `Libv2ray.measureOutboundDelay(configJson, url)` (Cloudflare 204 with fallback to Google 204).
     - Connects immediately to first working candidate, then continues optimizing in the background.
5. **Data & Repository Layer**:
   - `VpnRepository.kt`: Handles Cloudflare Worker endpoints, multi-route fallback, response parsing, node caching, and lockout verification (`/api/check_lockout`).
   - `PreferencesManager.kt`: Hardware-bound AES-CBC encryption using device fingerprint and package name seed.
6. **Presentation / UI Layer**:
   - 100% Jetpack Compose single-activity app.
   - `MainActivity.kt`: Navigation logic, status bar styling, deep link handling (`asanvpn://`).
   - `PinScreen.kt`, `ConnectScreen.kt`, `ExpiredScreen.kt`, `UpdateDialog.kt`.
7. **Logging Layer**:
   - `AppLogger.kt`: In-memory dual-tier logger (`userLogs` and `adminLogs`). Currently capped at `MAX_LOG_ENTRIES = 200`.

---

## 2. Logic Chain

1. **Repository Identity & Relationship**:
   - *From Observation 1.2*, `quirky-turing` and `AsanVPN` are distinct git repositories with different origin remotes (`30nama-4K-AndroidTV` vs `AsanVPN`).
   - However, the `android/` directory in both repos contains the exact same AsanVPN Android codebase, down to identical SHA-256 hashes on all 67 common files.
   - Therefore, any code modifications made to satisfy R1 and R2 in `quirky-turing\android` must be mirrored file-by-file into `AsanVPN\android` to maintain 100% parity (R3).

2. **Parity Gap Analysis**:
   - *From Observation 1.2*, `AsanVPN\android\.gitignore` exists in `AsanVPN\android` and is tracked in git commit `c1065c0`, but is missing in `quirky-turing\android`.
   - *From Observation 1.2*, `quirky-turing\android\.kotlin\errors\errors-1792793529735.log` exists only in `quirky-turing\android`.
   - Therefore, to achieve 100% file tree parity:
     - Copy `android\.gitignore` into `quirky-turing\android`.
     - Delete the transient compiler error log `.kotlin\errors\*.log`.

3. **Build Feasibility**:
   - *From Observation 1.3*, JDK 17 (`C:\Users\Arman\.jdks\jdk-17`) is verified and functional.
   - *From Observation 1.3*, both `assembleDebug` and `assembleRelease` compile cleanly and produce signed APKs using the existing `asanvpn-release.jks`.
   - Therefore, the local build environment is fully operational and ready for compilation verification during implementation.

4. **Requirements Mapping to Architecture**:
   - **R1 (Log Capping and Redaction)**:
     - *From Observation 1.5 (Logging Layer)*, `AppLogger.kt:16` sets `MAX_LOG_ENTRIES = 200`. Reducing this to `100` satisfies log buffer capping.
     - *From Observation 1.5 (Data and Latency Layers)*, `VpnRepository.kt` lines 252, 263, 272, 276, and 385 dump raw server responses and link parameters into `AppLogger.logAdmin`. `PingTester.kt` lines 81, 103, 110, 119, and 125 log server hostnames, IP addresses, ports, protocols, and security parameters.
     - Redacting these strings so that only link remark, latency delay (ms), and success/failure status are recorded will fulfill R1 without leaking sensitive endpoint information.
   - **R2 (Iran Direct Bypass & Iranian App Exclusions)**:
     - *From Observation 1.1 and 1.5 (Routing Layer)*, `custom_routing_white_iran` contains `"geosite:category-ir"` and `"geoip:ir"`, but `V2RayConfigBuilder.kt` lines 155-189 only contains a hardcoded list of 10 domains and `geoip:private`. Adding `"geosite:category-ir"`, `"geosite:ir"`, `"domain:ir"` to the direct domain rule and `"geoip:ir"` to the direct IP rule ensures full Xray routing engine bypass.
     - *From Observation 1.5 (Service Layer)*, `AsanVpnService.kt:115` already uses `builder.addDisallowedApplication(packageName)`. Iterating through a predefined registry of Iranian application package names (Nobitex `market.nobitex`, Up `com.asanpardakht.app`, Cafe Bazaar `com.farsitel.bazaar`, Divar `ir.divar`, Snapp `cab.snapp.passenger`, Tapsi `taxi.tap30.passenger`, banking and domestic apps) and adding installed packages via `addDisallowedApplication` will route their traffic outside the VPN tunnel.
     - *From Observation 1.5 (Core Layer)*, `V2RayCoreManager.copyAssetIfMissing` only copies files if missing. Implementing a background update check against official chocolate4iran release assets (`chocolate4iran/Iran-v2ray-rules`) will enable regular rule updates.

---

## 3. Caveats

1. **Git Remote Permissions & Branches**:
   - `quirky-turing` is currently tracking `30nama-4K-AndroidTV.git` on `main`, while `AsanVPN` tracks `AsanVPN.git` on `main`. Push operations to remote repositories are subject to user git credentials and network availability.
2. **Missing Unit Tests**:
   - Neither repository currently contains unit test files (`src/test` or `src/androidTest`). Verification is performed through Gradle task execution (`assembleDebug`, `assembleRelease`, `lint`), compilation integrity, and hash-based parity checks.
3. **App Disallowed Application Package Detection**:
   - `VpnService.Builder.addDisallowedApplication` throws `PackageManager.NameNotFoundException` if a package is not installed on the running device. The implementation must safely catch this exception or verify package presence before registration.

---

## 4. Conclusion

1. **Parity State**: `quirky-turing\android` and `AsanVPN\android` are identical in all 67 active source and resource files. Only `android\.gitignore` is missing from `quirky-turing\android`, and an untracked compiler log exists.
2. **Build Readiness**: Both `assembleDebug` and `assembleRelease` compile successfully on Windows with JDK 17 (`C:\Users\Arman\.jdks\jdk-17`) and Gradle 8.12.
3. **Architecture Mapping**: The codebase has clean separation of concerns. All 3 target requirements (R1, R2, R3) have clear, isolated insertion points across `AppLogger.kt`, `PingTester.kt`, `VpnRepository.kt`, `V2RayConfigBuilder.kt`, `AsanVpnService.kt`, and `V2RayCoreManager.kt`.
4. **Synchronization Strategy**:
   - Implement changes in `quirky-turing\android`.
   - Copy `android\.gitignore` to `quirky-turing\android` and remove `.kotlin\errors\*.log`.
   - Mirror all changed files into `AsanVPN\android`.
   - Verify 0 hash diffs across all source files.
   - Run `./gradlew assembleDebug` and `./gradlew assembleRelease` on both repositories.

---

## 5. Verification Method

### 5.1 Independent Verification Commands

To verify repository parity, run the following PowerShell command from `c:\Users\Arman\Documents\antigravity\quirky-turing`:

```powershell
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

Write-Host "Only in quirky-turing: $($onlyIn1 -join ', ')"
Write-Host "Only in AsanVPN: $($onlyIn2 -join ', ')"
Write-Host "Mismatched content files: $($diffs -join ', ')"
```

### 5.2 Build Verification Commands

To verify Gradle builds with JDK 17 on either repository:

```powershell
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
cd c:\Users\Arman\Documents\antigravity\quirky-turing\android
.\gradlew.bat assembleDebug assembleRelease

cd C:\Users\Arman\Documents\antigravity\AsanVPN\android
.\gradlew.bat assembleDebug assembleRelease
```

### 5.3 Invalidation Conditions
- Any file present in one `android/` directory but missing from the other (excluding build cache `.gradle`, `build`, `.idea`, `.kotlin`).
- Any SHA-256 hash mismatch between corresponding source/config/asset files in both repositories.
- Any compilation or R8 shrinking failure when running `assembleDebug` or `assembleRelease` under JDK 17.
