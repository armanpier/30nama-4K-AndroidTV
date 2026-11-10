# Dispatch: Worker M2 — Iran Direct Bypass Routing & Chocolate4Iran Auto-Update

**Task**: Implement Milestone 2 (R2)
**Owned Files**:
- `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt` (NEW)
- `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt` (NEW)
- `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`
- `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
- `android/app/src/main/java/com/asanvpn/app/MainActivity.kt`
- `android/app/src/main/java/com/asanvpn/app/data/PreferencesManager.kt`

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

**Detailed Requirements**:
1. **Iranian App Package Bypass (`IranAppBypassHelper.kt` & `AsanVpnService.kt`)**:
   - Create `IranAppBypassHelper.kt` with a comprehensive list of Iranian application package identifiers (Nobitex: `app.nobitex`, `market.nobitex`, `ir.nobitex`; Up: `com.sibche.aspardproject.app`, `ir.nasimpay.app`, `com.asanpardakht.app`; Cafe Bazaar: `com.farsitel.bazaar`; Myket: `ir.mservices.market`; ride-hailing: Snapp, Tapsi; marketplaces: Divar, Digikala, Torob; messaging: Rubika, Bale, Eitaa; and 20+ banking apps including BluBank, Mellat, Melli, Tejarat, Pasargad, Saman, etc.).
   - Implement `fun applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int` safely catching `PackageManager.NameNotFoundException` so only installed packages are added and uninstalled ones are safely skipped without throwing exceptions.
   - In `AsanVpnService.kt`, call `IranAppBypassHelper.applyDisallowedApplications(builder, this)` inside `startVpnTunnel` after adding `packageName`.
2. **Iran Direct Bypass Routing (`V2RayConfigBuilder.kt`)**:
   - Update the routing rules in `buildConfig`:
     - Under Rule 1 (`outboundTag = "direct"`), configure `"domain"` with `["geosite:category-ir", "geosite:ir", "domain:ir"]`.
     - Under Rule 2 (`outboundTag = "direct"`), configure `"ip"` with `["geoip:private", "geoip:ir"]`.
     - Ensure `domainStrategy` remains `"IPIfNonMatch"`.
3. **Chocolate4Iran Auto-Update Mechanism (`GeoAssetManager.kt`, `PreferencesManager.kt`, `MainActivity.kt`)**:
   - In `PreferencesManager.kt`, add `lastGeoRulesCheckTime: Long` (backing key `"last_geo_rules_check_timestamp"`).
   - Create `GeoAssetManager.kt`:
     - `ensureAssetsInitialized(context)`: copies `geoip.dat` and `geosite.dat` from APK assets to `context.getDir("assets", Context.MODE_PRIVATE)` if missing.
     - `suspend fun checkAndUpdateRules(context: Context, force: Boolean = false): Result<Boolean>`:
       Checks remote SHA256 checksums from jsDelivr CDN (`https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/<asset>.sha256sum`) and GitHub Raw fallback.
       If remote SHA256 differs from local file SHA256 (or force=true), downloads the asset to a `.tmp` file, verifies the downloaded file's SHA256 matches the expected remote hash, and atomically replaces the asset file (`tempFile.renameTo(finalFile)`).
       Updates `lastGeoRulesCheckTime`.
   - In `MainActivity.kt`:
     - In `onCreate`, call `GeoAssetManager.ensureAssetsInitialized(applicationContext)`.
     - Launch a background coroutine to call `GeoAssetManager.checkAndUpdateRules(applicationContext, force = false)` after a short initial delay.
4. **Verification**:
   - Verify compilation with JDK 17:
     `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`
   - Write handoff report to:
     `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\handoff.md`.

## 2026-11-09T23:26:20Z
[Message] timestamp=2026-11-09T23:26:20Z sender=4b000716-2a65-4da7-a250-c5ab7038a555 priority=MESSAGE_PRIORITY_HIGH content=You are worker_m2, a worker implementation agent.
Your working directory is: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2
Your identity: worker_m2 (Worker)
Your parent orchestrator conversation ID is: 4b000716-2a65-4da7-a250-c5ab7038a555

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read ORIGINAL_REQUEST.md before starting work:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md

Read PROJECT.md:
c:\Users\Arman\Documents\antigravity\quirky-turing\PROJECT.md

Read your dispatch task:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\DISPATCH.md

Read the survey findings from Explorer 2:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2\handoff.md

Your exclusive write ownership is restricted to:
- `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`
- `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`
- `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`
- `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
- `android/app/src/main/java/com/asanvpn/app/MainActivity.kt`
- `android/app/src/main/java/com/asanvpn/app/data/PreferencesManager.kt`

Tasks to execute:
1. Create `IranAppBypassHelper.kt`:
   - Comprehensive package list of 50+ Iranian apps (Nobitex: app.nobitex, market.nobitex, ir.nobitex; Up: com.sibche.aspardproject.app, ir.nasimpay.app, com.asanpardakht.app; Cafe Bazaar: com.farsitel.bazaar; Myket: ir.mservices.market; Snapp, Tapsi, Neshan, Balad; Divar, Digikala, Torob; Rubika, Bale, Eitaa; BluBank, Mellat, Melli, Tejarat, Pasargad, Saman, etc.).
   - `applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int` catching `PackageManager.NameNotFoundException` per package.
2. In `AsanVpnService.kt`:
   - Call `IranAppBypassHelper.applyDisallowedApplications(builder, this)` inside `startVpnTunnel`.
3. In `V2RayConfigBuilder.kt`:
   - Under Rule 1 (direct domains), set `"domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]`.
   - Under Rule 2 (direct IPs), set `"ip": ["geoip:private", "geoip:ir"]`.
4. In `PreferencesManager.kt`:
   - Add property `lastGeoRulesCheckTime: Long`.
5. Create `GeoAssetManager.kt`:
   - `ensureAssetsInitialized(context: Context)` copying `geoip.dat` and `geosite.dat` from assets to internal `app_assets` directory if missing.
   - `suspend fun checkAndUpdateRules(context: Context, force: Boolean = false): Result<Boolean>`:
     Fetches remote SHA256 checksums from jsDelivr CDN (`https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/<asset>.sha256sum`) and GitHub Raw fallback.
     If checksum differs from local (or force=true), downloads to temporary `.tmp` file, verifies SHA256 matches, atomically renames to final asset file, and records timestamp in `PreferencesManager`.
6. In `MainActivity.kt`:
   - In `onCreate`, call `GeoAssetManager.ensureAssetsInitialized(applicationContext)`.
   - Launch background coroutine on `Dispatchers.IO` to run `GeoAssetManager.checkAndUpdateRules(applicationContext, force = false)` after a 5-second initial delay.
7. Verify compilation with JDK 17:
   `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`
   Verify exit code 0 and successful compilation.
8. Write your handoff report to:
   c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\handoff.md
9. Send message to parent orchestrator confirming completion.
