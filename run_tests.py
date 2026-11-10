#!/usr/bin/env python3
"""
Root Unified Test Runner for Gemini Desktop Screenshare.
Discovers and executes all programmatic test suites in isolated subprocesses
with headless Qt configuration (QT_QPA_PLATFORM=offscreen) and pytest capture=no (-s)
to prevent Windows subshell closed-file I/O conflicts.
Renders clean execution metrics and exits with code 0 on complete pass.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

# Enforce offscreen Qt platform across the test execution environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Registry of all recognized test suites in logical execution order
TEST_SUITES = [
    # --- Milestone 4 Core Subsystems & Mock Servers ---
    {
        "name": "Auth & Persistence",
        "path": "gemini_desktop_screenshare/tests/test_auth.py",
        "description": "RFC 7636 PKCE S256, loopback redirect, DPAPI & Credential Manager, MockOAuthServer",
        "fast": True,
    },
    {
        "name": "Screen & Window Capture",
        "path": "gemini_desktop_screenshare/tests/test_capture.py",
        "description": "mss multi-monitor capture, HWND enumeration, Unicode safety, minimized recovery, 1024px scaler",
        "fast": True,
    },
    {
        "name": "Bidirectional Audio Pipeline",
        "path": "gemini_desktop_screenshare/tests/test_audio.py",
        "description": "16kHz mic input, silence injection when muted, 24kHz playback queue, <0.1ms barge-in purge",
        "fast": True,
    },
    {
        "name": "Gemini Multimodal Live WS",
        "path": "gemini_desktop_screenshare/tests/test_streaming.py",
        "description": "Setup handshake, 1.0 FPS video, 16kHz audio, text/audio synthesis, barge-in, MockGeminiLiveServer",
        "fast": True,
    },
    {
        "name": "On-Demand REST Query",
        "path": "gemini_desktop_screenshare/tests/test_ondemand.py",
        "description": "generateContent multimodal payload, Bearer auth, candidate parsing, MockGeminiRestServer",
        "fast": True,
    },
    {
        "name": "Dual-Mode End-to-End Integration",
        "path": "gemini_desktop_screenshare/tests/test_e2e.py",
        "description": "Headless PyQt6 GUI + AsyncWorker, live stream turn cycle, barge-in banner, on-demand query",
        "fast": True,
    },
    # --- Milestone 3 UI & Interaction Controls ---
    {
        "name": "UI Hierarchy & State Machine",
        "path": "gemini_desktop_screenshare/tests/test_ui_m3.py",
        "description": "PyQt6 components, ENABLEMENT_MATRIX enforcement, smart autoscroll, Win32 hotkeys",
        "fast": True,
    },
    {
        "name": "UI Adversarial Challenger",
        "path": "gemini_desktop_screenshare/tests/test_m3_adversarial_challenger.py",
        "description": "Sign-in churn, streaming toggles, illegal state transitions, corrupted hotkeys",
        "fast": False,
    },
    {
        "name": "UI Stress & Throughput",
        "path": "gemini_desktop_screenshare/tests/test_stress_m3.py",
        "description": "1000-token bursts, 60 FPS preview flood, rapid barge-in churn, 15 lifecycle iterations",
        "fast": False,
    },
    # --- Milestone 2 Backend Adversarial Baseline ---
    {
        "name": "Backend Adversarial M2",
        "path": "gemini_desktop_screenshare/tests/test_adversarial_m2.py",
        "description": "OAuth CSRF fuzzing, token expiry triggers, storage corruption, <=1.0 FPS throttling",
        "fast": False,
    },
    # --- Multi-Account, Model Selection & In-App Chat ---
    {
        "name": "Multi-Account & Model Selection",
        "path": "gemini_desktop_screenshare/tests/test_model_and_account_switching.py",
        "description": "Flash models, Argon, multi-account profile switching, and in-app chat queries",
        "fast": True,
    },
]


def run_suite(suite_path: str, verbose: bool = False) -> Tuple[bool, int, int, float, str]:
    """
    Executes a single test suite via pytest in a subprocess.
    Returns (success, passed_count, failed_count, duration, stdout_summary).
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        suite_path,
        "-s",  # Disable capture to avoid Windows closed-file I/O issues
        "-v" if verbose else "-q",
    ]

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    elapsed = time.perf_counter() - t0

    output = proc.stdout
    success = (proc.returncode == 0)

    # Parse pytest output for counts strictly from the final summary line
    passed = 0
    failed = 0

    # Search backwards for the final pytest summary line containing passed/failed counts
    for line in reversed(output.splitlines()):
        line_clean = line.strip()
        if not line_clean:
            continue
        m_pass = re.search(r"(\d+)\s+passed", line_clean)
        m_fail = re.search(r"(\d+)\s+failed", line_clean)
        m_err = re.search(r"(\d+)\s+error", line_clean)
        if m_pass or m_fail or m_err:
            if m_pass:
                passed = int(m_pass.group(1))
            if m_fail:
                failed = int(m_fail.group(1))
            if m_err:
                failed += int(m_err.group(1))
            break

    if success:
        failed = 0

    return success, passed, failed, elapsed, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gemini Desktop Screenshare Test Suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution output")
    parser.add_argument("--suite", type=str, default=None, help="Run a specific suite by name or path substring")
    parser.add_argument("--fast", action="store_true", help="Run only core fast test suites")
    args = parser.parse_args()

    suites_to_run = TEST_SUITES
    if args.fast:
        suites_to_run = [s for s in suites_to_run if s.get("fast", False)]

    if args.suite:
        query = args.suite.lower()
        suites_to_run = [s for s in suites_to_run if query in s["name"].lower() or query in s["path"].lower()]
        if not suites_to_run:
            print(f"Error: No test suite matched query '{args.suite}'. Available suites:")
            for s in TEST_SUITES:
                print(f"  - {s['name']} ({s['path']})")
            return 1

    print("=" * 90)
    print(" GEMINI DESKTOP SCREENSHARE -- PROGRAMMATIC TEST SUITE RUNNER")
    print(" Platform: Windows 10/11 (64-bit) | Qt Platform: offscreen (headless)")
    print("=" * 90)
    print(f"Discovered {len(suites_to_run)} test suites to execute.\n")

    results = []
    total_passed = 0
    total_failed = 0
    total_time = 0.0
    all_passed = True

    for i, suite in enumerate(suites_to_run, 1):
        rel_path = suite["path"]
        name = suite["name"]
        print(f"[{i:02d}/{len(suites_to_run):02d}] Running: {name} ({rel_path})...", flush=True)

        success, passed, failed, duration, output = run_suite(rel_path, verbose=args.verbose)
        results.append({
            "name": name,
            "path": rel_path,
            "success": success,
            "passed": passed,
            "failed": failed,
            "duration": duration,
            "output": output,
        })

        total_passed += passed
        total_failed += failed
        total_time += duration

        status_str = "PASS" if success else "FAIL"
        print(f"       --> [{status_str}] {passed} passed, {failed} failed in {duration:.2f}s\n")

        if not success:
            all_passed = False
            if not args.verbose:
                print("--- FAILURE DETAILS ---")
                print(output[-1500:] if len(output) > 1500 else output)
                print("-----------------------\n")

    # Format Summary Table
    print("\n" + "=" * 90)
    print(" TEST EXECUTION METRICS SUMMARY TABLE")
    print("=" * 90)
    header = f"{'#':<3} | {'Suite Name':<34} | {'Passed':<8} | {'Failed':<8} | {'Time (s)':<10} | {'Status':<8}"
    print(header)
    print("-" * len(header))

    for idx, r in enumerate(results, 1):
        status = "PASSED" if r["success"] else "FAILED"
        print(f"{idx:<3} | {r['name']:<34} | {r['passed']:<8} | {r['failed']:<8} | {r['duration']:<10.2f} | {status:<8}")

    print("-" * len(header))
    summary_line = f"TOTAL: {len(results)} suites | {total_passed} passed | {total_failed} failed | Total Time: {total_time:.2f}s"
    print(summary_line)
    print("=" * 90)

    if all_passed and total_failed == 0:
        print("\n>>> ALL TEST SUITES PASSED SUCCESSFULLY (100% PASS RATE) <<<\n")
        return 0
    else:
        print(f"\n>>> TEST SUITE FAILURES DETECTED: {total_failed} test(s) failed <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
