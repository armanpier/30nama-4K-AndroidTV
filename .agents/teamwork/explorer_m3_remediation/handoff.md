# Milestone 3 Remediation Analysis & Technical Fix Strategy Report

**Explorer**: `explorer_m3_remediation` (Role: Concurrency & Test Wiring Explorer)  
**Parent Orchestrator ID**: `4b000716-2a65-4da7-a250-c5ab7038a555`  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_remediation`  
**Target Repositories**:
1. `c:\Users\Arman\Documents\antigravity\quirky-turing\android`
2. `C:\Users\Arman\Documents\antigravity\AsanVPN\android`

---

## Executive Summary

This investigation analyzed the root causes and established the exact technical remediation specifications for the two critical issues identified during Milestone 3 Gate Iteration 1:
1. **Concurrency Defect in `GeoAssetManager.kt`**: Unsynchronized concurrent execution of `checkAndUpdateRules` and static `.tmp` file paths causing Windows file-lock collisions (`The process cannot access the file because it is being used by another process`), destination deletion failures, and `FileNotFoundException` in `GeoAssetManagerAdversarialTest`.
2. **Gradle Test Task Wiring & 0 Tests Run**: Omission of test dependencies (`junit:junit:4.13.2`) and lack of `@Test` annotations resulting in AGP/Gradle discovering and executing 0 tests during `./gradlew test`.
3. **Repository Synchronization**: A strict mirror sync and verification workflow ensuring 100% cryptographic parity (0 diffs) between `quirky-turing\android` and `AsanVPN\android`.

---

## 1. Observation

### 1.1 Direct Reproduction of Concurrency Crash in `GeoAssetManager.kt`
- Command:
  ```powershell
  $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
  $androidDir = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
  $androidJar = "C:\Users\Arman\AppData\Local\Android\Sdk\platforms\android-34\android.jar"
  $modulesPath = "$env:USERPROFILE\.gradle\caches\modules-2\files-2.1"
  $neededJars = @(
      $androidJar,
      (Get-ChildItem -Recurse -Filter "gson-2.10.1.jar" $modulesPath | Select-Object -First 1 -ExpandProperty FullName),
      (Get-ChildItem -Recurse -Filter "kotlin-stdlib-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources|common" } | Select-Object -First 1 -ExpandProperty FullName),
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
  & "$env:JAVA_HOME\bin\java.exe" --add-opens java.base/jdk.internal.misc=ALL-UNNAMED -cp ($cp -join ";") com.asanvpn.app.GeoAssetManagerAdversarialTest
  ```
- Verbatim Execution Log Output:
  ```
  [Log.w] [GeoAssetManager] Download attempt failed for geosite.dat from https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat: build\adversarial_test_assets\case5_concurrency\assets\geosite.dat.tmp -> build\adversarial_test_assets\case5_concurrency\assets\geosite.dat: Tried to overwrite the destination, but failed to delete it.
  [Log.w] [GeoAssetManager] Download attempt failed for geosite.dat from https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release/geosite.dat: build\adversarial_test_assets\case5_concurrency\assets\geosite.dat.tmp (The system cannot find the file specified)
  [Log.w] [GeoAssetManager] Download attempt failed for geosite.dat from https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geosite.dat: build\adversarial_test_assets\case5_concurrency\assets\geosite.dat.tmp: The source file doesn't exist.
  [Log.i] [GeoAssetManager] Successfully updated geosite.dat to hash a21d7ebeac36b8c95ef874f04b0887f38e0d5d835ffd3c37f670ede8eca53acf (0 bytes)
  [PASS] Concurrent_ZeroFailures: All 20 concurrent update coroutines completed without uncaught exceptions
  Exception in thread "main" java.io.FileNotFoundException: build\adversarial_test_assets\case5_concurrency\assets\geoip.dat (The system cannot find the file specified)
      at java.base/java.io.FileInputStream.open0(Native Method)
      at java.base/java.io.FileInputStream.open(FileInputStream.java:216)
      at java.base/java.io.FileInputStream.<init>(FileInputStream.java:157)
      at kotlin.io.FilesKt__FileReadWriteKt.readText(FileReadWrite.kt:125)
      at com.asanvpn.app.GeoAssetManagerAdversarialTest$Companion.testConcurrentUpdateStress(GeoAssetManagerAdversarialTest.kt:913)
  ```
- File & Line References:
  - `GeoAssetManager.kt:85`: `suspend fun checkAndUpdateRules(context: Context, force: Boolean = false)` lacks any synchronization primitive.
  - `GeoAssetManager.kt:168`: `val tempFile = File(targetDir, "$assetName.tmp")` creates identical static temp files across concurrent coroutines.
  - `GeoAssetManager.kt:195-206`: `finalFile.delete()` and `tempFile.renameTo(finalFile)` / `tempFile.copyTo(...)` collide with active Windows file handles.

### 1.2 Verification of 0 Tests Executed in Gradle `test` Task
- Command:
  ```powershell
  Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
  .\gradlew.bat test --no-daemon
  ```
- Verbatim Execution Log:
  ```
  > Task :app:testDebugUnitTest UP-TO-DATE
  > Task :app:testReleaseUnitTest UP-TO-DATE
  > Task :app:test UP-TO-DATE
  BUILD SUCCESSFUL in 27s
  ```
- Inspection of `app/build/reports/tests/testDebugUnitTest/index.html` (lines 22–25):
  ```html
  <div class="infoBox" id="tests">
  <div class="counter">0</div>
  <p>tests</p>
  </div>
  ```
- Inspection of `app/build.gradle.kts` (lines 76–101):
  - Zero `testImplementation` dependencies declared.
- Inspection of test source files in `app/src/test/java/com/asanvpn/app/`:
  - `AppLoggerEmpiricalTest.java:6`: `public static void main(String[] args)` (No `@Test`)
  - `util/AppLoggerStressTest.java:20`: `public static void main(String[] args)` (No `@Test`)
  - `M1RemediationAdversarialTest.java:60`: `public static void main(String[] args)` (No `@Test`)
  - `M2RoutingAndBypassEmpiricalTest.java:48`: `public static void main(String[] args)` (No `@Test`)
  - `GeoAssetManagerAdversarialTest.kt:77`: `companion object { fun main(args: Array<String>) }` (No `@Test`)
- Inspection of `M1RemediationAdversarialTest.java:344`:
  - `File repoFile = new File("android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt");`
  - In Gradle's `testDebugUnitTest`, working directory is `android/app`, which breaks this relative path unless resolved with a fallback.

### 1.3 Successful Offline Dependency Verification
- Tested dependency resolution using `testImplementation("junit:junit:4.13.2")` and `testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")`.
- Output:
  ```
  RESOLVED: junit-4.13.2.jar -> C:\Users\Arman\.gradle\caches\modules-2\files-2.1\junit\junit\4.13.2\8ac9e16d933b6fb43bc7f576336b8f4d7eb5ba12\junit-4.13.2.jar
  RESOLVED: hamcrest-core-1.3.jar -> C:\Users\Arman\.gradle\caches\modules-2\files-2.1\org.hamcrest\hamcrest-core\1.3\42a25dc3219429f0e5d060061f71acb49bf010a0\hamcrest-core-1.3.jar
  RESOLVED: kotlinx-coroutines-test-jvm-1.7.3.jar -> C:\Users\Arman\.gradle\caches\modules-2\files-2.1\org.jetbrains.kotlinx\kotlinx-coroutines-test-jvm\1.7.3\89e34400f452dab68fbb3caa66d854c89aaafa07\kotlinx-coroutines-test-jvm-1.7.3.jar
  ```
- Both dependencies resolve cleanly from local cache / repository configuration without errors.

---

## 2. Logic Chain

1. **Root Cause of Concurrency Failure**:
   - In `GeoAssetManager.kt`, `checkAndUpdateRules` was unprotected by any concurrency control primitive.
   - When 20 coroutines in `GeoAssetManagerAdversarialTest.kt:893-910` fired simultaneously, all 20 coroutines detected that an update was needed and called `downloadAndVerifyAsset`.
   - All 20 coroutines attempted to write to `File(targetDir, "$assetName.tmp")`.
   - On Windows, holding an open file handle locks the file. When another coroutine attempts to delete, overwrite, or rename that file, the Windows OS rejects the operation with `Tried to overwrite the destination, but failed to delete it` or `(The process cannot access the file because it is being used by another process)`.
   - In the race, `finalFile.delete()` was executed by one coroutine while another coroutine failed to complete its write, leaving `geoip.dat` or `geosite.dat` deleted or 0 bytes.
   - Consequently, line 913 threw `FileNotFoundException: assets\geoip.dat`.

2. **Necessity of `updateMutex.tryLock()` & Unique UUID Temp Files**:
   - Using `private val updateMutex = Mutex()` with non-blocking `tryLock()` in `checkAndUpdateRules` ensures that if an update is already underway, subsequent concurrent calls coalesce and return `Result.success(false)` immediately without spawning redundant downloads or colliding on disk.
   - Using `File(targetDir, "$assetName.${UUID.randomUUID()}.tmp")` guarantees that any concurrent download attempt operates in an isolated temporary file namespace, preventing cross-coroutine and cross-process file-locking collisions on Windows.
   - Enclosing the download in `try ... finally { if (tempFile.exists()) tempFile.delete() }` guarantees zero orphaned `.tmp` files.
   - Implementing `replaceFileSafely` provides atomic replacement on POSIX and fallback deletion/copy replacement on Windows.

3. **Root Cause of 0 Tests Executed in Gradle**:
   - AGP unit testing relies on JUnit runner discovery.
   - Without `testImplementation("junit:junit:4.13.2")` in `app/build.gradle.kts`, JUnit was absent from the build model.
   - Because test suites used `public static void main` instead of JUnit annotations, Gradle's test scanner found 0 tests and reported green vacuously.
   - By adding JUnit 4 dependencies, annotating runner methods with `@org.junit.Test`, replacing `System.exit(1)` with `throw new AssertionError(...)`, and configuring `tasks.withType<Test>` with `--add-opens java.base/jdk.internal.misc=ALL-UNNAMED`, `./gradlew test` discovers and executes all test suites, reporting genuine non-zero test numbers in the HTML report.
   - Registering a dedicated `runEmpiricalTests` task wired to `check` gives direct CLI execution parity.

---

## 3. Caveats

- Android unit tests run on the JVM without an emulator; Android platform classes rely on mock implementations (`android.jar` + `src/test/java/android/` mocks).
- Under Windows OS, `File.renameTo` will return `false` if the target file exists; `replaceFileSafely` specifically addresses this with target deletion and copy fallbacks.
- No other caveats.

---

## 4. Conclusion & Technical Remediation Specification

### Remediation Plan 1: Concurrency Fix in `GeoAssetManager.kt`

#### Target File:
`android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`

#### Proposed Implementation:
```kotlin
package com.asanvpn.app.util

import android.content.Context
import android.util.Log
import com.asanvpn.app.data.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.TimeUnit

object GeoAssetManager {

    private const val TAG = "GeoAssetManager"

    private const val JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-v2ray-rules@release"
    private const val GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release"
    private const val CHECK_INTERVAL_MS = 24L * 60L * 60L * 1000L

    // Concurrency control: ensures only one rule update check/download executes at a time
    private val updateMutex = Mutex()

    private val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .followRedirects(true)
            .build()
    }

    fun getAssetDir(context: Context): File = context.getDir("assets", Context.MODE_PRIVATE)

    fun ensureAssetsInitialized(context: Context) {
        val assetDir = getAssetDir(context)
        if (!assetDir.exists()) {
            assetDir.mkdirs()
        }
        // Purge any stale temporary files from previous interrupted runs
        assetDir.listFiles { _, name -> name.endsWith(".tmp") }?.forEach { it.delete() }

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
                Log.i(TAG, "Initialized asset $fileName in ${targetFile.absolutePath} (${targetFile.length()} bytes)")
            } catch (e: Exception) {
                Log.e(TAG, "Failed copying asset $fileName from APK assets: ${e.message}")
            }
        }
    }

    suspend fun checkAndUpdateRules(context: Context, force: Boolean = false): Result<Boolean> = withContext(Dispatchers.IO) {
        // Non-blocking tryLock: Coalesce concurrent update requests
        if (!updateMutex.tryLock()) {
            Log.d(TAG, "Rule update check already in progress; skipping concurrent request")
            return@withContext Result.success(false)
        }
        try {
            val prefs = PreferencesManager(context)
            val now = System.currentTimeMillis()
            val lastCheck = prefs.lastGeoRulesCheckTime

            if (!force && (now - lastCheck < CHECK_INTERVAL_MS) && (now >= lastCheck)) {
                Log.d(TAG, "Skipping geo rules check: last checked ${(now - lastCheck) / 1000}s ago")
                return@withContext Result.success(false)
            }

            val assetDir = getAssetDir(context)
            if (!assetDir.exists()) {
                assetDir.mkdirs()
            }

            // Cleanup any orphan temporary files
            assetDir.listFiles { _, name -> name.endsWith(".tmp") }?.forEach { it.delete() }

            var anyUpdated = false
            val assetsToCheck = listOf("geoip.dat", "geosite.dat")

            for (assetName in assetsToCheck) {
                val targetFile = File(assetDir, assetName)
                val currentHash = if (targetFile.exists() && targetFile.length() > 0) computeSha256(targetFile) else ""
                val remoteHash = fetchRemoteChecksum(assetName)

                if (remoteHash != null) {
                    val needsUpdate = force || !targetFile.exists() || targetFile.length() == 0L ||
                            !currentHash.equals(remoteHash, ignoreCase = true)

                    if (needsUpdate) {
                        Log.i(TAG, "Update detected for $assetName: local=$currentHash, remote=$remoteHash")
                        val downloaded = downloadAndVerifyAsset(assetName, remoteHash, assetDir)
                        if (downloaded) {
                            anyUpdated = true
                        }
                    } else {
                        Log.d(TAG, "Asset $assetName is already up to date ($currentHash)")
                    }
                } else {
                    Log.w(TAG, "Could not fetch remote checksum for $assetName from any mirror")
                }
            }

            prefs.lastGeoRulesCheckTime = now
            Result.success(anyUpdated)
        } catch (e: Exception) {
            Log.e(TAG, "Error checking/updating Chocolate4Iran rules: ${e.message}", e)
            Result.failure(e)
        } finally {
            updateMutex.unlock()
        }
    }

    private fun fetchRemoteChecksum(assetName: String): String? {
        val checkUrls = listOf(
            "$JSDELIVR_BASE/$assetName.sha256sum",
            "$GITHUB_RAW_BASE/$assetName.sha256sum"
        )
        for (url in checkUrls) {
            try {
                val request = Request.Builder()
                    .url(url)
                    .header("User-Agent", "AsanVPN-GeoAssetSync/1.0")
                    .build()

                httpClient.newCall(request).execute().use { resp ->
                    if (resp.isSuccessful) {
                        val body = resp.body?.string()?.trim() ?: ""
                        val hash = body.split(Regex("\\s+")).firstOrNull()?.trim()?.lowercase()
                        if (!hash.isNullOrBlank() && hash.length == 64 && hash.all { it in "0123456789abcdef" }) {
                            return hash
                        }
                    }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Checksum fetch failed from $url: ${e.message}")
            }
        }
        return null
    }

    private fun downloadAndVerifyAsset(assetName: String, expectedHash: String, targetDir: File): Boolean {
        val downloadUrls = listOf(
            "$JSDELIVR_BASE/$assetName",
            "$GITHUB_RAW_BASE/$assetName"
        )
        val finalFile = File(targetDir, assetName)

        for (url in downloadUrls) {
            // Unique temporary file path per download operation
            val tempFile = File(targetDir, "$assetName.${UUID.randomUUID()}.tmp")
            try {
                val request = Request.Builder()
                    .url(url)
                    .header("User-Agent", "AsanVPN-GeoAssetSync/1.0")
                    .build()

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
                        val replaced = replaceFileSafely(tempFile, finalFile)
                        if (replaced) {
                            Log.i(TAG, "Successfully updated $assetName to hash $actualHash (${finalFile.length()} bytes)")
                            return true
                        }
                    } else {
                        Log.w(TAG, "SHA256 mismatch for $assetName: expected $expectedHash, got $actualHash")
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Download attempt failed for $assetName from $url: ${e.message}")
            } finally {
                if (tempFile.exists()) {
                    tempFile.delete()
                }
            }
        }
        return false
    }

    private fun replaceFileSafely(source: File, target: File): Boolean {
        // Attempt 1: Direct rename (atomic POSIX on Linux/Android)
        if (source.renameTo(target)) {
            return true
        }
        // Attempt 2: Target deletion followed by rename (Windows compatibility)
        if (target.exists()) {
            target.delete()
        }
        if (source.renameTo(target)) {
            return true
        }
        // Attempt 3: Byte copy fallback
        return try {
            source.copyTo(target, overwrite = true)
            source.delete()
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed replacing ${target.name}: ${e.message}")
            false
        }
    }

    private fun computeSha256(file: File): String {
        if (!file.exists() || file.length() == 0L) return ""
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

---

### Remediation Plan 2: Gradle Test Task Wiring & JUnit Test Runner

#### Target File 1:
`android/app/build.gradle.kts`

#### Changes:
1. In `android { ... }`:
   ```kotlin
   testOptions {
       unitTests {
           isReturnDefaultValues = true
           isIncludeAndroidResources = false
       }
   }
   ```
2. In `dependencies { ... }`:
   ```kotlin
   testImplementation("junit:junit:4.13.2")
   testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
   ```
3. Test JVM configuration and task wiring:
   ```kotlin
   tasks.withType<Test> {
       jvmArgs(
           "--add-opens", "java.base/jdk.internal.misc=ALL-UNNAMED",
           "--add-opens", "java.base/java.lang=ALL-UNNAMED"
       )
       testLogging {
           events("passed", "skipped", "failed", "standardOut", "standardError")
           showStandardStreams = true
           exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
       }
   }

   tasks.register<JavaExec>("runEmpiricalTests") {
       group = "verification"
       description = "Direct JVM empirical test suite runner"
       val debugUnitTestCompile = tasks.named("compileDebugUnitTestKotlin")
       val debugUnitTestJavaCompile = tasks.named("compileDebugUnitTestJavaWithJavac")
       dependsOn(debugUnitTestCompile, debugUnitTestJavaCompile)

       val androidJar = file("${android.sdkDirectory}/platforms/${android.compileSdk}/android.jar")
       classpath = files(
           layout.buildDirectory.dir("intermediates/javac/debugUnitTest/compileDebugUnitTestJavaWithJavac/classes"),
           layout.buildDirectory.dir("tmp/kotlin-classes/debugUnitTest"),
           layout.buildDirectory.dir("intermediates/javac/debug/compileDebugJavaWithJavac/classes"),
           layout.buildDirectory.dir("tmp/kotlin-classes/debug"),
           androidJar,
           configurations.getByName("debugRuntimeClasspath"),
           configurations.getByName("debugUnitTestRuntimeClasspath")
       )
       jvmArgs(
           "--add-opens", "java.base/jdk.internal.misc=ALL-UNNAMED",
           "--add-opens", "java.base/java.lang=ALL-UNNAMED"
       )
       mainClass.set("com.asanvpn.app.AllEmpiricalTestSuiteRunner")
   }

   tasks.named("check") {
       dependsOn("runEmpiricalTests")
   }
   ```

#### Target File 2:
`android/app/src/test/java/com/asanvpn/app/AllEmpiricalTestSuiteRunner.java` (New unified runner)
```java
package com.asanvpn.app;

import com.asanvpn.app.util.AppLoggerStressTest;
import org.junit.Test;

public class AllEmpiricalTestSuiteRunner {

    @Test
    public void runAllEmpiricalTestSuites() throws Exception {
        main(new String[0]);
    }

    public static void main(String[] args) throws Exception {
        System.out.println("================================================================================");
        System.out.println("   ASANVPN ALL EMPIRICAL & ADVERSARIAL TEST SUITES RUNNER                       ");
        System.out.println("================================================================================");

        int failures = 0;

        System.out.println("\n>>> [1/5] Running AppLoggerEmpiricalTest...");
        try {
            AppLoggerEmpiricalTest.main(new String[0]);
        } catch (Throwable t) {
            t.printStackTrace();
            failures++;
        }

        System.out.println("\n>>> [2/5] Running AppLoggerStressTest...");
        try {
            AppLoggerStressTest.main(new String[0]);
        } catch (Throwable t) {
            t.printStackTrace();
            failures++;
        }

        System.out.println("\n>>> [3/5] Running M1RemediationAdversarialTest...");
        try {
            M1RemediationAdversarialTest.main(new String[0]);
        } catch (Throwable t) {
            t.printStackTrace();
            failures++;
        }

        System.out.println("\n>>> [4/5] Running M2RoutingAndBypassEmpiricalTest...");
        try {
            M2RoutingAndBypassEmpiricalTest.main(new String[0]);
        } catch (Throwable t) {
            t.printStackTrace();
            failures++;
        }

        System.out.println("\n>>> [5/5] Running GeoAssetManagerAdversarialTest...");
        try {
            GeoAssetManagerAdversarialTest.main(new String[0]);
        } catch (Throwable t) {
            t.printStackTrace();
            failures++;
        }

        System.out.println("\n================================================================================");
        if (failures > 0) {
            System.err.println("ALL EMPIRICAL TESTS FAILED: " + failures + " suites failed");
            throw new AssertionError(failures + " test suites failed");
        } else {
            System.out.println("ALL EMPIRICAL TESTS PASSED SUCCESSFULLY (5/5 SUITES)!");
        }
        System.out.println("================================================================================");
    }
}
```

#### Target File 3:
`android/app/src/test/java/com/asanvpn/app/M1RemediationAdversarialTest.java`
- Path fallback in `testSourceCodeStaticAudit()`:
  ```java
  File repoFile = new File("android/app/src/main/java/com/asanvpn/app/data/VpnRepository.kt");
  if (!repoFile.exists()) {
      repoFile = new File("src/main/java/com/asanvpn/app/data/VpnRepository.kt");
  }
  if (!repoFile.exists()) {
      repoFile = new File("app/src/main/java/com/asanvpn/app/data/VpnRepository.kt");
  }

  File mainFile = new File("android/app/src/main/java/com/asanvpn/app/MainActivity.kt");
  if (!mainFile.exists()) {
      mainFile = new File("src/main/java/com/asanvpn/app/MainActivity.kt");
  }
  if (!mainFile.exists()) {
      mainFile = new File("app/src/main/java/com/asanvpn/app/MainActivity.kt");
  }
  ```
- Replace `System.exit(1)` with `throw new AssertionError(failedTests + " tests failed")`.
- Add `@org.junit.Test public void testAllM1Suites() throws Exception { main(new String[0]); }`.

#### Target File 4:
`android/app/src/test/java/com/asanvpn/app/AppLoggerEmpiricalTest.java`
- Replace `if (failures > 0) System.exit(1);` with `if (failures > 0) throw new AssertionError(failures + " tests failed");`.
- Add `@org.junit.Test public void testAppLoggerEmpirical() { main(new String[0]); }`.

#### Target File 5:
`android/app/src/test/java/com/asanvpn/app/util/AppLoggerStressTest.java`
- Replace `if (testsFailed > 0) System.exit(1);` with `if (testsFailed > 0) throw new AssertionError(testsFailed + " tests failed");`.
- Add `@org.junit.Test public void testAppLoggerStress() { main(new String[0]); }`.

#### Target File 6:
`android/app/src/test/java/com/asanvpn/app/M2RoutingAndBypassEmpiricalTest.java`
- Replace `if (testsFailed > 0) System.exit(1);` with `if (testsFailed > 0) throw new AssertionError(testsFailed + " tests failed");`.
- Add `@org.junit.Test public void testM2RoutingAndBypass() { main(new String[0]); }`.

#### Target File 7:
`android/app/src/test/java/com/asanvpn/app/GeoAssetManagerAdversarialTest.kt`
- Replace `if (testsFailed > 0) System.exit(1)` with `if (testsFailed > 0) throw AssertionError("$testsFailed tests failed")`.
- Add `@org.junit.Test fun testGeoAssetManagerAdversarial() = kotlinx.coroutines.runBlocking { main(emptyArray()) }`.

---

### Remediation Plan 3: Repository Synchronization Protocol

1. **Working Directories**:
   - Primary source: `c:\Users\Arman\Documents\antigravity\quirky-turing\android`
   - Mirror target: `C:\Users\Arman\Documents\antigravity\AsanVPN\android`

2. **Full File Sync List**:
   - `app/build.gradle.kts`
   - `app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`
   - `app/src/test/java/com/asanvpn/app/GeoAssetManagerAdversarialTest.kt`
   - `app/src/test/java/com/asanvpn/app/M1RemediationAdversarialTest.java`
   - `app/src/test/java/com/asanvpn/app/AppLoggerEmpiricalTest.java`
   - `app/src/test/java/com/asanvpn/app/util/AppLoggerStressTest.java`
   - `app/src/test/java/com/asanvpn/app/M2RoutingAndBypassEmpiricalTest.java`
   - `app/src/test/java/com/asanvpn/app/AllEmpiricalTestSuiteRunner.java`

3. **Mirror Script (`sync_repos.ps1`)**:
   ```powershell
   $src = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   $dst = "C:\Users\Arman\Documents\antigravity\AsanVPN\android"

   $files = @(
       "app\build.gradle.kts",
       "app\src\main\java\com\asanvpn\app\util\GeoAssetManager.kt",
       "app\src\test\java\com\asanvpn\app\GeoAssetManagerAdversarialTest.kt",
       "app\src\test\java\com\asanvpn\app\M1RemediationAdversarialTest.java",
       "app\src\test\java\com\asanvpn\app\AppLoggerEmpiricalTest.java",
       "app\src\test\java\com\asanvpn\app\util\AppLoggerStressTest.java",
       "app\src\test\java\com\asanvpn\app\M2RoutingAndBypassEmpiricalTest.java",
       "app\src\test\java\com\asanvpn\app\AllEmpiricalTestSuiteRunner.java"
   )

   foreach ($rel in $files) {
       $sourcePath = Join-Path $src $rel
       $destPath = Join-Path $dst $rel
       $destDir = Split-Path -Parent $destPath
       if (-not (Test-Path $destDir)) {
           New-Item -ItemType Directory -Path $destDir -Force | Out-Null
       }
       Copy-Item -Path $sourcePath -Destination $destPath -Force
   }

   # Clean transient artifacts
   Remove-Item -Path (Join-Path $src ".kotlin\errors") -Recurse -Force -ErrorAction SilentlyContinue
   Remove-Item -Path (Join-Path $dst ".kotlin\errors") -Recurse -Force -ErrorAction SilentlyContinue
   ```

4. **Verification via Cryptographic Parity Script**:
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
   Write-Host "Only in 1: $($onlyIn1.Count), Only in 2: $($onlyIn2.Count), Content diffs: $($diffs.Count)"
   if ($onlyIn1.Count -ne 0 -or $onlyIn2.Count -ne 0 -or $diffs.Count -ne 0) {
       throw "Parity failure between quirky-turing and AsanVPN!"
   }
   ```

---

## 5. Verification Method

Once implemented by the worker agent:

1. **Verify Gradle Test Execution and Non-Zero Count**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   .\gradlew.bat testDebugUnitTest --no-daemon
   Get-Content "app\build\reports\tests\testDebugUnitTest\index.html" | Select-String -Pattern '<div class="counter">[0-9]+</div>' -Context 0, 1
   ```
   *Expected Outcome*: Test counter shows `>= 6` tests (all passing, 0 failures, 0 ignored).

2. **Verify Concurrency Stress Passing**:
   ```powershell
   $env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"
   $androidDir = "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   $androidJar = "C:\Users\Arman\AppData\Local\Android\Sdk\platforms\android-34\android.jar"
   $modulesPath = "$env:USERPROFILE\.gradle\caches\modules-2\files-2.1"
   $neededJars = @(
       $androidJar,
       (Get-ChildItem -Recurse -Filter "gson-2.10.1.jar" $modulesPath | Select-Object -First 1 -ExpandProperty FullName),
       (Get-ChildItem -Recurse -Filter "kotlin-stdlib-*.jar" $modulesPath | Where-Object { $_.Name -notmatch "sources|common" } | Select-Object -First 1 -ExpandProperty FullName),
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
   & "$env:JAVA_HOME\bin\java.exe" --add-opens java.base/jdk.internal.misc=ALL-UNNAMED -cp ($cp -join ";") com.asanvpn.app.GeoAssetManagerAdversarialTest
   ```
   *Expected Outcome*: Output ends with:
   ```
   ================================================================================
      TEST SUITE EXECUTION COMPLETE: 27 PASSED, 0 FAILED
   ================================================================================
   ```
   And process exits with returncode 0.

3. **Verify Unified Runner Execution**:
   ```powershell
   .\gradlew.bat runEmpiricalTests --no-daemon
   ```
   *Expected Outcome*: `BUILD SUCCESSFUL`, all 5 test suites execute and report passing.

4. **Verify Clean APK Builds on Both Repositories**:
   ```powershell
   Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"
   .\gradlew.bat assembleDebug assembleRelease --no-daemon
   Set-Location "C:\Users\Arman\Documents\antigravity\AsanVPN\android"
   .\gradlew.bat assembleDebug assembleRelease --no-daemon
   ```
   *Expected Outcome*: Both repositories compile with exit code 0 and produce valid APKs.

5. **Verify 100% Repository Parity**:
   ```powershell
   & "c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m3\verify_dispatch_parity.ps1"
   ```
   *Expected Outcome*: `Only in 1: 0, Only in 2: 0, Content diffs: 0`.
