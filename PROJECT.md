# Project: AsanVPN Android Log Limiting, Iran Bypass Routing & Repo Parity

## Architecture
- **Logging Layer (`com.asanvpn.app.util.AppLogger`)**: In-memory dual-tier log buffer (`userLogs` and `adminLogs`) with strict runtime cap of 100 entries (`MAX_LOG_ENTRIES = 100`). Standardized `logLinkTest` formatting strictly outputting link remark, latency in ms, and success/failure status. Redaction of raw server JSON payloads, unmasked PINs, device IDs, and server IPs/ports.
- **Routing Engine (`com.asanvpn.app.service.v2ray.V2RayConfigBuilder` & `V2RayCoreManager`)**: Intercepts domestic Iran domains (`geosite:category-ir`, `geosite:ir`, `domain:ir`) and Iran IPs (`geoip:ir`, `geoip:private`) using `domainStrategy: "IPIfNonMatch"` and routes them to the `direct` outbound.
- **Application Tunnel Bypass (`com.asanvpn.app.util.IranAppBypassHelper` & `AsanVpnService`)**: Defensively registers Iranian applications (Nobitex, Up, Cafe Bazaar, and 50+ banking, transportation, and domestic packages) via `VpnService.Builder.addDisallowedApplication`, bypassing the Linux `/dev/tun` interface entirely.
- **Rule Auto-Updater (`com.asanvpn.app.util.GeoAssetManager`)**: Periodic, bandwidth-efficient SHA256 checksum polling against official `Chocolate4U/Iran-v2ray-rules` CDN/GitHub mirrors, with atomic file swap into `context.getDir("assets", Context.MODE_PRIVATE)`.
- **Repository Parity & Build System**: Strict 100% file tree and SHA-256 content parity between `quirky-turing\android` and `AsanVPN\android`. Deterministic Gradle 8.12 compilation for `assembleDebug` and `assembleRelease` using JDK 17 (`C:\Users\Arman\.jdks\jdk-17`).

## Code Layout
- `android/app/src/main/java/com/asanvpn/app/util/AppLogger.kt`: In-memory log buffer, 100-entry cap, link test formatting.
- `android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt`: Subscription sync, sensitive payload and credential redaction.
- `android/app/src/main/java/com/asanvpn/app/service/PingTester.kt`: Waterfall latency testing, sanitized link test reporting.
- `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`: Package catalog and defensive `addDisallowedApplication` registrant.
- `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`: Chocolate4Iran asset initializer, remote SHA256 checker, and atomic downloader.
- `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`: Xray JSON routing rules for `geosite:ir`, `geosite:category-ir`, `geoip:ir`.
- `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`: VpnService startup integrating Iranian app bypass.
- `android/app/src/main/java/com/asanvpn/app/MainActivity.kt`: Asset initialization and background update trigger on app launch.
- `android/app/src/main/java/com/asanvpn/app/data/PreferencesManager.kt`: Persistent timestamp tracking for rule update intervals.
- `android/app/src/main/assets/`: Bundled `geoip.dat` and `geosite.dat` rule databases.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | App Log Capping to 100 Entries | Cap in-memory log buffer (`userLogs` & `adminLogs`) to max 100 entries | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Sensitive Link Config Redaction | Redact full link JSON, raw credentials, IPs, ports, and worker URLs from logs | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Concise Link Test Progress & Result Formatting | Format link test entries to display only remark, delay in ms, and success/failure | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Iran Domain & IP Direct Bypass Routing | Direct outbound routing for `geosite:category-ir`, `geosite:ir`, `domain:ir`, and `geoip:ir` | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Iranian Application Package Bypass | Exclude Nobitex, Up, Cafe Bazaar, and domestic apps via `addDisallowedApplication` | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Chocolate4Iran Auto-Update Mechanism | Periodic background check and atomic SHA256-verified update of geoip/geosite assets | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Full Code & Resource Repository Parity | Maintain 100% file tree and SHA-256 match between `quirky-turing\android` and `AsanVPN\android` | M3 | ORIGINAL_REQUEST §R3 |
| 8 | JDK 17 Compilation Verification | Build clean `assembleDebug` and `assembleRelease` APKs on both repositories with JDK 17 | M3 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | App Log Capping & Concise Link Redaction | `AppLogger.kt`, `VpnRepository.kt`, `PingTester.kt`, `MainActivity.kt` | none | DONE |
| M2 | Iran Direct Bypass Routing & Chocolate4Iran Auto-Update | `IranAppBypassHelper.kt`, `GeoAssetManager.kt`, `V2RayConfigBuilder.kt`, `AsanVpnService.kt`, `MainActivity.kt`, assets | none | DONE |
| M3 | Repository Parity Synchronization & JDK 17 Builds | Synchronize `quirky-turing\android` to `AsanVPN\android`, build debug & release APKs | M1, M2 | DONE |
| M4 | Final Milestone & Comprehensive Verification Gate | Full verification suite, 2x Reviewers, 2x Challengers, Forensic Auditor | M1, M2, M3 | DONE |

## Interface Contracts

### AppLogger ↔ PingTester & VpnRepository
```kotlin
package com.asanvpn.app.util

object AppLogger {
    // Maximum log entries enforced strictly at 100
    private const val MAX_LOG_ENTRIES = 100

    @Synchronized
    fun logUser(message: String)

    @Synchronized
    fun logAdmin(message: String)

    // Formatted link test output visible to both user and admin
    @Synchronized
    fun logLinkTest(remark: String, latencyMs: Long, isSuccess: Boolean)

    fun getUserLog(): String
    fun getAdminLog(): String
    fun clear()
}
```

### IranAppBypassHelper ↔ AsanVpnService
```kotlin
package com.asanvpn.app.util

import android.content.Context
import android.net.VpnService

object IranAppBypassHelper {
    val IRANIAN_PACKAGES: List<String>
    // Defensively registers installed Iranian packages, catching NameNotFoundException
    fun applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int
}
```

### GeoAssetManager ↔ V2RayCoreManager & MainActivity
```kotlin
package com.asanvpn.app.util

import android.content.Context
import java.io.File

object GeoAssetManager {
    fun getAssetDir(context: Context): File
    fun ensureAssetsInitialized(context: Context)
    // Checks remote sha256, downloads to temp file, verifies sha256, and atomically replaces asset
    suspend fun checkAndUpdateRules(context: Context, force: Boolean = false): Result<Boolean>
}
```
