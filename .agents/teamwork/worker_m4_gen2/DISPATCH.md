# Dispatch: Worker M4 (Gen 2) — Programmatic Test Suite, Mock Servers & E2E Verification Implementation

## Mission
Implement the complete programmatic test suite, standalone offline mock servers, unified test runner, and documentation deliverables for Milestone 4:
1. `gemini_desktop_screenshare/tests/mock_servers.py`
2. `gemini_desktop_screenshare/tests/conftest.py`
3. Subsystem test suites under `gemini_desktop_screenshare/tests/`:
   - `test_auth.py`
   - `test_capture.py`
   - `test_audio.py`
   - `test_streaming.py`
   - `test_ondemand.py`
   - `test_e2e.py`
4. Root test runner `run_tests.py`
5. Documentation & requirements:
   - `gemini_desktop_screenshare/README.md` and root `README.md`
   - `gemini_desktop_screenshare/VERIFICATION.md` and root `VERIFICATION.md`
   - `gemini_desktop_screenshare/requirements.txt` and root `requirements.txt`
6. Diagnostic fixes:
   - `gemini_desktop_screenshare/tests/test_protocol_auth_adversarial.py` (guard top-level stdout re-wrap with `if __name__ == '__main__':`)
   - `gemini_desktop_screenshare/capture/screen_capture.py` (avoid redundant `attach_thread_to_input_desktop()` calls that trigger WinError 170)
7. Execute all test suites and verify 100% pass rate.

## Reference Files to Inspect First
- Authoritative Request: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Document: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- Explorer M4.1 Blueprint: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_1_gen2\handoff.md`
- Explorer M4.2 Blueprint: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\handoff.md`
- Explorer M4.3 Blueprint: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_3_gen2\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Expected Output
Produce your handoff report at:
`c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\worker_m4_gen2\handoff.md`
detailing files created/modified, test execution logs, and verification evidence.
