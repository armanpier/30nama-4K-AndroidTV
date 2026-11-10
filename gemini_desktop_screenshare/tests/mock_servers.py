"""
Offline Mock Servers for Gemini Desktop Screenshare Test Suite.
Provides standalone, fully offline mock servers bound dynamically to ephemeral ports (127.0.0.1:0):
1. MockGeminiLiveServer: WebSocket server emulating the Gemini Multimodal Live API v1alpha.
2. MockGeminiRestServer: HTTP REST server emulating Gemini generateContent API.
3. MockOAuthServer: HTTP server emulating Google OAuth 2.0 PKCE /token, /userinfo, and /revoke endpoints.
"""

import asyncio
import base64
import http.server
import json
import logging
import secrets
import threading
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional
import websockets
from websockets.http11 import Response

logger = logging.getLogger(__name__)


class MockGeminiLiveServer:
    """
    Offline Mock Server emulating the Gemini Multimodal Live API v1alpha WebSocket endpoint.
    Runs on an ephemeral port (127.0.0.1:0) in a dedicated background daemon thread with
    an isolated asyncio event loop to ensure zero interference with client test loops.
    Supports both sync (`with server:`) and async (`async with server:`) context managers.
    """

    def __init__(
        self,
        reject_handshake_status: Optional[int] = None,
        expected_bearer_token: Optional[str] = None,
        simulate_setup_error: Optional[str] = None,
        auto_respond_model_turn: bool = False,
    ):
        self.reject_handshake_status = reject_handshake_status
        self.expected_bearer_token = expected_bearer_token
        self.simulate_setup_error = simulate_setup_error
        self.auto_respond_model_turn = auto_respond_model_turn

        self.port: Optional[int] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._server: Optional[Any] = None
        self._ready_event = threading.Event()
        self._stop_event: Optional[asyncio.Event] = None

        self.active_ws: Optional[Any] = None
        self.connected_event = threading.Event()
        self.client_handshake_headers: Dict[str, str] = {}

        # Recorded client interactions
        self.received_setup: Optional[Dict[str, Any]] = None
        self.received_frames: List[Dict[str, Any]] = []
        self.received_audio: List[Dict[str, Any]] = []
        self.received_client_turns: List[Dict[str, Any]] = []
        self.raw_received_messages: List[str] = []

    def start(self) -> "MockGeminiLiveServer":
        """Starts the server in a background thread and waits for port binding."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._ready_event.wait(timeout=5.0):
            raise TimeoutError("MockGeminiLiveServer failed to bind and start within 5.0 seconds.")
        return self

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()

        async def _process_request(connection, request):
            self.client_handshake_headers = dict(request.headers)
            # Rejection simulation (e.g. 401, 403, 429)
            if self.reject_handshake_status:
                status = self.reject_handshake_status
                reason = {401: "Unauthorized", 403: "Forbidden", 429: "Too Many Requests"}.get(status, "Error")
                return Response(
                    status,
                    reason,
                    websockets.datastructures.Headers({"Content-Type": "text/plain"}),
                    f"Handshake rejected: HTTP {status} {reason}".encode("utf-8"),
                )
            if self.expected_bearer_token:
                auth = request.headers.get("Authorization", "")
                if auth != f"Bearer {self.expected_bearer_token}":
                    return Response(
                        401,
                        "Unauthorized",
                        websockets.datastructures.Headers({"Content-Type": "text/plain"}),
                        b"Unauthorized: Missing or invalid Bearer token",
                    )
            return None

        async def _ws_handler(ws):
            self.active_ws = ws
            self.connected_event.set()
            try:
                # 1. Setup handshake
                raw_setup = await ws.recv()
                self.raw_received_messages.append(raw_setup)
                try:
                    setup_data = json.loads(raw_setup)
                except Exception:
                    setup_data = {}

                if isinstance(setup_data, dict):
                    self.received_setup = setup_data.get("setup", {})
                else:
                    self.received_setup = {}

                if self.simulate_setup_error:
                    err_payload = {
                        "error": {
                            "code": 400,
                            "message": self.simulate_setup_error,
                            "status": "INVALID_ARGUMENT",
                        }
                    }
                    await ws.send(json.dumps(err_payload))
                    await ws.close(code=1008)
                    return

                # Send setupComplete
                await ws.send(json.dumps({"setupComplete": {}}))

                # 2. Continuous message processing loop
                while True:
                    raw_msg = await ws.recv()
                    self.raw_received_messages.append(raw_msg)
                    try:
                        msg = json.loads(raw_msg)
                    except Exception:
                        continue

                    if not isinstance(msg, dict):
                        continue

                    now = time.perf_counter()
                    # Handle realtimeInput (video and audio)
                    if "realtimeInput" in msg and isinstance(msg["realtimeInput"], dict):
                        chunks = msg["realtimeInput"].get("mediaChunks", [])
                        if isinstance(chunks, list):
                            for chunk in chunks:
                                if not isinstance(chunk, dict):
                                    continue
                                mime = chunk.get("mimeType", "")
                                data_b64 = chunk.get("data", "")
                                if "image" in mime:
                                    self.received_frames.append({
                                        "timestamp": now,
                                        "data": data_b64,
                                        "bytes_len": len(data_b64),
                                    })
                                elif "audio" in mime:
                                    self.received_audio.append({
                                        "timestamp": now,
                                        "data": data_b64,
                                        "bytes_len": len(data_b64),
                                    })

                    # Handle discrete clientContent turns
                    if "clientContent" in msg:
                        self.received_client_turns.append(msg["clientContent"])

                    # Auto-responder if enabled
                    if self.auto_respond_model_turn:
                        await ws.send(json.dumps({
                            "serverContent": {
                                "modelTurn": {
                                    "parts": [{"text": "Auto-response acknowledging screen/audio"}]
                                },
                                "turnComplete": True,
                                "interrupted": False,
                            }
                        }))

            except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.warning("MockGeminiLiveServer ws exception: %s", e)
            finally:
                self.active_ws = None
                self.connected_event.clear()

        async def _main():
            self._server = await websockets.serve(
                _ws_handler,
                "127.0.0.1",
                0,
                process_request=_process_request,
            )
            self.port = self._server.sockets[0].getsockname()[1]
            self._ready_event.set()
            await self._stop_event.wait()
            if self.active_ws:
                try:
                    await self.active_ws.close()
                except Exception:
                    pass
            self._server.close()
            await self._server.wait_closed()

        self._loop.run_until_complete(_main())
        self._loop.close()

    def send_model_turn(
        self,
        text: str = "",
        pcm_bytes: bytes = b"",
        turn_complete: bool = False,
        timeout: float = 3.0,
    ) -> None:
        """Dispatches a realistic serverContent.modelTurn to the connected client."""
        if not self.active_ws or not self._loop:
            raise RuntimeError("Cannot send model turn: No active client WebSocket connection.")
        parts = []
        if text:
            parts.append({"text": text})
        if pcm_bytes:
            parts.append({
                "inlineData": {
                    "mimeType": "audio/pcm;rate=24000",
                    "data": base64.b64encode(pcm_bytes).decode("ascii"),
                }
            })
        payload = {
            "serverContent": {
                "modelTurn": {"parts": parts},
                "turnComplete": turn_complete,
                "interrupted": False,
            }
        }
        coro = self.active_ws.send(json.dumps(payload))
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.result(timeout=timeout)

    def send_interruption(self, timeout: float = 3.0) -> None:
        """Dispatches a barge-in interruption signal (interrupted: true)."""
        if not self.active_ws or not self._loop:
            raise RuntimeError("Cannot send interruption: No active client WebSocket connection.")
        payload = {"serverContent": {"interrupted": True}}
        coro = self.active_ws.send(json.dumps(payload))
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.result(timeout=timeout)

    def send_raw_frame(self, raw_str: str, timeout: float = 3.0) -> None:
        """Sends arbitrary raw text to test client malformed frame handling."""
        if not self.active_ws or not self._loop:
            raise RuntimeError("No active WebSocket connection.")
        coro = self.active_ws.send(raw_str)
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.result(timeout=timeout)

    def close_connection_abruptly(self, code: int = 1001) -> None:
        """Abruptly terminates the active client WebSocket."""
        if self.active_ws and self._loop:
            coro = self.active_ws.close(code=code)
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            try:
                future.result(timeout=2.0)
            except Exception:
                pass

    def stop(self) -> None:
        """Deterministic teardown closing all sockets and joining the thread."""
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=3.0)

    @property
    def ws_url(self) -> str:
        return f"ws://127.0.0.1:{self.port}"

    def __enter__(self) -> "MockGeminiLiveServer":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    async def __aenter__(self) -> "MockGeminiLiveServer":
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class MockGeminiRestServer:
    """
    Offline Mock Server emulating the Gemini REST generateContent API endpoint.
    Binds dynamically to an ephemeral port (127.0.0.1:0).
    Validates Authorization: Bearer <token> headers and multimodal inline JPEG payloads.
    Supports both sync (`with server:`) and async (`async with server:`) context managers.
    """

    def __init__(
        self,
        expected_bearer_token: Optional[str] = None,
        custom_response_text: Optional[str] = None,
        status_code: int = 200,
        empty_body: bool = False,
        invalid_json: bool = False,
        empty_candidates: bool = False,
    ):
        self.expected_bearer_token = expected_bearer_token
        self.custom_response_text = custom_response_text or "Default mock on-demand screen analysis."
        self.status_code = status_code
        self.empty_body = empty_body
        self.invalid_json = invalid_json
        self.empty_candidates = empty_candidates

        self.port: Optional[int] = None
        self.server: Optional[http.server.HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

        self.received_requests: List[Dict[str, Any]] = []

    def start(self) -> "MockGeminiRestServer":
        server_ref = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
                auth_header = self.headers.get("Authorization", "")

                try:
                    parsed_json = json.loads(raw_body) if raw_body else {}
                except Exception:
                    parsed_json = {}

                server_ref.received_requests.append({
                    "path": self.path,
                    "headers": dict(self.headers),
                    "auth": auth_header,
                    "body": parsed_json,
                    "raw_body": raw_body,
                })

                # Check Bearer token if required
                if server_ref.expected_bearer_token:
                    expected = f"Bearer {server_ref.expected_bearer_token}"
                    if auth_header != expected:
                        self.send_response(401)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        err_resp = {
                            "error": {
                                "code": 401,
                                "message": "Request is missing required authentication credential.",
                                "status": "UNAUTHENTICATED",
                            }
                        }
                        self.wfile.write(json.dumps(err_resp).encode("utf-8"))
                        return

                # Check custom error status simulation
                if server_ref.status_code != 200:
                    self.send_response(server_ref.status_code)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    err_resp = {
                        "error": {
                            "code": server_ref.status_code,
                            "message": f"Simulated error {server_ref.status_code}",
                            "status": "ERROR",
                        }
                    }
                    self.wfile.write(json.dumps(err_resp).encode("utf-8"))
                    return

                if server_ref.empty_body:
                    self.send_response(200)
                    self.end_headers()
                    return

                if server_ref.invalid_json:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"NOT_A_VALID_JSON_OBJECT")
                    return

                # Normal success response
                candidates = []
                if not server_ref.empty_candidates:
                    candidates = [
                        {
                            "content": {
                                "parts": [{"text": server_ref.custom_response_text}],
                                "role": "model",
                            },
                            "finishReason": "STOP",
                            "index": 0,
                        }
                    ]

                resp = {
                    "candidates": candidates,
                    "usageMetadata": {
                        "promptTokenCount": 265,
                        "candidatesTokenCount": 40,
                        "totalTokenCount": 305,
                    },
                }
                resp_bytes = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp_bytes)))
                self.end_headers()
                self.wfile.write(resp_bytes)

            def log_message(self, format, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=3.0)

    @property
    def rest_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1beta/models/gemini-2.0-flash:generateContent"

    def __enter__(self) -> "MockGeminiRestServer":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    async def __aenter__(self) -> "MockGeminiRestServer":
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class MockOAuthServer:
    """
    Offline Mock Server emulating Google OAuth 2.0 PKCE token endpoints:
    - /token (authorization code exchange & token refresh)
    - /userinfo (user profile fetch)
    - /revoke (token revocation)
    Supports both sync (`with server:`) and async (`async with server:`) context managers.
    """

    def __init__(
        self,
        should_fail_refresh: bool = False,
        refresh_error_code: int = 400,
        user_email: str = "mock_user@gmail.com",
        user_name: str = "Mock Google User",
    ):
        self.should_fail_refresh = should_fail_refresh
        self.refresh_error_code = refresh_error_code
        self.user_email = user_email
        self.user_name = user_name

        self.port: Optional[int] = None
        self.server: Optional[http.server.HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

        self.token_exchanges: List[Dict[str, Any]] = []
        self.token_refreshes: List[Dict[str, Any]] = []
        self.revocations: List[str] = []
        self.userinfo_fetches: List[str] = []

    def start(self) -> "MockOAuthServer":
        server_ref = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path.rstrip("/") == "/userinfo":
                    auth = self.headers.get("Authorization", "")
                    server_ref.userinfo_fetches.append(auth)
                    profile = {
                        "email": server_ref.user_email,
                        "name": server_ref.user_name,
                        "picture": "https://example.com/mock_avatar.png",
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(profile).encode("utf-8"))
                    return

                self.send_response(404)
                self.end_headers()

            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
                parsed_body = urllib.parse.parse_qs(body)
                parsed_path = urllib.parse.urlparse(self.path).path.rstrip("/")

                if parsed_path.endswith("token"):
                    grant_type = parsed_body.get("grant_type", [""])[0]
                    if grant_type == "authorization_code":
                        server_ref.token_exchanges.append(parsed_body)
                        resp = {
                            "access_token": f"ya29.mock_{secrets.token_hex(8)}",
                            "refresh_token": f"1//mock_refresh_{secrets.token_hex(8)}",
                            "expires_in": 3600,
                            "token_type": "Bearer",
                        }
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(resp).encode("utf-8"))
                        return
                    elif grant_type == "refresh_token":
                        server_ref.token_refreshes.append(parsed_body)
                        if server_ref.should_fail_refresh:
                            self.send_response(server_ref.refresh_error_code)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "error": "invalid_grant",
                                "error_description": "Token revoked",
                            }).encode("utf-8"))
                            return
                        resp = {
                            "access_token": f"ya29.refreshed_{secrets.token_hex(8)}",
                            "expires_in": 3600,
                        }
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(resp).encode("utf-8"))
                        return

                elif parsed_path.endswith("revoke"):
                    server_ref.revocations.append(self.path)
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
        return self

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=3.0)

    @property
    def token_uri(self) -> str:
        return f"http://127.0.0.1:{self.port}/token"

    @property
    def userinfo_uri(self) -> str:
        return f"http://127.0.0.1:{self.port}/userinfo"

    @property
    def revoke_uri(self) -> str:
        return f"http://127.0.0.1:{self.port}/revoke"

    def __enter__(self) -> "MockOAuthServer":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    async def __aenter__(self) -> "MockOAuthServer":
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
