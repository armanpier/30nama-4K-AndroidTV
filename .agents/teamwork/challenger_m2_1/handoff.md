# Empirical Adversarial Challenge Report — Milestone 2: Routing Rules & Application Bypass

**Challenger**: `challenger_m2_1`  
**Milestone**: Milestone 2 (Iran Direct Bypass Routing & Chocolate4Iran Auto-Update)  
**Verdict**: **APPROVE**  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\challenger_m2_1`  
**Date**: 2026-11-09T23:45:00Z  

---

## 1. Observation

### 1.1 Target Source Implementations
1. **`android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`**:
   - **Line 146**: Domain resolution strategy strictly configured:
     ```kotlin
     addProperty("domainStrategy", "IPIfNonMatch")
     ```
   - **Lines 148–154 (Rule 0)**: DNS query redirection to internal resolver:
     ```kotlin
     add(JsonObject().apply {
         addProperty("type", "field")
         addProperty("outboundTag", "dns-out")
         addProperty("port", "53")
     })
     ```
   - **Lines 156–165 (Rule 1)**: Direct Iranian domain routing via Chocolate4Iran geosite assets:
     ```kotlin
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
     ```
   - **Lines 167–176 (Rule 2)**: Direct private and domestic IP routing via Chocolate4Iran geoip assets:
     ```kotlin
     add(JsonObject().apply {
         addProperty("type", "field")
         addProperty("outboundTag", "direct")
         val ipArr = JsonArray().apply {
             add("geoip:private")
             add("geoip:ir")
         }
         add("ip", ipArr)
     })
     ```
   - **Lines 178–184 (Rule 3)**: Fallback outbound rule routing remaining TCP/UDP traffic to proxy:
     ```kotlin
     add(JsonObject().apply {
         addProperty("type", "field")
         addProperty("outboundTag", "proxy")
         addProperty("network", "tcp,udp")
     })
     ```
   - **Lines 109–120**: `direct` outbound configured with protocol `freedom` and `domainStrategy: "UseIP"`.

2. **`android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`**:
   - **Lines 20–107**: `IRANIAN_PACKAGES` defines 82 domestic package identifiers covering banking, cryptocurrency exchanges, ride-hailing, e-commerce, messengers, telecom, and streaming platforms.
   - Required packages from `DISPATCH.md` and `ORIGINAL_REQUEST.md` confirmed present:
     - Line 22: `"app.nobitex"` (Nobitex crypto)
     - Line 33: `"com.sibche.aspardproject.app"` (Asan Pardakht / Up)
     - Line 42: `"com.farsitel.bazaar"` (Cafe Bazaar)
   - **Lines 118–132**: `applyDisallowedApplications(builder: VpnService.Builder, context: Context): Int`:
     ```kotlin
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
     ```

3. **`android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`**:
   - **Line 122**: Calls `IranAppBypassHelper.applyDisallowedApplications(builder, this)` immediately before `builder.establish()`, ensuring all installed Iranian apps bypass the tunnel interface.

---

### 1.2 Empirical Test Execution & Results
A dedicated adversarial test harness was authored and compiled under `android/app/src/test/java/com/asanvpn/app/M2RoutingAndBypassEmpiricalTest.java` and executed with JDK 17:

```
===================================================================
  STARTING M2 ROUTING & APP BYPASS EMPIRICAL ADVERSARIAL TEST      
===================================================================

--- TEST 1: Standard V2RayConfigBuilder Routing Rules Verification ---
[PASS] ConfigJsonNotEmpty: Generated JSON must not be empty
[PASS] HasRoutingSection: Root JSON must contain 'routing' object
[PASS] DomainStrategyExactMatch: routing.domainStrategy must strictly equal 'IPIfNonMatch' (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] HasRulesArray: Routing must contain 'rules' array
[PASS] RulesCountAtLeast4: Rules must contain at least 4 rules (dns, iran-domain, iran-ip, proxy-fallback)
[PASS] Rule0Type: Rule 0 type (expected: field, got: field)
[PASS] Rule0OutboundTag: Rule 0 outboundTag (expected: dns-out, got: dns-out)
[PASS] Rule0Port: Rule 0 port (expected: 53, got: 53)
[PASS] Rule1Type: Rule 1 type (expected: field, got: field)
[PASS] Rule1OutboundTag: Rule 1 outboundTag (expected: direct, got: direct)
[PASS] Rule1HasDomain: Rule 1 must have 'domain' array
[PASS] Rule1DomainCount: Rule 1 domain list must have exactly 3 entries (expected: 3, got: 3)
[PASS] Rule1ContainsGeositeCategoryIr: Rule 1 contains 'geosite:category-ir'
[PASS] Rule1ContainsGeositeIr: Rule 1 contains 'geosite:ir'
[PASS] Rule1ContainsDomainIr: Rule 1 contains 'domain:ir'
[PASS] Rule1ExactDomainList: Rule 1 exact domain array sequence (expected: [geosite:category-ir, geosite:ir, domain:ir], got: [geosite:category-ir, geosite:ir, domain:ir])
[PASS] Rule2Type: Rule 2 type (expected: field, got: field)
[PASS] Rule2OutboundTag: Rule 2 outboundTag (expected: direct, got: direct)
[PASS] Rule2HasIp: Rule 2 must have 'ip' array
[PASS] Rule2IpCount: Rule 2 ip list must have exactly 2 entries (expected: 2, got: 2)
[PASS] Rule2ContainsGeoipPrivate: Rule 2 contains 'geoip:private'
[PASS] Rule2ContainsGeoipIr: Rule 2 contains 'geoip:ir'
[PASS] Rule2ExactIpList: Rule 2 exact ip array sequence (expected: [geoip:private, geoip:ir], got: [geoip:private, geoip:ir])
[PASS] Rule3Type: Rule 3 type (expected: field, got: field)
[PASS] Rule3OutboundTag: Rule 3 outboundTag (expected: proxy, got: proxy)
[PASS] Rule3Network: Rule 3 network (expected: tcp,udp, got: tcp,udp)
[PASS] DirectOutboundExists: Direct outbound must exist
[PASS] DirectProtocol: Direct protocol (expected: freedom, got: freedom)
[PASS] DirectSettingsDomainStrategy: Direct settings domainStrategy (expected: UseIP, got: UseIP)

--- TEST 2: V2RayConfigBuilder Routing Consistency Across Protocols ---
[PASS] Proto_vmess_DomainStrategy: domainStrategy invariant for protocol: vmess (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] Proto_vmess_Rule1Outbound: Rule 1 outboundTag invariant for protocol: vmess (expected: direct, got: direct)
[PASS] Proto_vmess_Rule1Entries: Rule 1 domains invariant for protocol: vmess
[PASS] Proto_vmess_Rule2Outbound: Rule 2 outboundTag invariant for protocol: vmess (expected: direct, got: direct)
[PASS] Proto_vmess_Rule2Entries: Rule 2 ips invariant for protocol: vmess
[PASS] Proto_trojan_DomainStrategy: domainStrategy invariant for protocol: trojan (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] Proto_trojan_Rule1Outbound: Rule 1 outboundTag invariant for protocol: trojan (expected: direct, got: direct)
[PASS] Proto_trojan_Rule1Entries: Rule 1 domains invariant for protocol: trojan
[PASS] Proto_trojan_Rule2Outbound: Rule 2 outboundTag invariant for protocol: trojan (expected: direct, got: direct)
[PASS] Proto_trojan_Rule2Entries: Rule 2 ips invariant for protocol: trojan
[PASS] Proto_shadowsocks_DomainStrategy: domainStrategy invariant for protocol: shadowsocks (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] Proto_shadowsocks_Rule1Outbound: Rule 1 outboundTag invariant for protocol: shadowsocks (expected: direct, got: direct)
[PASS] Proto_shadowsocks_Rule1Entries: Rule 1 domains invariant for protocol: shadowsocks
[PASS] Proto_shadowsocks_Rule2Outbound: Rule 2 outboundTag invariant for protocol: shadowsocks (expected: direct, got: direct)
[PASS] Proto_shadowsocks_Rule2Entries: Rule 2 ips invariant for protocol: shadowsocks
[PASS] Proto_vless_DomainStrategy: domainStrategy invariant for protocol: vless (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] Proto_vless_Rule1Outbound: Rule 1 outboundTag invariant for protocol: vless (expected: direct, got: direct)
[PASS] Proto_vless_Rule1Entries: Rule 1 domains invariant for protocol: vless
[PASS] Proto_vless_Rule2Outbound: Rule 2 outboundTag invariant for protocol: vless (expected: direct, got: direct)
[PASS] Proto_vless_Rule2Entries: Rule 2 ips invariant for protocol: vless

--- TEST 3: V2RayConfigBuilder Adversarial Edge Cases ---
[PASS] MinimalNodeDomainStrategy: Minimal node generates valid IPIfNonMatch (expected: IPIfNonMatch, got: IPIfNonMatch)
[PASS] MinimalNodeRoutingRules: Minimal node generates complete routing rules
[PASS] ExtremeNodeDomainStrategy: Extreme node preserves IPIfNonMatch (expected: IPIfNonMatch, got: IPIfNonMatch)

--- TEST 4: IRANIAN_PACKAGES Catalog Integrity Verification ---
[PASS] CatalogNotEmpty: Catalog must not be null or empty
Total Iranian packages cataloged: 82
[PASS] CatalogSizeAdequate: Catalog should cover at least 50 domestic applications (got 82)
[PASS] ContainsMandatory_app.nobitex: Must contain mandatory required package: app.nobitex
[PASS] ContainsMandatory_com.sibche.aspardproject.app: Must contain mandatory required package: com.sibche.aspardproject.app
[PASS] ContainsMandatory_com.farsitel.bazaar: Must contain mandatory required package: com.farsitel.bazaar
[PASS] ContainsDomestic_cab.snapp.passenger: Catalog should contain domestic package: cab.snapp.passenger
[PASS] ContainsDomestic_taxi.tap30.passenger: Catalog should contain domestic package: taxi.tap30.passenger
[PASS] ContainsDomestic_ir.divar: Catalog should contain domestic package: ir.divar
[PASS] ContainsDomestic_com.digikala.app: Catalog should contain domestic package: com.digikala.app
[PASS] ContainsDomestic_com.torob: Catalog should contain domestic package: com.torob
[PASS] ContainsDomestic_ir.ble.messenger: Catalog should contain domestic package: ir.ble.messenger
[PASS] ContainsDomestic_ir.eitaa.messenger: Catalog should contain domestic package: ir.eitaa.messenger
[PASS] ContainsDomestic_ir.resaneh1.iptv: Catalog should contain domestic package: ir.resaneh1.iptv
[PASS] ContainsDomestic_com.sb24.blubank: Catalog should contain domestic package: com.sb24.blubank
[PASS] ContainsDomestic_ir.bankmellat.mobile: Catalog should contain domestic package: ir.bankmellat.mobile
[PASS] ContainsDomestic_com.bmi.mobilebank: Catalog should contain domestic package: com.bmi.mobilebank
[PASS] ContainsDomestic_ir.mci.ecareapp: Catalog should contain domestic package: ir.mci.ecareapp
[PASS] ContainsDomestic_ir.mtn.irancell: Catalog should contain domestic package: ir.mtn.irancell
[PASS] NoInvalidPackageFormats: All package names must be valid Android package identifiers (invalid: [])
[PASS] NoDuplicatePackages: Catalog must not contain duplicate package identifiers (duplicates: [])

--- TEST 5: applyDisallowedApplications Clean NameNotFoundException Catch ---
[Log.i] IranAppBypass: Successfully bypassed 0 Iranian applications from VPN tunnel
[PASS] CleanCatchZeroInstalled: When no packages installed, return count must be 0 (expected: 0, got: 0)
[PASS] NoDisallowedAdded: Disallowed packages set must remain empty (expected: 0, got: 0)
[PASS] CleanCatchNoThrow: PackageManager.NameNotFoundException was cleanly caught for all missing packages without throwing

--- TEST 6: applyDisallowedApplications Partial Installation ---
[Log.i] IranAppBypass: Successfully bypassed 3 Iranian applications from VPN tunnel
[PASS] PartialInstallCount: Should successfully bypass exactly 3 installed packages (expected: 3, got: 3)
[PASS] DisallowedSizeMatches: Disallowed set size must equal 3 (expected: 3, got: 3)
[PASS] ContainsNobitex: Disallowed set contains app.nobitex
[PASS] ContainsUp: Disallowed set contains com.sibche.aspardproject.app
[PASS] ContainsBazaar: Disallowed set contains com.farsitel.bazaar

--- TEST 7: applyDisallowedApplications Full Installation ---
[Log.i] IranAppBypass: Successfully bypassed 82 Iranian applications from VPN tunnel
[PASS] FullInstallCount: Should successfully bypass all 82 packages (expected: 82, got: 82)
[PASS] FullDisallowedSize: Disallowed set size must equal total package count (expected: 82, got: 82)

--- TEST 8: applyDisallowedApplications Resilience to Unexpected Exceptions ---
[Log.w] IranAppBypass: Failed to disallow package com.sibche.aspardproject.app: Permission denied for testing
[Log.i] IranAppBypass: Successfully bypassed 2 Iranian applications from VPN tunnel
[PASS] ResilienceCount: Should bypass 2 packages when 1 package triggers SecurityException (expected: 2, got: 2)
[PASS] NobitexStillAdded: Nobitex successfully added
[PASS] BazaarStillAdded: Bazaar successfully added after faulted package
[PASS] FailedPackageNotAdded: Faulted package omitted from disallowed set
===================================================================
  M2 EMPIRICAL TEST RESULTS: 86 PASSED, 0 FAILED
===================================================================
```

---

## 2. Logic Chain

1. **Routing Integrity**:
   - Direct observation of `V2RayConfigBuilder.kt:146` and `Test 1` shows `domainStrategy` is configured as `"IPIfNonMatch"`.
   - Observation of `V2RayConfigBuilder.kt:156-165` and `Test 1` verifies Rule 1 has `outboundTag: "direct"` and exact domain list `["geosite:category-ir", "geosite:ir", "domain:ir"]`.
   - Observation of `V2RayConfigBuilder.kt:167-176` and `Test 1` verifies Rule 2 has `outboundTag: "direct"` and exact ip list `["geoip:private", "geoip:ir"]`.
   - Crucially, Rule 0 (DNS), Rule 1 (Domestic Domains), and Rule 2 (Domestic & LAN IPs) strictly precede Rule 3 (General Proxy). In V2Ray/Xray routing semantics, rules are evaluated sequentially top-to-bottom. Placing domestic direct rules before proxy rules guarantees that domestic traffic is never erroneously routed through the proxy tunnel.
   - `Test 2` and `Test 3` verify that across VMess, Trojan, Shadowsocks, VLESS (Reality, TLS, gRPC, WebSocket), minimal nodes with null fields, and extreme unicode inputs, the routing rules and `domainStrategy` are invariant and properly generated.

2. **Application Bypass Resilience**:
   - Observation of `IranAppBypassHelper.kt:20-107` and `Test 4` confirms that 82 applications are cataloged, exceeding the project requirement (50+).
   - `Test 4` confirms mandatory required packages (`app.nobitex`, `com.sibche.aspardproject.app`, `com.farsitel.bazaar`) are present.
   - `Test 4` confirms 0 invalid package identifiers and 0 duplicate entries.
   - `Test 5` confirms that on devices where none of the Iranian packages are installed, `applyDisallowedApplications` catches `PackageManager.NameNotFoundException` cleanly on every call, returning `0` without throwing any unhandled exceptions.
   - `Test 6` and `Test 7` verify that installed packages are registered with `builder.addDisallowedApplication(pkg)` and the returned count reflects installed applications.
   - `Test 8` confirms that if an unexpected exception occurs (e.g. `SecurityException`), the method catches generic `Exception`, logs a warning, and continues processing the remaining packages without terminating early.

3. **Build & Regression Verification**:
   - Both `./gradlew testDebugUnitTest`, `./gradlew assembleDebug`, and `./gradlew assembleRelease` compile successfully on JDK 17 (`C:\Users\Arman\.jdks\jdk-17`).

---

## 3. Caveats

- Runtime execution of the Xray-core Go binary (`libv2ray.aar`) and active TUN device routing (`/dev/tun`) require physical Android hardware or an Android virtual device with network privileges. The internal JSON routing configuration and Java/Kotlin helper logic were verified empirically at unit and adversarial simulation level.
- No other caveats.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- **Assessment**:
  1. `V2RayConfigBuilder.buildConfig(node)` correctly and strictly implements Rule 1 (`"geosite:category-ir"`, `"geosite:ir"`, `"domain:ir"` with `"outboundTag": "direct"`), Rule 2 (`"geoip:private"`, `"geoip:ir"` with `"outboundTag": "direct"`), and `domainStrategy: "IPIfNonMatch"`.
  2. `IranAppBypassHelper.applyDisallowedApplications` cleanly catches `PackageManager.NameNotFoundException`, resiliently handles unexpected exceptions, and correctly registers installed packages.
  3. `IRANIAN_PACKAGES` contains 82 validated domestic packages, including all required packages (`app.nobitex`, `com.sibche.aspardproject.app`, `com.farsitel.bazaar`).
  4. All 86 empirical test assertions passed with 0 failures.

---

## 5. Verification Method

To independently execute and verify the empirical challenge:

1. **Compile and execute empirical test suite**:
   ```powershell
   $testClasses = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\intermediates\javac\debugUnitTest\compileDebugUnitTestJavaWithJavac\classes"
   $kotlinClasses = "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build\tmp\kotlin-classes\debug"
   $gsonJar = "C:\Users\Arman\.gradle\caches\modules-2\files-2.1\com.google.code.gson\gson\2.10.1\b3add478d4382b78ea20b1671390a858002feb6c\gson-2.10.1.jar"
   $kotlinJar = "C:\Users\Arman\.gradle\caches\modules-2\files-2.1\org.jetbrains.kotlin\kotlin-stdlib\2.0.0\b48df2c4aede9586cc931ead433bc02d6fd7879e\kotlin-stdlib-2.0.0.jar"
   $cp = "$testClasses;$kotlinClasses;$gsonJar;$kotlinJar"
   $java = "C:\Users\Arman\.jdks\jdk-17\bin\java.exe"

   & $java -cp $cp com.asanvpn.app.M2RoutingAndBypassEmpiricalTest
   ```
   **Expected Result**: `M2 EMPIRICAL TEST RESULTS: 86 PASSED, 0 FAILED`.

2. **Run Gradle unit tests and builds**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   cd c:\Users\Arman\Documents\antigravity\quirky-turing\android
   .\gradlew.bat testDebugUnitTest
   .\gradlew.bat assembleDebug
   .\gradlew.bat assembleRelease
   ```
   **Expected Result**: `BUILD SUCCESSFUL`.

3. **Invalidation Conditions**:
   - `domainStrategy` in generated Xray config is anything other than `"IPIfNonMatch"`.
   - Rule 1 or Rule 2 missing required geosite/geoip entries or assigned non-direct outbound tag.
   - `applyDisallowedApplications` throws unhandled `PackageManager.NameNotFoundException` on missing packages.
   - Any required package (`app.nobitex`, `com.sibche.aspardproject.app`, `com.farsitel.bazaar`) absent from `IRANIAN_PACKAGES`.
