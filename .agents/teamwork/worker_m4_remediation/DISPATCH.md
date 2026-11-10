# Dispatch: Worker M4 Remediation (Gen 2) — Apply Iteration 2 Fixes

## Mission
Apply the specific remediation fixes identified by Reviewer M4.2 and Challenger M4.1 during Gate 4 Iteration 1:

1. **`gemini_desktop_screenshare/tests/test_m3_adversarial_challenger.py`**:
   - In `test_adversarial_destroyed_hwnd_preview_and_ondemand` (lines 604–609):
     Replace the fixed `time.sleep(0.1)` with a robust polling loop:
     ```python
     deadline = time.time() + 2.0
     while time.time() < deadline and window.state != AppState.AUTHENTICATED_IDLE:
         QApplication.processEvents()
         time.sleep(0.02)
     assert window.state == AppState.AUTHENTICATED_IDLE
     ```
     This eliminates the intermittent timing flake under multi-suite CPU load.

2. **`gemini_desktop_screenshare/tests/test_protocol_auth_adversarial.py`**:
   - Wrap top-level benchmark execution (lines 25–327) inside:
     ```python
     def main():
         ...
     if __name__ == "__main__":
         main()
     ```
     This ensures pytest collection on `gemini_desktop_screenshare/tests/` never triggers unhandled assertion errors during import.
   - Update line 239 from deprecated `mss.mss()` to `mss.MSS()`.

3. **`gemini_desktop_screenshare/tests/mock_servers.py`**:
   - In `MockGeminiLiveServer._ws_handler`:
     Guard incoming messages against scalar JSON values:
     ```python
     if not isinstance(msg, dict):
         continue
     ```
     And guard setup handshake parsing:
     ```python
     if not isinstance(setup_data, dict) or "setup" not in setup_data:
         # discard or handle gracefully
     ```
     This prevents unhandled `TypeError` / code 1011 when unexpected frames arrive.

4. **`gemini_desktop_screenshare/VERIFICATION.md` & root `VERIFICATION.md`**:
   - Update documentation to explicitly state that `python run_tests.py` is the canonical test runner because it provides clean subprocess isolation across Qt, audio, and network sockets.

5. **Test Execution & Verification**:
   - Execute `python run_tests.py` and verify all 10 suites pass with 100% success.
   - Execute `pytest gemini_desktop_screenshare/tests/test_mock_servers_adversarial.py -s -v` to ensure Challenger M4.1's stress tests pass.
   - Execute `pytest gemini_desktop_screenshare/tests/test_m4_2_adversarial_challenger.py -s -v` to ensure Challenger M4.2's stress tests pass.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Produce your completion handoff report at:
`c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m4_remediation\handoff.md`
