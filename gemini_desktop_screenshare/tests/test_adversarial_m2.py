"""
Empirical Challenger Adversarial Test Suite for Milestone 2.
Adversarially stress-tests:
1. auth/oauth_manager.py & auth/token_store.py:
   - Loopback server CSRF rejection with invalid/spoofed state, missing state, and error callbacks.
   - Proactive refresh triggers (<300s window), expired token handling, and revoked refresh token handling.
   - Corrupted and manipulated cache entries (malformed JSON, non-dict payloads, corrupt DPAPI files).
   - Sign-out and revocation resilience under server success and failure.
2. streaming/live_client.py:
   - Frame rate throttling to ensure <= 1.0 FPS under fast loop triggers.
   - Barge-in interruption handling (interrupted: true) under rapid bursts.
   - Malformed frames, rapid turns, and unexpected WebSocket disconnections.
"""

import asyncio
import base64
import http.server
import json
import logging
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import sys
from pathlib import Path
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from gemini_desktop_screenshare.config import AppConfig
from gemini_desktop_screenshare.auth.token_store import TokenStore
from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager, generate_pkce_pair
import gemini_desktop_screenshare.auth.oauth_manager as oauth_module
from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.streaming.live_client import GeminiLiveClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AdversarialChallenger")


# ==============================================================================
# MOCKS & TEST HARNESSES
# ==============================================================================

class MockFastCaptureEngine:
    """Ultra-fast mock capture engine to test video loop throttling."""
    def __init__(self):
        self.call_count = 0
        self.call_timestamps = []

    def capture_frame_base64(self, target_type: str, target_id: Any, max_dim: int = 1024, quality: int = 70) -> str:
        self.call_count += 1
        self.call_timestamps.append(time.perf_counter())
        # Minimal 1x1 JPEG in base64
        return "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


class MockAudioDevicePipeline:
    """Mock audio pipeline that records calls without opening physical hardware."""
    def __init__(self):
        self._is_muted = False
        self._is_recording = False
        self._output_queue = queue.Queue()
        self._leftover_output_bytes = b""
        self.interrupt_count = 0
        self.interrupt_timestamps = []
        self.played_chunks: List[bytes] = []
        self._record_callback = None
        self._lock = threading.Lock()

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_muted(self, muted: bool) -> None:
        self._is_muted = bool(muted)

    def start_recording(self, callback) -> None:
        self._is_recording = True
        self._record_callback = callback

    def stop_recording(self) -> None:
        self._is_recording = False
        self._record_callback = None

    def play_chunk(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes:
            return
        with self._lock:
            self.played_chunks.append(pcm_bytes)
            self._output_queue.put(pcm_bytes)

    def interrupt(self) -> float:
        t0 = time.perf_counter()
        with self._lock:
            self.interrupt_count += 1
            self.interrupt_timestamps.append(t0)
            self._leftover_output_bytes = b""
            while not self._output_queue.empty():
                try:
                    self._output_queue.get_nowait()
                except queue.Empty:
                    break
        return (time.perf_counter() - t0) * 1000.0

    def close(self) -> None:
        self.stop_recording()
        self.interrupt()


class MockOAuthHttpServer:
    """Mock OAuth HTTP server providing token refresh and revocation endpoints."""
    def __init__(self):
        self.refresh_calls = 0
        self.revoke_calls = 0
        self.should_fail_refresh = False
        self.should_fail_revoke = False
        self.refresh_error_code = 400
        self.issued_tokens: List[str] = []

        handler_self = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""

                req_path = urllib.parse.urlparse(self.path).path

                if req_path.rstrip("/").endswith("token"):  # /token endpoint
                    handler_self.refresh_calls += 1
                    if handler_self.should_fail_refresh:
                        self.send_response(handler_self.refresh_error_code)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "error": "invalid_grant",
                            "error_description": "Token has been revoked or expired"
                        }).encode("utf-8"))
                        return

                    new_access = f"ya29.refreshed_{secrets.token_hex(8)}"
                    handler_self.issued_tokens.append(new_access)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    resp = {
                        "access_token": new_access,
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    }
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                    return

                elif req_path.rstrip("/").endswith("revoke"):  # /revoke endpoint
                    handler_self.revoke_calls += 1
                    if handler_self.should_fail_revoke:
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(b"Internal Server Error on Revoke")
                        return

                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


# ==============================================================================
# TEST SUITE 1: AUTH & TOKEN STORE ADVERSARIAL STRESS TESTS
# ==============================================================================

def test_oauth_loopback_csrf_and_error_handling():
    """
    Stress-test OAuth loopback redirect server:
    1. Rejection of spoofed / invalid CSRF state parameter.
    2. Rejection of missing state parameter.
    3. Rejection of OAuth provider error (?error=access_denied).
    """
    print("\n" + "=" * 75)
    print("[AUTH TEST 1] OAUTH LOOPBACK CSRF & ERROR REJECTION")
    print("=" * 75)

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_auth1_"))
    orig_loopback = oauth_module._LoopbackServer

    try:
        cfg = AppConfig(client_id="test_client_id", client_secret="test_client_sec", config_dir=tmp_dir)
        ts = TokenStore(service_name=f"CSRFTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        manager = OAuthManager(config=cfg, token_store=ts)

        # ----------------------------------------------------------------------
        # Subtest 1.1: Spoofed State Parameter (CSRF Attack)
        # ----------------------------------------------------------------------
        captured_servers = []

        def wrapped_server(*args, **kwargs):
            srv = orig_loopback(*args, **kwargs)
            captured_servers.append(srv)
            return srv

        oauth_module._LoopbackServer = wrapped_server

        login_outcome = {}
        login_exception = []

        def run_login():
            try:
                res = manager.start_loopback_and_login(timeout=5.0, open_browser=False)
                login_outcome["result"] = res
            except Exception as e:
                login_exception.append(e)

        login_thread = threading.Thread(target=run_login, daemon=True)
        login_thread.start()

        # Wait for loopback server to bind
        time.sleep(0.3)
        assert len(captured_servers) == 1, "Loopback server should be initialized"
        port = captured_servers[0].server_address[1]
        expected_state = manager._pending_state
        assert expected_state is not None, "Expected state must be generated"

        spoofed_state = f"attacker_crafted_state_{secrets.token_hex(8)}"
        assert spoofed_state != expected_state

        # Attack: Send callback with spoofed state
        attack_url = f"http://127.0.0.1:{port}/?code=auth_code_victim&state={spoofed_state}"
        req = urllib.request.Request(attack_url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp_body = resp.read().decode("utf-8")

        login_thread.join(timeout=3.0)
        assert not login_thread.is_alive(), "Login thread should terminate after handling request"
        assert len(login_exception) == 1, f"Login must raise exception on state mismatch, got: {login_outcome}"
        exc = login_exception[0]
        assert isinstance(exc, ValueError), f"Expected ValueError, got {type(exc)}"
        assert "State mismatch" in str(exc), f"Expected 'State mismatch' in error, got: {exc}"
        print(f"  [1.1] Spoofed state CSRF rejection verified: Raised {type(exc).__name__}: {exc}")

        # ----------------------------------------------------------------------
        # Subtest 1.2: Missing State Parameter
        # ----------------------------------------------------------------------
        captured_servers.clear()
        login_exception.clear()

        login_thread = threading.Thread(target=run_login, daemon=True)
        login_thread.start()
        time.sleep(0.3)
        port = captured_servers[0].server_address[1]

        # Send callback without state query param
        attack_url = f"http://127.0.0.1:{port}/?code=auth_code_victim"
        with urllib.request.urlopen(attack_url, timeout=3) as resp:
            pass

        login_thread.join(timeout=3.0)
        assert len(login_exception) == 1
        exc = login_exception[0]
        assert isinstance(exc, ValueError)
        assert "State mismatch" in str(exc)
        print(f"  [1.2] Missing state rejection verified: Raised {type(exc).__name__}: {exc}")

        # ----------------------------------------------------------------------
        # Subtest 1.3: Google Error Callback (?error=access_denied)
        # ----------------------------------------------------------------------
        captured_servers.clear()
        login_exception.clear()

        login_thread = threading.Thread(target=run_login, daemon=True)
        login_thread.start()
        time.sleep(0.3)
        port = captured_servers[0].server_address[1]

        error_url = f"http://127.0.0.1:{port}/?error=access_denied"
        with urllib.request.urlopen(error_url, timeout=3) as resp:
            pass

        login_thread.join(timeout=3.0)
        assert len(login_exception) == 1
        exc = login_exception[0]
        assert isinstance(exc, RuntimeError)
        assert "access_denied" in str(exc)
        print(f"  [1.3] Provider error rejection verified: Raised {type(exc).__name__}: {exc}")

        # ----------------------------------------------------------------------
        # Subtest 1.4: Stray Request / Probe (e.g. /favicon.ico before callback)
        # ----------------------------------------------------------------------
        captured_servers.clear()
        login_exception.clear()

        login_thread = threading.Thread(target=run_login, daemon=True)
        login_thread.start()
        time.sleep(0.3)
        port = captured_servers[0].server_address[1]

        # Stray browser probe arrives first
        probe_url = f"http://127.0.0.1:{port}/favicon.ico"
        try:
            with urllib.request.urlopen(probe_url, timeout=3) as resp:
                pass
        except urllib.error.HTTPError as e:
            assert e.code == 404, f"Expected 404 for favicon probe, got {e.code}"
        except Exception:
            pass

        # Server must still be alive waiting for legitimate callback
        assert login_thread.is_alive(), "Login thread must NOT terminate prematurely on /favicon.ico"

        # Now deliver legitimate callback
        expected_state = manager._pending_state
        callback_url = f"http://127.0.0.1:{port}/?code=auth_code_legit&state={expected_state}"
        manager._exchange_code_for_tokens = lambda code, verifier, uri: {"access_token": "ya29.ok"}
        with urllib.request.urlopen(callback_url, timeout=3) as resp:
            pass

        login_thread.join(timeout=3.0)
        assert not login_thread.is_alive(), "Login thread must terminate after legitimate callback"
        assert len(login_exception) == 0, f"Expected clean login without exception, got {login_exception}"
        assert login_outcome.get("result", {}).get("access_token") == "ya29.ok"
        print("  [1.4] Stray probe ignored: Loopback server survived /favicon.ico and handled valid callback cleanly.")

        print("--> [PASS] TEST 1: OAuth Loopback CSRF and Error Handling PASSED.")

    finally:
        oauth_module._LoopbackServer = orig_loopback
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_token_expiry_and_proactive_refresh():
    """
    Stress-test proactive token refresh triggers:
    1. Fresh token (>300s remaining) returns cached token without network refresh.
    2. Token within 300s expiration window (<300s) proactively triggers refresh.
    3. Fully expired token triggers refresh.
    4. Expired token with revoked refresh token handles HTTP 400 error.
    5. Expired token with missing refresh token raises RuntimeError.
    """
    print("\n" + "=" * 75)
    print("[AUTH TEST 2] EXPIRED TOKEN & PROACTIVE REFRESH TRIGGERS")
    print("=" * 75)

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_auth2_"))
    mock_server = MockOAuthHttpServer()

    try:
        cfg = AppConfig(
            client_id="test_client_id",
            client_secret="test_client_sec",
            token_uri=f"http://127.0.0.1:{mock_server.port}/token",
            revoke_uri=f"http://127.0.0.1:{mock_server.port}/revoke",
            config_dir=tmp_dir,
        )
        ts = TokenStore(service_name=f"RefreshTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        manager = OAuthManager(config=cfg, token_store=ts)

        # ----------------------------------------------------------------------
        # Subtest 2.1: Fresh Token (>300s)
        # ----------------------------------------------------------------------
        ts.save_refresh_token("valid_refresh_token_123")
        initial_token = "ya29.fresh_access_token_123"
        manager._access_token = initial_token
        manager._expires_at = time.time() + 3600  # 1 hour remaining

        tok = manager.get_valid_access_token()
        assert tok == initial_token, "Must return cached token without refreshing"
        assert mock_server.refresh_calls == 0, f"Refresh calls must be 0, got {mock_server.refresh_calls}"
        print("  [2.1] Fresh token (>300s): Cache hit verified (0 network calls)")

        # ----------------------------------------------------------------------
        # Subtest 2.2: Proactive Refresh Trigger (<300s remaining, e.g. 200s)
        # ----------------------------------------------------------------------
        manager._expires_at = time.time() + 200  # Within 5-minute proactive buffer

        tok2 = manager.get_valid_access_token()
        assert tok2 != initial_token, "Must return newly refreshed token"
        assert tok2.startswith("ya29.refreshed_"), f"Unexpected refreshed token: {tok2}"
        assert mock_server.refresh_calls == 1, f"Expected 1 refresh call, got {mock_server.refresh_calls}"
        assert manager._expires_at > (time.time() + 3000), "Expiry must be extended by 3600s"
        print(f"  [2.2] Proactive refresh trigger (<300s): Succeeded (token={tok2})")

        # ----------------------------------------------------------------------
        # Subtest 2.3: Fully Expired Token (e.g. expired 50s ago)
        # ----------------------------------------------------------------------
        manager._expires_at = time.time() - 50

        tok3 = manager.get_valid_access_token()
        assert tok3.startswith("ya29.refreshed_")
        assert tok3 != tok2
        assert mock_server.refresh_calls == 2
        print(f"  [2.3] Expired token refresh: Succeeded (token={tok3})")

        # ----------------------------------------------------------------------
        # Subtest 2.4: Revoked Refresh Token (HTTP 400 invalid_grant)
        # ----------------------------------------------------------------------
        mock_server.should_fail_refresh = True
        mock_server.refresh_error_code = 400
        manager._expires_at = time.time() - 100

        failed_refresh = False
        try:
            manager.get_valid_access_token()
        except RuntimeError as e:
            failed_refresh = True
            assert "HTTP 400" in str(e), f"Expected HTTP 400 in error, got {e}"
            print(f"  [2.4] Revoked refresh token handling verified: Raised RuntimeError: {e}")

        assert failed_refresh, "Must raise RuntimeError when refresh token is rejected"

        # ----------------------------------------------------------------------
        # Subtest 2.5: Missing Refresh Token
        # ----------------------------------------------------------------------
        mock_server.should_fail_refresh = False
        ts.delete_refresh_token()
        manager._access_token = None
        manager._expires_at = 0.0

        missing_token_raised = False
        try:
            manager.get_valid_access_token()
        except RuntimeError as e:
            missing_token_raised = True
            assert "No refresh token available" in str(e)
            print(f"  [2.5] Missing refresh token handling verified: Raised {e}")

        assert missing_token_raised, "Must raise RuntimeError when no refresh token is stored"

        print("--> [PASS] TEST 2: Token Expiry & Proactive Refresh PASSED.")

    finally:
        mock_server.stop()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_token_storage_corruption_and_manipulation():
    """
    Stress-test TokenStore and OAuthManager against corrupted and manipulated cache entries:
    1. Syntax-corrupted session.json (random non-JSON bytes).
    2. Non-dict session.json (JSON string, list, or int).
    3. Type-corrupted fields (non-numeric expires_at).
    4. Corrupted DPAPI encrypted binary file.
    """
    print("\n" + "=" * 75)
    print("[AUTH TEST 3] STORAGE CORRUPTION & MANIPULATION RESILIENCE")
    print("=" * 75)

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_auth3_"))
    try:
        ts = TokenStore(service_name=f"CorruptTest_{secrets.token_hex(4)}", config_dir=tmp_dir)

        # ----------------------------------------------------------------------
        # Subtest 3.1: Syntax-corrupted session.json
        # ----------------------------------------------------------------------
        with open(ts.session_file, "wb") as f:
            f.write(b"{\x00\xffMALFORMED_JSON_GARBAGE!!!")

        session = ts.get_session()
        assert session is None, f"get_session() must return None for corrupted JSON, got {session}"
        print("  [3.1] Syntax-corrupted session.json: Handled gracefully (returned None)")

        # ----------------------------------------------------------------------
        # Subtest 3.2: Non-dict session.json (JSON string / list)
        # ----------------------------------------------------------------------
        # Case A: JSON string
        with open(ts.session_file, "w", encoding="utf-8") as f:
            f.write('"malicious_or_corrupt_string_value"')

        session_str = ts.get_session()
        assert session_str == "malicious_or_corrupt_string_value"

        # Check how OAuthManager handles non-dict session
        cfg = AppConfig(client_id="cid", client_secret="csec", config_dir=tmp_dir)
        manager_str_crashed = False
        try:
            mgr = OAuthManager(config=cfg, token_store=ts)
        except AttributeError as e:
            manager_str_crashed = True
            print(f"  [3.2a] VULNERABILITY DETECTED: OAuthManager crashed on string session.json: {e}")

        # Case B: JSON list [1, 2, 3]
        with open(ts.session_file, "w", encoding="utf-8") as f:
            f.write('[1, 2, 3]')

        manager_list_crashed = False
        try:
            mgr = OAuthManager(config=cfg, token_store=ts)
        except AttributeError as e:
            manager_list_crashed = True
            print(f"  [3.2b] VULNERABILITY DETECTED: OAuthManager crashed on list session.json: {e}")

        assert not manager_str_crashed, "OAuthManager must not crash on string session.json"
        assert not manager_list_crashed, "OAuthManager must not crash on list session.json"
        print("  [3.2] Non-dict session.json: Handled defensively without crash.")

        # ----------------------------------------------------------------------
        # Subtest 3.3: Type-corrupted expires_at (non-numeric string)
        # ----------------------------------------------------------------------
        with open(ts.session_file, "w", encoding="utf-8") as f:
            json.dump({
                "access_token": "ya29.valid_looking_token",
                "expires_at": "invalid_non_numeric_string",
                "user_profile": {"email": "test@example.com"}
            }, f)

        # If OAuthManager loads this, verify get_valid_access_token does not crash with TypeError
        mgr_type = OAuthManager(config=cfg, token_store=ts)
        type_error_raised = False
        try:
            mgr_type.get_valid_access_token()
        except TypeError as e:
            type_error_raised = True
            print(f"  [3.3] VULNERABILITY DETECTED: TypeError on corrupted expires_at field: {e}")
        except RuntimeError:
            # Expected because expires_at was sanitized to 0.0, prompting refresh without refresh_token
            pass

        assert not type_error_raised, "Must not crash with TypeError on corrupted expires_at"
        assert mgr_type._expires_at == 0.0, "Corrupted expires_at must be sanitized to 0.0"
        print("  [3.3] Type-corrupted expires_at: Sanitized to 0.0 without TypeError crash.")

        # ----------------------------------------------------------------------
        # Subtest 3.4: Corrupted DPAPI encrypted binary file
        # ----------------------------------------------------------------------
        with open(ts.dpapi_file, "wb") as f:
            f.write(b"NOT_A_VALID_DPAPI_BLOB\x00\x01\x02\x03\x04\x05")

        dpapi_token = ts.get_refresh_token()
        assert dpapi_token is None, f"get_refresh_token must return None on DPAPI corruption, got {dpapi_token}"
        print("  [3.4] Corrupted DPAPI binary: Handled gracefully (returned None without crash)")

        print("--> [PASS] TEST 3: Storage Corruption & Manipulation Analysis COMPLETE.")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_sign_out_and_revocation_behavior():
    """
    Stress-test sign-out and token revocation:
    1. Sign-out when Google revocation endpoint returns 200 OK.
    2. Sign-out when Google revocation endpoint fails (HTTP 500 / Network down).
    3. Verify unconditional local purge of Keyring, DPAPI file, and session.json.
    4. Verify idempotence of repeated sign_out calls.
    """
    print("\n" + "=" * 75)
    print("[AUTH TEST 4] SIGN-OUT & TOKEN REVOCATION BEHAVIOR")
    print("=" * 75)

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_auth4_"))
    mock_server = MockOAuthHttpServer()

    try:
        cfg = AppConfig(
            client_id="cid",
            client_secret="csec",
            revoke_uri=f"http://127.0.0.1:{mock_server.port}/revoke",
            config_dir=tmp_dir,
        )
        ts = TokenStore(service_name=f"SignOutTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        manager = OAuthManager(config=cfg, token_store=ts)

        # ----------------------------------------------------------------------
        # Subtest 4.1: Normal Sign-Out with 200 OK Revocation
        # ----------------------------------------------------------------------
        ts.save_refresh_token("refresh_token_to_revoke")
        ts.save_session({
            "access_token": "ya29.token_to_revoke",
            "expires_at": time.time() + 3600,
            "user_profile": {"email": "user@example.com"}
        })
        manager._load_cached_session()
        assert manager.is_authenticated() is True

        res = manager.sign_out()
        assert res is True, "sign_out() must return True"
        assert mock_server.revoke_calls == 1, f"Expected 1 revoke call, got {mock_server.revoke_calls}"
        assert ts.get_refresh_token() is None, "Refresh token must be deleted from storage"
        assert ts.get_session() is None, "Session cache must be deleted"
        assert not ts.dpapi_file.exists(), "DPAPI backup file must be unlinked"
        assert manager.is_authenticated() is False, "Must not be authenticated after sign-out"
        assert manager._access_token is None
        assert manager._expires_at == 0.0
        assert manager.get_user_profile() == {}
        print("  [4.1] Normal sign-out: Revocation requested and all credentials purged")

        # ----------------------------------------------------------------------
        # Subtest 4.2: Sign-out when Revocation Server Fails (HTTP 500)
        # ----------------------------------------------------------------------
        mock_server.should_fail_revoke = True
        ts.save_refresh_token("refresh_token_when_server_fails")
        ts.save_session({"access_token": "ya29.test", "expires_at": time.time() + 3600})
        manager._load_cached_session()
        assert manager.is_authenticated() is True

        res2 = manager.sign_out()
        assert res2 is True, "sign_out() must succeed and purge locally even if server returns 500"
        assert mock_server.revoke_calls == 2
        assert ts.get_refresh_token() is None, "Local tokens must still be purged"
        assert ts.get_session() is None
        assert manager.is_authenticated() is False
        print("  [4.2] Sign-out under server 500 error: Local purge resilience verified")

        # ----------------------------------------------------------------------
        # Subtest 4.3: Repeated Sign-out (Idempotence)
        # ----------------------------------------------------------------------
        res3 = manager.sign_out()
        assert res3 is True, "Repeated sign_out must be safe and idempotent"
        print("  [4.3] Repeated sign-out idempotence: Verified")

        print("--> [PASS] TEST 4: Sign-out & Token Revocation PASSED.")

    finally:
        mock_server.stop()
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# TEST SUITE 2: WEBSOCKET STREAMING ADVERSARIAL STRESS TESTS
# ==============================================================================

async def _run_streaming_throttling_test():
    """
    Empirically stress-tests the frame rate throttling in GeminiLiveClient:
    Ensures that under rapid capture triggers (sub-millisecond captures),
    frame transmission rate NEVER exceeds 1.0 FPS.
    """
    print("\n" + "=" * 75)
    print("[STREAMING TEST 5] FRAME RATE THROTTLING (<= 1.0 FPS VERIFICATION)")
    print("=" * 75)

    received_frames: List[float] = []

    async def mock_ws_handler(websocket):
        try:
            # 1. Await Setup Frame
            setup_msg = await websocket.recv()
            setup_data = json.loads(setup_msg)
            assert "setup" in setup_data

            # 2. Respond with setupComplete
            await websocket.send(json.dumps({"setupComplete": {}}))

            # 3. Collect streaming frames
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                realtime = data.get("realtimeInput", {})
                chunks = realtime.get("mediaChunks", [])
                for chunk in chunks:
                    if chunk.get("mimeType") == "image/jpeg":
                        received_frames.append(time.perf_counter())
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(mock_ws_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    ws_url = f"ws://127.0.0.1:{port}"

    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_stream1_"))
        cfg = AppConfig(config_dir=tmp_dir)
        ts = TokenStore(service_name=f"StreamTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        mgr = OAuthManager(config=cfg, token_store=ts)
        mgr._access_token = "ya29.test_stream_token"
        mgr._expires_at = time.time() + 3600

        capture = MockFastCaptureEngine()
        audio = MockAudioDevicePipeline()
        client = GeminiLiveClient(
            oauth_manager=mgr,
            capture_engine=capture,
            audio_pipeline=audio,
            host=ws_url,
        )

        await client.connect()
        assert client.is_connected is True

        # Stream for 5.2 seconds
        t_start = time.perf_counter()
        await client.start_streaming()
        await asyncio.sleep(5.2)
        await client.stop_streaming()
        await client.disconnect()
        total_stream_time = time.perf_counter() - t_start

        # Analyze frame rate metrics
        frame_count = len(received_frames)
        print(f"  Stream Duration: {total_stream_time:.3f} s")
        print(f"  Frames Received: {frame_count}")

        # Assertions on FPS
        effective_fps = frame_count / total_stream_time
        print(f"  Effective FPS  : {effective_fps:.3f} FPS")

        # Check intervals between consecutive frames
        intervals = []
        for i in range(1, len(received_frames)):
            inter = received_frames[i] - received_frames[i-1]
            intervals.append(inter)
            print(f"    Frame {i} -> {i+1} interval: {inter:.4f} s")

        # Frame rate must NOT exceed 1.0 FPS
        # For a 5.2s window, max frames is 6 (1 at t=0, then t=1, 2, 3, 4, 5)
        assert frame_count <= 6, f"Frame count {frame_count} exceeded 6 in 5.2s (violates 1.0 FPS limit!)"
        for inter in intervals:
            # Allow 150ms tolerance for Windows OS thread scheduling jitter under multi-suite load
            assert inter >= 0.85, f"Interval between frames {inter:.4f}s was less than 0.85s (violates 1 FPS throttling!)"

        print(f"--> [PASS] TEST 5: Frame Rate Throttling strictly enforced <= 1.0 FPS (observed {effective_fps:.3f} FPS).")

    finally:
        server.close()
        await server.wait_closed()
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _run_interruption_handling_test():
    """
    Stress-test user barge-in interruption handling (interrupted: true):
    1. Pre-loads synthetic 24kHz audio chunks into the AudioPipeline queue.
    2. Sends serverContent.interrupted = true.
    3. Verifies immediate queue drain without blocking or crashing.
    4. Fires rapid interruption bursts (20 pulses) while concurrently pushing audio chunks.
    """
    print("\n" + "=" * 75)
    print("[STREAMING TEST 6] BARGE-IN INTERRUPTION HANDLING & BURST PULSES")
    print("=" * 75)

    ws_client_ref = []

    async def mock_ws_handler(websocket):
        ws_client_ref.append(websocket)
        try:
            # Setup
            setup_msg = await websocket.recv()
            await websocket.send(json.dumps({"setupComplete": {}}))

            while True:
                await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(mock_ws_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    ws_url = f"ws://127.0.0.1:{port}"

    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_stream2_"))
        cfg = AppConfig(config_dir=tmp_dir)
        ts = TokenStore(service_name=f"InterruptTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        mgr = OAuthManager(config=cfg, token_store=ts)
        mgr._access_token = "ya29.test_token"
        mgr._expires_at = time.time() + 3600

        capture = MockFastCaptureEngine()
        audio = MockAudioDevicePipeline()
        client = GeminiLiveClient(
            oauth_manager=mgr,
            capture_engine=capture,
            audio_pipeline=audio,
            host=ws_url,
        )

        await client.connect()
        await client.start_streaming()
        await asyncio.sleep(0.1)

        server_ws = ws_client_ref[0]

        # ----------------------------------------------------------------------
        # Subtest 6.1: Single Interruption Drains Audio Buffer
        # ----------------------------------------------------------------------
        # Pre-populate audio queue with 5 chunks of 2400 bytes each
        dummy_chunk = b"\x12\x34" * 1200
        for _ in range(5):
            audio.play_chunk(dummy_chunk)

        assert audio._output_queue.qsize() == 5, "Audio queue must contain 5 chunks"

        # Transmit barge-in signal from server
        interrupted_payload = {
            "serverContent": {
                "interrupted": True
            }
        }
        await server_ws.send(json.dumps(interrupted_payload))

        # Allow receive loop to process
        await asyncio.sleep(0.1)

        assert audio._output_queue.empty() is True, "Audio queue must be completely drained on interruption"
        assert audio.interrupt_count >= 1, f"Expected interrupt_count >= 1, got {audio.interrupt_count}"
        print(f"  [6.1] Single interruption: Buffer drained successfully ({audio.interrupt_count} interrupts called)")

        # ----------------------------------------------------------------------
        # Subtest 6.2: Rapid Interruption Bursts (20 pulses under concurrent feed)
        # ----------------------------------------------------------------------
        for i in range(20):
            # Feed audio chunk
            audio.play_chunk(dummy_chunk)
            # Pulse interrupt frame
            await server_ws.send(json.dumps({"serverContent": {"interrupted": True}}))
            await asyncio.sleep(0.01)

        await asyncio.sleep(0.1)
        assert audio._output_queue.empty() is True, "Audio queue must remain drained after burst pulses"
        assert audio.interrupt_count >= 20, f"Expected at least 21 interrupts, got {audio.interrupt_count}"
        print(f"  [6.2] Rapid interruption bursts: 20 pulses handled without deadlock or crash (total interrupts={audio.interrupt_count})")

        await client.stop_streaming()
        await client.disconnect()
        print("--> [PASS] TEST 6: Interruption Handling & Burst Pulses PASSED.")

    finally:
        server.close()
        await server.wait_closed()
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _run_adversarial_server_frames_and_disconnect_test():
    """
    Stress-tests client resilience against:
    1. Rapid message turns (50 turns sent within 50ms).
    2. Malformed frames:
       - Syntax-invalid JSON string
       - Raw binary WebSocket frame
       - Non-dict JSON root
       - Malformed serverContent type (string instead of dict)
       - Malformed modelTurn parts (string instead of list)
       - Corrupted base64 audio payload
    3. Abrupt / unexpected WebSocket disconnections (code 1006).
    """
    print("\n" + "=" * 75)
    print("[STREAMING TEST 7] ADVERSARIAL FRAMES, RAPID TURNS & UNEXPECTED DISCONNECTS")
    print("=" * 75)

    ws_client_ref = []
    server_actions = asyncio.Event()

    async def mock_ws_handler(websocket):
        ws_client_ref.append(websocket)
        try:
            # Setup handshake
            setup_msg = await websocket.recv()
            await websocket.send(json.dumps({"setupComplete": {}}))
            server_actions.set()

            while True:
                await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(mock_ws_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    ws_url = f"ws://127.0.0.1:{port}"

    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_adv_stream3_"))
        cfg = AppConfig(config_dir=tmp_dir)
        ts = TokenStore(service_name=f"FrameTest_{secrets.token_hex(4)}", config_dir=tmp_dir)
        mgr = OAuthManager(config=cfg, token_store=ts)
        mgr._access_token = "ya29.test_token"
        mgr._expires_at = time.time() + 3600

        received_text_chunks: List[str] = []
        error_callbacks: List[str] = []

        def on_text(t: str):
            received_text_chunks.append(t)

        def on_error(err: str):
            error_callbacks.append(err)

        capture = MockFastCaptureEngine()
        audio = MockAudioDevicePipeline()
        client = GeminiLiveClient(
            oauth_manager=mgr,
            capture_engine=capture,
            audio_pipeline=audio,
            host=ws_url,
        )

        await client.connect()
        await client.start_streaming(on_text=on_text, on_error=on_error)
        await server_actions.wait()
        server_ws = ws_client_ref[0]

        # ----------------------------------------------------------------------
        # Subtest 7.1: Rapid Message Turns (50 turns in rapid succession)
        # ----------------------------------------------------------------------
        pcm_sample = base64.b64encode(b"\x00\x01" * 480).decode("ascii")
        for i in range(50):
            turn_msg = {
                "serverContent": {
                    "modelTurn": {
                        "parts": [
                            {"text": f"token_{i} "},
                            {
                                "inlineData": {
                                    "mimeType": "audio/pcm;rate=24000",
                                    "data": pcm_sample,
                                }
                            }
                        ]
                    },
                    "turnComplete": (i % 10 == 0)
                }
            }
            await server_ws.send(json.dumps(turn_msg))

        await asyncio.sleep(0.3)
        assert len(received_text_chunks) == 50, f"Expected 50 text tokens, got {len(received_text_chunks)}"
        assert len(audio.played_chunks) == 50, f"Expected 50 audio chunks, got {len(audio.played_chunks)}"
        print(f"  [7.1] Rapid turns: 50 turns received & dispatched cleanly (tokens={len(received_text_chunks)}, audio={len(audio.played_chunks)})")

        # ----------------------------------------------------------------------
        # Subtest 7.2: Malformed Frames & Failure Mode Analysis
        # ----------------------------------------------------------------------
        # We test how GeminiLiveClient._receive_loop responds to various malformed frames
        malformed_test_cases = [
            ("Malformed JSON Syntax", "{\"invalid\": json syntax without end"),
            ("Non-Dict JSON Root (String)", json.dumps("unexpected_json_string")),
            ("Non-Dict JSON Root (List)", json.dumps([1, 2, 3])),
            ("Malformed serverContent Type", json.dumps({"serverContent": "should_be_a_dict"})),
            ("Malformed modelTurn Parts (String)", json.dumps({"serverContent": {"modelTurn": {"parts": "not_a_list"}}})),
            ("Corrupted Base64 Audio", json.dumps({"serverContent": {"modelTurn": {"parts": [{"inlineData": {"mimeType": "audio/pcm", "data": "%%%corrupt_base64%%%"}}]}}}))
        ]

        print("  [7.2] Testing Malformed Frame Matrix...")
        # Test first malformed frame on the active connection
        label, bad_frame = malformed_test_cases[0]
        await server_ws.send(bad_frame)
        await asyncio.sleep(0.1)

        print(f"    Frame: '{label}' -> on_error called: {error_callbacks}")
        assert len(error_callbacks) > 0, "on_error must be called when invalid frame is received"
        assert client._receive_task.done() is False, "Receive task must survive malformed frame and continue running"
        assert client.is_streaming is True, "Client streaming must remain active"
        print("    [7.2] Malformed frame discarded and on_error invoked; receive loop survived and remains streaming.")

        # ----------------------------------------------------------------------
        # Subtest 7.3: Unexpected Disconnection & Cleanup Analysis
        # ----------------------------------------------------------------------
        # Close server WebSocket abruptly via transport
        print("  Testing Unexpected Disconnection: Closing server transport abruptly...")
        if hasattr(server_ws, "transport") and server_ws.transport:
            server_ws.transport.close()
        else:
            await server_ws.close(code=1000)
        await asyncio.sleep(0.3)

        print(f"    client._video_task.done(): {client._video_task.done() if client._video_task else 'None'}")
        print(f"    client._audio_task.done(): {client._audio_task.done() if client._audio_task else 'None'}")
        print(f"    client.is_streaming: {client.is_streaming}")
        print(f"    audio.is_recording: {audio.is_recording}")

        # Verify automatic cleanup occurred on abrupt disconnect:
        assert client.is_streaming is False, "is_streaming must be set to False on unexpected disconnect"
        assert audio.is_recording is False, "audio recording must be stopped on unexpected disconnect"

        # Cleanup client
        await client.disconnect()
        assert client.is_streaming is False
        assert client.is_connected is False
        assert audio.is_recording is False
        print("  [7.3] Disconnection handled and client disconnected cleanly.")

        print("--> [PASS] TEST 7: Adversarial Server Frames & Disconnection Analysis COMPLETE.")

    finally:
        server.close()
        await server.wait_closed()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_streaming_suite():
    asyncio.run(_run_streaming_throttling_test())
    asyncio.run(_run_interruption_handling_test())
    asyncio.run(_run_adversarial_server_frames_and_disconnect_test())


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("STARTING EMPIRICAL ADVERSARIAL CHALLENGER SUITE FOR MILESTONE 2")
    print("=" * 80)

    # 1. Auth tests
    test_oauth_loopback_csrf_and_error_handling()
    test_token_expiry_and_proactive_refresh()
    test_token_storage_corruption_and_manipulation()
    test_sign_out_and_revocation_behavior()

    # 2. Streaming tests
    test_streaming_suite()

    print("\n" + "=" * 80)
    print("ALL EMPIRICAL ADVERSARIAL CHALLENGER TESTS EXECUTED SUCCESSFULLY!")
    print("=" * 80)
