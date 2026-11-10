# Handoff Report — Milestone 2: Routing Correctness & Application Bypass Review

**Agent**: `reviewer_m2_1` (Reviewer & Critic)  
**Parent Orchestrator ID**: `4b000716-2a65-4da7-a250-c5ab7038a555`  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m2_1`  
**Timestamp**: `2026-11-10T03:09:00Z`  
**Type**: Hard Handoff  

---

## Review Summary

**Verdict**: **APPROVE**  
**Integrity Audit**: PASS (Zero integrity violations, zero facade implementations, zero hardcoded test shortcuts).  
**Build & Test Verification**: PASS (Both `compileDebugSources` and `testDebugUnitTest` passed cleanly with exit code 0 under JDK 17).  

---

## 1. Observation

### 1.1 `IranAppBypassHelper.kt` Package Catalog & Defensive Catch
- **File**: `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`
- **Lines 20–107**: Catalog of 66 package identifiers across 9 critical Iranian sectors:
  - Nobitex: `"app.nobitex"`, `"market.nobitex"`, `"ir.nobitex"` (all 3 package variants present)
  - Up / Asan Pardakht: `"com.sibche.aspardproject.app"`, `"ir.nasimpay.app"`, `"com.asanpardakht.app"` (all 3 variants present)
  - Cafe Bazaar: `"com.farsitel.bazaar"`
  - Other app stores: `"ir.mservices.market"` (Myket), `"com.charkhoneh.android"` (Charkhoneh)
  - Banking apps: 18 financial institutions including `"com.sb24.blubank"`, `"com.blubank"`, `"ir.bankmellat.mobile"`, `"ir.mellatbank.mobile"`, `"com.bmi.mobilebank"`, `"ir.bmi.bam"`, `"com.tejaratbank.tejaratmobile"`, `"ir.banksepah.mobile"`, `"com.bpi.app"`, `"com.sb24.mobilebank"`, `"com.bki.mobilebank"`, `"com.bankrefah.mobilebank"`, `"com.saderatbank.sepehri"`, `"com.maskan.mb"`, `"com.sinabank.mb"`, `"com.shahr.mb"`, `"com.ayandeh.mb"`, `"com.karafarinbank.mobile"`, `"com.parsian.mobile"`, `"ir.resalat.mb"`, `"ir.postbank.mb"`.
  - Payment apps: Hamrah Card (`ir.mizan.hamrahcard`), 724 (`ir.sep.android`), Top (`ir.pec.toptop`), Sekeh (`ir.behpardakht.sekeh`), Digipay (`com.digipay.app`), Iva (`com.sadadpsp.iva`).
  - Transport & Navigation: Snapp passenger/driver/box (`cab.snapp.passenger`, `cab.snapp.driver`, `cab.snapp.box`), SnappFood (`com.zoodfood.android`), Tapsi (`taxi.tap30.passenger`, `taxi.tap30.driver`), Maxim (`com.maximtaxi.client`), Neshan (`org.neshan.maps`), Balad (`ir.balad`).
  - Marketplaces: Divar (`ir.divar`), Digikala (`com.digikala.app`), Torob (`com.torob`, `ir.takhfifan.torob`), Basalam (`ir.basalam`), Sheypoor (`com.sheypoor.mobile`), Emalls (`com.emalls`), Bamilo (`com.bamilo.android`).
  - Messaging & Social: Rubika (`ir.resaneh1.iptv`), Bale (`ir.ble.messenger`), Eitaa (`ir.eitaa.messenger`), Soroush (`mobi.mm.msenger`, `mobi.mm.msenger.plus`), Gap (`ir.gap.messenger`), iGap (`net.iGap`), Shad (`ir.medu.shad`), Aparat (`com.aparat`).
  - Crypto exchanges: Wallex, AbanTether, Ramzinex, Bitpin, Sarmayex, Exir, Ompfinex, Tabdeal.
  - Streaming: Filimo, Namava, Filmnet, Telewebion, Taaghche, Fidibo.
- **Lines 118–132**: Defensive exception handling:
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
  `PackageManager.NameNotFoundException` is explicitly caught and ignored so absent packages never trigger an unhandled exception or crash the service. General `Exception` is also caught as a defense-in-depth measure.

### 1.2 `AsanVpnService.kt` Tunnel Registration
- **File**: `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
- **Lines 114–124**:
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
  `IranAppBypassHelper.applyDisallowedApplications(builder, this)` is called inside `startVpnTunnel` on `builder` prior to `builder.establish()`. Self-bypass (`packageName`) is also applied to prevent routing loops.

### 1.3 `V2RayConfigBuilder.kt` Direct Routing Rules & Domain Strategy
- **File**: `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`
- **Lines 144–187**:
  ```kotlin
  val routing = JsonObject().apply {
      addProperty("domainStrategy", "IPIfNonMatch")
      val rules = JsonArray().apply {
          // Rule 0: Hijack port 53 DNS queries to internal DNS engine
          add(JsonObject().apply {
              addProperty("type", "field")
              addProperty("outboundTag", "dns-out")
              addProperty("port", "53")
          })

          // Rule 1: Direct Iranian domains (Chocolate4Iran geosite rules)
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

          // Rule 2: Direct private LAN & Iran IP ranges (Chocolate4Iran geoip rules)
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
  ```
  - Rule 1 contains `"domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]` with `"outboundTag": "direct"`.
  - Rule 2 contains `"ip": ["geoip:private", "geoip:ir"]` with `"outboundTag": "direct"`.
  - `"domainStrategy": "IPIfNonMatch"` is configured at the routing root.
  - Outbounds section defines `"direct"` using `protocol: "freedom"` with `domainStrategy: "UseIP"` in settings and streamSettings.sockopt.

### 1.4 Compilation and Unit Tests with JDK 17
- **Tool**: `run_command`
- **Command 1**:
  `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`
  - **Result**: `BUILD SUCCESSFUL in 20s`, 15 actionable tasks, exit code 0.
- **Command 2**:
  `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat testDebugUnitTest --no-daemon`
  - **Result**: `BUILD SUCCESSFUL in 30s`, 21 actionable tasks, exit code 0.

---

## 2. Logic Chain

1. **Defense against Banking / Domestic Application Tunneling**:
   - From Observation 1.1, Iranian domestic banking and crypto exchanges enforce geofencing and flag or block connections originating from foreign VPN proxy IPs.
   - Calling `builder.addDisallowedApplication(pkg)` registers the application UID directly with Android's Linux network namespace routing tables. Packets from these applications bypass `/dev/tun` and route straight to cellular or Wi-Fi.
   - By iterating over `IRANIAN_PACKAGES` and catching `PackageManager.NameNotFoundException`, the method guarantees that uninstalled packages are safely ignored without throwing runtime exceptions.
   - From Observation 1.2, `AsanVpnService.kt` calls this helper before calling `builder.establish()`, ensuring the disallowed application list is fully populated before the tunnel interface is instantiated.

2. **Accurate Split-Tunneling Routing Rules**:
   - From Observation 1.3, `V2RayConfigBuilder.kt` defines Rule 1 for Iranian domains (`geosite:category-ir`, `geosite:ir`, `domain:ir`) and Rule 2 for Iranian and private IP addresses (`geoip:private`, `geoip:ir`), directing both to the `direct` outbound.
   - Using `"domainStrategy": "IPIfNonMatch"` guarantees that incoming connection requests are first matched against domain rules. If unmatched, the domain is resolved to an IP address by Xray's internal DNS resolver, and then checked against Rule 2's GeoIP rule before finally falling through to proxy egress.
   - Rule 0 directs DNS traffic on port 53 to `dns-out`, preventing DNS leakage and ensuring domain sniffing works correctly.

3. **Compilation and Integrity**:
   - From Observation 1.4, clean compilation and successful test execution confirm that all types, imports, package references, and build scripts are properly configured and aligned with JDK 17.
   - Zero shortcuts, dummy facade methods, or hardcoded mock results exist. The implementation interacts with real Android OS APIs (`VpnService.Builder`, `PackageManager`, `SharedPreferences`) and legitimate Xray configuration JSON specifications.

---

## 3. Caveats

- **Physical Device Runtime Testing**:
  - Headless/CLI Gradle compilation verifies source syntax, bytecode generation, and unit tests, but physical tunnel split-routing behaviour on actual devices depends on the device firmware's support for `VpnService.Builder.addDisallowedApplication` (supported natively on Android 5.0+ / API 21+).
- **Rule File Reload on Storage**:
  - When `GeoAssetManager` updates `geoip.dat` or `geosite.dat` on disk, active connections continue uninterrupted; updated routing definitions will take full effect upon reconnection or core reload.

---

## 4. Conclusion

The Milestone 2 deliverables meet all functional, interface contract, and adversarial criteria:
- `IranAppBypassHelper.kt` contains 66 package IDs across Nobitex, Up, Cafe Bazaar, banking, crypto, navigation, and domestic messengers. `PackageManager.NameNotFoundException` is defensively handled.
- `AsanVpnService.kt` invokes `IranAppBypassHelper.applyDisallowedApplications(builder, this)` prior to `builder.establish()`.
- `V2RayConfigBuilder.kt` configures direct routing for Iranian domains and IPs with `domainStrategy: "IPIfNonMatch"`.
- Clean compilation and test pass achieved under JDK 17.

**Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce this verification:

1. **Verify Compilation**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   .\gradlew.bat compileDebugSources --no-daemon
   ```
   *Pass Condition*: `BUILD SUCCESSFUL`, exit code 0.

2. **Verify Unit Tests**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   .\gradlew.bat testDebugUnitTest --no-daemon
   ```
   *Pass Condition*: `BUILD SUCCESSFUL`, exit code 0.

3. **Inspect Application Bypass List**:
   - Check `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt` lines 20–107.
   - Confirm Nobitex (`app.nobitex`, `market.nobitex`, `ir.nobitex`), Up (`com.sibche.aspardproject.app`, `ir.nasimpay.app`, `com.asanpardakht.app`), Cafe Bazaar (`com.farsitel.bazaar`), and banking packages.
   - Confirm lines 124–125 catch `PackageManager.NameNotFoundException`.

4. **Inspect VPN Service Integration**:
   - Check `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt` lines 122–124.
   - Confirm `IranAppBypassHelper.applyDisallowedApplications(builder, this)` is called immediately before `builder.establish()`.

5. **Inspect Xray Configuration Builder**:
   - Check `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt` lines 144–187.
   - Confirm Rule 1 (`geosite:category-ir`, `geosite:ir`, `domain:ir`), Rule 2 (`geoip:private`, `geoip:ir`), and `"domainStrategy": "IPIfNonMatch"`.
