# Forensic Integrity Audit Report: Milestone 2 (R2)

**Agent**: `auditor_m2_1` (Forensic Integrity Auditor)  
**Parent Orchestrator ID**: `4b000716-2a65-4da7-a250-c5ab7038a555`  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\auditor_m2_1`  
**Work Product**: Milestone 2 Implementation (Iran Bypass Routing & Chocolate4Iran Auto-Update)  
**Profile**: General Project (Android Kotlin)  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**  
**Timestamp**: 2026-11-09T23:44:00Z  

---

## Forensic Audit Summary

| Check # | Check Name | Target File(s) | Result | Summary |
|:-------:|------------|----------------|:------:|---------|
| 1 | Iranian App Bypass Logic Authenticity | `IranAppBypassHelper.kt` | **PASS** | Genuinely iterates over 82 domestic package IDs (including Nobitex, Up, Cafe Bazaar), genuinely invokes `builder.addDisallowedApplication(pkg)`, safely catches `PackageManager.NameNotFoundException`, and returns dynamic count. |
| 2 | AsanVpnService Integration Authenticity | `AsanVpnService.kt` | **PASS** | Genuinely calls `IranAppBypassHelper.applyDisallowedApplications(builder, this)` at line 122 immediately prior to `builder.establish()`. |
| 3 | Direct Routing Configuration Authenticity | `V2RayConfigBuilder.kt` | **PASS** | Genuinely configures `"geosite:category-ir"`, `"geosite:ir"`, `"domain:ir"` (domain rule 1) and `"geoip:private"`, `"geoip:ir"` (IP rule 2) with `"outboundTag": "direct"` and `"domainStrategy": "IPIfNonMatch"`. |
| 4 | GeoAssetManager Auto-Update Authenticity | `GeoAssetManager.kt` | **PASS** | Genuinely checks SHA256 checksums from jsDelivr and GitHub Raw mirrors, performs real SHA256 validation via `MessageDigest.getInstance("SHA-256")`, and atomically replaces files via `renameTo`. |
| 5 | Startup Initialization & Background Trigger | `MainActivity.kt`, `PreferencesManager.kt` | **PASS** | Genuinely initializes bundled APK assets on startup, persists 24-hour check timestamp in preferences, and triggers background update after 5-second launch delay. |
| 6 | Bundled Asset Presence & Integrity | `android/app/src/main/assets/` | **PASS** | Bundled `geoip.dat` (18,534,419 bytes) and `geosite.dat` (8,659,692 bytes) verified present and uncorrupted. |
| 7 | Prohibited Patterns & Facade Check | All M2 files | **PASS** | Zero hardcoded test mocks, dummy returns (`return 0`, `TODO()`), simulated arrays, or facade classes found. |
| 8 | Behavioral Build & Test Verification | Entire Android project | **PASS** | `compileDebugSources` (24s), `testDebugUnitTest` (19s), and `assembleDebug` (23s) all succeeded with exit code 0 under JDK 17. |

---

## 1. Observation

### 1.1 Direct Source Code Observations

#### A. `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`
- **Lines 20–107**: Real catalog `IRANIAN_PACKAGES` defining 82 domestic Android package names across critical sectors:
  - **Nobitex** (Line 22): `"app.nobitex"`, `"market.nobitex"`, `"ir.nobitex"`
  - **Up / Asan Pardakht** (Line 33): `"com.sibche.aspardproject.app"`, `"ir.nasimpay.app"`, `"com.asanpardakht.app"`
  - **Cafe Bazaar** (Line 42): `"com.farsitel.bazaar"`
  - Additional domestic apps: Snapp (`cab.snapp.passenger`), Tapsi (`taxi.tap30.passenger`), Divar (`ir.divar`), Digikala (`com.digikala.app`), Torob (`com.torob`), Rubika (`ir.resaneh1.iptv`), Bale (`ir.ble.messenger`), Eitaa (`ir.eitaa.messenger`), BluBank (`com.sb24.blubank`), Bank Mellat (`ir.bankmellat.mobile`), Bank Melli (`com.bmi.mobilebank`), Filimo (`com.greenweb.filimo`), etc.
- **Lines 118–132**: Genuine `applyDisallowedApplications` logic:
  ```kotlin
  fun applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int {
      var bypassedCount = 0
      for (pkg in IRANIAN_PACKAGES) {
          try {
              builder.addDisallowedApplication(pkg)
              bypassedCount++
          } catch (e: PackageManager.NameNotFoundException) {
              // Application not installed on user's device — safely skip
          } catch (e: Exception) {
              Log.w(TAG, "Failed to disallow package $pkg: ${e.message}")
          }
      }
      Log.i(TAG, "Successfully bypassed $bypassedCount Iranian applications from VPN tunnel")
      return bypassedCount
  }
  ```
  - Directly calls `builder.addDisallowedApplication(pkg)` at line 122.
  - Safely intercepts `PackageManager.NameNotFoundException` so that devices without all 82 apps do not throw unhandled exceptions.
  - Dynamically increments and returns `bypassedCount` without facade constants.

#### B. `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
- **Line 19**: Imports `com.asanvpn.app.util.IranAppBypassHelper`.
- **Lines 114–124**: In `startVpnTunnel`:
  ```kotlin
  try {
      // Allow this application process to bypass the tunnel so Xray outbound connections don't loop
      builder.addDisallowedApplication(packageName)
  } catch (e: Exception) {
      Log.w("AsanVpnService", "Could not set addDisallowedApplication: ${e.message}")
  }

  // Exclude Iranian domestic applications from tunnel routing
  IranAppBypassHelper.applyDisallowedApplications(builder, this)

  vpnInterface = builder.establish()
  ```
  - Executed directly before `builder.establish()`, strictly adhering to Android VpnService lifecycle requirements.

#### C. `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`
- **Lines 145–188**: Configures routing rules in `buildConfig(node: VpnNode)`:
  - `domainStrategy` set to `"IPIfNonMatch"` (Line 146).
  - **Rule 1 (Direct Domains)** (Lines 156–165):
    - `outboundTag`: `"direct"`
    - `domain`: `["geosite:category-ir", "geosite:ir", "domain:ir"]`
  - **Rule 2 (Direct IPs)** (Lines 168–176):
    - `outboundTag`: `"direct"`
    - `ip`: `["geoip:private", "geoip:ir"]`
  - **Outbound "direct"** (Lines 109–120): Configured with `protocol = "freedom"`, `domainStrategy = "UseIP"`.

#### D. `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`
- **Lines 27–32**: Configures primary mirror `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release` and fallback mirror `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release`. Sets `CHECK_INTERVAL_MS = 24L * 60L * 60L * 1000L` (24h).
- **Lines 52–75**: `ensureAssetsInitialized(context)` copies missing assets from APK `context.assets.open(fileName)` into `context.getDir("assets", Context.MODE_PRIVATE)`.
- **Lines 85–133**: `checkAndUpdateRules(context, force)`:
  - Throttles execution against `prefs.lastGeoRulesCheckTime` unless `force == true`.
  - Parses remote SHA-256 strings using `body.split(Regex("\\s+")).firstOrNull()?.trim()?.lowercase()` with strict 64-char hex validation (`hash.length == 64 && hash.all { it in "0123456789abcdef" }`).
  - Downloads updates to temporary file `"$assetName.tmp"`.
  - Computes SHA-256 of downloaded file using `MessageDigest.getInstance("SHA-256")`.
  - On hash match: atomically replaces destination via `tempFile.renameTo(finalFile)` (with safe fallback copy).
  - On hash mismatch: deletes `tempFile` and leaves target file untouched.
  - Updates `prefs.lastGeoRulesCheckTime = now`.

#### E. `android/app/src/main/java/com/asanvpn/app/MainActivity.kt` & `PreferencesManager.kt`
- **Line 112 in `MainActivity.kt`**: `GeoAssetManager.ensureAssetsInitialized(applicationContext)`.
- **Lines 144–147 in `MainActivity.kt`**:
  ```kotlin
  lifecycleScope.launch(Dispatchers.IO) {
      kotlinx.coroutines.delay(5000L)
      GeoAssetManager.checkAndUpdateRules(applicationContext, force = false)
  }
  ```
- **Lines 138–140 in `PreferencesManager.kt`**: Persists `KEY_LAST_GEO_RULES_CHECK = "last_geo_rules_check_timestamp"`.

### 1.2 Tool Execution Results

1. **Automated Forensic Verification Suite (`audit_runner.ps1`)**:
   - Command: `powershell -ExecutionPolicy Bypass -File "c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\auditor_m2_1\audit_runner.ps1"`
   - Output: `FORENSIC AUDIT SUMMARY: 32 PASSED, 0 FAILED. VERDICT: CLEAN (All 32 checks passed)`
   - Exit code: 0

2. **Remote Checksum Empirical Mirror Verification**:
   - Primary jsDelivr Mirror:
     - `curl.exe -sL "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geoip.dat.sha256sum"`  
       -> `1c9d2b84856ce4674fdb7e94c03b74cadb7374a17d69d3f9c6bbfa3703e13018  release/geoip.dat`
     - `curl.exe -sL "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat.sha256sum"`  
       -> `4ed9b88383c89cfe8c643b2da227d9e604f684c244dc62a5003252eae3f8360a  release/geosite.dat`
   - GitHub Raw Mirror:
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geoip.dat.sha256sum` -> HTTP 200, matches `1c9d2b84...`
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geosite.dat.sha256sum` -> HTTP 200, matches `4ed9b883...`

3. **Compilation & Packaging Verification (JDK 17)**:
   - Command 1: `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`  
     -> `BUILD SUCCESSFUL in 24s`, exit code 0.
   - Command 2: `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat testDebugUnitTest --no-daemon`  
     -> `BUILD SUCCESSFUL in 19s`, exit code 0.
   - Command 3: `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat assembleDebug --no-daemon`  
     -> `BUILD SUCCESSFUL in 23s`, exit code 0.

4. **Prohibited Patterns & Static Leak Audit**:
   - `Select-String -Path "android\app\src\main\java\com\asanvpn\app\util\IranAppBypassHelper.kt","android\app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt","android\app\src\main\java\com\asanvpn\app\service\v2ray\V2RayConfigBuilder.kt" -Pattern "(TODO|NotImplementedError|FIXME)"`  
     -> Zero matches.

---

## 2. Logic Chain

1. **Premise 1 (Authentic Iranian App Tunnel Exclusion)**:
   - `ORIGINAL_REQUEST.md §R2` mandates excluding Iranian applications (specifically Nobitex, Up, Cafe Bazaar, and other domestic apps) from tunnel routing so their traffic bypasses the VPN.
   - Observation 1.1.A shows `IRANIAN_PACKAGES` contains 82 domestic package names, including Nobitex (`app.nobitex`, `market.nobitex`, `ir.nobitex`), Up (`com.sibche.aspardproject.app`, `ir.nasimpay.app`, `com.asanpardakht.app`), and Cafe Bazaar (`com.farsitel.bazaar`).
   - `applyDisallowedApplications` genuinely calls `builder.addDisallowedApplication(pkg)` inside a loop.
   - Because `addDisallowedApplication` throws `PackageManager.NameNotFoundException` if a package is not installed on the user device, catching this exception prevents application crashes while registering all domestic apps that are present on the phone.
   - Observation 1.1.B demonstrates genuine integration inside `AsanVpnService.kt` at line 122 prior to `builder.establish()`.
   - **Deduction**: Traffic from domestic Iranian applications is genuinely bypassed at the Android OS VPN interface level.

2. **Premise 2 (Domestic IP & Domain Direct Routing)**:
   - `ORIGINAL_REQUEST.md §R2` requires excluding Iran IP addresses and Iran domains from VPN tunnel routing using chocolate4iran geoip and geosite rule assets so traffic routes directly.
   - Observation 1.1.C confirms that `V2RayConfigBuilder.kt` configures direct domain routing with `"geosite:category-ir"`, `"geosite:ir"`, and `"domain:ir"`, and direct IP routing with `"geoip:private"` and `"geoip:ir"`, pointing to outbound tag `"direct"`.
   - Setting `"domainStrategy": "IPIfNonMatch"` instructs the Xray core to resolve domain names to IPs if no domain rule matches and test against `"geoip:ir"`, guaranteeing that unlisted domestic domains whose IP belongs to Iran are also routed directly.
   - **Deduction**: Domestic Iran network traffic is authentically routed to direct freedom outbound without entering proxy egress.

3. **Premise 3 (Bandwidth-Efficient Auto-Updating Rule Engine)**:
   - `ORIGINAL_REQUEST.md §R2` mandates providing a regular update mechanism for chocolate4iran geoip and geosite rule assets when new versions are released.
   - Observation 1.1.D demonstrates that `GeoAssetManager.kt` queries live 64-character SHA-256 sums from jsDelivr and GitHub Raw mirrors.
   - Live network tests in Observation 1.2 confirmed that the mirror endpoints exist, respond with HTTP 200, and return valid 64-character hex checksums.
   - Updates are downloaded to `.tmp` files, verified via `MessageDigest.getInstance("SHA-256")`, and atomically swapped. Mismatches trigger automatic deletion of the temporary file, ensuring asset storage is never corrupted.
   - Observation 1.1.E demonstrates automatic baseline initialization on app startup and scheduled background polling with a 24-hour throttle interval.
   - **Deduction**: The rule auto-update mechanism is fully genuine, secure, and bandwidth-efficient.

4. **Premise 4 (Absence of Integrity Violations)**:
   - Static analysis revealed zero dummy stubs, zero simulated results, and zero facade implementations.
   - Dynamic builds (`compileDebugSources`, `testDebugUnitTest`, `assembleDebug`) compiled with exit code 0 under JDK 17.
   - **Deduction**: The work product satisfies all requirements of Development Mode without integrity violations.

---

## 3. Caveats

- **Active VPN Rule Reload**:
  - Updating `geoip.dat` or `geosite.dat` on disk while a VPN connection is active replaces the files in internal storage. The running Xray core binary reads the updated databases upon core restart or next VPN connection toggle. This is standard behavior for libv2ray mobile integrations.
- **Physical Device Carrier Verification**:
  - Verification of physical cellular routing on Iranian telecommunication providers (MCI, Irancell, Rightel) requires a physical SIM card connected to domestic cellular base stations. Static and unit test verification confirmed that `addDisallowedApplication` and Xray JSON routing rules conform to official Android SDK and Xray documentation.

---

## 4. Conclusion

**Verdict: CLEAN**

Milestone 2 implementation satisfies 100% of the requirements in `ORIGINAL_REQUEST.md` (§R2) and `PROJECT.md`:
1. `IranAppBypassHelper.kt` genuinely calls `builder.addDisallowedApplication(pkg)` for 82 Iranian domestic applications (including Nobitex, Up, Cafe Bazaar) and is genuinely integrated into `AsanVpnService.kt`.
2. `V2RayConfigBuilder.kt` genuinely routes `geosite:category-ir`, `geosite:ir`, `domain:ir`, and `geoip:ir` to direct outbound with `domainStrategy: "IPIfNonMatch"`.
3. `GeoAssetManager.kt` genuinely downloads, computes SHA256 hashes via `MessageDigest`, and atomically swaps assets with 24-hour throttling and APK fallback.
4. Clean compilation and packaging verified under JDK 17 (`BUILD SUCCESSFUL` for `compileDebugSources`, `testDebugUnitTest`, and `assembleDebug`).

Zero integrity violations detected. Milestone 2 is approved.

---

## 5. Verification Method

To independently verify this audit:

```powershell
# 1. Run the automated 32-assertion audit runner:
powershell -ExecutionPolicy Bypass -File "c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\auditor_m2_1\audit_runner.ps1"

# 2. Verify compilation, unit tests, and APK assembly with JDK 17:
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
.\gradlew.bat compileDebugSources --no-daemon
.\gradlew.bat testDebugUnitTest --no-daemon
.\gradlew.bat assembleDebug --no-daemon

# 3. Test Chocolate4Iran live CDN checksum responses:
curl.exe -sL "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geoip.dat.sha256sum"
curl.exe -sL "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat.sha256sum"
```

### Invalidation Conditions:
- Absence of Nobitex, Up, or Cafe Bazaar packages in `IranAppBypassHelper.kt`.
- Failure of `IranAppBypassHelper.applyDisallowedApplications` to invoke `builder.addDisallowedApplication(pkg)`.
- Omission of `geosite:category-ir`, `geosite:ir`, `domain:ir`, or `geoip:ir` from the direct routing rule in `V2RayConfigBuilder.kt`.
- Hardcoded hash returns or mock downloads in `GeoAssetManager.kt`.
- Any compilation or test failure under JDK 17.
