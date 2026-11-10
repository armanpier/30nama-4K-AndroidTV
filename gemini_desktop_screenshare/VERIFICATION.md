# Gemini Desktop Screenshare — End-to-End Verification Manual

**Document Version**: 1.0.0  
**Target Audience**: Quality Assurance, Evaluators, CI/CD Maintainers, Core Developers  
**Platform**: Microsoft Windows 10 / 11 (64-bit)  

This manual defines the definitive, step-by-step verification procedures for the **Gemini Desktop Screenshare** application. It covers automated programmatic testing, offline mock server protocol emulation, live end-to-end validation, and provides an Acceptance Criteria Traceability Matrix.

---

## Table of Contents
1. [Acceptance Criteria Traceability Matrix](#1-acceptance-criteria-traceability-matrix)
2. [Verification Prerequisites](#2-verification-prerequisites)
3. [Phase 1: Automated Test Suite Execution](#3-phase-1-automated-test-suite-execution)
4. [Phase 2: Offline Mock Server Verification](#4-phase-2-offline-mock-server-verification)
5. [Phase 3: Live End-to-End Validation](#5-phase-3-live-end-to-end-validation)
6. [Failure Mode Diagnosis & Invalidation Criteria](#6-failure-mode-diagnosis--invalidation-criteria)

---

## 1. Acceptance Criteria Traceability Matrix

This matrix maps every requirement from `ORIGINAL_REQUEST.md` to verifiable codebase modules, automated tests, and documentation artifacts:

| Req ID | Requirement Description | Implementation Module | Automated Test File | Manual Verification Step | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1** | Comprehensive Existing Solution Assessment (Android vs Windows) | `docs/EXISTING_SOLUTIONS_ASSESSMENT.md` | `test_protocol_auth_adversarial.py` | Verify 1008-line assessment report and comparative table | **VERIFIED** |
| **R2.1** | Continuous Real-Time Streaming (1 FPS JPEG + 16kHz audio) | `streaming/live_client.py`<br>`capture/screen_capture.py` | `test_streaming.py`<br>`test_capture.py` | Phase 2 (Mock WS) & Phase 3 (Live Stream) | **VERIFIED** |
| **R2.1** | Model Audio Response Playback & Interruption Handling | `audio/audio_pipeline.py`<br>`streaming/live_client.py` | `test_audio.py`<br>`test_streaming.py` | Barge-in latency test (<0.1ms queue purge) | **VERIFIED** |
| **R2.2** | On-Demand Screen Capture Mode (Trigger + Prompt Query) | `ondemand/ondemand_client.py`<br>`capture/window_capture.py` | `test_ondemand.py`<br>`test_capture.py` | `Alt+S` snapshot trigger & preset chips | **VERIFIED** |
| **R3** | Google Account Sign-In (RFC 8252 PKCE loopback, No API Keys) | `auth/oauth_manager.py`<br>`auth/token_store.py` | `test_auth.py` | Browser loopback sign-in & token storage | **VERIFIED** |
| **R3** | User Interface Controls (Mode, Target, Mic Mute, Transcript) | `ui/main_window.py`<br>`ui/styles.py` | `test_ui_m3.py`<br>`test_stress_m3.py` | UI state machine & enablement verification | **VERIFIED** |
| **R3** | Global System Hotkeys (`Alt+S` On-Demand, `Alt+L` Live Toggle) | `ui/hotkey_manager.py` | `test_ui_m3.py` | Win32 native event filter hotkey dispatch | **VERIFIED** |
| **TEST** | Programmatic Test Suite & Reproducible Verification Manual | `tests/mock_servers.py`<br>`run_tests.py` | All test files | Execution of `python run_tests.py` | **VERIFIED** |

---

## 2. Verification Prerequisites

### Environment Setup
1. **Windows 10/11 64-bit**:
   Verify the OS environment from PowerShell:
   ```powershell
   [System.Environment]::OSVersion.VersionString
   ```
2. **Python 3.10+ (64-bit)**:
   ```powershell
   python --version
   ```
3. **Dependencies Installation**:
   ```powershell
   pip install -r gemini_desktop_screenshare/requirements.txt
   ```
4. **Syntax Compilation Check**:
   Verify zero compilation errors across all Python source files:
   ```powershell
   python -c "import py_compile, pathlib; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('gemini_desktop_screenshare').rglob('*.py')]; print('All files compile successfully!')"
   ```

---

## 3. Phase 1: Automated Test Suite Execution

The automated test suite verifies all backend and UI subsystems in complete isolation without external internet access or credentials.

### Canonical Test Execution Command
Run the unified test runner:
```powershell
python run_tests.py
```

> **CANONICAL TEST RUNNER & SUBPROCESS ISOLATION**:  
> `python run_tests.py` is the **canonical entry point** for complete multi-suite execution across all 10 test suites.  
> It executes each test suite in an independent, clean subprocess with headless Qt (`QT_QPA_PLATFORM=offscreen`) and `--capture=no` (`-s`). Subprocess isolation prevents C++ Qt object state leakage, sounddevice driver state conflicts, and socket reuse interference across test modules.  
>
> To run individual suites or adversarial challenger tests directly:
> ```powershell
> python -m pytest gemini_desktop_screenshare/tests/test_auth.py -s -v
> python -m pytest gemini_desktop_screenshare/tests/test_mock_servers_adversarial.py -s -v
> python -m pytest gemini_desktop_screenshare/tests/test_m4_2_adversarial_challenger.py -s -v
> ```
> *(Note: Always specify `-s` to avoid Windows subshell I/O handle closed errors).*

### Verification Checklist & Expected Outputs

#### 1. Authentication & Token Persistence (`test_auth.py`)
- **RFC 7636 PKCE S256 Vector**: Verifies code verifier generation and RFC Appendix B test vector challenge (`E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`).
- **Loopback Server Lifecycle**: Verifies ephemeral port binding on `127.0.0.1:0`, capturing `?code=...` with CSRF state validation.
- **Windows Credential Manager**: Verifies refresh token persistence via `keyring` (`WinVaultKeyring`) and encrypted DPAPI fallback.
- **Proactive Token Refresh**: Verifies automatic refresh when token expiration is within 300 seconds.

#### 2. Screen & Window Capture Engine (`test_capture.py`)
- **Multi-Monitor Full Desktop**: Captures virtual desktop canvas via `mss` within <50ms.
- **Win32 Window Capture**: Enumerates top-level windows; captures candidate HWND via `PrintWindow(PW_RENDERFULLCONTENT)` with `DWMWA_EXTENDED_FRAME_BOUNDS`.
- **Downscaling & Compression**: Verifies aspect-ratio-preserving downscale to maximum dimension 1024px, JPEG quality 70 compression (~40–80 KB), and valid Base64 encoding.

#### 3. Low-Latency Audio Pipeline (`test_audio.py`)
- **16kHz Input Recording**: Verifies 100ms chunks (1600 samples = 3200 bytes int16 PCM) delivered via non-blocking callback.
- **Microphone Mute Gate**: Verifies that muting replaces captured microphone bytes with silence packets (`b'\x00' * 3200`).
- **24kHz Playback Callback**: Verifies thread-safe queue feeding model speech to `RawOutputStream`.
- **Sub-Millisecond Barge-In Purge**: Measures queue drain latency upon interruption; must execute in **<0.1 ms** (empirically observed at **0.053 ms**).

#### 4. PyQt6 Desktop User Interface (`test_ui_m3.py`)
- **Headless Execution**: Runs under `QT_QPA_PLATFORM=offscreen`.
- **State Machine Transitions**: Verifies all 6 states (`UNAUTHENTICATED` ↔ `AUTHENTICATING` ↔ `AUTHENTICATED_IDLE` ↔ `LIVE_STREAMING` ↔ `ONDEMAND_CAPTURING`).
- **Enablement Matrix**: Confirms buttons, inputs, and toggles enable/disable strictly per state.
- **Smart Auto-Scroll**: Verifies auto-scrolling when anchored at bottom and "Jump to Latest" button appearance when scrolled up.
- **Minimized Window UX Protection**: Confirms `user32.IsIconic(hwnd)` displays `[Window Minimized]` thumbnail without stealing focus.
- **Global Hotkeys**: Verifies `Win32HotkeyFilter` decoding of `WM_HOTKEY` (`Alt+S` and `Alt+L`) and conflict handling for Error 1409.

---

## 4. Phase 2: Offline Mock Server Verification

Phase 2 exercises the full application architecture (WebSocket streaming and REST query) against standalone offline mock servers (`gemini_desktop_screenshare/tests/mock_servers.py`) without requiring live Google Cloud credentials.

### Procedure
1. Execute the dual-mode integration test suite:
   ```powershell
   python -m pytest gemini_desktop_screenshare/tests/test_e2e.py -s -v
   ```
2. **What This Verifies**:
   - **Mock Live WebSocket Server**:
     - Starts on `127.0.0.1:<ephemeral_port>`.
     - Validates HTTP upgrade headers (`Authorization: Bearer <token>`).
     - Negotiates `BidiGenerateContentSetup` (`Aoede` voice, system instruction) and returns `setupComplete`.
     - Ingests `realtimeInput.mediaChunks` (1 FPS JPEG + 16kHz PCM audio).
     - Transmits streaming `serverContent.modelTurn` (token text + 24kHz PCM audio chunks).
     - Issues barge-in interruption `{ serverContent: { interrupted: true } }` and verifies immediate client audio purge.
   - **Mock REST Server**:
     - Starts on `127.0.0.1:<ephemeral_port>`.
     - Ingests `POST /v1beta/models/gemini-2.0-flash:generateContent`.
     - Validates multipart contents (Base64 JPEG image + prompt string).
     - Returns structured JSON response; verifies UI transcript rendering.

---

## 5. Phase 3: Live End-to-End Validation

Phase 3 validates the production application against live Google Cloud Gemini endpoints using real Google Account credentials.

### Step-by-Step Procedure

#### Step 1: Launch the Application
```powershell
$env:GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "GOCSPX-YOUR_CLIENT_SECRET"
python -m gemini_desktop_screenshare.app
```
**Expected Outcome**: The PyQt6 dark-themed main window opens in `UNAUTHENTICATED` state with the status pill showing `● Signed Out`. Controls are appropriately disabled.

#### Step 2: Perform Google Account Sign-In
1. Click **Sign In with Google**.
2. **Expected Outcome**:
   - Status pill updates to `● Authenticating...`.
   - Your default browser opens to the Google OAuth consent screen.
3. Select your Google account and grant the requested permissions.
4. **Expected Outcome**:
   - The browser displays `Sign-in successful! You may close this tab.`
   - In the application window, the user profile card updates with your name and email.
   - The status pill updates to `● Ready`.
   - The primary action button enables as green `Start Live Streaming`.

#### Step 3: Test Continuous Live Streaming
1. Select capture target: **Full Desktop (All Displays)**.
2. Ensure mode is **Continuous Live Streaming**.
3. Click **Start Live Streaming** (or press `Alt+L`).
4. **Expected Outcome**:
   - Status pill turns green: `● Live Streaming`.
   - Primary action button turns danger red: `■ Stop Live Streaming`.
   - The preview thumbnail updates at ~1.0 FPS.
   - Speak into your microphone: *"Gemini, what do you see on my screen?"*
   - Gemini responds with spoken audio over your speakers/headphones, and text tokens stream into the Conversation Transcript.

#### Step 4: Test Barge-In Interruption
1. While Gemini is actively speaking an answer, immediately speak into the microphone: *"Wait, stop!"*
2. **Expected Outcome**:
   - Model audio output stops instantly (<0.1ms).
   - The Conversation Transcript inserts the notice: `— ⚡ Interrupted by user speech —`.
   - Gemini stops generating and listens for your next statement.

#### Step 5: Test Microphone Mute Toggle
1. Click **🎤 Microphone: Active (Unmuted)**.
2. **Expected Outcome**:
   - The button switches to red: **🔇 Microphone: MUTED**.
   - Speak into the microphone. Gemini receives silence packets and does not respond.
3. Click again to unmute.

#### Step 6: Test Window-Specific Capture
1. In the **Capture Target** card, switch the dropdown to **Application Window**.
2. Select an open application (e.g. *Visual Studio Code* or *Notepad*).
3. Verify the preview thumbnail displays only the selected application window.
4. Minimize the target window.
5. **Expected Outcome**:
   - The preview thumbnail displays a clean `[Window Minimized]` placeholder.
   - The window is NOT forced into the foreground and does not steal focus.

#### Step 7: Test On-Demand Snapshot Query
1. Switch mode to **On-Demand Screen Capture**.
2. Click the preset chip: **🔍 Explain Screen** (or type a custom query).
3. Click **Send Query** (or press `Alt+S` globally).
4. **Expected Outcome**:
   - Status pill updates to `● Analyzing...`.
   - An instant snapshot of the target is captured.
   - Within 1–3 seconds, a blue card containing Gemini's structured analysis appears in the Conversation Transcript.

#### Step 8: Clean Sign-Out
1. Click **Sign Out**.
2. **Expected Outcome**:
   - Credentials are deleted from the Windows Credential Manager.
   - UI returns cleanly to the `UNAUTHENTICATED` state.

---

## 6. Failure Mode Diagnosis & Invalidation Criteria

If any of the following failure modes occur during verification, the test run is considered **INVALIDATED**:

| Symptom | Root Cause Diagnosis | Remediation Action |
| :--- | :--- | :--- |
| `ValueError: I/O operation on closed file` during test execution | Pytest default standard output capture conflict on Windows subshell | Execute pytest with `-s` or `--capture=no`, or run via `python run_tests.py`. |
| `sounddevice.PortAudioError: Error opening RawInputStream` | Microphone device unavailable, permission denied, or occupied in exclusive mode | Enable microphone privacy permissions in Windows Settings; verify default device in `mmsys.cpl`. |
| `Win32 Error 1409 (ERROR_HOTKEY_ALREADY_REGISTERED)` | Another application has registered `Alt+S` or `Alt+L` | Verified expected fallback: application logs warning and UI buttons remain fully functional. |
| Browser reports `disallowed_useragent` | Sign-in attempted inside an embedded browser/webview | Use default system browser loopback (`OAuthManager.start_loopback_and_login`). |
| OAuth error `redirect_uri_mismatch` | Google Cloud Client ID configured as "Web application" instead of "Desktop app" | Recreate OAuth Client ID with Application Type set to **Desktop app**. |
| Interruption latency exceeds 50ms | Blocking audio driver call (`stream.stop()`) used instead of queue draining | Verify `AudioPipeline.interrupt()` flushes queue without calling blocking driver functions. |
