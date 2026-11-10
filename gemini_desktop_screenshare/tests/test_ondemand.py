"""
Unit tests for On-Demand Screen Capture and Multimodal Query Subsystem.
Tests REST generateContent payload construction, Bearer token injection,
successful candidate parsing, empty candidates/parts handling, HTTP error status codes,
and end-to-end full screen/window query targeting against MockGeminiRestServer.
"""

import pytest

from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
from gemini_desktop_screenshare.ondemand.ondemand_client import OnDemandClient
from gemini_desktop_screenshare.tests.mock_servers import MockGeminiRestServer


class MockOAuthManager:
    def __init__(self, token="mock_bearer_token_abc"):
        self.token = token

    def get_valid_access_token(self):
        return self.token


class MockCaptureEngine:
    def __init__(self):
        self.b64_frame = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        self.captured_targets = []

    def capture_frame_base64(self, target_type="full_screen", target_id=0, max_dim=1024, quality=70):
        self.captured_targets.append((target_type, target_id))
        return self.b64_frame


# ------------------------------------------------------------------------------
# 1. Payload Structure & Authorization Header Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ondemand_query_payload_structure_and_bearer_auth():
    """Verifies that OnDemandClient submits correctly formatted Gemini multimodal payload and Bearer header."""
    with MockGeminiRestServer(expected_bearer_token="secret_access_token_777") as server:
        oauth = MockOAuthManager("secret_access_token_777")
        cap = MockCaptureEngine()
        client = OnDemandClient(oauth, cap, rest_host=server.rest_url)

        res = await client.query_image(
            image_b64=cap.b64_frame,
            prompt="Analyze the open window and explain the error.",
        )

        assert res == server.custom_response_text
        assert len(server.received_requests) == 1
        req = server.received_requests[0]
        assert req["auth"] == "Bearer secret_access_token_777"

        body = req["body"]
        assert "contents" in body
        parts = body["contents"][0]["parts"]
        assert parts[0]["inlineData"]["mimeType"] == "image/jpeg"
        assert parts[0]["inlineData"]["data"] == cap.b64_frame
        assert parts[1]["text"] == "Analyze the open window and explain the error."


# ------------------------------------------------------------------------------
# 2. Response Parsing Edge Cases
# ------------------------------------------------------------------------------
def test_ondemand_successful_response_parsing():
    """Verifies parsing model candidate text parts into combined text string."""
    client = OnDemandClient(MockOAuthManager(), MockCaptureEngine())
    resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Line 1: No errors observed. "},
                        {"text": "Line 2: Ready to proceed."},
                    ]
                }
            }
        ]
    }
    parsed = client._parse_gemini_response(resp_json)
    assert parsed == "Line 1: No errors observed. Line 2: Ready to proceed."


def test_ondemand_empty_candidates_handling():
    """Verifies graceful handling of empty candidates list."""
    client = OnDemandClient(MockOAuthManager(), MockCaptureEngine())
    resp_json = {"candidates": []}
    parsed = client._parse_gemini_response(resp_json)
    assert parsed == "No candidates returned by Gemini."


def test_ondemand_empty_text_parts_handling():
    """Verifies graceful handling of candidates without text parts."""
    client = OnDemandClient(MockOAuthManager(), MockCaptureEngine())
    resp_json = {"candidates": [{"content": {"parts": []}}]}
    parsed = client._parse_gemini_response(resp_json)
    assert parsed == "Empty response received."


def test_ondemand_api_error_response_handling():
    """Verifies that an error field in response JSON raises RuntimeError."""
    client = OnDemandClient(MockOAuthManager(), MockCaptureEngine())
    resp_json = {"error": {"code": 403, "message": "Permission denied on model resource."}}
    with pytest.raises(RuntimeError, match="Gemini API returned error"):
        client._parse_gemini_response(resp_json)


# ------------------------------------------------------------------------------
# 3. HTTP Status Codes & Error Handling Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ondemand_http_error_status_handling():
    """Verifies that HTTP 403/500 status codes raise RuntimeError."""
    with MockGeminiRestServer(status_code=403) as server:
        client = OnDemandClient(MockOAuthManager(), MockCaptureEngine(), rest_host=server.rest_url)
        with pytest.raises(RuntimeError, match=r"Gemini REST error \(HTTP 403\)"):
            await client.query_image("b64_data", "test prompt")


# ------------------------------------------------------------------------------
# 4. Target Delegation (Full Screen & Window) Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ondemand_query_target_full_screen():
    """Verifies querying target_type='full_screen' delegates to capture engine and returns answer."""
    with MockGeminiRestServer(custom_response_text="Full screen desktop analyzed.") as server:
        cap = MockCaptureEngine()
        client = OnDemandClient(MockOAuthManager(), cap, rest_host=server.rest_url)

        res = await client.query_target(
            target_type=CaptureTarget.FULL_SCREEN,
            target_id=0,
            prompt="Summarize full desktop",
        )

        assert res == "Full screen desktop analyzed."
        assert len(cap.captured_targets) == 1
        assert cap.captured_targets[0] == (CaptureTarget.FULL_SCREEN, 0)


@pytest.mark.asyncio
async def test_ondemand_query_target_window():
    """Verifies querying target_type='window' delegates to capture engine with HWND."""
    with MockGeminiRestServer(custom_response_text="Application window analyzed.") as server:
        cap = MockCaptureEngine()
        client = OnDemandClient(MockOAuthManager(), cap, rest_host=server.rest_url)

        res = await client.query_target(
            target_type=CaptureTarget.WINDOW,
            target_id=123456,
            prompt="Detect code errors in window",
        )

        assert res == "Application window analyzed."
        assert len(cap.captured_targets) == 1
        assert cap.captured_targets[0] == (CaptureTarget.WINDOW, 123456)
