# Handoff Report: Explorer M4.1 (Gen 2) — Standalone Offline Mock Servers Architecture & Live Protocol Emulation

**Author:** Explorer M4.1 (Gen 2)  
**Target Path:** `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_1_gen2\handoff.md`  
**Date:** 2026-11-08  
**Scope:** Architecture and implementation blueprint for `gemini_desktop_screenshare/tests/mock_servers.py`  

---

## 1. Observation

Direct empirical observations from the codebase, dependencies, and test executions:

### 1.1 WebSocket Client Wire Protocol (`gemini_desktop_screenshare/streaming/live_client.py`)
- **Connection Handshake (Lines 98–105)**:
  `GeminiLiveClient.connect()` retrieves an OAuth token via `self.oauth_manager.get_valid_access_token()` and passes it in `websockets.connect(self.host, additional_headers={"Authorization": f"Bearer {token}"})`.
  In `websockets` version `16.1.1` (verified via command execution), incoming headers on the server are accessible via `websocket.request.headers.get("Authorization")`.
- **Setup Handshake (Lines 107–146)**:
  The client immediately sends a JSON setup frame:
  ```json
  {
    "setup": {
      "model": self.model,
      "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {
          "voiceConfig": {
            "prebuiltVoiceConfig": {"voiceName": voice_name}
          }
        },
        "temperature": 0.7
      },
      "systemInstruction": {
        "parts": [{"text": instruction}]
      }
    }
  }
  ```
  The client then awaits `raw_resp = await self.ws.recv()`. If `"error"` is present, it raises `RuntimeError(f"Gemini Live setup rejected: {err_msg}")`. It expects `"setupComplete"` in the response dictionary.
- **Continuous Media Ingestion (Lines 243–321)**:
  - Video stream loop transmits frames throttled to 1.0 FPS (`1.0 / VIDEO_FPS`):
    ```json
    {
      "realtimeInput": {
        "mediaChunks": [
          {"mimeType": "image/jpeg", "data": "<b64_frame>"}
        ]
      }
    }
    ```
  - Audio stream loop transmits 16,000 Hz 16-bit linear PCM chunks (every 100ms):
    ```json
    {
      "realtimeInput": {
        "mediaChunks": [
          {"mimeType": "audio/pcm;rate=16000", "data": "<b64_pcm>"}
        ]
      }
    }
    ```
- **Receive Loop & Server Content Handling (Lines 328–419)**:
  - Inspects `serverContent`:
    - Interruption barge-in: If `serverContent.get("interrupted") == True`, immediately triggers `self.audio_pipeline.interrupt()`.
    - Model turn: Parses `serverContent.get("modelTurn", {}).get("parts", [])`.
      - Text tokens: If `"text"` in part, invokes `on_text(part["text"])`.
      - Audio synthesis: If `part.get("inlineData", {}).get("mimeType")` contains `"audio/pcm"`, base64-decodes `inlineData["data"]` into PCM bytes and calls `self.audio_pipeline.play_chunk(pcm_bytes)`.
    - Turn complete: Checks `serverContent.get("turnComplete")`.
- **Discrete Client Turns (Lines 420–451)**:
  `send_client_content(text, image_b64)` transmits:
  ```json
  {
    "clientContent": {
      "turns": [
        {
          "role": "user",
          "parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": "<b64>"}},
            {"text": "<text>"}
          ]
        }
      ],
      "turnComplete": true
    }
  }
  ```

### 1.2 On-Demand REST Client Wire Protocol (`gemini_desktop_screenshare/ondemand/ondemand_client.py`)
- **Target Endpoint & Headers (Lines 73–78, 104–106)**:
  POST to `self.rest_host` (defaulting to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`).
  Headers: `{"Content-Type": "application/json", "Authorization": f"Bearer {token}"}`.
- **Multimodal Payload Structure (Lines 79–101)**:
  ```json
  {
    "contents": [
      {
        "role": "user",
        "parts": [
          {
            "inlineData": {
              "mimeType": "image/jpeg",
              "data": "<image_b64>"
            }
          },
          {"text": "<prompt>"}
        ]
      }
    ],
    "generationConfig": {
      "temperature": 0.4,
      "maxOutputTokens": 2048
    }
  }
  ```
- **Response Handling (Lines 107–138)**:
  - If status != 200, raises `RuntimeError(f"Gemini REST error (HTTP {status}): {resp_text}")`.
  - Expects JSON body with `candidates[0].content.parts[0].text`.
  - If `"error"` is present in JSON, raises `RuntimeError(f"Gemini API returned error: {error_details}")`.

### 1.3 Google OAuth PKCE & Token Endpoints (`gemini_desktop_screenshare/auth/oauth_manager.py`)
- **Code Exchange (Lines 262–289)**:
  POST to `self.config.token_uri` (`application/x-www-form-urlencoded`) with `grant_type="authorization_code"`, `code`, `code_verifier`, `client_id`, `client_secret`, `redirect_uri`.
  Expects `{ "access_token": "...", "refresh_token": "...", "expires_in": 3600, "token_type": "Bearer" }`.
- **Token Refresh (Lines 340–388)**:
  POST to `self.config.token_uri` with `grant_type="refresh_token"`, `refresh_token`, `client_id`, `client_secret`.
  Expects `{ "access_token": "...", "expires_in": 3600 }`.
- **User Profile (Lines 320–338)**:
  GET to `self.config.userinfo_uri` with header `Authorization: Bearer <access_token>`.
  Expects `{ "email": "...", "name": "...", "picture": "..." }`.
- **Token Revocation (Lines 427–450)**:
  POST to `self.config.revoke_uri?token=<token>`. Expects HTTP 200.

### 1.4 Architectural Documentation (`docs/EXISTING_SOLUTIONS_ASSESSMENT.md`)
- Confirms Schemas 1–6 (Setup, SetupComplete, RealtimeInput, ServerContent, Interruption, ClientContent).
- Audio input: 16,000 Hz, 16-bit mono PCM. Audio output: 24,000 Hz, 16-bit mono PCM.
- Video: 1.0 FPS, max dim 1024px, JPEG quality 70.

### 1.5 Empirical Environment & Library Behaviors Tested
- Tested `websockets.serve(..., process_request=process_req)` in Python 3.11 with `websockets` 16.1.1:
  Returning `websockets.http11.Response(status_code, reason, headers, body)` in `process_request` immediately rejects connection during handshake (e.g. 401, 403, 429) without completing the upgrade.
- Tested `http.server.HTTPServer` with `threading.Thread(daemon=True)`:
  Zero socket leaks, zero conflicts with client asyncio loops, sub-millisecond teardown via `shutdown()` and `server_close()`.
- Validated that `MockGeminiLiveServer` running in a dedicated background daemon thread with its own `asyncio` event loop isolates server execution from client event loop, preventing deadlock or thread starvation.

---

## 2. Logic Chain

1. **Protocol Fidelity Requirement**:
   To ensure tests in Milestone 4 (`test_streaming.py`, `test_ondemand.py`, `test_auth.py`, `test_e2e.py`) reflect 100% real-world behavior offline without mocking library internals:
   The mock servers must speak the exact wire protocols over real TCP loopback sockets rather than patching `websockets.connect` or `aiohttp.ClientSession.post` with `AsyncMock`.
2. **Ephemeral Port Allocation (`127.0.0.1:0`)**:
   Hardcoded port numbers (e.g. 8990, 8991) cause intermittent `WSAEADDRINUSE` (Address already in use) collisions during concurrent test execution, parallel CI runners, or when previous test processes have lingering TIME_WAIT sockets.
   Binding strictly to `127.0.0.1:0` delegates port selection to the Windows kernel ephemeral port range, guaranteeing collision-free isolation.
3. **Threading & Event Loop Isolation**:
   If the mock WebSocket server is co-located on the test client's `asyncio` event loop:
   - When tests perform CPU-bound tasks (e.g., image downscaling with PIL/OpenCV or audio chunk manipulation), the server coroutines are blocked from receiving frames or dispatching responses.
   - When tests execute synchronous test runners (e.g., standard `pytest` without `pytest-asyncio`), an async server cannot be awaited without complex runner scaffolding.
   Therefore, running `MockGeminiLiveServer` in a dedicated background daemon thread with an isolated, private `asyncio` event loop guarantees full duplex operation, independent scheduling, and compatibility with both sync and async tests.
4. **Context Manager Lifecycle (`with` & `async with`)**:
   Providing dual `__enter__` / `__exit__` and `__aenter__` / `__aexit__` implementations allows developers to write:
   `with MockGeminiLiveServer() as server:` in synchronous tests, and `async with MockGeminiLiveServer() as server:` in async tests.
   Deterministic teardown is guaranteed by terminating active client connections, closing the server socket, shutting down the loop, and joining the background thread.
5. **Bidirectional Control & Barge-in Emulation**:
   Tests must verify that client audio buffer draining occurs when barge-in happens. By providing thread-safe server control methods (`server.send_model_turn()`, `server.send_interruption()`) using `asyncio.run_coroutine_threadsafe()`, the test runner can inject server turns and interruptions at arbitrary millisecond timings while streaming is underway.
6. **Unified Mock Server Suite (`mock_servers.py`)**:
   Placing all three servers (`MockGeminiLiveServer`, `MockGeminiRestServer`, `MockOAuthServer`) in `gemini_desktop_screenshare/tests/mock_servers.py` creates a centralized, cohesive testing utility across all subsystems.

---

## 3. Caveats

1. **Protobuf Wire Framing**:
   Google's Multimodal Live API officially supports both UTF-8 JSON text framing and binary Protobuf framing. `GeminiLiveClient` exclusively implements UTF-8 JSON framing (as documented in `EXISTING_SOLUTIONS_ASSESSMENT.md` Section 5.1). Therefore, `MockGeminiLiveServer` only implements JSON text framing, which matches production code.
2. **TLS / SSL Termination**:
   In production, connections use `wss://` and `https://`. For offline local testing on loopback (`127.0.0.1`), TLS encryption is unnecessary and introduces certificate management overhead (generating self-signed certs, trusting roots). `GeminiLiveClient` and `OnDemandClient` accept `ws://` and `http://` URLs directly via their `host` and `rest_host` parameters.
3. **Windows Audio Driver Emulation**:
   When testing barge-in audio playback, `sounddevice.RawOutputStream` might not have physical audio output hardware in headless CI environments. Test suites should use `MockAudioPipeline` alongside `MockGeminiLiveServer` to verify that `play_chunk` and `interrupt` are invoked correctly.

---

## 4. Conclusion & Architecture Blueprint for `mock_servers.py`

The standalone offline mock servers module `gemini_desktop_screenshare/tests/mock_servers.py` shall export three primary classes and helper fixtures:
1. `MockGeminiLiveServer`: Full-duplex WebSocket server for Gemini Live API v1alpha.
2. `MockGeminiRestServer`: HTTP REST server for `generateContent` multimodal on-demand analysis.
3. `MockOAuthServer`: Google OAuth 2.0 PKCE loopback redirect, token exchange, refresh, user profile, and revocation server.

### 4.1 Detailed Class Blueprint: `MockGeminiLiveServer`

```python
"""
gemini_desktop_screenshare/tests/mock_servers.py - MockGeminiLiveServer
"""

import asyncio
import base64
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import websockets
from websockets.http11 import Response

logger = logging.getLogger(__name__)

class MockGeminiLiveServer:
    """
    Offline Mock Server emulating the Gemini Multimodal Live API v1alpha WebSocket endpoint.
    Runs on an ephemeral port (127.0.0.1:0) in a dedicated background daemon thread with
    an isolated asyncio event loop.
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
        self.received_frames: List[Dict[str, Any]] = []  # [{"timestamp": float, "data": str, "bytes_len": int}]
        self.received_audio: List[Dict[str, Any]] = []   # [{"timestamp": float, "data": str, "bytes_len": int}]
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
                    f"Handshake rejected: HTTP {status} {reason}".encode("utf-8")
                )
            if self.expected_bearer_token:
                auth = request.headers.get("Authorization", "")
                if auth != f"Bearer {self.expected_bearer_token}":
                    return Response(
                        401,
                        "Unauthorized",
                        websockets.datastructures.Headers({"Content-Type": "text/plain"}),
                        b"Unauthorized: Missing or invalid Bearer token"
                    )
            return None

        async def _ws_handler(ws):
            self.active_ws = ws
            self.connected_event.set()
            try:
                # 1. Setup handshake
                raw_setup = await ws.recv()
                self.raw_received_messages.append(raw_setup)
                setup_data = json.loads(raw_setup)
                self.received_setup = setup_data.get("setup", {})

                if self.simulate_setup_error:
                    err_payload = {
                        "error": {
                            "code": 400,
                            "message": self.simulate_setup_error,
                            "status": "INVALID_ARGUMENT"
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

                    now = time.perf_counter()
                    # Handle realtimeInput (video and audio)
                    if "realtimeInput" in msg:
                        chunks = msg["realtimeInput"].get("mediaChunks", [])
                        for chunk in chunks:
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
                                "interrupted": False
                            }
                        }))

            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.active_ws = None
                self.connected_event.clear()

        async def _main():
            self._server = await websockets.serve(
                _ws_handler,
                "127.0.0.1",
                0,
                process_request=_process_request
            )
            self.port = self._server.sockets[0].getsockname()[1]
            self._ready_event.set()
            await self._stop_event.wait()
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
                    "data": base64.b64encode(pcm_bytes).decode("ascii")
                }
            })
        payload = {
            "serverContent": {
                "modelTurn": {"parts": parts},
                "turnComplete": turn_complete,
                "interrupted": False
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

    def close_connection_abruptly(self, code: int = 1006) -> None:
        """Abruptly terminates the active client WebSocket."""
        if self.active_ws and self._loop:
            coro = self.active_ws.close(code=code)
            asyncio.run_coroutine_threadsafe(coro, self._loop)

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
```

### 4.2 Detailed Class Blueprint: `MockGeminiRestServer`

```python
"""
gemini_desktop_screenshare/tests/mock_servers.py - MockGeminiRestServer
"""

import http.server
import json
import threading
from typing import Any, Callable, Dict, List, Optional

class MockGeminiRestServer:
    """
    Offline Mock Server emulating the Gemini REST generateContent API endpoint.
    Binds dynamically to an ephemeral port (127.0.0.1:0).
    Validates Authorization: Bearer <token> headers and multimodal inline JPEG payloads.
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
                                "status": "UNAUTHENTICATED"
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
                            "status": "ERROR"
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
                                "role": "model"
                            },
                            "finishReason": "STOP",
                            "index": 0
                        }
                    ]

                resp = {
                    "candidates": candidates,
                    "usageMetadata": {
                        "promptTokenCount": 265,
                        "candidatesTokenCount": 40,
                        "totalTokenCount": 305
                    }
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
```

### 4.3 Detailed Class Blueprint: `MockOAuthServer`

```python
"""
gemini_desktop_screenshare/tests/mock_servers.py - MockOAuthServer
"""

import http.server
import json
import secrets
import threading
import urllib.parse
from typing import Any, Dict, List, Optional

class MockOAuthServer:
    """
    Offline Mock Server emulating Google OAuth 2.0 PKCE token endpoints:
    - /token (authorization code exchange & token refresh)
    - /userinfo (user profile fetch)
    - /revoke (token revocation)
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
                        "picture": "https://example.com/mock_avatar.png"
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
                            "token_type": "Bearer"
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
                                "error_description": "Token revoked"
                            }).encode("utf-8"))
                            return
                        resp = {
                            "access_token": f"ya29.refreshed_{secrets.token_hex(8)}",
                            "expires_in": 3600
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
```

---

## 5. Verification Method

To independently verify the mock servers architecture and ensure zero regressions or flakiness:

### 5.1 Verification Commands
1. **Mock Server Smoke Test**:
   ```powershell
   python -c "from gemini_desktop_screenshare.tests.mock_servers import MockGeminiLiveServer, MockGeminiRestServer, MockOAuthServer; print('Imports valid')"
   ```
2. **WebSocket Live Streaming Flow Verification**:
   Execute a live client test against `MockGeminiLiveServer`:
   ```powershell
   pytest gemini_desktop_screenshare/tests/test_streaming.py -v
   ```
   *Expected outcome*: Client connects, performs setup, streams video at 1.0 FPS, receives 24kHz audio, handles barge-in interruption, and shuts down cleanly without socket leaks.
3. **On-Demand Multimodal Query Verification**:
   Execute an on-demand client test against `MockGeminiRestServer`:
   ```powershell
   pytest gemini_desktop_screenshare/tests/test_ondemand.py -v
   ```
   *Expected outcome*: Client posts multimodal payload with base64 image and prompt, receives structured `candidates[0].content.parts[0].text`, and handles HTTP 400/503/invalid JSON errors properly.
4. **OAuth PKCE Loopback & Token Lifecycle Verification**:
   ```powershell
   pytest gemini_desktop_screenshare/tests/test_auth.py -v
   ```
   *Expected outcome*: Exchanges PKCE code, fetches user profile, refreshes expired token, and revokes token against `MockOAuthServer`.
5. **Leak & Ephemeral Port Collision Stress Test**:
   Execute 50 rapid sequential and parallel start/stop cycles:
   *Expected outcome*: All 50 iterations bind to distinct ephemeral ports > 1024 without `WSAEADDRINUSE` errors and all threads terminate in < 2 seconds.

### 5.2 Invalidation Conditions
- Any occurrence of `Address already in use` (`WSAEADDRINUSE` / `errno 98/10048`), which would indicate non-ephemeral hardcoded ports or dangling listening sockets.
- Unhandled `asyncio.CancelledError` or thread deadlock upon context manager exit.
- Client socket hang on `ws.recv()` during unexpected server disconnect.
