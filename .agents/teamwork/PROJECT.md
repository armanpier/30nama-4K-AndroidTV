# Project: Gemini Desktop Screen Sharing for Windows

## Architecture & System Overview
A native Windows desktop application providing dual-mode screen sharing with Google Gemini:
1. **Continuous Real-Time Streaming**: Live desktop screen frames (1 FPS downscaled JPEG) and microphone audio (16kHz 16-bit PCM) streamed over a bidirectional WebSocket to Gemini Multimodal Live API, with real-time model audio playback (24kHz PCM) and barge-in interruption handling.
2. **On-Demand Capture**: Instant snapshot of the full desktop or a specific application window triggered via UI button or global hotkey (`Alt+S`), paired with a user query and submitted to Gemini with visual response display.
3. **Google Account Authentication**: Standard RFC 8252 OAuth 2.0 PKCE flow using the system browser and local loopback server (`127.0.0.1:<port>`), storing tokens securely in Windows Credential Manager and injecting Bearer tokens into Gemini API requests.
4. **Desktop UI**: PyQt6 application with dark mode styling, target window selector, mode toggles, audio controls, live preview, and live transcript panel.
5. **Testing Architecture**: Programmatic test suite utilizing offline mock WebSocket and REST servers for 100% reproducible testing without live credentials.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Existing Solution Assessment Report | Comprehensive documentation of Android Gemini Live vs Windows, community tools analysis, Multimodal Live WebSocket protocol, and comparative gap analysis | M1 | Survey |
| 2 | Google Account OAuth 2.0 PKCE Flow | RFC 8252 installed app flow with RFC 7636 PKCE S256, ephemeral loopback redirect server, system browser launch | M2 | Survey |
| 3 | Windows Secure Token Persistence | Windows Credential Manager (`keyring`) & DPAPI storage for refresh tokens, non-sensitive session cache, automatic refresh | M2 | Survey |
| 4 | Windows Screen Capture Engine | High-performance multi-monitor full desktop capture using `mss` with session desktop attachment | M2 | Survey |
| 5 | Window-Specific HWND Capture | Window enumeration, filtering, `DWMWA_EXTENDED_FRAME_BOUNDS`, `PrintWindow(PW_RENDERFULLCONTENT)` and minimized window handling | M2 | Survey |
| 6 | Frame Processing & Downscaling | Aspect-ratio-preserving downscale to 1024x768, JPEG quality 70 compression (~110 KB), Base64 encoding | M2 | Survey |
| 7 | Gemini Multimodal Live WebSocket Client | Stateful WebSocket client, `setup` negotiation, voice config, realtime input frame packing | M2 | Survey |
| 8 | Bidirectional Audio Pipeline | 16kHz PCM microphone capture, 24kHz PCM speaker playback, instant audio buffer purge on interruption | M2 | Survey |
| 9 | On-Demand Capture & Query Module | Snapshot trigger (hotkey/button), prompt query formatting, REST `generateContent` / WebSocket turn execution | M2 | Survey |
| 10 | PyQt6 Modern Desktop User Interface | Google sign-in status, capture target dropdown, mode selector, audio mute toggle, live preview, live transcript | M3 | Survey |
| 11 | Global System Hotkeys | Win32 `RegisterHotKey` (`Alt+S` on-demand capture, `Alt+L` live toggle) with Qt event filter integration | M3 | Survey |
| 12 | Programmatic Test Suite & Mock Servers | Offline mock Gemini Live WebSocket server, mock REST server, unit tests for capture, audio, auth, and E2E dual-mode integration | M4 | Survey |
| 13 | Verification Instructions & User Guide | Reproducible startup, testing, and Google Cloud configuration documentation | M4 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Existing Solution Assessment & Architecture Report | Comprehensive research report comparing Android Gemini Live to Windows desktop, analyzing existing tools, protocol schemas, and limitations (`gemini_desktop_screenshare/docs/EXISTING_SOLUTIONS_ASSESSMENT.md`) | none | DONE |
| M2 | Core Engine: Auth, Capture, Live Streaming & On-Demand | OAuth PKCE loopback client, Windows Credential Manager persistence, screen & window capture engine, Gemini Multimodal Live WebSocket client, audio pipeline, and on-demand client (`auth/`, `capture/`, `audio/`, `streaming/`, `ondemand/`) | M1 | DONE |
| M3 | Desktop User Interface & Interaction Controls | PyQt6 application with sign-in card, target selector, mode toggle, mic toggle, live preview, live transcript, and global hotkeys (`ui/`, `app.py`) | M2 | DONE |
| M4 | Programmatic Test Suite & E2E Verification | Standalone offline mock WebSocket and REST servers, complete unit & integration test suite, verification instructions (`tests/`, `run_tests.py`, `README.md`, `VERIFICATION.md`) | M2, M3 | DONE |

## Interface Contracts

### 1. `auth.oauth_manager.OAuthManager`
```python
class OAuthManager:
    def __init__(self, config_path: Optional[str] = None): ...
    def get_auth_url(self) -> Tuple[str, str, str]: ... # (auth_url, state, code_verifier)
    def start_loopback_and_login(self, timeout: float = 120.0) -> Dict[str, Any]: ...
    def refresh_access_token(self) -> str: ...
    def get_valid_access_token(self) -> str: ...
    def is_authenticated(self) -> bool: ...
    def get_user_profile(self) -> Dict[str, str]: ... # {"email": ..., "name": ...}
    def sign_out(self) -> bool: ...
```

### 2. `capture.screen_capture.ScreenCaptureEngine`
```python
class CaptureTarget:
    FULL_SCREEN = "full_screen"
    WINDOW = "window"

class ScreenCaptureEngine:
    def capture_screen(self, monitor_index: int = 0) -> Image.Image: ...
    def capture_window(self, hwnd: int) -> Image.Image: ...
    def capture_frame_jpeg(self, target_type: str, target_id: Any, max_dim: int = 1024, quality: int = 70) -> bytes: ...
    def capture_frame_base64(self, target_type: str, target_id: Any, max_dim: int = 1024, quality: int = 70) -> str: ...
    def list_windows(self) -> List[Dict[str, Any]]: ... # [{"hwnd": int, "title": str, "rect": Tuple}]
```

### 3. `audio.audio_pipeline.AudioPipeline`
```python
class AudioPipeline:
    def __init__(self, input_rate: int = 16000, output_rate: int = 24000): ...
    def start_recording(self, callback: Callable[[bytes], None]): ...
    def stop_recording(self): ...
    def set_muted(self, muted: bool): ...
    def play_chunk(self, pcm_bytes: bytes): ...
    def interrupt(self): ... # Immediately drain output audio buffer
    def close(self): ...
```

### 4. `streaming.live_client.GeminiLiveClient`
```python
class GeminiLiveClient:
    def __init__(self, oauth_manager: OAuthManager, capture_engine: ScreenCaptureEngine, audio_pipeline: AudioPipeline, host: Optional[str] = None): ...
    async def connect(self, voice_name: str = "Aoede", system_instruction: str = ""): ...
    async def start_streaming(self, target_type: str, target_id: Any, on_text: Callable[[str], None], on_error: Callable[[str], None]): ...
    async def stop_streaming(self): ...
    async def disconnect(self): ...
```

### 5. `ondemand.ondemand_client.OnDemandClient`
```python
class OnDemandClient:
    def __init__(self, oauth_manager: OAuthManager, capture_engine: ScreenCaptureEngine, rest_host: Optional[str] = None): ...
    async def query_target(self, target_type: str, target_id: Any, prompt: str) -> str: ...
```

## Code Layout
All application source code resides under: `gemini_desktop_screenshare/`
```
gemini_desktop_screenshare/
├── README.md
├── VERIFICATION.md
├── requirements.txt
├── app.py                      # Application entry point
├── config.py                   # Default configurations & settings
├── auth/
│   ├── __init__.py
│   ├── oauth_manager.py        # RFC 8252 PKCE loopback authentication
│   └── token_store.py          # Windows Credential Manager & DPAPI storage
├── capture/
│   ├── __init__.py
│   ├── screen_capture.py       # Full screen capture with mss
│   └── window_capture.py       # Win32 HWND enumeration and PrintWindow
├── audio/
│   ├── __init__.py
│   └── audio_pipeline.py       # 16kHz capture, 24kHz playback, instant interruption
├── streaming/
│   ├── __init__.py
│   └── live_client.py          # Gemini Multimodal Live WebSocket client
├── ondemand/
│   ├── __init__.py
│   └── ondemand_client.py      # On-demand snapshot query via REST / WebSocket
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Modern PyQt6 GUI
│   ├── hotkey_manager.py       # Win32 RegisterHotKey integration
│   └── styles.py               # Modern dark theme QSS stylesheets
└── tests/
    ├── __init__.py
    ├── mock_servers.py         # Offline mock Gemini Live WebSocket & REST servers
    ├── test_auth.py            # Unit tests for OAuth PKCE, tokens, Credential Manager
    ├── test_capture.py         # Unit tests for screen and window capture
    ├── test_audio.py           # Unit tests for audio capture, playback, interruption
    ├── test_ondemand.py        # Unit tests for on-demand multimodal capture
    ├── test_streaming.py       # Unit tests for Gemini Live WebSocket streaming
    └── test_e2e.py             # E2E dual-mode integration tests
run_tests.py                    # Standalone test runner script
```
