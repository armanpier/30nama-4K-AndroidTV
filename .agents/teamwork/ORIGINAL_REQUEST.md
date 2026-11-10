# Original User Request

## Initial Request — 2026-11-09T22:38:51Z

Implement app log limiting, concise link test logging for users and admins, Iran IP/domain/app routing bypass with auto-updating chocolate4iran rules, and repository synchronization for AsanVPN Android.

Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\android
Integrity mode: development

## Requirements

### R1. App Log Capping and Redaction
- Cap the application log buffer to a maximum of 100 entries to reduce application load.
- Redact detailed/full link configurations from the log: neither admin nor regular users need to see full raw link tests in the log.
- Format link test log entries so users and admins can see link testing progress and results directly in the log containing only the link remark, delay (latency number in ms), and success or failure status.

### R2. Iran IP, Domain, and Application Direct Bypass Routing
- Exclude Iran IP addresses and Iran domains from the VPN tunnel routing using chocolate4iran geoip and geosite rule assets so traffic to them routes directly.
- Exclude Iranian applications (e.g. Nobitex, Up آپ, Cafe Bazaar کافه بازار, and other Iranian apps) from tunnel routing so their traffic bypasses the VPN.
- Provide a regular update mechanism for chocolate4iran geoip and geosite rule assets when new versions are released.

### R3. Repository Parity and Build Verification
- Maintain exact code and resource parity between:
  - `c:\Users\Arman\Documents\antigravity\quirky-turing\android`
  - `C:\Users\Arman\Documents\antigravity\AsanVPN\android`
- Ensure release and debug builds compile successfully with JDK 17 (`$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"`).

## Acceptance Criteria

### Log Limiting and Formatting
- [ ] Application log buffer size does not exceed 100 entries during runtime.
- [ ] Log output for link tests displays only link remark, delay (ms), and success/failure status without dumping full raw link test details or sensitive configs.

### Routing Exclusions and Rule Updates
- [ ] Traffic destined for Iran IPs and Iran domains (via chocolate4iran geoip and geosite rules) routes directly outside the VPN tunnel.
- [ ] Traffic from specified Iranian apps (including Nobitex, Up, Cafe Bazaar) is excluded from the VPN tunnel.
- [ ] Mechanism for regularly updating chocolate4iran geoip and geosite rule assets is functional and handles version updates.

### Parity and Build
- [ ] All code and configuration changes are identical between `quirky-turing\android` and `AsanVPN\android`.
- [ ] Android project compiles successfully using Gradle with JDK 17 (`$env:JAVA_HOME = "C:\Users\Arman\.jdks\jdk-17"`).
