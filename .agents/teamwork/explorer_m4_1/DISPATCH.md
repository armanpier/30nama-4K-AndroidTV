# Dispatch: Explorer M4.1 — Offline Mock Servers Architecture & Live Protocol Emulation

## Mission
Investigate and design the standalone offline mock servers for the Gemini Desktop Screenshare application (`gemini_desktop_screenshare/tests/mock_servers.py`):
1. Mock Gemini Multimodal Live WebSocket Server:
   - Implements the exact Gemini Multimodal Live API v1alpha bidirectional WebSocket protocol.
   - Handles `setup` handshake and responds with `setupComplete`.
   - Accepts client `realtimeInput` messages with `mediaChunks` (audio PCM 16kHz and image JPEG base64).
   - Generates and streams realistic `serverContent.modelTurn.parts` containing both text parts (transcripts) and inline PCM audio chunks (24kHz 16-bit mono).
   - Supports barge-in interruption signals (`interrupted: True` and handling client turn cancellations).
   - Simulates edge cases: connection drops, malformed client frames, rate limit errors (`429`), invalid token rejections (`401/403`).
2. Mock Gemini REST API Server:
   - Emulates `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`.
   - Parses multipart contents (multimodal snapshot image + text prompt) with Bearer token authentication header validation.
   - Returns structured `candidates[0].content.parts[0].text` responses.
   - Simulates error responses (empty body, 400 bad request, 503 unavailable, invalid JSON).
3. Lifecycle & Port Management:
   - Dynamic ephemeral port binding (`127.0.0.1:0`) to eliminate port collisions during concurrent test execution.
   - Clean background thread / asyncio server startup, context manager lifecycle (`async with MockLiveServer() as server:` / `MockRestServer()`), and deterministic teardown without socket leaks.

## Reference Files to Inspect
- Original Request: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Document: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- Assessment Document: `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\docs\EXISTING_SOLUTIONS_ASSESSMENT.md`
- Streaming Client: `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\streaming\live_client.py`
- On-Demand Client: `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\ondemand\ondemand_client.py`
- Auth Manager: `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\auth\oauth_manager.py`

## Expected Output
Produce a comprehensive handoff report at:
`c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_1\handoff.md`
detailing:
- Exact message schemas for Mock Live WebSocket and Mock REST servers.
- Architecture and implementation blueprints for `mock_servers.py`.
- Threading, asyncio, and socket lifecycle management.
- Recommendation for Worker implementation.
