# Handoff Report — Explorer Survey 2: Iran IP/Domain/App Routing Bypass & Chocolate4Iran Rule Updating

**Agent**: `explorer_survey_2` (Explorer)  
**Parent Conversation ID**: `4b000716-2a65-4da7-a250-c5ab7038a555`  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2`  
**Timestamp**: `2026-11-09T22:52:00Z`  
**Type**: Hard Handoff  

---

## 1. Observation

### 1.1 Existing Routing Configuration in `quirky-turing`
In `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\service\v2ray\V2RayConfigBuilder.kt`:
Lines 144 to 194:
```kotlin
// 5. Routing: Iran split tunneling + general proxy
val routing = JsonObject().apply {
    addProperty("domainStrategy", "IPIfNonMatch")
    val rules = JsonArray().apply {
        // Rule 0: Hijack port 53 DNS queries to internal DNS engine
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "dns-out")
            addProperty("port", "53")
        })

        // Rule 1: Direct Iranian domains
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "direct")
            val domainArr = JsonArray().apply {
                add("domain:ir")
                add("domain:shaparak.ir")
                add("domain:blubank.sb24.ir")
                add("domain:divar.ir")
                add("domain:snapp.ir")
                add("domain:torob.com")
                add("domain:digikala.com")
                add("domain:rubika.ir")
                add("domain:bale.ai")
                add("domain:eitaa.com")
            }
            add("domain", domainArr)
        })

        // Rule 2: Direct private LAN
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "direct")
            val ipArr = JsonArray().apply {
                add("geoip:private")
            }
            add("ip", ipArr)
        })

        // Rule 3: All other TCP & UDP -> proxy
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "proxy")
            addProperty("network", "tcp,udp")
        })
    }
    add("rules", rules)
}
```
**Direct Observation**:
1. `Rule 1` lists only 10 hardcoded domains. It lacks `geosite:ir` and `geosite:category-ir`.
2. `Rule 2` only checks `geoip:private`. It completely lacks `geoip:ir`.
3. Consequently, any Iranian service hosted outside those 10 domains or accessed by domestic IP is routed through the proxy outbound.

### 1.2 Asset Bundling and Runtime Core Loading
In `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\service\v2ray\V2RayCoreManager.kt`:
Lines 42 to 51:
```kotlin
Seq.setContext(context.applicationContext)
val assetDir = context.getDir("assets", Context.MODE_PRIVATE)

// Copy geoip.dat & geosite.dat from apk assets if missing
copyAssetIfMissing(context, "geoip.dat", assetDir)
copyAssetIfMissing(context, "geosite.dat", assetDir)

Libv2ray.initCoreEnv(assetDir.absolutePath, "")
Log.i(TAG, "V2Ray Core Env Initialized: ${Libv2ray.checkVersionX()}")
```
And lines 58 to 72:
```kotlin
private fun copyAssetIfMissing(context: Context, fileName: String, targetDir: File) {
    val targetFile = File(targetDir, fileName)
    if (!targetFile.exists() || targetFile.length() == 0L) {
        try {
            context.assets.open(fileName).use { input ->
                FileOutputStream(targetFile).use { output ->
                    input.copyTo(output)
                }
            }
            Log.i(TAG, "Copied asset $fileName to ${targetFile.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Could not copy asset $fileName: ${e.message}")
        }
    }
}
```
**Direct Observation**:
1. Runtime assets are loaded from `context.getDir("assets", Context.MODE_PRIVATE)` (`/data/user/0/com.asanvpn.app/app_assets`), which is a writable directory on internal app storage.
2. `copyAssetIfMissing` only copies from APK `assets/` if the destination file does not exist or has 0 bytes. It does not update existing files when updated in APK or remotely.
3. Bundled assets in `app/src/main/assets/`:
   - `geoip.dat`: 18,534,419 bytes (SHA256: `7806115947F8A704D347FA103AA83AADC2CD531A72B82C44D991D598AC23EAE9`)
   - `geosite.dat`: 8,659,692 bytes (SHA256: `725397E93D0043146973220C106EB7E53CCBFD39508A63389E9FA0F7D616C06D`)
   - String verification on bundled `geosite.dat`: `category-ir` is `False`, `ir` is `True`. The currently bundled `geosite.dat` is generic v2fly, not Chocolate4Iran!
4. An unreferenced asset file exists at `app/src/main/assets/custom_routing_white_iran` (lines 23 to 36):
   ```json
   {
     "remarks": "Bypass Iran domains",
     "outboundTag": "direct",
     "domain": [
       "domain:ir",
       "geosite:category-ir"
     ]
   },
   {
     "remarks": "Bypass Iran IP",
     "outboundTag": "direct",
     "ip": [
        "geoip:ir"
     ]
   }
   ```
   This confirms that `geosite:category-ir` and `geoip:ir` were intended for Iranian bypass.

### 1.3 VpnService Tunnel Configuration & Application Bypass
In `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\service\AsanVpnService.kt`:
Lines 105 to 119:
```kotlin
val builder = Builder()
    .setSession("آسان وی‌پی‌ان")
    .setMtu(1500)
    .addAddress("172.19.0.1", 30)
    .addDnsServer("1.1.1.1")
    .addDnsServer("8.8.8.8")
    .addRoute("0.0.0.0", 0)

try {
    // Allow this application process to bypass the tunnel so Xray outbound connections don't loop
    builder.addDisallowedApplication(packageName)
} catch (e: Exception) {
    Log.w("AsanVpnService", "Could not set addDisallowedApplication: ${e.message}")
}
```
**Direct Observation**:
1. `builder.addDisallowedApplication(packageName)` is currently called only for `AsanVPN` itself.
2. Iranian applications (Nobitex, Up, Cafe Bazaar, banking apps, etc.) are NOT currently added to `addDisallowedApplication`.
3. In Android `VpnService.Builder`, `addDisallowedApplication(String packageName)` throws `PackageManager.NameNotFoundException` if the package is not installed on the user's device. Each addition must be wrapped in `try { ... } catch (e: PackageManager.NameNotFoundException) { ... }`.

### 1.4 Chocolate4Iran (`Chocolate4U/Iran-v2ray-rules`) Repository & Endpoints
Verified live via direct HTTP queries:
1. Latest release tag: `202611091318` (released 2026-11-09T13:19:29Z).
2. Assets published per release:
   - `geoip.dat` (~16,475,447 bytes) + `geoip.dat.sha256sum` (84 bytes)
   - `geosite.dat` (~8,467,156 bytes) + `geosite.dat.sha256sum` (86 bytes)
   - `geoip-lite.dat` (~37,658 bytes) + `geoip-lite.dat.sha256sum` (89 bytes)
   - `geosite-lite.dat` (~1,954,260 bytes) + `geosite-lite.dat.sha256sum` (91 bytes)
3. Direct download URLs on `release` branch:
   - Primary jsDelivr CDN mirror (fast, unthrottled, no rate limit in Iran):
     - `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geoip.dat`
     - `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat`
     - `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geoip.dat.sha256sum`
     - `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat.sha256sum`
   - GitHub raw fallback:
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geoip.dat`
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geosite.dat`
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geoip.dat.sha256sum`
     - `https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geosite.dat.sha256sum`
   - GitHub Releases API: `https://api.github.com/repos/Chocolate4U/Iran-v2ray-rules/releases/latest`
4. Sha256sum file content format:
   `1c9d2b84856ce4674fdb7e94c03b74cadb7374a17d69d3f9c6bbfa3703e13018  release/geoip.dat`
   (64-character hex hash followed by space and filename).
5. Categories provided by Chocolate4Iran:
   - `geoip:ir`: All Iran IP allocations (MaxMind + IP2Location) + domestic messengers (`eitaa`, `rubika`) + local CDNs (`arvancloud`, `derakcloud`, `iranserver`, `parspack`).
   - `geoip:private`: RFC1918 LAN addresses.
   - `geosite:ir`: Non-.ir TLD Iranian domains + all `.ir` domains.
   - `geosite:category-ir`: Mirror of `geosite:ir` with dead/inactive domains pruned daily.

### 1.5 Target Iranian Application Package Identifiers
Verified package names for required and standard Iranian apps:
- **Cafe Bazaar (کافه بازار)**: `com.farsitel.bazaar`
- **Up (آپ / آسان پرداخت)**: `com.sibche.aspardproject.app` (primary), `ir.nasimpay.app`, `com.asanpardakht.app`
- **Nobitex (نوبیتکس)**: `app.nobitex` (primary), `market.nobitex` (Bazaar release), `ir.nobitex`
- **Myket (مایکت)**: `ir.mservices.market`
- **Ride Hailing & Logistics**:
  - Snapp: `cab.snapp.passenger`, `cab.snapp.driver`
  - SnappFood: `com.zoodfood.android`
  - SnappBox: `cab.snapp.box`
  - Tapsi: `taxi.tap30.passenger`, `taxi.tap30.driver`
- **Marketplaces**: `ir.divar`, `com.digikala.app`, `com.torob`, `ir.takhfifan.torob`, `ir.basalam`, `com.sheypoor.mobile`, `com.emalls`
- **Messengers & Social**: `ir.resaneh1.iptv` (Rubika), `ir.ble.messenger` (Bale), `ir.eitaa.messenger` (Eitaa), `mobi.mm.msenger` (Soroush), `ir.gap.messenger` (Gap), `net.iGap`, `ir.medu.shad` (Shad)
- **Navigation**: `org.neshan.maps`, `ir.balad`
- **Telecom**: `ir.mci.ecareapp` (Hamrah-e Aval), `ir.mtn.irancell` (Irancell), `ir.rightel.myrightel` (Rightel)
- **Banking & Fintech**: `com.sb24.blubank`, `com.blubank`, `ir.bankmellat.mobile`, `ir.mellatbank.mobile`, `com.bmi.mobilebank`, `ir.bmi.bam`, `com.tejaratbank.tejaratmobile`, `ir.banksepah.mobile`, `com.bpi.app` (Pasargad), `com.sb24.mobilebank` (Saman), `com.bki.mobilebank` (Keshavarzi), `com.bankrefah.mobilebank`, `com.saderatbank.sepehri`, `com.maskan.mb`, `ir.mizan.hamrahcard`, `ir.sep.android` (724), `ir.pec.toptop` (Top), `ir.behpardakht.sekeh` (Sekeh), `com.digipay.app`
- **Streaming & Media**: `com.greenweb.filimo`, `ir.shatel.namava`, `com.filmnet`, `com.aparat`, `simayehamrah.android` (Telewebion), `ir.mservices.taaghche`, `com.fidibo.reader`

### 1.6 Build Verification
Running `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; .\gradlew tasks --dry-run` in `android`:
Result: `BUILD SUCCESSFUL in 24s`.

---

## 2. Logic Chain

1. **Why Iranian apps break on VPN**:
   - Many Iranian banking and crypto platforms (e.g. Nobitex, Up, BluBank, Mellat) block or suspend accounts when requests originate from foreign IP ranges or VPN tunnels due to central bank (CBI / Shaparak) security policies and sanctions compliance.
   - If packets enter the VPN interface, even direct routing within Xray does not prevent apps from detecting an active VPN network interface or experiencing TLS SNI blocking.
   - **Resolution**: Using Android `VpnService.Builder.addDisallowedApplication` disallows the app UID at the Linux kernel network table level. Packets from Nobitex, Up, Cafe Bazaar, and banking apps leave the device directly through the physical cellular or Wi-Fi interface, never entering `/dev/tun`.

2. **Why `addDisallowedApplication` requires defensive iteration**:
   - `VpnService.Builder.addDisallowedApplication(packageName)` calls `PackageManager.getPackageUid(packageName, 0)`.
   - If the package is not installed, it throws `PackageManager.NameNotFoundException`. If unhandled, this crashes the VPN startup.
   - Wrapping each package addition in a `try-catch` allows the app to maintain a comprehensive list of 50+ Iranian apps while safely applying bypass only to the apps actually present on the user's phone.

3. **Why Xray routing rules must include both `geoip:ir` and `geosite:ir` / `geosite:category-ir`**:
   - Android apps not on the disallowed list, browser tabs (Chrome, Firefox), and background webviews frequently visit Iranian websites (`.ir`, `.com`, `.org`) or Iranian API servers.
   - In `V2RayConfigBuilder.kt`, currently only 10 domains are hardcoded in `domainArr`, and NO `geoip:ir` rule exists in `ipArr`.
   - By adding `"geosite:ir"`, `"geosite:category-ir"`, and `"domain:ir"` to the direct domain rule, and adding `"geoip:ir"` to the direct IP rule with `domainStrategy: "IPIfNonMatch"`, all domestic traffic is intercepted by Xray and routed directly via `freedom` outbound without consuming proxy traffic or exposing users to regional blocking.

4. **Why Chocolate4Iran rule assets must be auto-updated**:
   - Iranian IP allocations change frequently as domestic CDNs (ArvanCloud, Derak, IranServer, ParsPack) expand and mobile carriers allocate new CIDRs.
   - Domain blocking and mirror reconfigurations happen daily in Iran.
   - Chocolate4Iran compiles and publishes updated `geoip.dat` and `geosite.dat` releases every 1 to 3 days.
   - Storing assets in `context.getDir("assets", Context.MODE_PRIVATE)` (`app_assets`) allows writing updated files without requiring APK updates or elevated permissions.

5. **Why checksum checking is superior to direct asset downloading**:
   - Full `geoip.dat` is ~16.5 MB and `geosite.dat` is ~8.5 MB (total ~25 MB).
   - Downloading 25 MB on every app launch would consume massive cellular bandwidth and battery.
   - Checking `geoip.dat.sha256sum` and `geosite.dat.sha256sum` costs only ~170 bytes.
   - The app only initiates the full download when the remote SHA256 differs from the locally stored SHA256.
   - Furthermore, verifying SHA256 before atomic replacement ensures incomplete or corrupted downloads are never loaded by the Xray core.

---

## 3. Caveats

1. **Lite vs Full Assets**:
   - Chocolate4Iran provides both full (`geoip.dat` 16.5MB, `geosite.dat` 8.5MB) and lite (`geoip-lite.dat` 37KB, `geosite-lite.dat` 1.95MB).
   - While `geoip-lite.dat` only contains `geoip:ir` and `geoip:private` (which perfectly matches our routing rules), libv2ray expects the file to be named `geoip.dat`.
   - Using full `geoip.dat` and `geosite.dat` preserves standard Xray compatibility if users or admins ever add rules referencing other categories.
2. **First-run without internet**:
   - If an initial install runs offline before any auto-update, bundled assets in the APK are used as baseline.
   - Bundling current Chocolate4Iran `geoip.dat` and `geosite.dat` directly into `app/src/main/assets/` guarantees that initial installs have up-to-date Iranian routing out of the box even before the first update cycle.
3. **Running VPN during asset replacement**:
   - If `geoip.dat` / `geosite.dat` files in `app_assets` are replaced while the VPN is actively running, existing sockets continue unaffected.
   - To avoid file corruption or read contention, updates must download to `.tmp` files, verify checksums, and atomically rename (`tmpFile.renameTo(targetFile)`).
   - The new routing definitions will be loaded upon next connection or configuration switch.

---

## 4. Conclusion & Recommended Implementation Strategy

### 4.1 Component 1: Iranian Application Bypass Helper (`IranAppBypassHelper.kt`)
Create `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\util\IranAppBypassHelper.kt`:
```kotlin
package com.asanvpn.app.util

import android.content.Context
import android.content.pm.PackageManager
import android.net.VpnService
import android.util.Log

object IranAppBypassHelper {

    private const val TAG = "IranAppBypass"

    val IRANIAN_PACKAGES = listOf(
        // Required & Top Iranian Apps
        "app.nobitex", "market.nobitex", "ir.nobitex",               // Nobitex (نوبیتکس)
        "com.sibche.aspardproject.app", "ir.nasimpay.app", "com.asanpardakht.app", // Up (آپ - آسان پرداخت)
        "com.farsitel.bazaar",                                      // Cafe Bazaar (کافه بازار)
        "ir.mservices.market",                                      // Myket (مایکت)

        // Ride-Hailing, Delivery & Logistics
        "cab.snapp.passenger", "cab.snapp.driver", "cab.snapp.box", // Snapp (اسنپ)
        "com.zoodfood.android",                                     // SnappFood (اسنپ فود)
        "taxi.tap30.passenger", "taxi.tap30.driver",                // Tapsi (تپسی)
        "org.neshan.maps", "ir.balad",                              // Neshan & Balad (نشان و بلد)

        // E-Commerce & Marketplaces
        "ir.divar", "com.digikala.app", "com.torob",                // Divar, Digikala, Torob (دیوار، دیجی‌کالا، ترب)
        "ir.takhfifan.torob", "ir.basalam", "com.sheypoor.mobile", "com.emalls",

        // Messengers & Social Media
        "ir.resaneh1.iptv",                                         // Rubika (روبیکا)
        "ir.ble.messenger",                                         // Bale (بله)
        "ir.eitaa.messenger",                                       // Eitaa (ایتا)
        "mobi.mm.msenger", "ir.gap.messenger", "net.iGap", "ir.medu.shad",

        // Telecom Operators
        "ir.mci.ecareapp", "ir.mtn.irancell", "ir.rightel.myrightel", "com.shatel.my",

        // Banking & Payment Apps
        "com.sb24.blubank", "com.blubank",                          // BluBank (بلو بانک)
        "ir.bankmellat.mobile", "ir.mellatbank.mobile",             // Bank Mellat (بانک ملت)
        "com.bmi.mobilebank", "ir.bmi.bam",                         // Bank Melli / BAM (بانک ملی)
        "com.tejaratbank.tejaratmobile",                            // Bank Tejarat (بانک تجارت)
        "ir.banksepah.mobile",                                      // Bank Sepah (بانک سپه)
        "com.bpi.app",                                              // Bank Pasargad (بانک پاسارگاد)
        "com.sb24.mobilebank",                                      // Bank Saman (بانک سامان)
        "com.bki.mobilebank", "com.bankrefah.mobilebank",
        "com.saderatbank.sepehri", "com.maskan.mb", "com.sinabank.mb", "com.shahr.mb",
        "ir.mizan.hamrahcard",                                      // Hamrah Card (همراه کارت)
        "ir.sep.android", "ir.pec.toptop", "ir.behpardakht.sekeh", "com.digipay.app",

        // Streaming & Media
        "com.greenweb.filimo", "ir.shatel.namava", "com.filmnet", "com.aparat",
        "simayehamrah.android", "ir.mservices.taaghche", "com.fidibo.reader"
    )

    fun applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int {
        var bypassedCount = 0
        for (pkg in IRANIAN_PACKAGES) {
            try {
                builder.addDisallowedApplication(pkg)
                bypassedCount++
            } catch (e: PackageManager.NameNotFoundException) {
                // Not installed on user device, safely skip
            } catch (e: Exception) {
                Log.w(TAG, "Failed to disallow package $pkg: ${e.message}")
            }
        }
        Log.i(TAG, "Successfully bypassed $bypassedCount Iranian applications from VPN tunnel")
        return bypassedCount
    }
}
```

### 4.2 Component 2: V2Ray Routing Configuration (`V2RayConfigBuilder.kt`)
Update `V2RayConfigBuilder.kt` lines 144 to 194 to:
```kotlin
// 5. Routing: Iran split tunneling + general proxy
val routing = JsonObject().apply {
    addProperty("domainStrategy", "IPIfNonMatch")
    val rules = JsonArray().apply {
        // Rule 0: Hijack port 53 DNS queries to internal DNS engine
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "dns-out")
            addProperty("port", "53")
        })

        // Rule 1: Direct Iranian domains (Chocolate4Iran Geosite rules)
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "direct")
            val domainArr = JsonArray().apply {
                add("geosite:category-ir")
                add("geosite:ir")
                add("domain:ir")
            }
            add("domain", domainArr)
        })

        // Rule 2: Direct private LAN & Iran IP ranges (Chocolate4Iran GeoIP rules)
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "direct")
            val ipArr = JsonArray().apply {
                add("geoip:private")
                add("geoip:ir")
            }
            add("ip", ipArr)
        })

        // Rule 3: All other TCP & UDP -> proxy
        add(JsonObject().apply {
            addProperty("type", "field")
            addProperty("outboundTag", "proxy")
            addProperty("network", "tcp,udp")
        })
    }
    add("rules", rules)
}
root.add("routing", routing)
```

### 4.3 Component 3: Chocolate4Iran Rule Asset Manager (`GeoAssetManager.kt`)
Create `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt`:
```kotlin
package com.asanvpn.app.util

import android.content.Context
import android.util.Log
import com.asanvpn.app.data.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

object GeoAssetManager {

    private const val TAG = "GeoAssetManager"

    // Primary jsDelivr CDN mirrors (fast and accessible in Iran)
    private const val JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release"
    // GitHub Raw fallback
    private const val GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release"

    private val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .followRedirects(true)
            .build()
    }

    fun getAssetDir(context: Context): File = context.getDir("assets", Context.MODE_PRIVATE)

    /**
     * Copies APK bundled assets if missing or on fresh install.
     */
    fun ensureAssetsInitialized(context: Context) {
        val assetDir = getAssetDir(context)
        copyAssetIfMissing(context, "geoip.dat", assetDir)
        copyAssetIfMissing(context, "geosite.dat", assetDir)
    }

    private fun copyAssetIfMissing(context: Context, fileName: String, targetDir: File) {
        val targetFile = File(targetDir, fileName)
        if (!targetFile.exists() || targetFile.length() == 0L) {
            try {
                context.assets.open(fileName).use { input ->
                    FileOutputStream(targetFile).use { output ->
                        input.copyTo(output)
                    }
                }
                Log.i(TAG, "Copied asset $fileName to ${targetFile.absolutePath}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed copying asset $fileName: ${e.message}")
            }
        }
    }

    /**
     * Checks remote chocolate4iran SHA256 checksums and updates assets if newer version is released.
     */
    suspend fun checkAndUpdateRules(context: Context, force: Boolean = false): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val prefs = PreferencesManager(context)
            val now = System.currentTimeMillis()

            // Throttle checks to once every 24 hours unless forced
            if (!force && (now - prefs.lastGeoRulesCheckTime < 24 * 3600 * 1000L)) {
                return@withContext Result.success(false)
            }

            val assetDir = getAssetDir(context)
            var updated = false

            for (assetName in listOf("geoip.dat", "geosite.dat")) {
                val targetFile = File(assetDir, assetName)
                val currentHash = if (targetFile.exists()) computeSha256(targetFile) else ""
                val remoteHash = fetchRemoteChecksum(assetName)

                if (remoteHash != null && (remoteHash.lowercase() != currentHash.lowercase() || force)) {
                    Log.i(TAG, "Update available for $assetName: local=$currentHash, remote=$remoteHash")
                    val downloaded = downloadAndVerifyAsset(assetName, remoteHash, assetDir)
                    if (downloaded) {
                        updated = true
                    }
                }
            }

            prefs.lastGeoRulesCheckTime = now
            Result.success(updated)
        } catch (e: Exception) {
            Log.e(TAG, "Error checking/updating chocolate4iran rules", e)
            Result.failure(e)
        }
    }

    private fun fetchRemoteChecksum(assetName: String): String? {
        val checkUrls = listOf(
            "$JSDELIVR_BASE/$assetName.sha256sum",
            "$GITHUB_RAW_BASE/$assetName.sha256sum"
        )
        for (url in checkUrls) {
            try {
                val request = Request.Builder().url(url).header("User-Agent", "AsanVPN-RulesSync").build()
                httpClient.newCall(request).execute().use { resp ->
                    if (resp.isSuccessful) {
                        val body = resp.body?.string()?.trim() ?: ""
                        val hash = body.split(Regex("\\s+")).firstOrNull()?.trim()
                        if (!hash.isNullOrBlank() && hash.length == 64) {
                            return hash
                        }
                    }
                }
            } catch (e: Exception) {
                // Try next mirror
            }
        }
        return null
    }

    private fun downloadAndVerifyAsset(assetName: String, expectedHash: String, targetDir: File): Boolean {
        val downloadUrls = listOf(
            "$JSDELIVR_BASE/$assetName",
            "$GITHUB_RAW_BASE/$assetName"
        )
        val tempFile = File(targetDir, "$assetName.tmp")
        val finalFile = File(targetDir, assetName)

        for (url in downloadUrls) {
            try {
                if (tempFile.exists()) tempFile.delete()

                val request = Request.Builder().url(url).header("User-Agent", "AsanVPN-RulesSync").build()
                httpClient.newCall(request).execute().use { resp ->
                    if (resp.isSuccessful) {
                        resp.body?.byteStream()?.use { input ->
                            FileOutputStream(tempFile).use { output ->
                                input.copyTo(output)
                            }
                        }
                    }
                }

                if (tempFile.exists() && tempFile.length() > 0) {
                    val actualHash = computeSha256(tempFile)
                    if (actualHash.equals(expectedHash, ignoreCase = true)) {
                        if (finalFile.exists()) finalFile.delete()
                        val renamed = tempFile.renameTo(finalFile)
                        if (renamed) {
                            Log.i(TAG, "Successfully updated $assetName to latest version ($actualHash)")
                            return true
                        }
                    } else {
                        Log.w(TAG, "Checksum mismatch for $assetName: expected $expectedHash, got $actualHash")
                        tempFile.delete()
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed downloading $assetName from $url: ${e.message}")
            }
        }
        return false
    }

    private fun computeSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buf = ByteArray(8192)
            var bytesRead: Int
            while (input.read(buf).also { bytesRead = it } != -1) {
                digest.update(buf, 0, bytesRead)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
```

### 4.4 Component 4: Integration in `PreferencesManager.kt`
Add tracking preferences in `PreferencesManager.kt`:
```kotlin
private const val KEY_LAST_GEO_RULES_CHECK = "last_geo_rules_check_timestamp"

var lastGeoRulesCheckTime: Long
    get() = prefs.getLong(KEY_LAST_GEO_RULES_CHECK, 0L)
    set(value) = prefs.edit().putLong(KEY_LAST_GEO_RULES_CHECK, value).apply()
```

### 4.5 Component 5: Integration in `AsanVpnService.kt`
In `startVpnTunnel`:
```kotlin
// 1. Bypass AsanVPN process
builder.addDisallowedApplication(packageName)

// 2. Bypass Iranian applications (Nobitex, Up, Cafe Bazaar, banking, etc.)
IranAppBypassHelper.applyDisallowedApplications(builder, this)
```

### 4.6 Component 6: Integration in `MainActivity.kt`
In `onCreate`:
```kotlin
// Ensure assets initialized
GeoAssetManager.ensureAssetsInitialized(applicationContext)

// Trigger periodic background chocolate4iran rules update check
lifecycleScope.launch(Dispatchers.IO) {
    kotlinx.coroutines.delay(5000L)
    GeoAssetManager.checkAndUpdateRules(applicationContext, force = false)
}
```

### 4.7 Component 7: Repository Parity & Bundled Assets
1. Fetch and bundle the latest official Chocolate4Iran `geoip.dat` and `geosite.dat` into both:
   - `c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\assets\`
   - `C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\src\main\assets\`
2. Keep identical implementation files between both repositories.

---

## 5. Verification Method

To independently verify the implementation:

1. **Gradle Compilation Verification**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   cd "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   .\gradlew assembleDebug --stacktrace
   ```
   **Pass Condition**: Build completes with exit code 0 and generated APK in `app/build/outputs/apk/debug/`.

2. **Routing Rules JSON Verification**:
   Inspect the JSON output generated by `V2RayConfigBuilder.buildConfig(node)`:
   - Verify `"routing"."rules"` contains `"domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]` mapped to `"outboundTag": "direct"`.
   - Verify `"routing"."rules"` contains `"ip": ["geoip:private", "geoip:ir"]` mapped to `"outboundTag": "direct"`.

3. **Per-App Bypass Verification**:
   - Install the APK on an Android test device or emulator.
   - Inspect logcat: `adb logcat -s IranAppBypass AsanVpnService`
   - Verify log message: `Successfully bypassed X Iranian applications from VPN tunnel`.
   - Check with Nobitex or Up installed: traffic routes directly without VPN IP or connection errors.

4. **Asset Update Verification**:
   - Run unit test or trigger `GeoAssetManager.checkAndUpdateRules(context, force = true)`.
   - Verify network request to `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geoip.dat.sha256sum`.
   - Verify SHA256 checksum comparison and successful atomic write to `context.getDir("assets", Context.MODE_PRIVATE)`.

5. **Repository Parity Verification**:
   ```powershell
   Compare-Object -ReferenceObject (Get-ChildItem -Path "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src\main\java" -Recurse) -DifferenceObject (Get-ChildItem -Path "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\src\main\java" -Recurse)
   ```
   **Pass Condition**: Zero file differences between `quirky-turing` and `AsanVPN`.
