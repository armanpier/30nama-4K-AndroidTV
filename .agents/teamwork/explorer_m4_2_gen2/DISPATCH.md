# Dispatch: Explorer M4.2 (Gen 2) — Programmatic Test Suites Architecture & Test Matrix

## Mission
Investigate and design the complete programmatic test suite across all subsystems and end-to-end integration:
1. Subsystem Test Modules to Design:
   - `gemini_desktop_screenshare/tests/test_auth.py`:
     - RFC 7636 PKCE S256 verifier/challenge generation and verification.
     - RFC 8252 loopback server lifecycle, port selection, timeout, and multiple-request handling (e.g. `/favicon.ico` vs `/oauth2callback`).
     - Token persistence: Windows Credential Manager (`keyring`), DPAPI encryption/decryption, session cache json validation, automatic token refresh.
   - `gemini_desktop_screenshare/tests/test_capture.py`:
     - Full desktop capture across multiple monitors with `mss`.
     - Window enumeration, title filtering, geometry extraction via `DWMWA_EXTENDED_FRAME_BOUNDS`.
     - `PrintWindow` capture with black frame detection and fallback foreground mss cropping.
     - Downscaling to max 1024x768 while preserving aspect ratio, JPEG quality 70 compression, base64 encoding.
     - Target window destruction / invalid HWND handling.
   - `gemini_desktop_screenshare/tests/test_audio.py`:
     - 16kHz PCM microphone audio recording callback and queue.
     - Silence packet injection when microphone is muted.
     - 24kHz PCM speaker playback queue and non-blocking callback.
     - Instant barge-in interruption: audio queue flush (<0.1ms), stream stop/restart.
   - `gemini_desktop_screenshare/tests/test_streaming.py`:
     - Live client setup handshake with mock WebSocket server.
     - Continuous audio and video frame packaging and transmission.
     - Server message decoding (text tokens and audio chunks).
     - Barge-in notification and local playback interruption.
     - Disconnect handling, network failure resilience, and clean session shutdown.
   - `gemini_desktop_screenshare/tests/test_ondemand.py`:
     - Instant snapshot capture of full desktop and specific window.
     - Multimodal payload formatting and REST `generateContent` execution.
     - Response parsing and markdown formatting.
     - Network timeout and API error recovery.
   - `gemini_desktop_screenshare/tests/test_e2e.py`:
     - Dual-mode end-to-end integration: starting live streaming, toggling mic mute, switching capture targets, triggering on-demand snapshot query, barge-in interruption, and clean shutdown.
   - Root Test Runner `run_tests.py`:
     - Discovers and executes all test suites (`test_backend_engine.py`, `test_ui_m3.py`, `test_m3_adversarial_challenger.py`, `test_stress_m3.py`, and all new Milestone 4 tests).
     - Outputs clear colored summary tables and returns exit code 0 when all tests pass.

## Reference Files to Inspect
- Original Request: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Document: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- Core Modules: `auth/`, `capture/`, `audio/`, `streaming/`, `ondemand/`, `ui/`, `app.py`
- Existing Tests: `gemini_desktop_screenshare/tests/test_backend_engine.py`, `test_adversarial_m2.py`, `test_ui_m3.py`, `test_m3_adversarial_challenger.py`, `test_stress_m3.py`

## Expected Output
Produce a comprehensive handoff report at:
`c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\handoff.md`
detailing:
- Detailed test matrix across all 6 test modules + `run_tests.py`.
- Mocking boundaries vs real component execution.
- Deterministic fixture design (pytest fixtures, temporary credential stores, mock audio devices).
- Concrete recommendations for the Worker implementation.


## 2026-11-08T16:21:51Z
You are Explorer M4.2 (Gen 2).
Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\
Authoritative user request: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md
Dispatch file: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\DISPATCH.md
Project plan: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md

Read your DISPATCH.md and ORIGINAL_REQUEST.md.
Investigate and design the complete programmatic test suite across all subsystems and end-to-end integration:
- Subsystem test modules: `test_auth.py`, `test_capture.py`, `test_audio.py`, `test_streaming.py`, `test_ondemand.py`, `test_e2e.py`.
- Root test runner: `run_tests.py`.
Inspect the existing codebase in `gemini_desktop_screenshare/` and existing tests in `gemini_desktop_screenshare/tests/`.

Produce your handoff report at:
`c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\handoff.md`

Remember: You are read-only. Do not modify production code files.
When finished, send a message to the orchestrator with a summary and the path to your handoff report.
