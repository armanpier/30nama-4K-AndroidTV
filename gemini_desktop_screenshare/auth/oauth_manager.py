"""
Google OAuth 2.0 PKCE authentication manager for Windows Desktop.
Implements RFC 8252 (OAuth 2.0 for Native Apps) and RFC 7636 (PKCE S256)
with an ephemeral local loopback redirect server (127.0.0.1:0).
"""

import base64
import hashlib
import http.server
import json
import logging
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict, Optional, Tuple

from gemini_desktop_screenshare.config import AppConfig, load_config
from gemini_desktop_screenshare.auth.token_store import TokenStore

logger = logging.getLogger(__name__)


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generates a cryptographically secure RFC 7636 PKCE code_verifier and code_challenge.
    - code_verifier: 32 random octets, unpadded base64url encoded -> 43 characters.
    - code_challenge: SHA-256 of code_verifier, unpadded base64url encoded -> 43 characters.
    """
    raw_octets = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(raw_octets).decode("ascii").rstrip("=")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


class _OAuthRedirectHandler(http.server.BaseHTTPRequestHandler):
    """Internal HTTP handler for capturing Google's OAuth redirect on loopback."""

    server: "_LoopbackServer"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        code = qs.get("code", [None])[0]
        state = qs.get("state", [None])[0]
        error = qs.get("error", [None])[0]

        # Ignore auxiliary requests (e.g. /favicon.ico, /robots.txt) without code or error
        if not code and not error:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        self.server.received_code = code
        self.server.received_state = state
        self.server.received_error = error
        self.server.done = True

        if error:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head><title>Authentication Failed</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #1a1a1a; color: #ff6b6b;">
    <h2>Authentication Failed</h2>
    <p>Google returned error: <code>{error}</code></p>
    <p>You can close this window and return to Gemini Desktop.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        # Validate state before returning success page to prevent showing misleading success screen
        if self.server.expected_state is not None and state != self.server.expected_state:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Security Error</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #1a1a1a; color: #ff6b6b;">
    <h2>Authentication Security Error</h2>
    <p>CSRF state validation failed. Authorization request aborted.</p>
    <p>You may close this window.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = """<!DOCTYPE html>
<html>
<head><title>Sign-in Complete</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #1a1a1a; color: #e0e0e0;">
    <h2 style="color: #4dabf7;">Sign-in Successful!</h2>
    <p>Your Google Account has been linked to Gemini Desktop Screenshare.</p>
    <p>You may now safely close this browser tab and return to the application.</p>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP request logging to console."""
        pass


class _LoopbackServer(http.server.HTTPServer):
    """Custom HTTP server holding captured OAuth parameters."""

    def __init__(self, server_address: Tuple[str, int], expected_state: Optional[str] = None):
        super().__init__(server_address, _OAuthRedirectHandler)
        self.received_code: Optional[str] = None
        self.received_state: Optional[str] = None
        self.received_error: Optional[str] = None
        self.expected_state: Optional[str] = expected_state
        self.done: bool = False
        self._is_closed: bool = False
        self.timeout = 0.5


class OAuthManager:
    """
    Coordinates Google OAuth 2.0 PKCE authentication flow, token refreshing,
    and credential storage in Windows Credential Manager and DPAPI.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[AppConfig] = None,
        token_store: Optional[TokenStore] = None,
    ):
        if config is not None:
            self.config = config
        else:
            self.config = load_config(config_path)

        self.token_store = token_store or TokenStore(
            service_name="GeminiDesktopScreenshare",
            config_dir=self.config.config_dir,
        )

        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._user_profile: Dict[str, str] = {}
        self._pending_verifier: Optional[str] = None
        self._pending_state: Optional[str] = None

        # Load existing session from disk if present
        self._load_cached_session()

    def _load_cached_session(self) -> None:
        """Restores session information from disk cache with defensive validation."""
        session = self.token_store.get_session()
        if isinstance(session, dict):
            self._access_token = session.get("access_token")
            raw_exp = session.get("expires_at", 0.0)
            try:
                self._expires_at = float(raw_exp)
            except (ValueError, TypeError):
                logger.warning("Corrupted expires_at in session cache (%r); resetting to 0.0", raw_exp)
                self._expires_at = 0.0
            raw_profile = session.get("user_profile", {})
            self._user_profile = raw_profile if isinstance(raw_profile, dict) else {}
        else:
            self._access_token = None
            self._expires_at = 0.0
            self._user_profile = {}

    def get_auth_url(self, redirect_uri: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Constructs the Google OAuth 2.0 authorization URL with RFC 7636 PKCE S256 parameters.
        Returns (auth_url, state, code_verifier).
        """
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        self._pending_verifier = code_verifier
        self._pending_state = state

        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        if redirect_uri:
            params["redirect_uri"] = redirect_uri

        auth_url = f"{self.config.auth_uri}?{urllib.parse.urlencode(params)}"
        return auth_url, state, code_verifier

    def start_loopback_and_login(self, timeout: float = 120.0, open_browser: bool = True) -> Dict[str, Any]:
        """
        Launches an ephemeral loopback HTTP server on 127.0.0.1:0, opens the system browser,
        captures Google's OAuth 2.0 redirect, and exchanges authorization code for tokens.
        Handles requests in a loop until the redirect with code/error is received, ignoring
        stray requests such as /favicon.ico.
        """
        server = _LoopbackServer(("127.0.0.1", 0))
        host, port = server.server_address
        redirect_uri = f"http://127.0.0.1:{port}"
        logger.info("Started ephemeral OAuth loopback server on %s", redirect_uri)

        auth_url, expected_state, code_verifier = self.get_auth_url(redirect_uri=redirect_uri)
        server.expected_state = expected_state

        if open_browser:
            logger.info("Opening system browser for Google sign-in: %s", auth_url)
            webbrowser.open(auth_url)

        def _serve():
            while not server.done and not server._is_closed:
                try:
                    server.handle_request()
                except Exception:
                    break

        server_thread = threading.Thread(target=_serve)
        server_thread.daemon = True
        server_thread.start()

        # Wait for the redirect callback
        start_time = time.time()
        while not server.done and server_thread.is_alive():
            if time.time() - start_time > timeout:
                server._is_closed = True
                server.server_close()
                raise TimeoutError("OAuth login timed out waiting for browser callback.")
            time.sleep(0.05)

        server._is_closed = True
        server.server_close()

        if server.received_error:
            raise RuntimeError(f"Google OAuth failed: {server.received_error}")

        if not server.received_code:
            raise RuntimeError("OAuth redirect completed without authorization code.")

        if server.received_state != expected_state:
            raise ValueError(f"State mismatch! Expected {expected_state}, got {server.received_state}")

        # Exchange code for access & refresh tokens
        return self._exchange_code_for_tokens(server.received_code, code_verifier, redirect_uri)

    def _exchange_code_for_tokens(
        self, code: str, code_verifier: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchanges the PKCE authorization code for OAuth tokens."""
        token_payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        encoded_data = urllib.parse.urlencode(token_payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.token_uri,
            data=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("Token exchange failed: HTTP %s - %s", e.code, err_body)
            raise RuntimeError(f"Token exchange failed: HTTP {e.code} - {err_body}") from e

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise RuntimeError("OAuth response did not contain access_token.")

        self._access_token = access_token
        self._expires_at = time.time() + float(expires_in)

        if refresh_token:
            self.token_store.save_refresh_token(refresh_token)

        # Retrieve user profile
        profile = self._fetch_user_profile(access_token)
        self._user_profile = profile

        # Update session cache
        self.token_store.save_session({
            "access_token": self._access_token,
            "expires_at": self._expires_at,
            "user_profile": self._user_profile,
        })

        return {
            "access_token": self._access_token,
            "expires_at": self._expires_at,
            "user_profile": self._user_profile,
        }

    def _fetch_user_profile(self, access_token: str) -> Dict[str, str]:
        """Fetches basic user profile from Google UserInfo endpoint."""
        req = urllib.request.Request(
            self.config.userinfo_uri,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "email": data.get("email", ""),
                    "name": data.get("name", ""),
                    "picture": data.get("picture", ""),
                }
        except Exception as e:
            logger.warning("Could not fetch user profile: %s", e)
            return {"email": "user@gmail.com", "name": "Google User"}

    def refresh_access_token(self) -> str:
        """
        Uses the securely stored refresh token to obtain a fresh access token.
        """
        refresh_token = self.token_store.get_refresh_token()
        if not refresh_token:
            raise RuntimeError("No refresh token available. User must sign in.")

        refresh_payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        encoded_data = urllib.parse.urlencode(refresh_payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.token_uri,
            data=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("Token refresh failed: HTTP %s - %s", e.code, err_body)
            raise RuntimeError(f"Token refresh failed: HTTP {e.code} - {err_body}") from e

        access_token = data.get("access_token")
        if not access_token:
            raise RuntimeError("Token refresh response missing access_token.")

        expires_in = data.get("expires_in", 3600)
        self._access_token = access_token
        self._expires_at = time.time() + float(expires_in)

        # If a new refresh token is issued during rotation, update it
        new_refresh = data.get("refresh_token")
        if new_refresh:
            self.token_store.save_refresh_token(new_refresh)

        # Update session cache
        self.token_store.save_session({
            "access_token": self._access_token,
            "expires_at": self._expires_at,
            "user_profile": self._user_profile,
        })

        return self._access_token

    def get_valid_access_token(self) -> str:
        """
        Returns a valid access token.
        Proactively refreshes the token if within 5 minutes (300 seconds) of expiration.
        """
        try:
            expires_at = float(self._expires_at)
        except (ValueError, TypeError):
            expires_at = 0.0

        # If token exists and is valid for > 5 more minutes, return it
        if self._access_token and time.time() < (expires_at - 300):
            return self._access_token

        # Otherwise perform proactive refresh
        return self.refresh_access_token()

    def is_authenticated(self) -> bool:
        """
        Returns True if the user has an active access token, a stored refresh token, or an API key.
        """
        if getattr(self.config, "api_key", ""):
            return True

        try:
            expires_at = float(self._expires_at)
        except (ValueError, TypeError):
            expires_at = 0.0

        if self._access_token and time.time() < expires_at:
            return True
        return self.token_store.get_refresh_token() is not None

    def get_user_profile(self) -> Dict[str, str]:
        """Returns the authenticated user profile dict."""
        if not self._user_profile:
            self._load_cached_session()
        if not self._user_profile and getattr(self.config, "api_key", ""):
            return {
                "name": "Gemini API User",
                "email": "Connected via API Key",
                "picture": "",
            }
        return dict(self._user_profile)

    def sign_out(self) -> bool:
        """
        Signs the user out: revokes tokens at Google, deletes credentials from
        Windows Credential Manager / DPAPI, and clears session data.
        """
        refresh_token = self.token_store.get_refresh_token()
        token_to_revoke = refresh_token or self._access_token

        if token_to_revoke:
            try:
                revoke_url = f"{self.config.revoke_uri}?token={urllib.parse.quote(token_to_revoke)}"
                req = urllib.request.Request(revoke_url, data=b"", method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    pass
                logger.info("Successfully revoked token at Google OAuth endpoint.")
            except Exception as e:
                logger.warning("Could not revoke token with Google: %s", e)

        # Clear credentials and local session cache
        self.token_store.clear_session()
        self._access_token = None
        self._expires_at = 0.0
        self._user_profile = {}
        if getattr(self.config, "api_key", ""):
            self.config.api_key = ""
        return True
