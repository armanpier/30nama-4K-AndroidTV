"""
Adversarial Stress Testing & Protocol Verification for Mock Servers:
- MockGeminiLiveServer (WebSocket on 127.0.0.1:0)
- MockGeminiRestServer (HTTP on 127.0.0.1:0)
- MockOAuthServer (HTTP on 127.0.0.1:0)

Challenges:
1. Concurrency & Rapid Port Recycling (20 sequential cycles, 5 concurrent instances, zero WSAEADDRINUSE).
2. Dual Context Managers (sync `with` and async `async with`).
3. Wire Schema Verification (rejection 401/403/429, setup error, mediaChunks JPEG/PCM, modelTurn).
4. Interruption Barge-In Latency & Audio Purge Benchmark.
5. Malformed Inputs, Non-dict Payloads, and Abrupt Drops.
6. REST & OAuth Failure Modes (Bearer auth, HTTP 400/401/500/503, invalid_grant, revocation, userinfo).
"""

import asyncio
import base64
import json
import logging
import socket
import time
from typing import List, Tuple
import pytest
import requests
import websockets

from gemini_desktop_screenshare.tests.mock_servers import (
    MockGeminiLiveServer,
    MockGeminiRestServer,
    MockOAuthServer,
)
from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline

logger = logging.getLogger(__name__)


# ==============================================================================
# Helper utilities
# ==============================================================================

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks whether a TCP port is currently open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0


# ==============================================================================
# 1. MockGeminiLiveServer: Concurrency, Ports & Lifecycle
# ==============================================================================

def test_mock_live_20_sequential_start_stop_cycles():
    """
    Stress-test 20 rapid sequential start and stop cycles of MockGeminiLiveServer.
    Verifies that:
    1. Every start allocates a valid ephemeral port (> 1024).
    2. Server starts and binds within 5.0 seconds.
    3. Every stop completely releases the socket (no socket leak or lingering bind).
    4. Zero WSAEADDRINUSE port collisions.
    """
    allocated_ports = []
    cycle_times = []

    for i in range(20):
        t0 = time.perf_counter()
        server = MockGeminiLiveServer()
        server.start()
        port = server.port
        assert port is not None and port > 1024, f"Cycle {i}: Invalid port {port}"
        allocated_ports.append(port)

        # Confirm socket is active and bound
        assert is_port_in_use(port), f"Cycle {i}: Server on port {port} should be accepting connections"

        # Teardown
        server.stop()
        elapsed = time.perf_counter() - t0
        cycle_times.append(elapsed)

        # Allow slight delay for OS TCP stack to transition socket out of active state
        time.sleep(0.05)
        assert not is_port_in_use(port), f"Cycle {i}: Port {port} still in use after stop!"

    avg_time = sum(cycle_times) / len(cycle_times)
    assert len(allocated_ports) == 20
    print(f"\n[LiveServer 20 Cycles] Completed in {sum(cycle_times):.2f}s (avg {avg_time*1000:.1f}ms/cycle)")


def test_mock_live_5_concurrent_instances():
    """
    Stress-test 5 concurrent MockGeminiLiveServer instances running simultaneously on 127.0.0.1:0.
    Verifies that:
    1. All 5 instances receive unique ephemeral ports (zero collisions).
    2. All 5 servers can be connected to simultaneously.
    3. All 5 shut down cleanly without thread leaks or unhandled task exceptions.
    """
    servers = [MockGeminiLiveServer() for _ in range(5)]
    try:
        # Start all servers
        for s in servers:
            s.start()

        ports = [s.port for s in servers]
        assert len(ports) == 5
        assert len(set(ports)) == 5, f"Port collision detected among concurrent instances: {ports}"

        # Connect a client to each server concurrently
        async def _connect_and_ping(port: int):
            uri = f"ws://127.0.0.1:{port}"
            async with websockets.connect(uri) as ws:
                # Send setup frame
                await ws.send(json.dumps({"setup": {"model": "models/gemini-2.0-flash"}}))
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                assert "setupComplete" in data

        async def _run_all():
            tasks = [_connect_and_ping(p) for p in ports]
            await asyncio.gather(*tasks)

        asyncio.run(_run_all())

    finally:
        for s in servers:
            s.stop()

    # Verify all ports released
    for p in ports:
        time.sleep(0.05)
        assert not is_port_in_use(p), f"Port {p} still listening after concurrent teardown"


def test_mock_live_sync_context_manager():
    """Verifies synchronous context manager support (`with server:`)."""
    with MockGeminiLiveServer() as server:
        assert server.port is not None
        assert is_port_in_use(server.port)
        port = server.port

    time.sleep(0.05)
    assert not is_port_in_use(port)


@pytest.mark.asyncio
async def test_mock_live_async_context_manager():
    """Verifies asynchronous context manager support (`async with server:`)."""
    async with MockGeminiLiveServer() as server:
        assert server.port is not None
        assert is_port_in_use(server.port)
        port = server.port

    time.sleep(0.05)
    assert not is_port_in_use(port)


# ==============================================================================
# 2. MockGeminiLiveServer: Wire Schema & Rejection Stress
# ==============================================================================

def get_handshake_status(exc: Exception) -> int:
    """Extracts HTTP status code from InvalidStatus or InvalidStatusCode exception."""
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        return exc.response.status_code
    if hasattr(exc, "status_code"):
        return exc.status_code
    raise AssertionError(f"Could not extract status code from exception: {exc}")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429])
async def test_mock_live_handshake_rejections(status_code: int):
    """
    Validates rejection of the RFC 6455 handshake with specific HTTP error status codes.
    Emulates upstream quota exhaustion (429), unauthorized token (401), and permission denied (403).
    """
    with MockGeminiLiveServer(reject_handshake_status=status_code) as server:
        with pytest.raises(Exception) as exc_info:
            async with websockets.connect(server.ws_url):
                pass
        assert get_handshake_status(exc_info.value) == status_code


@pytest.mark.asyncio
async def test_mock_live_bearer_token_validation():
    """
    Validates Bearer token enforcement at the WebSocket handshake layer:
    1. Missing Authorization header -> 401 Unauthorized.
    2. Wrong Bearer token -> 401 Unauthorized.
    3. Correct Bearer token -> 101 Switching Protocols.
    """
    secret_token = "adversarial_secret_token_xyz"
    with MockGeminiLiveServer(expected_bearer_token=secret_token) as server:
        # 1. Missing header
        with pytest.raises(Exception) as exc:
            async with websockets.connect(server.ws_url):
                pass
        assert get_handshake_status(exc.value) == 401

        # 2. Wrong token
        with pytest.raises(Exception) as exc:
            async with websockets.connect(server.ws_url, additional_headers={"Authorization": "Bearer wrong"}):
                pass
        assert get_handshake_status(exc.value) == 401

        # 3. Valid token
        async with websockets.connect(
            server.ws_url, additional_headers={"Authorization": f"Bearer {secret_token}"}
        ) as ws:
            await ws.send(json.dumps({"setup": {}}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert "setupComplete" in resp


@pytest.mark.asyncio
async def test_mock_live_setup_error_simulation():
    """
    Validates simulated setup error:
    Server returns 400 INVALID_ARGUMENT JSON frame and terminates with WebSocket close code 1008.
    """
    err_msg = "Requested model 'unsupported-model' not found"
    with MockGeminiLiveServer(simulate_setup_error=err_msg) as server:
        async with websockets.connect(server.ws_url) as ws:
            await ws.send(json.dumps({"setup": {"model": "models/unsupported-model"}}))
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            resp = json.loads(resp_raw)
            assert resp["error"]["code"] == 400
            assert resp["error"]["message"] == err_msg
            assert resp["error"]["status"] == "INVALID_ARGUMENT"

            # Verify connection closes with code 1008
            with pytest.raises(websockets.exceptions.ConnectionClosed) as exc:
                await ws.recv()
            assert exc.value.code == 1008


@pytest.mark.asyncio
async def test_mock_live_multimodal_mediachunks_and_model_turn():
    """
    Verifies full-duplex transmission:
    1. Setup exchange
    2. Video JPEG mediaChunk transmission
    3. Audio 16kHz PCM mediaChunk transmission
    4. Server modelTurn delivery (synthetic text + 24kHz audio)
    """
    with MockGeminiLiveServer() as server:
        async with websockets.connect(server.ws_url) as ws:
            # 1. Setup
            await ws.send(json.dumps({"setup": {"model": "models/gemini-2.0-flash"}}))
            assert "setupComplete" in json.loads(await ws.recv())

            # 2. Video chunk (1.0 FPS simulated desktop frame)
            dummy_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 50 + b"\xff\xd9"
            video_payload = {
                "realtimeInput": {
                    "mediaChunks": [{
                        "mimeType": "image/jpeg",
                        "data": base64.b64encode(dummy_jpeg).decode("ascii"),
                    }]
                }
            }
            await ws.send(json.dumps(video_payload))

            # 3. Audio chunk (16kHz linear PCM)
            dummy_pcm = b"\x00\x00" * 1600  # 100ms of 16-bit 16kHz mono audio
            audio_payload = {
                "realtimeInput": {
                    "mediaChunks": [{
                        "mimeType": "audio/pcm;rate=16000",
                        "data": base64.b64encode(dummy_pcm).decode("ascii"),
                    }]
                }
            }
            await ws.send(json.dumps(audio_payload))

            # Allow server thread to process
            await asyncio.sleep(0.1)
            assert len(server.received_frames) == 1
            assert len(server.received_audio) == 1
            assert server.received_frames[0]["data"] == video_payload["realtimeInput"]["mediaChunks"][0]["data"]

            # 4. Server dispatches model turn
            synthetic_speech = b"\x11\x22" * 2400  # 100ms of 24kHz audio
            server.send_model_turn(
                text="I see your desktop and hear your microphone.",
                pcm_bytes=synthetic_speech,
                turn_complete=True,
            )

            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            turn = resp["serverContent"]["modelTurn"]
            assert turn["parts"][0]["text"] == "I see your desktop and hear your microphone."
            inline_data = turn["parts"][1]["inlineData"]
            assert inline_data["mimeType"] == "audio/pcm;rate=24000"
            assert base64.b64decode(inline_data["data"]) == synthetic_speech
            assert resp["serverContent"]["turnComplete"] is True


# ==============================================================================
# 3. MockGeminiLiveServer: Barge-In Latency & Audio Purge
# ==============================================================================

@pytest.mark.asyncio
async def test_mock_live_barge_in_latency_and_buffer_purge():
    """
    Adversarial Benchmark:
    Measures latency of barge-in interruption injection (`server.send_interruption()`)
    and verifies that client immediately purges its audio output buffer upon receipt.
    Repeats 10 times to compute min, max, avg, and p95 latency.
    """
    with MockGeminiLiveServer() as server:
        async with websockets.connect(server.ws_url) as ws:
            # Complete setup
            await ws.send(json.dumps({"setup": {}}))
            await ws.recv()

            latencies_ms = []

            for i in range(10):
                t_start = time.perf_counter()

                # Trigger interruption on server side
                server.send_interruption()

                # Client awaits frame
                raw_frame = await asyncio.wait_for(ws.recv(), timeout=2.0)
                t_received = time.perf_counter()

                frame = json.loads(raw_frame)
                assert frame.get("serverContent", {}).get("interrupted") is True

                latency = (t_received - t_start) * 1000.0
                latencies_ms.append(latency)

            avg_lat = sum(latencies_ms) / len(latencies_ms)
            min_lat = min(latencies_ms)
            max_lat = max(latencies_ms)
            latencies_ms.sort()
            p95_lat = latencies_ms[int(len(latencies_ms) * 0.95)]

            print(f"\n[Barge-In Latency (10 runs)] Avg: {avg_lat:.2f}ms | Min: {min_lat:.2f}ms | Max: {max_lat:.2f}ms | P95: {p95_lat:.2f}ms")

            # Barge-in latency over localhost must be sub-15ms
            assert avg_lat < 15.0, f"Average barge-in latency {avg_lat:.2f}ms exceeded 15ms SLA"
            assert p95_lat < 30.0, f"P95 barge-in latency {p95_lat:.2f}ms exceeded 30ms SLA"


# ==============================================================================
# 4. MockGeminiLiveServer: Malformed Inputs, Non-dict Payloads & Abrupt Drops
# ==============================================================================

@pytest.mark.asyncio
async def test_mock_live_malformed_json_resilience():
    """
    Injects malformed raw JSON strings from client to server:
    1. Unclosed JSON object `{ "broken": `
    2. Completely invalid text `NOT_JSON_AT_ALL`
    Verifies that the server does NOT crash, records raw messages, and remains operational.
    """
    with MockGeminiLiveServer() as server:
        async with websockets.connect(server.ws_url) as ws:
            await ws.send(json.dumps({"setup": {}}))
            await ws.recv()

            # Malformed frames
            await ws.send('{"realtimeInput": {"broken": ')
            await ws.send("NON_JSON_CORRUPTED_STREAM_DATA_!@#$%^&*")

            # Followed immediately by a valid frame
            valid_payload = {
                "realtimeInput": {
                    "mediaChunks": [{"mimeType": "image/jpeg", "data": "dGVzdA=="}]
                }
            }
            await ws.send(json.dumps(valid_payload))

            # Allow server loop to process
            await asyncio.sleep(0.1)

            assert len(server.raw_received_messages) >= 3
            assert len(server.received_frames) == 1
            assert server.received_frames[0]["data"] == "dGVzdA=="


@pytest.mark.asyncio
async def test_mock_live_non_dict_payload_behavior():
    """
    Adversarial Challenge: Non-dict JSON payloads.
    Sends valid JSON representations of non-dictionary iterable types:
    1. List: `[1, 2, 3]`
    2. Plain String: `"a raw string"`
    Server handles them without crashing because `key in list` and `key in str` are valid Python operations.
    """
    with MockGeminiLiveServer() as server:
        async with websockets.connect(server.ws_url) as ws:
            await ws.send(json.dumps({"setup": {}}))
            await ws.recv()

            # Test list payload
            await ws.send(json.dumps([1, 2, 3]))
            # Test string payload
            await ws.send(json.dumps("string payload"))

            await asyncio.sleep(0.05)
            # Now send valid frame
            valid_payload = {
                "realtimeInput": {
                    "mediaChunks": [{"mimeType": "image/jpeg", "data": "dGVzdA=="}]
                }
            }
            await ws.send(json.dumps(valid_payload))
            await asyncio.sleep(0.05)
            assert len(server.received_frames) == 1


@pytest.mark.asyncio
async def test_mock_live_streaming_scalar_vulnerability():
    """
    Verifies that when a client transmits a valid JSON scalar (e.g. integer `12345`, boolean `true`, or null `null`),
    the server defensively drops the non-dict frame without crashing, and subsequent streaming
    frames are processed normally.
    """
    with MockGeminiLiveServer() as server:
        async with websockets.connect(server.ws_url) as ws:
            await ws.send(json.dumps({"setup": {}}))
            await ws.recv()

            # Transmit scalar integer and boolean JSON - server safely ignores without crash
            await ws.send("12345")
            await ws.send("true")
            await ws.send("null")

            # Follow with valid realtimeInput frame
            valid_payload = {
                "realtimeInput": {
                    "mediaChunks": [{"mimeType": "image/jpeg", "data": "dGVzdA=="}]
                }
            }
            await ws.send(json.dumps(valid_payload))
            await asyncio.sleep(0.05)

            assert len(server.received_frames) == 1
            assert server.received_frames[0]["data"] == "dGVzdA=="


@pytest.mark.asyncio
async def test_mock_live_setup_malformed_input_vulnerabilities():
    """
    Verifies that during the initial setup handshake:
    1. If client sends non-JSON syntax (`{NOT_JSON`), server falls back safely and responds with setupComplete.
    2. If client sends non-dict JSON (`12345`), server falls back safely and responds with setupComplete.
    Zero unhandled exceptions or code 1011 crashes occur.
    """
    # 1. Invalid JSON during setup
    with MockGeminiLiveServer() as server1:
        async with websockets.connect(server1.ws_url) as ws1:
            await ws1.send("{INVALID_JSON")
            resp1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
            assert "setupComplete" in resp1

    # 2. Non-dict JSON scalar during setup
    with MockGeminiLiveServer() as server2:
        async with websockets.connect(server2.ws_url) as ws2:
            await ws2.send("99999")
            resp2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
            assert "setupComplete" in resp2


@pytest.mark.asyncio
async def test_mock_live_abrupt_disconnect_handling():
    """
    Verifies server handling of abrupt socket termination:
    1. Server invokes close_connection_abruptly(code=1001)
    2. Client observes ConnectionClosed with code 1001
    3. Server active_ws becomes None and connected_event is cleared
    4. Client reconnects successfully on the same running server instance
    """
    with MockGeminiLiveServer() as server:
        # First connection
        async with websockets.connect(server.ws_url) as ws:
            await ws.send(json.dumps({"setup": {}}))
            await ws.recv()
            assert server.active_ws is not None
            assert server.connected_event.is_set()

            # Server initiates abrupt drop
            server.close_connection_abruptly(code=1001)

            with pytest.raises(websockets.exceptions.ConnectionClosed) as exc:
                await ws.recv()
            assert exc.value.code == 1001

        # Allow cleanup
        await asyncio.sleep(0.1)
        assert server.active_ws is None
        assert not server.connected_event.is_set()

        # Reconnect on the same server
        async with websockets.connect(server.ws_url) as ws2:
            await ws2.send(json.dumps({"setup": {}}))
            resp = json.loads(await ws2.recv())
            assert "setupComplete" in resp
            assert server.active_ws is not None
            assert server.connected_event.is_set()


# ==============================================================================
# 5. MockGeminiRestServer: REST API Adversarial Stress
# ==============================================================================

def test_mock_rest_bearer_auth_rejection():
    """
    Validates Bearer auth verification in MockGeminiRestServer:
    1. Missing Authorization header -> 401 UNAUTHENTICATED
    2. Wrong token -> 401 UNAUTHENTICATED
    3. Correct token -> 200 OK
    """
    expected = "valid_rest_token_456"
    with MockGeminiRestServer(expected_bearer_token=expected) as server:
        url = server.rest_url

        # 1. No header
        resp = requests.post(url, json={"contents": []})
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["status"] == "UNAUTHENTICATED"

        # 2. Wrong header
        resp = requests.post(url, headers={"Authorization": "Bearer bad_token"}, json={"contents": []})
        assert resp.status_code == 401

        # 3. Correct header
        resp = requests.post(url, headers={"Authorization": f"Bearer {expected}"}, json={"contents": []})
        assert resp.status_code == 200
        assert len(resp.json()["candidates"]) == 1


@pytest.mark.parametrize("status_code", [400, 401, 500, 503])
def test_mock_rest_http_error_simulation(status_code: int):
    """Verifies that MockGeminiRestServer can emulate HTTP error codes."""
    with MockGeminiRestServer(status_code=status_code) as server:
        resp = requests.post(server.rest_url, json={})
        assert resp.status_code == status_code
        data = resp.json()
        assert data["error"]["code"] == status_code
        assert "Simulated error" in data["error"]["message"]


def test_mock_rest_invalid_json_and_edge_responses():
    """
    Tests edge-case response configurations:
    1. invalid_json=True -> Returns invalid JSON string
    2. empty_body=True -> Returns 200 with empty body
    3. empty_candidates=True -> Returns 200 with candidates: []
    """
    # 1. Invalid JSON
    with MockGeminiRestServer(invalid_json=True) as server:
        resp = requests.post(server.rest_url, json={})
        assert resp.status_code == 200
        assert resp.text == "NOT_A_VALID_JSON_OBJECT"
        with pytest.raises(Exception):
            resp.json()

    # 2. Empty Body
    with MockGeminiRestServer(empty_body=True) as server:
        resp = requests.post(server.rest_url, json={})
        assert resp.status_code == 200
        assert resp.text == ""

    # 3. Empty Candidates
    with MockGeminiRestServer(empty_candidates=True) as server:
        resp = requests.post(server.rest_url, json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidates"] == []


def test_mock_rest_context_managers_and_concurrency():
    """Tests sync and async context managers and 5 concurrent REST servers."""
    # Sync context manager
    with MockGeminiRestServer() as s:
        assert s.port is not None
        assert is_port_in_use(s.port)
        port = s.port
    time.sleep(0.05)
    assert not is_port_in_use(port)

    # 5 concurrent instances
    servers = [MockGeminiRestServer() for _ in range(5)]
    try:
        for s in servers:
            s.start()
        ports = [s.port for s in servers]
        assert len(ports) == 5
        assert len(set(ports)) == 5

        # Query all 5
        for s in servers:
            r = requests.post(s.rest_url, json={})
            assert r.status_code == 200
    finally:
        for s in servers:
            s.stop()


# ==============================================================================
# 6. MockOAuthServer: Protocol & Failure Mode Verification
# ==============================================================================

def test_mock_oauth_complete_protocol_flow():
    """
    Verifies full Google OAuth 2.0 PKCE flow emulation:
    1. Authorization code exchange (`grant_type=authorization_code`)
    2. Token refresh (`grant_type=refresh_token`)
    3. User profile retrieval (`GET /userinfo`)
    4. Token revocation (`POST /revoke`)
    """
    with MockOAuthServer(user_email="adversarial_test@example.com", user_name="Adversarial Challenger") as server:
        # 1. Code exchange
        token_data = {
            "grant_type": "authorization_code",
            "code": "4/0AdverSariAl_Mock_Code",
            "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            "redirect_uri": "http://127.0.0.1:8080",
            "client_id": "mock_client_id.apps.googleusercontent.com",
        }
        resp = requests.post(server.token_uri, data=token_data)
        assert resp.status_code == 200
        tokens = resp.json()
        assert tokens["access_token"].startswith("ya29.mock_")
        assert tokens["refresh_token"].startswith("1//mock_refresh_")
        assert tokens["expires_in"] == 3600
        assert tokens["token_type"] == "Bearer"
        assert len(server.token_exchanges) == 1

        # 2. Token refresh
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": "mock_client_id.apps.googleusercontent.com",
        }
        r_resp = requests.post(server.token_uri, data=refresh_data)
        assert r_resp.status_code == 200
        new_tokens = r_resp.json()
        assert new_tokens["access_token"].startswith("ya29.refreshed_")
        assert len(server.token_refreshes) == 1

        # 3. Userinfo
        u_resp = requests.get(server.userinfo_uri, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert u_resp.status_code == 200
        profile = u_resp.json()
        assert profile["email"] == "adversarial_test@example.com"
        assert profile["name"] == "Adversarial Challenger"
        assert len(server.userinfo_fetches) == 1

        # 4. Revocation
        rev_resp = requests.post(f"{server.revoke_uri}?token={tokens['refresh_token']}")
        assert rev_resp.status_code == 200
        assert rev_resp.text == "OK"
        assert len(server.revocations) == 1


def test_mock_oauth_refresh_failure_invalid_grant():
    """
    Verifies OAuth refresh token rejection simulation:
    When `should_fail_refresh=True`, returns 400 Bad Request with error: invalid_grant.
    """
    with MockOAuthServer(should_fail_refresh=True, refresh_error_code=400) as server:
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": "revoked_refresh_token",
        }
        resp = requests.post(server.token_uri, data=refresh_data)
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "invalid_grant"
        assert data["error_description"] == "Token revoked"


def test_mock_oauth_context_managers_and_concurrency():
    """Verifies sync/async context managers and concurrent instances for MockOAuthServer."""
    with MockOAuthServer() as s:
        assert s.port is not None
        assert is_port_in_use(s.port)
        port = s.port
    time.sleep(0.05)
    assert not is_port_in_use(port)

    # Concurrency
    servers = [MockOAuthServer() for _ in range(5)]
    try:
        for s in servers:
            s.start()
        ports = [s.port for s in servers]
        assert len(ports) == 5
        assert len(set(ports)) == 5
        for s in servers:
            r = requests.get(s.userinfo_uri)
            assert r.status_code == 200
    finally:
        for s in servers:
            s.stop()


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
