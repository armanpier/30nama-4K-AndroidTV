## 2026-11-10T00:30:30Z
You are worker_m3_remediation (Role: Parity & Build Remediation Worker).
Your working directory is: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m3_remediation

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You must read ORIGINAL_REQUEST.md first:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md
Also review PROJECT.md:
c:\Users\Arman\Documents\antigravity\quirky-turing\PROJECT.md
And the Explorer Remediation Report detailing the exact technical specifications and code fixes:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_remediation\handoff.md
And Reviewer M3.2's handoff report:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m3_2\handoff.md

Your task:
Implement the remediation changes to resolve the concurrency defect in `GeoAssetManager.kt`, wire Gradle test execution so `./gradlew test` executes unit tests with non-zero counts, and maintain 100% bit-for-bit repository parity between `quirky-turing\android` and `AsanVPN\android`.

Steps:
1. Concurrency Fix in `GeoAssetManager.kt`:
   - Follow `explorer_m3_remediation\handoff.md` § 4 Remediation Plan 1:
   - Add `private val updateMutex = Mutex()`.
   - In `checkAndUpdateRules`, add `if (!updateMutex.tryLock()) { Log.d(TAG, "Rule update check already in progress; skipping concurrent request"); return@withContext Result.success(false) }` inside try/finally { updateMutex.unlock() }.
   - In `downloadAndVerifyAsset`, create uniquely named temporary files per download operation (`val tempFile = File(targetDir, "$assetName.${UUID.randomUUID()}.tmp")`), delete stale `.tmp` files in `ensureAssetsInitialized`, implement `replaceFileSafely(tempFile, finalFile)`, and delete `tempFile` in `finally`.
2. Gradle Test Wiring & Test Suites Updates:
   - Follow `explorer_m3_remediation\handoff.md` § 4 Remediation Plan 2:
   - In `android/app/build.gradle.kts`:
     - Add `testOptions { unitTests { isReturnDefaultValues = true; isIncludeAndroidResources = false } }`.
     - Add `testImplementation("junit:junit:4.13.2")` and `testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")`.
     - Configure `tasks.withType<Test>` with `--add-opens java.base/jdk.internal.misc=ALL-UNNAMED` and `--add-opens java.base/java.lang=ALL-UNNAMED`.
     - Register `tasks.register<JavaExec>("runEmpiricalTests")` wired to `check`.
   - Create `app/src/test/java/com/asanvpn/app/AllEmpiricalTestSuiteRunner.java` with `@org.junit.Test`.
   - In `M1RemediationAdversarialTest.java`: add path fallbacks (`android/app/...`, `src/...`, `app/src/...`) in `testSourceCodeStaticAudit()`, replace `System.exit(1)` with `throw new AssertionError(...)`, add `@org.junit.Test`.
   - In `AppLoggerEmpiricalTest.java`: replace `System.exit(1)` with `throw new AssertionError(...)`, add `@org.junit.Test`.
   - In `AppLoggerStressTest.java`: replace `System.exit(1)` with `throw new AssertionError(...)`, add `@org.junit.Test`.
   - In `M2RoutingAndBypassEmpiricalTest.java`: replace `System.exit(1)` with `throw new AssertionError(...)`, add `@org.junit.Test`.
   - In `GeoAssetManagerAdversarialTest.kt`: replace `System.exit(1)` with `throw AssertionError(...)`, add `@org.junit.Test fun testGeoAssetManagerAdversarial() = kotlinx.coroutines.runBlocking { main(emptyArray()) }`.
3. Repository Mirroring:
   - Copy all modified and added files to `C:\Users\Arman\Documents\antigravity\AsanVPN\android`.
   - Clean `.kotlin\errors` transient directories.
   - Run parity check script to verify `Only in 1: 0, Only in 2: 0, Content diffs: 0`.
4. Verification:
   - Run `.\gradlew.bat testDebugUnitTest --no-daemon` on both repos: verify exit code 0 and non-zero test count in HTML report (`app/build/reports/tests/testDebugUnitTest/index.html`).
   - Run `.\gradlew.bat runEmpiricalTests --no-daemon` on both repos: verify all 5 test suites pass.
   - Run `.\gradlew.bat assembleDebug assembleRelease --no-daemon` under JDK 17 ($env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17") on both repos: verify exit code 0 and valid APK outputs.
   - Verify post-build repository parity remains 0 diffs.

Deliver your implementation and verification report in handoff.md in your working directory.
Send a message when complete.
