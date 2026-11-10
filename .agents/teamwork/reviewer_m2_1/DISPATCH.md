# Dispatch: Reviewer M2_1 — Routing & Application Bypass Review

**Task**: Review Milestone 2 implementation for routing correctness and application bypass
**Inputs**:
- `ORIGINAL_REQUEST.md`: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- `PROJECT.md`: `c:\Users\Arman\Documents\antigravity\quirky-turing\PROJECT.md`
- Worker M2 handoff: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\handoff.md`
- Code files:
  - `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`
  - `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
  - `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`

**Scope & Verification**:
1. Verify `IranAppBypassHelper.kt` packages: check presence of Nobitex (`app.nobitex`, `market.nobitex`, `ir.nobitex`), Up (`com.sibche.aspardproject.app`, `ir.nasimpay.app`, `com.asanpardakht.app`), Cafe Bazaar (`com.farsitel.bazaar`), and other banking/crypto/transport apps.
2. Verify that `applyDisallowedApplications` catches `PackageManager.NameNotFoundException` per package so missing packages never crash the VPN service.
3. Verify `AsanVpnService.kt`: confirm `IranAppBypassHelper.applyDisallowedApplications(builder, this)` is called inside `startVpnTunnel`.
4. Verify `V2RayConfigBuilder.kt`: confirm Rule 1 contains `"domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]` with `"outboundTag": "direct"`, and Rule 2 contains `"ip": ["geoip:private", "geoip:ir"]` with `"outboundTag": "direct"`, and `"domainStrategy": "IPIfNonMatch"`.
5. Verify clean compilation with JDK 17:
   `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`
6. Record verdict (APPROVE or REQUEST_CHANGES) in:
   `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m2_1\handoff.md`

## 2026-11-09T23:35:47Z
[Message] timestamp=2026-11-09T23:35:47Z sender=4b000716-2a65-4da7-a250-c5ab7038a555 priority=MESSAGE_PRIORITY_HIGH content=You are reviewer_m2_1, a code review agent.
Your working directory is: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m2_1
Your identity: reviewer_m2_1 (Reviewer)
Your parent orchestrator conversation ID is: 4b000716-2a65-4da7-a250-c5ab7038a555

MANDATORY: Read ORIGINAL_REQUEST.md before starting work:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md

Read PROJECT.md:
c:\Users\Arman\Documents\antigravity\quirky-turing\PROJECT.md

Read your dispatch task:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m2_1\DISPATCH.md

Read Worker M2 handoff:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\handoff.md

Review:
1. `IranAppBypassHelper.kt`: check packages (Nobitex, Up, Cafe Bazaar, banking, transport apps) and verify `PackageManager.NameNotFoundException` is defensively caught.
2. `AsanVpnService.kt`: verify `IranAppBypassHelper.applyDisallowedApplications(builder, this)` is called inside `startVpnTunnel`.
3. `V2RayConfigBuilder.kt`: verify direct routing rules for `"domain": ["geosite:category-ir", "geosite:ir", "domain:ir"]` and `"ip": ["geoip:private", "geoip:ir"]` with `domainStrategy: "IPIfNonMatch"`.
4. Compile with JDK 17:
   `$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"; Set-Location "c:\Users\Arman\Documents\antigravity\quirky-turing\android"; .\gradlew.bat compileDebugSources --no-daemon`
5. Record verdict (APPROVE or REQUEST_CHANGES) in:
   `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\reviewer_m2_1\handoff.md`
6. Send message to parent orchestrator with summary and explicit verdict.
