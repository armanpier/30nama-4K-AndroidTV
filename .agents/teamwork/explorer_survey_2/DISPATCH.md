# Dispatch: Explorer Survey 2

**Task**: Survey Iran IP/Domain/App Routing Bypass & chocolate4iran Rule Update Mechanism
**Scope**:
- Examine routing configuration generation and VPN service engine in `c:\Users\Arman\Documents\antigravity\quirky-turing\android`.
- Check how routing rules (direct, proxy, block) and assets (geoip.dat, geosite.dat, etc.) are bundled and used.
- Investigate chocolate4iran repository/releases format, URLs, asset files (geoip-iran, geosite-iran, etc.), download/update logic, version checking, storage location, and how the core loads them.
- Investigate application package bypass routing in Android VpnService (`VpnService.Builder.addDisallowedApplication`) or per-app proxy / routing rules for Iranian apps (Nobitex, Up, Cafe Bazaar, etc.).
- Formulate concrete design for auto-updating chocolate4iran geoip/geosite assets and bypassing Iran IPs/domains/apps.
- Write your comprehensive findings to `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2\handoff.md`.

## 2026-11-09T22:41:27Z
You are explorer_survey_2, an exploration agent.
Your working directory is: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2
Your identity: explorer_survey_2 (Explorer)
Your parent orchestrator conversation ID is: 4b000716-2a65-4da7-a250-c5ab7038a555

MANDATORY: Read ORIGINAL_REQUEST.md before starting work:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md

Also read your dispatch task:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2\DISPATCH.md

Your task is to survey VPN routing, Iran IP/domain/app bypass, and chocolate4iran rule updating:
1. Examine routing configuration generation and VPN service engine in `c:\Users\Arman\Documents\antigravity\quirky-turing\android` (compare with `C:\Users\Arman\Documents\antigravity\AsanVPN\android` if needed).
2. Trace how routing rules (direct, proxy, block) and assets (geoip.dat, geosite.dat, etc.) are bundled and used.
3. Investigate chocolate4iran repository/releases format, URLs, asset files (geoip-iran, geosite-iran, etc.), download/update logic, version checking, storage location, and how the core loads them.
4. Investigate application package bypass routing in Android VpnService (`VpnService.Builder.addDisallowedApplication`) or per-app proxy / routing rules for Iranian apps (Nobitex, Up آپ, Cafe Bazaar کافه بازار, and other common Iranian packages).
5. Formulate the concrete implementation strategy for:
   - Direct bypass routing of Iran IPs and domains using chocolate4iran geoip/geosite rules.
   - Excluding specified Iranian apps (including Nobitex, Up, Cafe Bazaar, etc.) from VPN tunnel routing.
   - Providing a functional, regular update mechanism for chocolate4iran geoip and geosite rule assets handling version updates.
6. Write your comprehensive findings and recommendations to:
   c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_survey_2\handoff.md
7. When done, send a message to your parent orchestrator with a concise summary and confirm handoff.md is ready.
