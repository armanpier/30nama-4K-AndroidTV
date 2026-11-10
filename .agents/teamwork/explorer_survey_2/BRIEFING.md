# BRIEFING — 2026-11-09T22:50:00Z

## Mission
Survey VPN routing, Iran IP/domain/app bypass, and chocolate4iran rule updating for AsanVPN Android.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2
- Original parent: 4b000716-2a65-4da7-a250-c5ab7038a555
- Milestone: M1_SURVEY

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Scope limited to routing configuration, geoip/geosite assets, chocolate4iran updates, and Iran app bypass
- Deliver handoff.md with 5-component report structure

## Current Parent
- Conversation ID: 4b000716-2a65-4da7-a250-c5ab7038a555
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `V2RayConfigBuilder.kt`: analyzed routing rules generation (lines 144–194)
  - `V2RayCoreManager.kt`: analyzed asset copying and `Libv2ray.initCoreEnv` (lines 39–56)
  - `AsanVpnService.kt`: analyzed `VpnService.Builder` and `addDisallowedApplication` (lines 105–120)
  - `AppUpdateManager.kt` & `PreferencesManager.kt`: investigated HTTP client, resilient DNS, and storage
  - `assets/`: examined `geoip.dat`, `geosite.dat`, `custom_routing_white_iran`
  - GitHub & jsDelivr Chocolate4U/Iran-v2ray-rules repository, releases API, file formats, and SHA256 checksums
  - Iranian application package identifiers (Nobitex, Up, Cafe Bazaar, banking, telecom, etc.)
  - Gradle JDK 17 build verified via `./gradlew tasks --dry-run`
- **Key findings**:
  - `V2RayConfigBuilder.kt` lacks `geoip:ir` and `geosite:ir` / `geosite:category-ir` routing rules; currently has only 10 hardcoded domains.
  - Assets are stored in `context.getDir("assets", Context.MODE_PRIVATE)` (`/data/user/0/com.asanvpn.app/app_assets`), which is writable at runtime.
  - Chocolate4U releases `geoip.dat` (~16.5MB) and `geosite.dat` (~8.5MB) along with 85-byte `.sha256sum` files accessible via jsDelivr and GitHub raw.
  - `VpnService.Builder.addDisallowedApplication` allows per-app kernel-level bypass for Iranian apps; non-installed apps throw `PackageManager.NameNotFoundException` which must be caught per package.
- **Unexplored areas**: None within survey scope.

## Key Decisions Made
- Formulated concrete implementation strategy covering routing rules, per-app bypass, and auto-updating assets with checksum verification.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — final survey report
