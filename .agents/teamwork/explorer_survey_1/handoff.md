# Comprehensive Survey & Architecture Report: App Log Capping, Link Testing & Config Redaction

**Agent**: `explorer_survey_1` (Explorer)  
**Task**: Survey logging and link-testing subsystem of AsanVPN Android  
**Target Repositories**:
- `c:\Users\Arman\Documents\antigravity\quirky-turing\android`
- `C:\Users\Arman\Documents\antigravity\AsanVPN\android`

---

## 1. Observation

### 1.1 Repository Parity & Build Environment
- **Comparison Command**:
  ```powershell
  git --no-pager diff --no-index "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src" "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\src"
  git --no-pager diff --no-index "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\build.gradle.kts" "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\build.gradle.kts"
  ```
  Result: Exit code 0, 0 lines of diff across all code and resource files. Exact source parity exists between `quirky-turing\android` and `AsanVPN\android`.
- **JDK 17 & Gradle**:
  - JDK 17 installed at `C:\Users\Arman\.jdks\jdk-17` (JVM 17.0.21 Adoptium).
  - Gradle 8.12 (`gradlew.bat`) executes and passes dry-run compilation (`.\gradlew.bat compileDebugSources --dry-run` completed with `BUILD SUCCESSFUL in 21s`).

---

### 1.2 Log Storage, Buffering, and Display Subsystem
- **Buffer Storage**:
  - File: `android/app/src/main/java/com/asanvpn/app/util/AppLogger.kt`
  - Implementation: In-memory Kotlin singleton (`object AppLogger`).
  - Lines 14–16:
    ```kotlin
    private val userLogs = mutableListOf<String>()
    private val adminLogs = mutableListOf<String>()
    private const val MAX_LOG_ENTRIES = 200
    ```
  - Buffer Mechanism: The log is held strictly in RAM in two `mutableListOf<String>` collections (`userLogs` and `adminLogs`). There is no SQLite, Room, or disk file persistence.
  - Ingestion & Trimming (Lines 18–33, 51–58):
    ```kotlin
    @Synchronized
    fun logUser(message: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val entry = "[$time] $message"
        userLogs.add(entry)
        adminLogs.add(entry) // Admin log contains everything user sees + technical details
        trim()
    }

    @Synchronized
    fun logAdmin(message: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val entry = "[$time] [ADMIN] $message"
        adminLogs.add(entry)
        trim()
    }

    private fun trim() {
        while (userLogs.size > MAX_LOG_ENTRIES) {
            userLogs.removeAt(0)
        }
        while (adminLogs.size > MAX_LOG_ENTRIES) {
            adminLogs.removeAt(0)
        }
    }
    ```
- **Display Subsystem**:
  - Files:
    - `android/app/src/main/java/com/asanvpn/app/ui/screens/ConnectScreen.kt` (lines 920–1010)
    - `android/app/src/main/java/com/asanvpn/app/ui/screens/PinScreen.kt` (lines 820–905)
  - Display Mechanism: Jetpack Compose `AlertDialog` displaying a scrollable text container:
    ```kotlin
    val currentLogText = if (isAdminMode) AppLogger.getAdminLog() else AppLogger.getUserLog()
    ```
  - Rendering is done via a single `Text(text = currentLogText)` within a sunken `Box` modifier with `.verticalScroll(rememberScrollState())`.
  - Non-admin users see `userLogs` (retrieved via `AppLogger.getUserLog()`, returning a Persian fallback `"گزارشی برای نمایش وجود ندارد."` if empty).
  - Admin users (authenticated via PIN or dialog) see `adminLogs` (retrieved via `AppLogger.getAdminLog()`).
  - A "کپی گزارش" (Copy Log) button writes `currentLogText` to `android.content.ClipboardManager`.

---

### 1.3 Link Testing Execution and Current Logging
- **Execution Engine**:
  - File: `android/app/src/main/java/com/asanvpn/app/service/PingTester.kt`
  - Four distinct testing components:
    1. **TCP Handshake Prescan** (`testTcpLatency`, lines 306–316):
       - Uses `Socket().connect(InetSocketAddress(host, port), timeoutMs)`.
       - Timeout: 2500ms for tier 1; 1200ms for lower tiers.
       - Runs in parallel via `async { ... }.awaitAll()`.
       - Filter criteria: filters nodes where TCP latency > 0, takes top 10 candidates for real delay testing. Not logged to `AppLogger`.
    2. **Real Outbound Delay (Libv2ray HTTP 204 Tunnel Delay)** (`measureRealDelay`, lines 228–250):
       - Generates temporary minimal test config via `V2RayConfigBuilder.buildTestConfig(node)`.
       - Invokes native Go core via `Libv2ray.measureOutboundDelay(configJson, TEST_URL_PRIMARY)` (`TEST_URL_PRIMARY = "https://cp.cloudflare.com/generate_204"`).
       - Fallback endpoint if primary fails: `TEST_URL_FALLBACK = "https://www.gstatic.com/generate_204"`.
       - Returns latency in milliseconds or `-1L` if unreachable.
    3. **Active Connected Latency** (`testConnectedRealLatency`, lines 255–282):
       - Triggered periodically every 10 seconds while connected in `MainActivity.kt` (lines 120–131).
       - Tries `V2RayCoreManager.measureDelay(TEST_URL_PRIMARY)`, falling back to `OkHttpClient` GET 204 over `tun0`.
       - Updates UI state (`currentServerPing`, `prefs.selectedServerPing`); intentionally NOT appended to `AppLogger` to prevent log buffer exhaustion.
    4. **Priority Waterfall Cascade** (`connectFastAndOptimize`, lines 44–150):
       - Groups nodes by `panelPriority ?: 1`.
       - Runs TCP prescan then `measureRealDelay` on top candidates.
       - Connects immediately to the first responsive node (`onFirstOkNode`), then continues testing to optimize if a node is > 25ms faster (`onFastestNodeFound`).
       - Halts cascade on tier success; cascades to next priority tier only on full tier failure.

- **Current Logging in `PingTester.kt`**:
  - Tier Start (Lines 80–81):
    - `AppLogger.logUser("🔍 بررسی سرورهای $tierName...")`
    - `AppLogger.logAdmin("Testing Tier $tier ($tierName) with ${tierNodes.size} nodes: ${tierNodes.map { "${it.remark} (${it.server}:${it.port})" }}")`
  - Node Success (Lines 102–103):
    - `AppLogger.logUser("⚡ تست موفق سرور [${node.remark}] — پینگ: ${realDelay}ms")`
    - `AppLogger.logAdmin("Tier $tier OK: [${node.remark}] (${node.server}:${node.port}) -> REAL latency: ${realDelay}ms (protocol: ${node.protocol}, security: ${node.security})")`
  - Fast Connect Assignment (Lines 109–110):
    - `AppLogger.logUser("🚀 انتخاب سرور پایدار [${node.remark}]")`
    - `AppLogger.logAdmin("Cascade SUCCESS. Assigned node [${node.remark}] (${node.server}:${node.port})")`
  - Optimization Switch (Lines 118–119):
    - `AppLogger.logUser("⚡ تعویض به سرور سریع‌تر: [${node.remark}] (${realDelay}ms)")`
    - `AppLogger.logAdmin("Cascade OPTIMIZE: [${node.remark}] (${realDelay}ms vs $prevRemark ${prevLat}ms)")`
  - Node Failure (Lines 124–125):
    - `AppLogger.logUser("⚠️ سرور [${node.remark}] در دسترس نیست")`
    - `AppLogger.logAdmin("Tier $tier candidate FAILED: [${node.remark}] (${node.server}:${node.port})")`
  - Cascade Halt / Failover (Lines 134–141):
    - `AppLogger.logUser("✅ اتصال به سرورهای $tierName نهایی شد")`
    - `AppLogger.logAdmin(">> [Cascade HALTED] Tier $tier successful.")`
    - `AppLogger.logUser("⚠️ سرورهای $tierName پاسخ ندادند. در حال بررسی اولویت بعدی...")`
    - `AppLogger.logAdmin(">> [Cascade FAILOVER] Tier $tier timed out. Cascading to next tier.")`

---

### 1.4 Detailed / Sensitive Link Configurations & Raw Outputs Logging Locations
Direct inspection of code reveals the following locations dumping sensitive configurations, raw JSON payloads, IP addresses, ports, or credentials into `AppLogger`:

1. **`android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt` line 252**:
   ```kotlin
   AppLogger.logAdmin("Connect SUCCESS. Nodes: $count. Raw response: $responseStr")
   ```
   **Exposure**: Dumps `$responseStr` in its entirety. This contains the full backend worker JSON with all proxy nodes (`VpnNode` objects), containing:
   - Plain server IP addresses and hostnames (`server`)
   - Port numbers (`port`)
   - VLESS / Trojan UUIDs and passwords (`uuid`, `password`)
   - Reality keys (`pbk`), short IDs (`sid`), spiderX (`spx`)
   - TLS SNI hostnames (`sni`)
   - Raw embedded `xray_config` and `singbox_config` objects if provided
   - User account info, remaining bytes, expiration details
2. **`android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt` lines 263, 272, 276, 385**:
   ```kotlin
   Line 263: AppLogger.logAdmin("Auth Rejected: HTTP ${response.code} | Status: ${parsed.status} | $responseStr")
   Line 272: AppLogger.logAdmin("Rate limited: $responseStr")
   Line 276: AppLogger.logAdmin("Server returned non-success: ${response.code} / ${parsed?.status}: $responseStr")
   Line 385: AppLogger.logAdmin("Lockout cleared via check_lockout: $respStr")
   ```
   **Exposure**: Full raw error and status bodies logged to `adminLogs`.
3. **`android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt` lines 201, 208**:
   ```kotlin
   Line 201: AppLogger.logAdmin("Sync initiated for PIN: $pin (Device: $deviceId)")
   Line 208: AppLogger.logAdmin("Connecting to route: $url")
   ```
   **Exposure**: Logs plain text user PIN, device hardware ID, and de-obfuscated worker endpoint URLs (defeating the XOR string protection in `workerEndpoints`).
4. **`android/app/src/main/java/com/asanvpn/app/service/PingTester.kt` line 81**:
   ```kotlin
   AppLogger.logAdmin("Testing Tier $tier ($tierName) with ${tierNodes.size} nodes: ${tierNodes.map { "${it.remark} (${it.server}:${it.port})" }}")
   ```
   **Exposure**: Explicitly exposes server IP/hostname and port `${it.server}:${it.port}` for all candidate nodes in the tier.
5. **`android/app/src/main/java/com/asanvpn/app/service/PingTester.kt` lines 103, 110, 125**:
   ```kotlin
   Line 103: AppLogger.logAdmin("Tier $tier OK: [${node.remark}] (${node.server}:${node.port}) -> REAL latency: ${realDelay}ms (protocol: ${node.protocol}, security: ${node.security})")
   Line 110: AppLogger.logAdmin("Cascade SUCCESS. Assigned node [${node.remark}] (${node.server}:${node.port})")
   Line 125: AppLogger.logAdmin("Tier $tier candidate FAILED: [${node.remark}] (${node.server}:${node.port})")
   ```
   **Exposure**: Server IP, port, protocol, and security configuration are emitted for every single candidate node tested.

---

## 2. Logic Chain

1. **Log Buffer Capping Logic**:
   - *From Observation 1.2*: `AppLogger.kt:16` sets `MAX_LOG_ENTRIES = 200`. When `logUser` or `logAdmin` is invoked, `trim()` executes `while (list.size > MAX_LOG_ENTRIES) list.removeAt(0)`.
   - *Requirement R1*: "Cap the application log buffer to a maximum of 100 entries to reduce application load."
   - *Inference*: Changing `MAX_LOG_ENTRIES = 100` in `AppLogger.kt` guarantees that neither `userLogs` nor `adminLogs` ever exceeds 100 entries during runtime.
   - *Impact*: Lowers in-memory overhead and limits Compose string concatenation and text layout recalculation in `ConnectScreen` and `PinScreen` dialogs.

2. **Config Redaction Logic**:
   - *From Observation 1.4*: `VpnRepository.kt` (lines 252, 263, 272, 276) and `PingTester.kt` (lines 81, 103, 110, 125) write raw JSON responses, credentials, IPs, ports, and protocols to `adminLogs`.
   - *Requirement R1*: "Redact detailed/full link configurations from the log: neither admin nor regular users need to see full raw link tests in the log."
   - *Inference*:
     - In `VpnRepository.kt`, line 252 must replace `Raw response: $responseStr` with sanitized metadata (e.g., `Connect SUCCESS. Received $count subscription nodes.`).
     - Error lines 263, 272, 276 must log only HTTP status code and parsed status without raw JSON bodies.
     - Sensitive identifiers (PIN, Device ID) in line 201 must be masked (e.g., `***${pin.takeLast(2)}`), and worker endpoint URLs in line 208 must be masked.
     - In `PingTester.kt`, candidate listings and test result logs must remove `${node.server}:${node.port}`, protocol, and security strings.

3. **Concise Link Test Log Formatting Logic**:
   - *From Observation 1.3*: In `PingTester.kt`, node tests currently log two separate entries per test: one in `logUser` and a verbose technical one in `logAdmin`. On failure, `logUser` reports "در دسترس نیست" without latency or standard status, while `logAdmin` dumps `${node.server}:${node.port}`.
   - *Requirement R1*: "Format link test log entries so users and admins can see link testing progress and results directly in the log containing only: link remark, delay (latency number in ms), and success or failure status."
   - *From Observation 1.2*: `logUser(message)` appends the entry to **both** `userLogs` and `adminLogs`.
   - *Inference*: By routing link test results through a unified format visible to both user and admin (or via `logUser`), both tiers see the test progress and results containing strictly:
     - Link remark: `[remark]`
     - Delay: `${latencyMs}ms` (or `تایم‌اوت` / `-1ms` on failure)
     - Status: `موفق` (Success) or `ناموفق` (Failure)
   - Removing the secondary `logAdmin` call with `${node.server}:${node.port}` halves log entry consumption per node test and eliminates credential/endpoint leakage for admins.

---

## 3. Caveats

1. **Logcat (`android.util.Log`) vs `AppLogger`**:
   - `android.util.Log.i(TAG, ...)` is also used inside `PingTester.kt` and `MainActivity.kt`.
   - These go to Android OS Logcat (accessible only via ADB USB debugging), NOT the in-app UI log dialogs.
   - To ensure complete security hygiene and prevent device-level log sniffing, Logcat calls in `PingTester.kt` should also be sanitized to omit raw server IPs and ports.
2. **Periodic Latency Checks**:
   - `PingTester.testConnectedRealLatency()` runs in a 10-second loop in `MainActivity.kt`.
   - It currently does NOT call `AppLogger`. It must remain excluded from `AppLogger` so it does not fill the 100-entry log buffer.
3. **Repository Parity Guarantee**:
   - Any modifications made to `quirky-turing\android` must be mirrored identically to `C:\Users\Arman\Documents\antigravity\AsanVPN\android` as required by R3.

---

## 4. Conclusion & Concrete Implementation Strategy

### 4.1 Target Files & Changes

#### A. `android/app/src/main/java/com/asanvpn/app/util/AppLogger.kt`
1. **Reduce Maximum Buffer Size**:
   Change `MAX_LOG_ENTRIES` from 200 to 100:
   ```kotlin
   // Before:
   private const val MAX_LOG_ENTRIES = 200

   // After:
   private const val MAX_LOG_ENTRIES = 100
   ```
2. **Add Standardized Link Test Log Helper**:
   Add a dedicated synchronized method to format link test progress and results consistently for both user and admin:
   ```kotlin
   @Synchronized
   fun logLinkTest(remark: String, latencyMs: Long, isSuccess: Boolean) {
       val icon = if (isSuccess) "⚡" else "⚠️"
       val statusText = if (isSuccess) "موفق" else "ناموفق"
       val latencyText = if (isSuccess && latencyMs > 0) "${latencyMs}ms" else "تایم‌اوت"
       val entry = "$icon [$remark] — پینگ: $latencyText ($statusText)"
       logUser(entry)
   }
   ```
   *(Note: Because `logUser` appends to both `userLogs` and `adminLogs`, calling this automatically updates both user and admin views with the exact required fields: remark, latency in ms, and status).*

---

#### B. `android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt`
1. **Redact Sensitive Connection & Auth Logs**:
   - Line 201:
     ```kotlin
     // Before:
     AppLogger.logAdmin("Sync initiated for PIN: $pin (Device: $deviceId)")
     // After:
     AppLogger.logAdmin("Sync initiated for PIN: ***${pin.takeLast(2)}")
     ```
   - Line 208:
     ```kotlin
     // Before:
     AppLogger.logAdmin("Connecting to route: $url")
     // After:
     AppLogger.logAdmin("Connecting to subscription route...")
     ```
   - Line 252 (Critical Redaction):
     ```kotlin
     // Before:
     AppLogger.logAdmin("Connect SUCCESS. Nodes: $count. Raw response: $responseStr")
     // After:
     AppLogger.logAdmin("Connect SUCCESS. Received $count subscription nodes.")
     ```
   - Lines 263, 272, 276:
     ```kotlin
     // Before:
     AppLogger.logAdmin("Auth Rejected: HTTP ${response.code} | Status: ${parsed.status} | $responseStr")
     AppLogger.logAdmin("Rate limited: $responseStr")
     AppLogger.logAdmin("Server returned non-success: ${response.code} / ${parsed?.status}: $responseStr")
     // After:
     AppLogger.logAdmin("Auth Rejected: HTTP ${response.code} | Status: ${parsed?.status}")
     AppLogger.logAdmin("Rate limited: HTTP ${response.code}")
     AppLogger.logAdmin("Server returned non-success: HTTP ${response.code}")
     ```
   - Line 385:
     ```kotlin
     // Before:
     AppLogger.logAdmin("Lockout cleared via check_lockout: $respStr")
     // After:
     AppLogger.logAdmin("Lockout cleared via check_lockout")
     ```

---

#### C. `android/app/src/main/java/com/asanvpn/app/service/PingTester.kt`
1. **Sanitize Tier Announcement (Line 81)**:
   ```kotlin
   // Before:
   AppLogger.logAdmin("Testing Tier $tier ($tierName) with ${tierNodes.size} nodes: ${tierNodes.map { "${it.remark} (${it.server}:${it.port})" }}")
   // After:
   AppLogger.logAdmin("Testing Tier $tier ($tierName) with ${tierNodes.size} nodes")
   ```
2. **Format Link Test Results (Lines 102–103, 124–125)**:
   - On Success:
     ```kotlin
     // Before:
     AppLogger.logUser("⚡ تست موفق سرور [${node.remark}] — پینگ: ${realDelay}ms")
     AppLogger.logAdmin("Tier $tier OK: [${node.remark}] (${node.server}:${node.port}) -> REAL latency: ${realDelay}ms (protocol: ${node.protocol}, security: ${node.security})")
     // After:
     AppLogger.logLinkTest(node.remark, realDelay, isSuccess = true)
     ```
   - On Failure:
     ```kotlin
     // Before:
     AppLogger.logUser("⚠️ سرور [${node.remark}] در دسترس نیست")
     AppLogger.logAdmin("Tier $tier candidate FAILED: [${node.remark}] (${node.server}:${node.port})")
     // After:
     AppLogger.logLinkTest(node.remark, -1L, isSuccess = false)
     ```
3. **Sanitize Assignment Logs (Line 110)**:
   ```kotlin
   // Before:
   AppLogger.logAdmin("Cascade SUCCESS. Assigned node [${node.remark}] (${node.server}:${node.port})")
   // After:
   AppLogger.logAdmin("Cascade SUCCESS. Assigned node [${node.remark}]")
   ```

---

## 5. Verification Method

### 5.1 Independent Code & Structure Inspection
1. **Buffer Size Cap**:
   - Inspect `AppLogger.kt`: verify `MAX_LOG_ENTRIES == 100`.
   - Verify `trim()` is called on every write and caps both `userLogs` and `adminLogs` to `<= 100`.
2. **Config Redaction**:
   - Search for `responseStr` in `AppLogger.log*`: ensure 0 occurrences.
   - Search for `it.server` or `node.server` in `AppLogger.log*`: ensure 0 occurrences.
   - Search for `pin` or `deviceId` in `AppLogger.log*`: ensure only masked PIN is logged.
3. **Link Test Format**:
   - Inspect test logging in `PingTester.kt`: ensure all result messages follow the concise pattern containing ONLY: link remark, latency (in ms), and status (success/failure).

### 5.2 Build Verification Commands
Run in PowerShell with JDK 17:
```powershell
$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
.\gradlew.bat compileDebugSources --no-daemon
```
Verify exit code is 0.

### 5.3 Repository Parity Check
Run:
```powershell
git --no-pager diff --no-index "c:\Users\Arman\Documents\antigravity\quirky-turing\android\app\src" "C:\Users\Arman\Documents\antigravity\AsanVPN\android\app\src"
```
Verify zero differences exist between the two repositories.
