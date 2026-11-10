# BRIEFING — 2026-11-09T23:35:00Z

## Mission
Execute Milestone 2: Implement Iran IP/Domain/App direct bypass routing and Chocolate4Iran rule auto-updater for AsanVPN Android.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2
- Original parent: d14990da-b9ef-4371-b0a5-2617d9e7778c
- Milestone: Milestone 2 (Backend Engine)
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2
- Original parent: 4b000716-2a65-4da7-a250-c5ab7038a555
- Milestone: Milestone 2 (Iran Bypass Routing & Chocolate4Iran Auto-Update)

## 🔒 Key Constraints
- Genuine implementation only, no cheating, no mock/dummy implementations masquerading as real.
- Sounddevice audio pipeline: 16kHz in (100ms blocks, 3200B), 24kHz out, queue drain interruption (<0.1ms).
- Screen & Window capture: OpenInputDesktop/SetThreadDesktop, mss, PrintWindow PW_RENDERFULLCONTENT, DPI awareness, sanitize titles.
- OAuth: RFC 8252 + RFC 7636 (PKCE S256), loopback 127.0.0.1:0, Windows Credential Manager / DPAPI, proactive refresh.
- Gemini Live WebSocket: websockets 14+ `additional_headers`, BidiGenerateContent, setup frame, 1 FPS JPEG + 16kHz audio streaming, handle serverContent.
- On-Demand Capture Client: snapshot capture + multimodal prompt, REST / WebSocket fallback, response parsing.
- Exclusive write ownership restricted to:
  - `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`
  - `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`
  - `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`
  - `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`
  - `android/app/src/main/java/com/asanvpn/app/MainActivity.kt`
  - `android/app/src/main/java/com/asanvpn/app/data/PreferencesManager.kt`
- Java 17 compatibility.
- Genuine real logic with error handling, atomic file updates, SHA256 checksum verification, and graceful bypass failure handling.

## Current Parent
- Conversation ID: 4b000716-2a65-4da7-a250-c5ab7038a555
- Updated: 2026-11-09T23:35:00Z

## Task Summary
- **What to build**: Iran app bypass helper with 60+ packages, V2Ray routing direct rules (geosite:category-ir, geosite:ir, domain:ir, geoip:private, geoip:ir), GeoAssetManager with atomic SHA256 update, PreferencesManager tracking, and MainActivity lifecycle integration.
- **Success criteria**: Gradle compileDebugSources, testDebugUnitTest, and assembleDebug exit code 0; genuine bypass and auto-updating logic implemented.
- **Interface contracts**: PROJECT.md § Interface Contracts
- **Code layout**: PROJECT.md § Code Layout

## Change Tracker
- **Files modified**:
  - `android/app/src/main/java/com/asanvpn/app/util/IranAppBypassHelper.kt`: Catalog of 60+ Iranian app packages and safe `applyDisallowedApplications`
  - `android/app/src/main/java/com/asanvpn/app/service/AsanVpnService.kt`: Integrated `IranAppBypassHelper.applyDisallowedApplications(builder, this)`
  - `android/app/src/main/java/com/asanvpn/app/service/v2ray/V2RayConfigBuilder.kt`: Direct domain rules (`geosite:category-ir`, `geosite:ir`, `domain:ir`) and IP rules (`geoip:private`, `geoip:ir`)
  - `android/app/src/main/java/com/asanvpn/app/data/PreferencesManager.kt`: Added `lastGeoRulesCheckTime` persistence property
  - `android/app/src/main/java/com/asanvpn/app/util/GeoAssetManager.kt`: APK asset initialization, jsDelivr/GitHub SHA256 polling, atomic download and replacement
  - `android/app/src/main/java/com/asanvpn/app/MainActivity.kt`: Asset initialization and background update check trigger
- **Build status**: PASS (`compileDebugSources`, `testDebugUnitTest`, `assembleDebug` all exit 0)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS. All compilation and unit tests passed cleanly with JDK 17.
- **Lint status**: 0 errors. Clean compilation.
- **Tests added/modified**: Existing unit test suite passes with exit code 0.

## Loaded Skills
- None specified

## Key Decisions Made
- Defensive per-package iteration with try-catch in `IranAppBypassHelper` prevents crashes from missing apps while ensuring installed apps bypass `/dev/tun`.
- Dual CDN (jsDelivr primary, GitHub Raw fallback) SHA256 check minimizes bandwidth to ~85 bytes and guarantees file integrity before atomic swap.
- Background check in `MainActivity` with 5-second initial delay prevents contention with startup and initial UI rendering.

## Artifact Index
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\DISPATCH.md` — assignment
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\progress.md` — heartbeat and progress
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m2\handoff.md` — completion report
