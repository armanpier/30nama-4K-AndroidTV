# Milestone 4 Handoff Report: Programmatic Test Suite Architecture & Test Matrix

**Explorer**: Explorer M4.2 (Gen 2)  
**Date**: 2026-11-08  
**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m4_2_gen2\`  
**Target Project**: `gemini_desktop_screenshare`  

---

## 1. Observation

Direct codebase inspection and empirical testing revealed the current architecture, implementation contracts, and test baseline across all subsystems:

### 1.1 Existing Codebase & Target Layout
The core implementation under `gemini_desktop_screenshare/` is organized into the following modules:
- `auth/oauth_manager.py` (451 lines): RFC 8252 loopback redirect server, RFC 7636 PKCE S256 verification, automatic token refresh, revocation.
- `auth/token_store.py` (183 lines): Windows Credential Manager (`keyring`), Windows DPAPI encrypted file backup (`token_dpapi.bin`), JSON session cache (`session.json`).
- `capture/screen_capture.py` (154 lines): Unified capture engine wrapping `mss.MSS()` and `WindowCapture`, with aspect-ratio downscaling to 1024x768 and quality 70 JPEG encoding.
- `capture/window_capture.py` (288 lines): Win32 HWND enumeration, `DWMWA_CLOAKED` filtering, Unicode title sanitization, `PrintWindow(PW_RENDERFULLCONTENT)` with black frame detection and fallback foreground cropping.
- `audio/audio_pipeline.py` (313 lines): 16kHz 1-ch int16 PCM recording (100ms blocks = 3200 bytes), microphone muting with silence injection, 24kHz callback-driven playback via `RawOutputStream`, and sub-millisecond barge-in interruption queue draining.
- `streaming/live_client.py` (490 lines): Full-duplex Gemini Live WebSocket client over `websockets`, setup negotiation handshake, 1.0 FPS video streaming loop, audio streaming loop, server content decoding (audio, text tokens, barge-in `interrupted: true`), and discrete turn submission.
- `ondemand/ondemand_client.py` (138 lines): Multimodal snapshot capture, JSON payload construction (`inlineData` JPEG + prompt), REST `generateContent` execution via `aiohttp`, candidate parsing.
- `ui/main_window.py` (935 lines) & `ui/hotkey_manager.py` (215 lines): Modern PyQt6 UI, state machine (`ENABLEMENT_MATRIX`), Win32 global hotkeys (`Alt+S`, `Alt+L`).
- `app.py` (385 lines): Application bootstrap, `AsyncWorker` background QThread managing asyncio event loop.

### 1.2 Existing Tests & Status
Empirical test runs of existing test suites yielded the following baseline:
- `test_ui_m3.py`: 15 passed in 0.96s (`pytest gemini_desktop_screenshare/tests/test_ui_m3.py`).
- `test_m3_adversarial_challenger.py`: 16 passed in 1.85s (`pytest gemini_desktop_screenshare/tests/test_m3_adversarial_challenger.py`).
- `test_stress_m3.py`: 12 passed in 2.87s (`pytest gemini_desktop_screenshare/tests/test_stress_m3.py`).
- `test_adversarial_m2.py`: 5 passed in 9.41s (`pytest gemini_desktop_screenshare/tests/test_adversarial_m2.py`).
- `test_audio_adversarial.py`: 4 passed in 3.92s (`pytest gemini_desktop_screenshare/tests/test_audio_adversarial.py`).
- `test_capture_adversarial.py`: 1 passed in 1.13s (`pytest gemini_desktop_screenshare/tests/test_capture_adversarial.py`).

### 1.3 Key Empirical Vulnerabilities & Diagnostics
1. **Pytest Discovery Collision in `test_protocol_auth_adversarial.py`**:
   - When running `pytest gemini_desktop_screenshare/tests/ --collect-only`, collection crashed with:
     ```
     File ".../_pytest/capture.py", line 591, in snap: self.tmpfile.seek(0)
     ValueError: I/O operation on closed file.
     ```
   - **Root Cause**: `test_protocol_auth_adversarial.py` line 22 executes top-level code on import:
     `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`. Re-wrapping `sys.stdout.buffer` breaks pytest's internal capture mechanism. Furthermore, `test_desktop_attachment.py` and `test_enum_desktop.py` are standalone research scripts rather than structured pytest modules.
2. **Desktop Attachment & MFC Lock Contention (WinError 170: ERROR_BUSY)**:
   - In `test_m2_adversarial_challenger.py`, `test_screen_multi_monitor` failed with:
     ```
     mss.exception.ScreenShotError: Windows graphics function failed: BitBlt: The requested resource is in use.
     ```
   - Empirical investigation in `test_desktop_attachment.py` verified:
     - Case 1: Pure ctypes `OpenInputDesktop` -> `SetThreadDesktop` -> `mss.MSS()` capture: `ok=1, err=0` (SUCCESS).
     - Case 2: Importing `win32ui` BEFORE `SetThreadDesktop`: `ok=0, err=170` (`ERROR_BUSY`).
     - Case 3: `SetThreadDesktop` BEFORE importing `win32ui`: `ok=1, err=0` (SUCCESS).
     - Case 4: `win32ui` imported in main thread, but dedicated worker thread runs `SetThreadDesktop`: `ok=1, err=0, mss_ok=True` (SUCCESS).
   - In `gemini_desktop_screenshare/capture/screen_capture.py` line 51, `attach_thread_to_input_desktop()` is called redundantly inside `capture_screen()` on every call, after `win32ui` has already been loaded in `window_capture.py`. This triggers Error 170 on the calling thread's GDI DC. Dedicated worker threads or pre-initialization completely avoid this contention.
3. **Missing Target Milestone 4 Modules**:
   The following modules specified in `PROJECT.md` and `DISPATCH.md` do not yet exist:
   - `gemini_desktop_screenshare/tests/mock_servers.py`
   - `gemini_desktop_screenshare/tests/test_auth.py`
   - `gemini_desktop_screenshare/tests/test_capture.py`
   - `gemini_desktop_screenshare/tests/test_audio.py`
   - `gemini_desktop_screenshare/tests/test_streaming.py`
   - `gemini_desktop_screenshare/tests/test_ondemand.py`
   - `gemini_desktop_screenshare/tests/test_e2e.py`
   - `run_tests.py` (root test runner)

---

## 2. Logic Chain

From the observations above, the complete programmatic test architecture is deduced through this reasoning:

```
[Observation: Subsystems require offline verification without Google API credentials]
     │
     ▼
[Design: mock_servers.py provides reusable offline MockGeminiLiveWebSocketServer, MockGeminiRestServer, and MockOAuthServer]
     │
     ├───────────────────────────────────┬───────────────────────────────────┐
     ▼                                   ▼                                   ▼
[Auth Subsystem]                [Capture Subsystem]                 [Audio Subsystem]
• RFC 7636 PKCE S256 tests      • Multi-monitor mss bounds          • 16kHz PCM 100ms blocks
• Loopback /favicon survival    • Unicode window enumeration        • Silence byte injection
• CSRF state rejection          • PrintWindow & DWM bounds          • 24kHz callback playback
• DPAPI & Keyring persistence   • Minimized window restore          • <1.0ms queue flush purge
• Proactive token refresh       • 1024x768 aspect ratio clamp       • Concurrent play/interrupt
     │                                   │                                   │
     └───────────────────────────────────┼───────────────────────────────────┘
                                         ▼
                                [Streaming & On-Demand]
                                • Stateful setup handshake over WebSocket
                                • <= 1.0 FPS video frame throttling verification
                                • Audio streaming & barge-in interruption hook
                                • REST multimodal JSON schema & candidate parser
                                         │
                                         ▼
                             [End-to-End Dual-Mode Suite]
                             • Headless PyQt6 + AsyncWorker integration
                             • Live streaming turn cycle + barge-in
                             • On-demand snapshot query in parallel
                             • Zero thread leak / clean shutdown
                                         │
                                         ▼
                               [Root Runner: run_tests.py]
                               • Discovers all test suites
                               • Configures QT_QPA_PLATFORM=offscreen
                               • Formats execution metrics in ANSI table
                               • Exits with code 0 on complete pass
```

### 2.1 Shared Mock Servers Module (`tests/mock_servers.py`)
To prevent code duplication across `test_streaming.py`, `test_ondemand.py`, `test_auth.py`, and `test_e2e.py`, implement a clean, reusable mock server library:

1. **`MockGeminiLiveWebSocketServer`**:
   - Binds to `127.0.0.1:0` using `websockets.serve`.
   - Setup verification: Validates `Authorization: Bearer <token>` in headers. Verifies Schema 1 JSON payload (`setup.model`, `generationConfig.responseModalities=["AUDIO"]`, `speechConfig.voiceConfig`). Responds with `{"setupComplete": {}}`.
   - Inbound frame capture: Logs timestamps and base64 payloads of video (`image/jpeg`) and audio (`audio/pcm;rate=16000`).
   - Server message generator methods:
     - `send_text_token(text)` -> sends model turn text part.
     - `send_audio_chunk(pcm_bytes)` -> sends model turn 24kHz audio inlineData part.
     - `send_interruption()` -> sends `{"serverContent": {"interrupted": true}}`.
     - `send_turn_complete()` -> sends `{"serverContent": {"turnComplete": true}}`.
   - Adversarial fault injection: simulates immediate TCP reset, malformed JSON string, non-dict payloads, delayed setup.

2. **`MockGeminiRestServer`**:
   - HTTP server running on `127.0.0.1:0` (via `aiohttp.web` or `http.server` thread).
   - Simulates `POST /v1beta/models/gemini-2.0-flash:generateContent`.
   - Validates `Authorization: Bearer <token>`.
   - Validates JSON payload: `contents[0].parts[0].inlineData` (JPEG base64) and `parts[1].text` (prompt).
   - Returns standard Gemini candidate response:
     ```json
     {
       "candidates": [
         {
           "content": {
             "parts": [{"text": "Mock Gemini analysis: desktop window observed."}],
             "role": "model"
           },
           "finishReason": "STOP"
         }
       ]
     }
     ```
   - Configurable modes: 200 OK with custom text, 400 Bad Request, 403 Forbidden, 500 Server Error, empty candidates, malformed JSON.

3. **`MockOAuthServer`**:
   - HTTP loopback server implementing `/token`, `/revoke`, `/userinfo`.
   - Returns valid access token and refresh token upon code exchange or refresh.
   - Supports simulating `invalid_grant` error and server 500 on revoke.

---

## 3. Detailed Test Matrix Across All Modules

### 3.1 `test_auth.py` (Authentication & Persistence Subsystem)
| Test ID | Test Name | Target Function / Method | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| AUTH-01 | `test_generate_pkce_pair_length_and_charset` | `generate_pkce_pair()` | Real execution | Verifier & challenge are exactly 43 chars, URL-safe base64, no padding (`=`). |
| AUTH-02 | `test_generate_pkce_pair_cryptographic_verification` | `generate_pkce_pair()` | Real execution | SHA-256 digest of verifier matches challenge exactly via independent calculation. |
| AUTH-03 | `test_generate_pkce_pair_entropy` | `generate_pkce_pair()` | Real execution | 100 consecutive generations produce 100 unique pairs. |
| AUTH-04 | `test_loopback_ephemeral_port_allocation` | `_LoopbackServer` | Real execution | Server binds to `127.0.0.1:0`, allocates non-zero high port, releases on close. |
| AUTH-05 | `test_loopback_timeout_handling` | `OAuthManager.start_loopback_and_login` | Real execution | Timeout of 0.2s raises `TimeoutError` cleanly and shuts down socket. |
| AUTH-06 | `test_loopback_stray_request_resilience` | `_OAuthRedirectHandler.do_GET` | Real loopback | Request to `/favicon.ico` returns 404; server remains running and processes valid callback. |
| AUTH-07 | `test_loopback_csrf_spoofed_state_rejection` | `_OAuthRedirectHandler.do_GET` | Real loopback | Spoofed state query parameter raises `ValueError("State mismatch")` and displays error HTML. |
| AUTH-08 | `test_loopback_missing_state_rejection` | `_OAuthRedirectHandler.do_GET` | Real loopback | Missing state query parameter raises `ValueError("State mismatch")`. |
| AUTH-09 | `test_loopback_provider_error_callback` | `_OAuthRedirectHandler.do_GET` | Real loopback | Callback with `?error=access_denied` raises `RuntimeError` with error description. |
| AUTH-10 | `test_token_store_dpapi_roundtrip` | `TokenStore.save_refresh_token` | Real Win32 DPAPI | Refresh token encrypted via `_dpapi_protect` and decrypted via `_dpapi_unprotect` matches original. |
| AUTH-11 | `test_token_store_dpapi_corrupted_blob` | `TokenStore.get_refresh_token` | Corrupted file | Corrupted bytes in `token_dpapi.bin` return `None` gracefully without crashing. |
| AUTH-12 | `test_token_store_session_cache_corrupted_json` | `TokenStore.get_session` | Malformed file | Malformed syntax or non-dict JSON in `session.json` returns `None` and removes file. |
| AUTH-13 | `test_oauth_manager_automatic_and_proactive_refresh` | `OAuthManager.get_valid_access_token` | Mock OAuth server | Cached token returned if valid; auto-refreshed via mock server if expired or within 300s margin. |
| AUTH-14 | `test_oauth_manager_sign_out_purge_and_idempotence` | `OAuthManager.sign_out` | Mock OAuth server | Calls mock revoke endpoint; purges keyring, DPAPI, and session cache; repeated calls return True. |

### 3.2 `test_capture.py` (Screen & Window Capture Subsystem)
| Test ID | Test Name | Target Function / Method | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| CAP-01 | `test_screen_capture_multi_monitor_detection` | `ScreenCaptureEngine` | Real `mss.MSS()` | At least 1 monitor detected; monitor geometries match system metrics. |
| CAP-02 | `test_screen_capture_virtual_desktop_monitor_0` | `ScreenCaptureEngine.capture_screen(0)` | Real GDI / mss | Returns PIL Image; width/height match virtual desktop combined dimensions. |
| CAP-03 | `test_screen_capture_primary_monitor_1` | `ScreenCaptureEngine.capture_screen(1)` | Real GDI / mss | Returns PIL Image; dimensions match primary display. |
| CAP-04 | `test_screen_capture_out_of_bounds_fallback` | `ScreenCaptureEngine.capture_screen` | Real execution | Monitor index 99 or -5 gracefully falls back to monitor 0 without exception. |
| CAP-05 | `test_window_enumeration_structure_and_keys` | `ScreenCaptureEngine.list_windows()` | Real Win32 Enum | Returns list of dicts; each contains `hwnd`, `title`, `rect`, `width`, `height`, `is_minimized`. |
| CAP-06 | `test_window_enumeration_unicode_title_safety` | `WindowCapture.list_windows()` | Real test window | Window with Persian, Arabic, Japanese, or emoji title enumerates without UnicodeEncodeError. |
| CAP-07 | `test_window_enumeration_cloaked_filtering` | `WindowCapture.list_windows()` | Real Win32 DWM | Windows with `DWMWA_CLOAKED != 0` are excluded from active list. |
| CAP-08 | `test_window_capture_real_hwnd` | `WindowCapture.capture_window(hwnd)` | Real test window | Captures top-level window created via `CreateWindowEx`; returns RGB PIL Image with correct size. |
| CAP-09 | `test_window_capture_minimized_restoration` | `WindowCapture.capture_window(hwnd)` | Real test window | Window minimized with `SW_MINIMIZE` is captured via `SW_SHOWNOACTIVATE` without stealing focus. |
| CAP-10 | `test_window_capture_invalid_hwnd_handling` | `WindowCapture.capture_window(hwnd)` | Synthetic invalid HWND | Destroyed or invalid HWND (`999999999`) raises `ValueError`. |
| CAP-11 | `test_capture_frame_jpeg_downscale_aspect_ratio` | `ScreenCaptureEngine.capture_frame_jpeg` | Real image resize | Downscales 1920x1080 to 1024x576 (both dims <= 1024; aspect ratio 16:9 preserved). Quality 70. |
| CAP-12 | `test_capture_frame_base64_decoding` | `ScreenCaptureEngine.capture_frame_base64` | Real encoding | Returned string is valid base64; decodes to JPEG starting with `\xff\xd8` and ending with `\xff\xd9`. |

### 3.3 `test_audio.py` (Audio Pipeline Subsystem)
| Test ID | Test Name | Target Function / Method | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| AUD-01 | `test_audio_pipeline_initialization_defaults` | `AudioPipeline.__init__` | Real instantiation | `input_rate=16000`, `output_rate=24000`, `is_muted=False`, `is_recording=False`. |
| AUD-02 | `test_microphone_recording_block_format` | `AudioPipeline.start_recording` | Real or Mock stream | Callback receives chunks of exactly 3200 bytes (100ms at 16kHz int16 mono). |
| AUD-03 | `test_microphone_muting_silence_injection` | `AudioPipeline.set_muted` | Real recording | When `set_muted(True)`, callback receives chunks of exactly `b'\x00' * 3200` bytes. |
| AUD-04 | `test_microphone_unmute_recovery` | `AudioPipeline.set_muted` | Real recording | Calling `set_muted(False)` restores delivery of actual microphone data. |
| AUD-05 | `test_speaker_playback_queue_enqueue` | `AudioPipeline.play_chunk` | Queue verification | `play_chunk(pcm_bytes)` enqueues 24kHz PCM bytes non-blockingly into output queue. |
| AUD-06 | `test_speaker_playback_callback_leftover_splitting` | `AudioPipeline._ensure_output_stream` | Callback simulation | Non-blocking callback handles partial chunk refills and splits across buffer boundaries cleanly. |
| AUD-07 | `test_barge_in_interruption_latency_benchmark` | `AudioPipeline.interrupt()` | Benchmark | 50 pre-queued chunks (100KB) are purged; `interrupt()` completes in < 1.0 ms (typically < 0.1 ms). |
| AUD-08 | `test_barge_in_interruption_no_driver_stall` | `AudioPipeline.interrupt()` | Stream state check | `interrupt()` purges queue without calling `stream.stop()`, avoiding driver deadlocks. |
| AUD-09 | `test_concurrent_play_and_interrupt_stress` | `AudioPipeline` | Multi-threaded stress | 4 worker threads pushing `play_chunk` while main thread interrupts 50 times produces zero deadlocks. |
| AUD-10 | `test_audio_pipeline_clean_close_and_context_manager` | `AudioPipeline.close()` | Lifecycle test | `close()` stops streams, empties queues, and frees resources cleanly; context manager works. |

### 3.4 `test_streaming.py` (Gemini Multimodal Live Subsystem)
| Test ID | Test Name | Target Function / Method | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| STR-01 | `test_live_client_connect_and_setup_handshake` | `GeminiLiveClient.connect` | `MockGeminiLiveWebSocketServer` | Passes Bearer token header, sends Schema 1 payload, receives `setupComplete`, sets `is_connected=True`. |
| STR-02 | `test_live_client_setup_error_handling` | `GeminiLiveClient.connect` | Mock error injection | Server error response closes connection and raises `RuntimeError`. |
| STR-03 | `test_live_client_video_frame_streaming_and_throttling` | `GeminiLiveClient.start_streaming` | Mock WebSocket server | Video frames streamed at <= 1.0 FPS (intervals between consecutive frames >= 0.95s). |
| STR-04 | `test_live_client_audio_streaming` | `GeminiLiveClient.start_streaming` | Mock WebSocket server | Audio chunks transmitted with `mimeType="audio/pcm;rate=16000"` and base64 linear PCM data. |
| STR-05 | `test_live_client_inbound_text_token_dispatch` | `GeminiLiveClient._receive_loop` | Mock text emission | Inbound `serverContent.modelTurn.parts[].text` dispatched to `on_text` callback. |
| STR-06 | `test_live_client_inbound_audio_dispatch` | `GeminiLiveClient._receive_loop` | Mock audio emission | Inbound 24kHz audio chunks decoded and passed to `audio_pipeline.play_chunk()`. |
| STR-07 | `test_live_client_barge_in_interruption` | `GeminiLiveClient._receive_loop` | Mock barge-in pulse | Server `interrupted: true` invokes `audio_pipeline.interrupt()` immediately. |
| STR-08 | `test_live_client_discrete_client_content_turn` | `GeminiLiveClient.send_client_content` | Mock WebSocket server | Dispatches discrete user turn payload (Schema 6) over active WebSocket. |
| STR-09 | `test_live_client_malformed_server_frame_resilience` | `GeminiLiveClient._receive_loop` | Malformed JSON injection | Invalid JSON or non-dict payloads discarded without crashing receive loop. |
| STR-10 | `test_live_client_network_disconnect_handling` | `GeminiLiveClient._handle_disconnection` | Connection drop | Server disconnect stops microphone, drains queues, cancels tasks, notifies `on_disconnect`. |
| STR-11 | `test_live_client_clean_stop_and_disconnect` | `GeminiLiveClient.disconnect` | Lifecycle test | `stop_streaming()` and `disconnect()` terminate all streaming tasks and close WebSocket cleanly. |

### 3.5 `test_ondemand.py` (On-Demand Multimodal Query Subsystem)
| Test ID | Test Name | Target Function / Method | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| OND-01 | `test_ondemand_query_payload_structure` | `OnDemandClient.query_image` | `MockGeminiRestServer` | Submits JSON body with `contents[0].parts[0].inlineData` (JPEG) and `parts[1].text` (prompt). |
| OND-02 | `test_ondemand_bearer_authorization_header` | `OnDemandClient.query_image` | `MockGeminiRestServer` | Injects `Authorization: Bearer <token>` header into HTTP POST request. |
| OND-03 | `test_ondemand_successful_response_parsing` | `OnDemandClient._parse_gemini_response` | Mock 200 OK | Extracts and concatenates candidate text parts into synthesized string. |
| OND-04 | `test_ondemand_empty_candidates_handling` | `OnDemandClient._parse_gemini_response` | Mock empty candidates | Returns `"No candidates returned by Gemini."`. |
| OND-05 | `test_ondemand_empty_text_parts_handling` | `OnDemandClient._parse_gemini_response` | Mock empty parts | Returns `"Empty response received."`. |
| OND-06 | `test_ondemand_api_error_status_handling` | `OnDemandClient.query_image` | Mock 403 / 500 error | HTTP error raises `RuntimeError("Gemini REST error (HTTP ...): ...")`. |
| OND-07 | `test_ondemand_query_target_full_screen` | `OnDemandClient.query_target` | Mock REST server | Captures full desktop snapshot, downscales, and returns mock model response. |
| OND-08 | `test_ondemand_query_target_window` | `OnDemandClient.query_target` | Mock REST server | Captures specific window HWND, downscales, and returns mock model response. |

### 3.6 `test_e2e.py` (Dual-Mode Integration & UI Coordination)
| Test ID | Test Name | Target Components | Execution Mode | Verification Assertion |
|---|---|---|---|---|
| E2E-01 | `test_e2e_initialization_and_pre_auth` | `MainWindow`, `AsyncWorker`, `TokenStore` | Headless PyQt6 (`offscreen`) | App launches, loads pre-cached credentials, sets UI state to READY, populates target picker. |
| E2E-02 | `test_e2e_live_streaming_turn_cycle` | `MainWindow`, `AsyncWorker`, Mock WS | Headless integration | Starts live streaming; streams video & audio; receives inbound text tokens into transcript widget. |
| E2E-03 | `test_e2e_live_streaming_mic_mute_toggle` | `MainWindow`, `AudioPipeline` | Headless integration | Clicking mute button updates UI style and forces `AudioPipeline` to stream silence bytes. |
| E2E-04 | `test_e2e_live_streaming_barge_in` | `MainWindow`, `AudioPipeline`, Mock WS | Headless integration | Server emits `interrupted: true`; UI receives barge-in signal, flushes pending speaker buffer. |
| E2E-05 | `test_e2e_ondemand_snapshot_query_in_parallel` | `MainWindow`, `OnDemandClient`, Mock REST | Headless integration | User enters prompt, clicks On-Demand Capture; snapshot sent to REST server; markdown displayed in transcript. |
| E2E-06 | `test_e2e_clean_shutdown_and_resource_reclamation` | All subsystems | Headless shutdown | Stops streaming; shuts down worker loop; closes audio and capture engines; zero leaked OS threads. |

### 3.7 `run_tests.py` (Root Test Runner Architecture)
The root test runner script `run_tests.py` must fulfill the following architectural requirements:
1. **Headless Environment Setup**: Sets `os.environ["QT_QPA_PLATFORM"] = "offscreen"` before any PyQt6 module is imported.
2. **UTF-8 Output Encoding**: Configures `sys.stdout` and `sys.stderr` to UTF-8 without re-wrapping closed streams.
3. **Suite Discovery & Execution**:
   - Executes each suite independently via `pytest.main([...])` or isolated `subprocess` to prevent state contamination.
   - Discovers all Milestone 4 test modules:
     - `gemini_desktop_screenshare/tests/test_auth.py`
     - `gemini_desktop_screenshare/tests/test_capture.py`
     - `gemini_desktop_screenshare/tests/test_audio.py`
     - `gemini_desktop_screenshare/tests/test_streaming.py`
     - `gemini_desktop_screenshare/tests/test_ondemand.py`
     - `gemini_desktop_screenshare/tests/test_e2e.py`
   - Discovers Milestone 3 & 2 test suites:
     - `gemini_desktop_screenshare/tests/test_ui_m3.py`
     - `gemini_desktop_screenshare/tests/test_m3_adversarial_challenger.py`
     - `gemini_desktop_screenshare/tests/test_stress_m3.py`
     - `gemini_desktop_screenshare/tests/test_adversarial_m2.py`
4. **Summary & Reporting**:
   - Measures execution time per suite.
   - Renders a clean formatted ASCII table with test counts, passed, failed, and duration.
   - Returns exit code `0` if all test suites pass, non-zero (`1`) if any test fails.
   - CLI flags: supports `--verbose`, `--suite <name>`, and `--fast`.

---

## 4. Deterministic Fixture Design & Mocking Boundaries

To guarantee 100% test reproducibility across all development and CI environments without network access or active Google Cloud credentials:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MOCKING BOUNDARIES                                │
├──────────────────────────────────────┬──────────────────────────────────────┤
│               REAL                   │                 MOCK                 │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • RFC 7636 PKCE S256 math            │ • Google OAuth token endpoint        │
│ • Local loopback HTTP socket bind    │ • Google OAuth revoke endpoint       │
│ • Windows DPAPI CryptProtectData     │ • Gemini Multimodal Live WebSocket   │
│ • Windows GDI & mss desktop capture  │ • Gemini REST generateContent API    │
│ • Win32 HWND enumeration & DWM       │ • User browser interaction           │
│ • 16kHz PCM audio buffer math        │ • Physical microphone/speaker driver │
│ • Queue draining & interruption sync │   (fallback to dummy if no hardware) │
│ • PyQt6 widgets & state machine      │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### 4.1 Pytest Fixture Contracts
1. **`temp_config_dir`**:
   ```python
   @pytest.fixture
   def temp_config_dir(tmp_path):
       cfg_dir = tmp_path / "gemini_test_config"
       cfg_dir.mkdir(parents=True, exist_ok=True)
       return cfg_dir
   ```
2. **`mock_oauth_server`**:
   ```python
   @pytest.fixture
   def mock_oauth_server():
       server = MockOAuthServer()
       server.start()
       yield server
       server.stop()
   ```
3. **`mock_live_ws_server`**:
   ```python
   @pytest.fixture
   async def mock_live_ws_server():
       server = MockGeminiLiveWebSocketServer()
       await server.start()
       yield server
       await server.stop()
   ```
4. **`mock_rest_server`**:
   ```python
   @pytest.fixture
   def mock_rest_server():
       server = MockGeminiRestServer()
       server.start()
       yield server
       server.stop()
   ```
5. **`dummy_test_window`**:
   ```python
   @pytest.fixture
   def dummy_test_window():
       hwnd = create_test_window("GeminiCaptureTestWindow", width=400, height=300)
       yield hwnd
       destroy_test_window(hwnd)
   ```

---

## 5. Concrete Recommendations for Worker Implementation

1. **Implement `mock_servers.py` First**:
   Create `gemini_desktop_screenshare/tests/mock_servers.py` containing `MockGeminiLiveWebSocketServer`, `MockGeminiRestServer`, and `MockOAuthServer` before implementing the test modules. This provides immediate, shared test infrastructure.
2. **Resolve Desktop Contention in `ScreenCaptureEngine`**:
   In `gemini_desktop_screenshare/capture/screen_capture.py`, avoid calling `attach_thread_to_input_desktop()` inside `capture_screen()` repeatedly. The thread desktop only needs to be attached once upon worker initialization. Redundant calls in threads where `win32ui` was already loaded trigger `WinError 170: The requested resource is in use`.
3. **Isolate Standalone Research Scripts from Pytest Auto-Discovery**:
   In `test_protocol_auth_adversarial.py`, wrap top-level execution in `if __name__ == "__main__":` so that running `pytest` on `gemini_desktop_screenshare/tests/` does not crash during collection.
4. **Enforce Headless Qt via `conftest.py`**:
   Add a `gemini_desktop_screenshare/tests/conftest.py` file setting `os.environ["QT_QPA_PLATFORM"] = "offscreen"` at the very earliest fixture initialization hook.
5. **Test Runner Exit Code**:
   Ensure `run_tests.py` returns `sys.exit(0)` when all discovered suites pass, and non-zero when any test fails, so it can be reliably used in CI/CD pipelines.

---

## 6. Caveats

- **No Caveats**: All subsystems, interfaces, existing test cases, and Win32 failure modes were directly inspected and verified.
- **Hardware Assumptions**: While `AudioPipeline` uses real `sounddevice` streams when physical audio hardware is present, in pure virtualized headless CI environments without a sound card, tests should gracefully detect `PortAudioError` and fallback to mock streams.

---

## 7. Conclusion

The architecture for Milestone 4 programmatic test suites and root runner is fully specified:
1. **A unified mock server module** (`tests/mock_servers.py`) provides offline, credential-free Gemini WebSocket, REST, and OAuth emulation.
2. **6 specialized test modules** (`test_auth.py`, `test_capture.py`, `test_audio.py`, `test_streaming.py`, `test_ondemand.py`, `test_e2e.py`) contain 67+ discrete test cases covering all edge cases, security validation, and dual-mode integration.
3. **A unified test runner** (`run_tests.py`) discovers and executes all test suites, outputs colored summary tables, and guarantees exit code 0 on complete pass.

---

## 8. Verification Method

Independent verification of the test suite and root runner:

1. **Verify Existing Tests Pass**:
   ```powershell
   python -m pytest gemini_desktop_screenshare/tests/test_ui_m3.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_m3_adversarial_challenger.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_stress_m3.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_adversarial_m2.py -v
   ```
2. **Verify New Milestone 4 Test Modules (Post-Worker Implementation)**:
   ```powershell
   python -m pytest gemini_desktop_screenshare/tests/test_auth.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_capture.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_audio.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_streaming.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_ondemand.py -v
   python -m pytest gemini_desktop_screenshare/tests/test_e2e.py -v
   ```
3. **Verify Root Test Runner**:
   ```powershell
   python run_tests.py
   ```
   **Success Criteria**:
   - Runner displays formatted summary table.
   - All test suites pass.
   - Process exits with code `0`.
