"""
Unit & Integration tests for Authentication & Token Persistence subsystem.
Covers RFC 7636 PKCE S256 generation, loopback redirect server, CSRF protection,
Windows DPAPI encryption, session caching, and MockOAuthServer token lifecycle.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request
import pytest

from gemini_desktop_screenshare.auth.oauth_manager import (
    OAuthManager,
    generate_pkce_pair,
    _LoopbackServer,
    _OAuthRedirectHandler,
)
from gemini_desktop_screenshare.auth.token_store import TokenStore
from gemini_desktop_screenshare.config import AppConfig
from gemini_desktop_screenshare.tests.mock_servers import MockOAuthServer


# ------------------------------------------------------------------------------
# 1. PKCE Mathematical & Cryptographic Verification
# ------------------------------------------------------------------------------
def test_generate_pkce_pair_length_and_charset():
    """Verifies that generated PKCE verifier and challenge are exactly 43 chars, urlsafe, and unpadded."""
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) == 43
    assert len(challenge) == 43
    assert "=" not in verifier
    assert "=" not in challenge
    # URL safe characters
    assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in verifier)
    assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in challenge)


def test_generate_pkce_pair_cryptographic_verification():
    """Verifies that SHA-256 of verifier exactly yields the challenge."""
    verifier, challenge = generate_pkce_pair()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    assert challenge == expected_challenge


def test_generate_pkce_pair_entropy():
    """Verifies that 100 consecutive generations produce 100 unique verifier-challenge pairs."""
    verifiers = set()
    challenges = set()
    for _ in range(100):
        v, c = generate_pkce_pair()
        verifiers.add(v)
        challenges.add(c)
    assert len(verifiers) == 100
    assert len(challenges) == 100


# ------------------------------------------------------------------------------
# 2. Loopback Redirect Server Tests
# ------------------------------------------------------------------------------
def test_loopback_ephemeral_port_allocation():
    """Verifies that _LoopbackServer binds to 127.0.0.1:0 and allocates an ephemeral port."""
    server = _LoopbackServer(("127.0.0.1", 0), _OAuthRedirectHandler)
    try:
        port = server.server_address[1]
        assert port > 0
        assert port != 80
        assert port != 8080
    finally:
        server.server_close()


def test_loopback_timeout_handling(temp_config_dir):
    """Verifies that start_loopback_and_login with short timeout raises TimeoutError cleanly."""
    cfg = AppConfig(
        config_dir=Path(temp_config_dir),
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    mgr = OAuthManager(config=cfg)
    with pytest.raises(TimeoutError):
        # We give 0.1s timeout and do not navigate or send any callback
        mgr.start_loopback_and_login(timeout=0.1)


def test_loopback_stray_request_resilience():
    """Verifies that requests to /favicon.ico return 404 and the server stays running."""
    import threading

    server = _LoopbackServer(("127.0.0.1", 0), _OAuthRedirectHandler)
    server.expected_state = "correct_state"
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        # Request favicon
        req = urllib.request.Request(f"http://127.0.0.1:{port}/favicon.ico")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 404
        assert not server.done

        # Request valid callback
        cb_url = f"http://127.0.0.1:{port}/callback?code=test_code_123&state=correct_state"
        with urllib.request.urlopen(cb_url) as resp:
            assert resp.status == 200

        assert server.done
        assert server.received_code == "test_code_123"
        assert server.received_state == "correct_state"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)


def test_loopback_csrf_spoofed_state_rejection():
    """Verifies that spoofed state causes CSRF rejection."""
    import threading

    server = _LoopbackServer(("127.0.0.1", 0), _OAuthRedirectHandler)
    server.expected_state = "authentic_state_token"
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        cb_url = f"http://127.0.0.1:{port}/callback?code=test_code_123&state=spoofed_state_token"
        with urllib.request.urlopen(cb_url) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "CSRF state validation failed" in html

        assert server.done
        assert server.received_state == "spoofed_state_token"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)


def test_loopback_provider_error_callback():
    """Verifies that Google callback with ?error=access_denied sets received_error and serves error page."""
    import threading

    server = _LoopbackServer(("127.0.0.1", 0), _OAuthRedirectHandler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        cb_url = f"http://127.0.0.1:{port}/callback?error=access_denied"
        with urllib.request.urlopen(cb_url) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "access_denied" in html

        assert server.done
        assert server.received_error == "access_denied"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)


# ------------------------------------------------------------------------------
# 3. Windows DPAPI & Token Storage Persistence
# ------------------------------------------------------------------------------
def test_token_store_dpapi_roundtrip(temp_config_dir):
    """Verifies that DPAPI encrypt and decrypt preserves the exact secret string."""
    store = TokenStore(config_dir=Path(temp_config_dir))
    original = "1//mock_refresh_token_secret_xyz123"

    try:
        encrypted = store._dpapi_protect(original.encode("utf-8"))
        assert encrypted != original.encode("utf-8")
        decrypted = store._dpapi_unprotect(encrypted).decode("utf-8")
        assert decrypted == original
    except RuntimeError:
        pytest.skip("win32crypt DPAPI not available in this environment.")


def test_token_store_dpapi_corrupted_blob(temp_config_dir):
    """Verifies that corrupted bytes in token_dpapi.bin return None without crashing."""
    store = TokenStore(config_dir=Path(temp_config_dir))
    store.delete_refresh_token()
    # Write garbage corrupted data
    with open(store.dpapi_file, "wb") as f:
        f.write(b"CORRUPTED_NON_DPAPI_GARBAGE_BYTES_1234567890")

    result = store.get_refresh_token()
    assert result is None


def test_token_store_session_cache_corrupted_json(temp_config_dir):
    """Verifies that malformed JSON in session.json returns None safely."""
    store = TokenStore(config_dir=Path(temp_config_dir))
    with open(store.session_file, "w", encoding="utf-8") as f:
        f.write("{ INVALID JSON NOT TERMINATED ...")

    session = store.get_session()
    assert session is None


def test_token_store_session_cache_crud(temp_config_dir):
    """Verifies creating, reading, updating, and clearing session cache."""
    store = TokenStore(config_dir=Path(temp_config_dir))
    session_data = {
        "access_token": "ya29.test_token",
        "expires_at": time.time() + 3600,
        "user_profile": {"email": "user@example.com", "name": "Test User"},
    }
    store.save_session(session_data)
    loaded = store.get_session()
    assert loaded["access_token"] == "ya29.test_token"
    assert loaded["user_profile"]["email"] == "user@example.com"

    store.clear_session()
    assert store.get_session() is None


# ------------------------------------------------------------------------------
# 4. OAuthManager Lifecycle with MockOAuthServer
# ------------------------------------------------------------------------------
def test_oauth_manager_automatic_and_proactive_refresh(temp_config_dir):
    """Verifies token retrieval, caching, and automatic proactive refresh using MockOAuthServer."""
    with MockOAuthServer() as mock_oauth:
        cfg = AppConfig(
            config_dir=Path(temp_config_dir),
            client_id="mock_client_id",
            client_secret="mock_client_secret",
            token_uri=mock_oauth.token_uri,
            userinfo_uri=mock_oauth.userinfo_uri,
            revoke_uri=mock_oauth.revoke_uri,
        )
        mgr = OAuthManager(config=cfg)

        # Pre-seed session cache with expiring token (expires in 60s, which is < 300s margin)
        mgr.token_store.save_refresh_token("1//mock_valid_refresh_token")
        mgr.token_store.save_session({
            "access_token": "ya29.old_token",
            "expires_at": time.time() + 60,
            "user_profile": {"email": "old@example.com", "name": "Old Name"},
        })
        mgr._load_cached_session()

        # Calling get_valid_access_token should detect imminent expiration and refresh
        new_token = mgr.get_valid_access_token()
        assert new_token.startswith("ya29.refreshed_")
        assert len(mock_oauth.token_refreshes) == 1

        # Profile fetch from server
        profile = mgr._fetch_user_profile(new_token)
        assert profile.get("email") == "mock_user@gmail.com"
        assert len(mock_oauth.userinfo_fetches) == 1


def test_oauth_manager_sign_out_purge_and_idempotence(temp_config_dir):
    """Verifies that sign_out revokes token on server, purges local stores, and is idempotent."""
    with MockOAuthServer() as mock_oauth:
        cfg = AppConfig(
            config_dir=Path(temp_config_dir),
            client_id="mock_client_id",
            client_secret="mock_client_secret",
            token_uri=mock_oauth.token_uri,
            userinfo_uri=mock_oauth.userinfo_uri,
            revoke_uri=mock_oauth.revoke_uri,
        )
        mgr = OAuthManager(config=cfg)

        mgr.token_store.save_refresh_token("1//mock_refresh_to_revoke")
        mgr.token_store.save_session({
            "access_token": "ya29.to_revoke",
            "expires_at": time.time() + 3600,
        })

        assert mgr.is_authenticated()

        # Sign out
        res1 = mgr.sign_out()
        assert res1 is True
        assert not mgr.is_authenticated()
        assert mgr.token_store.get_session() is None
        assert len(mock_oauth.revocations) == 1

        # Repeated sign_out should be idempotent and return True
        res2 = mgr.sign_out()
        assert res2 is True
