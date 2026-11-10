## 2026-11-08T16:18:48Z
Investigate existing solutions for live-screensharing a Windows desktop with Gemini like on Android, and build a Windows application providing both real-time live desktop streaming and on-demand screen capture with Gemini using Google Account sign-in.

Working directory: ~/teamwork_projects/gemini_desktop_screenshare
Integrity mode: development

## Requirements

### R1. Existing Solution Assessment
Investigate and document existing official or community methods and tools for live screensharing a Windows desktop with Gemini (similar to Android's Gemini Live screen sharing), including Google Account authentication options for desktop vs Android, their capabilities, current limitations, and whether they satisfy desktop live sharing.

### R2. Dual-Mode Desktop Screen Sharing Application
If existing tools are insufficient or absent, implement a Windows application supporting two interaction modes:
1. Continuous real-time streaming: capturing live desktop screen frames and microphone audio, streaming them to Gemini, and playing back model audio responses.
2. On-demand capture: capturing the desktop screen or selected window via a hotkey or button trigger and sending the screenshot with a user query to Gemini.

### R3. Authentication and User Interface
Authenticate users via Google Account sign-in rather than requiring API keys, mirroring the Gemini mobile app sign-in experience. Provide a user interface or control mechanism to manage Google sign-in status, select the capture target (full screen or specific window), toggle microphone audio, and switch between continuous live streaming and on-demand capture.

## Acceptance Criteria

### Research and Assessment
- [ ] Comprehensive documentation of existing tools, APIs, authentication mechanisms, and workflows for Windows desktop Gemini screen sharing, comparing their capabilities to Android's native screen sharing.

### Application Functionality
- [ ] User authentication functions via Google Account sign-in (OAuth / Google login flow) without requiring manual API key entry.
- [ ] Application captures desktop screen frames and streams them continuously with microphone audio over a live Gemini session.
- [ ] Application receives and plays back real-time audio responses from Gemini during live streaming.
- [ ] On-demand mode successfully captures a snapshot of the display or chosen window upon trigger and returns Gemini's multimodal response.
- [ ] Capture targets and audio controls can be toggled via the user interface.

### Verification and Quality
- [ ] Programmatic test suite covering screen capture routines, audio device handling, and authentication/communication flows (with mock/emulated responses).
- [ ] End-to-end verification instructions and documentation allowing reproducible startup and testing on Windows.

---
RESUMPTION CONTEXT:
You are orchestrator_gen2, succeeding the previous orchestrator which completed Milestones 1, 2, and 3:
1. Milestone 1 (Assessment & Architecture Document, R1): Completed and Verified (Gate PASSED: CLEAN audit, 2x APPROVE, 2x CONFIRMED). Document is located at `gemini_desktop_screenshare/docs/EXISTING_SOLUTIONS_ASSESSMENT.md`.
2. Milestone 2 (Core Backend Engine, R2.1, R2.2, R3): Completed and Verified (Gate PASSED: 5 remediation fixes verified passing `test_backend_engine.py` and `test_adversarial_m2.py`). Modules: `config.py`, `auth/`, `capture/`, `audio/`, `streaming/`, `ondemand/`.
3. Milestone 3 (Desktop User Interface & Interaction Controls, R3): Completed and Verified (Gate PASSED: 3 remediation fixes verified; 43/43 tests pass across `test_ui_m3.py`, `test_m3_adversarial_challenger.py`, and `test_stress_m3.py`). Modules: `ui/styles.py`, `ui/hotkey_manager.py`, `ui/main_window.py`, `app.py`.

YOUR REMAINING SCOPE:
- Milestone 4: Programmatic Test Suite & E2E Verification
  - Implement mock servers and test suite covering offline mock Gemini Live WebSocket server and mock REST server.
  - Implement unified test runner (`run_tests.py`), README.md, and VERIFICATION.md providing reproducible startup and verification steps.
  - Execute Gate 4 review and audit.
- Final Verification & Claim Victory to Sentinel when complete.
