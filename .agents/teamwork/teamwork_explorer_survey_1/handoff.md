# Gemini Live Desktop Screen Sharing — Comprehensive Survey & Protocol Report

## 1. Observation

### 1.1 Android's Gemini Live Screen Sharing Implementation & Architecture
Android's native "Share screen with Live" and "Ask about this screen" capabilities operate through a tightly integrated OS stack combining privileged system tokens, capture frameworks, and low-latency bidirectional streaming:

1. **Screen Capture Mechanism**:
   - **Framework API**: Utilizes Android's `MediaProjection` architecture (`android.media.projection.MediaProjectionManager`).
   - **Consent & Token Flow**: The system issues an intent via `MediaProjectionManager.createScreenCaptureIntent()`. Once granted by the user via the system dialog, a `MediaProjection` token is returned.
   - **Display Mirroring**: The token invokes `createVirtualDisplay("GeminiScreenSharing", width, height, densityDpi, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, surface, null, null)`.
   - **Surface & Buffer Ingestion**: The virtual display targets either a hardware `Surface` or an `ImageReader` configured with `ImageFormat.YUV_420_888` or `HardwareBuffer` format.
   - **Granular Scoping (Android 14+ / API 34)**: Android 14 introduced `MediaProjectionConfig.createConfigForUserChoice()`, presenting the user with an option to share a single application window or the entire screen. When single-app sharing is selected, system overlays, notifications, and navigation bars are excluded at the compositor level.

2. **Foreground Service Requirement**:
   - Android enforces strict lifecycle boundaries: starting with Android 10 (and mandated with runtime checks in Android 14), screen capture requires a running `Service` with `android:foregroundServiceType="mediaProjection"` declared in the `AndroidManifest.xml`.
   - The service must display an ongoing, non-dismissible notification while screen capture is active to safeguard user privacy.

3. **Frame Downscaling & Compression Pipeline**:
   - **Frame Throttling**: Rather than capturing at display refresh rates (60Hz–120Hz), the background thread throttles capture to **1 frame per second (1 FPS)** (or on-demand during fast visual scene changes).
   - **Resolution Scaling**: Display resolutions (e.g., 1080x2400 or 1440x3120) are downscaled using hardware scalers (RenderScript / OpenGL / Vulkan / `Bitmap.createScaledBitmap`) to a bounded bounding box (typically ~720p to 1024px maximum dimension) preserving aspect ratio.
   - **Encoding**: Frames are compressed into JPEG format (`Bitmap.compress(Bitmap.CompressFormat.JPEG, 75, outputStream)`), yielding chunks between 50 KB and 100 KB.

4. **Audio Capture, AEC, and Duplex Synchronization**:
   - **Capture Hardware**: Captured using `AudioRecord` (or AAudio / Oboe) configured for `AudioFormat.ENCODING_PCM_16BIT`, `AudioFormat.CHANNEL_IN_MONO`, sample rate `16000 Hz`.
   - **Acoustic Echo Cancellation (AEC)**: Android phones employ hardware/system DSP Acoustic Echo Cancellation (`android.media.audiofx.AcousticEchoCanceler.create(audioRecord.audioSessionId)`). This prevents Gemini's synthetic voice output through the device speaker from feeding back into the microphone.
   - **Buffer Size**: 20ms to 100ms PCM audio frames (320 to 1600 samples, 640 to 3200 bytes) are buffered and dispatched immediately.

5. **Bidirectional Network Transport**:
   - Audio chunks and video frames are multiplexed onto a persistent stateful WebSocket (or bidirectional gRPC) connection to Google's Multimodal Live endpoint.
   - Visual frames and audio chunks are packaged into `realtimeInput.mediaChunks`.
   - Downstream synthesized voice is received as 24kHz PCM chunks and fed directly to `AudioTrack` with minimal buffering (~50ms buffer).
   - Server-side Voice Activity Detection (VAD) monitors user speech; if the user interrupts the model, the server emits `interrupted: true`, causing the client to immediately flush the `AudioTrack` buffer.

---

### 1.2 Existing Windows Desktop Solutions, Tools & Community Projects

Our survey examined official Google desktop offerings, browser-based applications, and community open-source repositories:

| Category | Project / Tool | Architecture & Mechanism | Authentication | Strengths | Critical Deficiencies & Gaps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Official Google Web** | **Gemini Web App** (`gemini.google.com`) | Web client (Angular/Closure). Supports text, static image/document attachments, voice input. | Google Account (Browser session cookies) | Native Google Account login, zero installation. | **No continuous screen sharing**. Only accepts static single-image uploads or live webcam test; cannot stream live desktop. |
| **Official Google Sample** | **`google-gemini/live-api-web-console`** | React + TypeScript web app. Uses `navigator.mediaDevices.getDisplayMedia` + HTML5 `<canvas>` + WebSocket. | Raw Gemini API Key input (`?key=...`) | Reference implementation of Live API; supports mic, webcam, and screen share at ~1 FPS JPEG. | Requires manual API key; browser tab throttles when minimized; no native desktop integration, window hotkeys, or persistent tray icon. |
| **Electron Desktop** | **`ViaAnthroposBenevolentia/gemini-2-live-electron`** | Electron application wrapping Chromium's `desktopCapturer` API (`desktopCapturer.getSources`) and WebRTC audio/video. | Raw Gemini API Key | Dedicated desktop window; screen & window selector; native window frame. | Requires manual API key; heavy runtime footprint (~150MB+ bundle); lacks dual-mode on-demand trigger and native OS hotkeys. |
| **Python Toolkits** | **`saharmor/gemini-multimodal-playground`** | Python + FastAPI + Streamlit / CLI script using `mss` for screen capture, `pyaudio`, WebSockets. | Raw Gemini API Key | Clean modular Python code; low latency capture; straightforward pipeline. | Requires API key; lacks Google OAuth login flow; minimal GUI; no window-specific bounding box isolation; audio feedback on speakers without AEC. |
| **Python CLI Extension** | **`automateyournetwork/GeminiCLI_ScreenShare`** | CLI / MCP tool capturing screen snapshots and piping to Gemini CLI via slash commands. | API Key / Local MCP config | Fast on-demand terminal snapshots. | No continuous live duplex voice/video streaming; purely turn-based static screenshots. |
| **Framework Starter** | **`pipecat-ai/gemini-live-web-starter`** | Pipecat WebRTC framework interfacing with Gemini Live backend. | API Key via server backend | Polished WebRTC audio handling; interruption handling. | Requires running a multi-component Pipecat server infrastructure; web UI; requires API key. |
| **OBS Workaround** | **OBS Studio + Virtual Cam** | OBS screen capture -> OBS Virtual Camera -> browser WebRTC/Web console. | Tied to browser console | High control over scene composition and cropping. | Extreme setup friction; multi-window clunky configuration; high CPU/GPU overhead; not an integrated app. |

#### Summary of Existing Desktop Gaps:
1. **Authentication Friction**: None of the desktop or web community projects offer a smooth "Sign in with Google" OAuth 2.0 PKCE desktop flow. All demand an exposed, raw Google AI Studio API key (`GEMINI_API_KEY`).
2. **Dual-Mode Disconnect**: Tools implement either exclusively live streaming (web consoles) or exclusively static snapshots (CLI screenshot tools). None seamlessly blend a continuous live conversational session with an on-demand hotkey-driven snapshot/query mode.
3. **Audio Loopback / AEC on Windows**: Desktop PCs typically have standalone speakers and desk microphones. Without hardware AEC (which Android phones have), desktop screen sharing tools frequently suffer from audio echo when Gemini speaks, unless push-to-talk or software muting is implemented.
4. **Window Selection & Scoping**: Many tools only capture the entire virtual desktop (`mss.monitors[0]`), inadvertently leaking private windows, multi-monitor spans, or notification banners.

---

### 1.3 Gemini Multimodal Live API Protocol Details & Specifications

The Gemini Multimodal Live API uses a bidirectional, full-duplex WebSocket connection.

#### 1.3.1 Connection Endpoints & Transport
* **Google AI Studio / Generative Language API**:
  - Endpoint: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent`
  - Alternative Path: `v1beta` endpoint:
    `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
  - Authentication query param: `?key=<GEMINI_API_KEY>` or `?access_token=<OAUTH_ACCESS_TOKEN>`
  - Authentication header: `Authorization: Bearer <OAUTH_ACCESS_TOKEN>`
* **Vertex AI Endpoint (Google Cloud Enterprise)**:
  - Endpoint: `wss://<LOCATION>-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent`
  - Authentication header: `Authorization: Bearer <GCP_OAUTH_TOKEN>`

#### 1.3.2 Supported Models
* `models/gemini-2.0-flash-exp` (or `gemini-2.0-flash-realtime-exp`)
* `models/gemini-2.5-flash`

#### 1.3.3 Protocol Wire Messages & Lifecycle

```
Client                                                  Server (Gemini Live)
  |                                                               |
  |=== 1. WSS Handshake (Headers: Authorization: Bearer ...) ====>|
  |                                                               |
  |--- 2. Client Setup Message (BidiGenerateContentSetup) ------->|
  |<-- 3. Server Setup Complete (BidiGenerateContentSetupComplete)|
  |                                                               |
  |=== Duplex Streaming Session Active ===========================|
  |                                                               |
  |--- 4a. Audio Chunk (PCM 16kHz Mono) ------------------------->|
  |--- 4b. Video Frame (JPEG @ 1 FPS) --------------------------->|
  |                                                               |
  |<-- 5a. Model Turn: Audio Chunks (PCM 24kHz Mono) -------------|
  |<-- 5b. Model Turn: Text Tokens / Transcript Delta ------------|
  |<-- 5c. Turn Complete Flag (turnComplete: true) ---------------|
  |                                                               |
  |--- 6. User Speaks (Interruption / Barge-in) ----------------->|
  |<-- 7. Interrupted Signal (interrupted: true) -----------------|
  |    [Client flushes audio output buffer immediately]           |
  |                                                               |
  |--- 8. On-Demand Structured Turn (clientContent) ------------->|
  |<-- 9. Model Response Turn (serverContent) --------------------|
```

#### Complete Wire Schemas:

##### Step 1: Initial Setup Frame (`BidiGenerateContentSetup`)
Must be the first payload sent by the client upon socket connection.
```json
{
  "setup": {
    "model": "models/gemini-2.0-flash-exp",
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {
        "voiceConfig": {
          "prebuiltVoiceConfig": {
            "voiceName": "Aoede"
          }
        }
      },
      "temperature": 0.7,
      "maxOutputTokens": 1024
    },
    "systemInstruction": {
      "parts": [
        {
          "text": "You are a live AI desktop assistant. You observe the user's computer screen and listen to their voice. Provide concise, clear, and proactive assistance based on what is visible on screen."
        }
      ]
    }
  }
}
```
* **Supported Voice Names**:
  - `Aoede`: Female, conversational, natural, breezy.
  - `Charon`: Male, informative, calm, lower register.
  - `Fenrir`: Male, energetic, dynamic.
  - `Kore`: Female, firm, articulate, confident.
  - `Puck`: Male, upbeat, lively, middle register.

##### Step 2: Server Setup Acknowledgment (`BidiGenerateContentSetupComplete`)
```json
{
  "setupComplete": {}
}
```

##### Step 3: Realtime Continuous Ingestion (`BidiGenerateContentRealtimeInput`)
Used for streaming raw microphone audio and periodic screen captures.
```json
{
  "realtimeInput": {
    "mediaChunks": [
      {
        "mimeType": "audio/pcm;rate=16000",
        "data": "<BASE64_ENCODED_16BIT_LE_16000HZ_PCM_BYTES>"
      },
      {
        "mimeType": "image/jpeg",
        "data": "<BASE64_ENCODED_JPEG_IMAGE_BYTES>"
      }
    ]
  }
}
```

##### Step 4: Server Streaming Response (`BidiGenerateContentServerMessage`)
```json
{
  "serverContent": {
    "modelTurn": {
      "parts": [
        {
          "inlineData": {
            "mimeType": "audio/pcm;rate=24000",
            "data": "<BASE64_ENCODED_16BIT_LE_24000HZ_PCM_BYTES>"
          }
        },
        {
          "text": "I can see your Python code in VS Code. On line 42, there is an unclosed parenthesis."
        }
      ]
    },
    "turnComplete": false,
    "interrupted": false
  }
}
```

##### Step 5: User Interruption / Barge-in Frame
When the user speaks while the model is outputting audio:
```json
{
  "serverContent": {
    "interrupted": true
  }
}
```
*Client action*: Immediately cancel playback, discard remaining queued audio bytes in the local audio driver, and listen to the user.

##### Step 6: Discrete / On-Demand Query Frame (`BidiGenerateContentClientContent`)
Used when the user triggers an explicit on-demand snapshot with a specific question:
```json
{
  "clientContent": {
    "turns": [
      {
        "role": "user",
        "parts": [
          {
            "inlineData": {
              "mimeType": "image/jpeg",
              "data": "<BASE64_ENCODED_HIGH_RES_SCREENSHOT>"
            }
          },
          {
            "text": "Explain what this error dialog box is asking and what I should click."
          }
        ]
      }
    ],
    "turnComplete": true
  }
}
```

---

### 1.4 Operational Limitations, Bandwidth, Frame Rates, and Audio Formats

1. **Screen Frame Rate Recommendations**:
   - **Recommended Rate**: **1.0 Frame Per Second (1 FPS)** (interval = 1000ms).
   - **Why 1 FPS is Standard**:
     - Gemini processes images by tiling them into patches of visual tokens (~258 tokens per frame).
     - At 1 FPS: 258 tokens/sec = 15,480 tokens/min = ~155,000 tokens per 10-minute session.
     - At 30 FPS: 7,740 tokens/sec = 464,400 tokens/min = context window exhaustion in ~2 minutes!
     - 1 FPS provides optimal temporal comprehension for desktop UI, text editing, web browsing, and system interaction without overwhelming context buffers or triggering API rate limits.
   - **On-Demand Burst Rate**: If significant motion or a discrete user action occurs, sending a single immediate snapshot ahead of the 1-second timer maintains instantaneous responsiveness.

2. **Screen Resolution & Encoding Parameters**:
   - **Target Resolution**: 1280x720 (720p) or 1024x768 (max dimension 1024px).
   - **Encoding**: JPEG with quality set between 75% and 80%.
   - **Compression Performance**: A 1024x768 desktop screenshot compressed at JPEG quality 75 produces a ~60 KB to ~90 KB payload. Base64 encoding expands this by 33% to ~80 KB - ~120 KB per second on the wire.
   - **Readability**: 1024px width is sufficient to render standard 12pt–14pt code fonts and dialog text legibly for Gemini's vision encoder.

3. **Audio Specifications**:
   - **Client Ingestion Audio**:
     - Format: Raw Linear PCM 16-bit Signed Little-Endian.
     - Sample Rate: `16,000 Hz` (16 kHz).
     - Channels: `1` (Mono).
     - Chunk Size: 100ms (1,600 samples = 3,200 bytes per chunk).
     - Wire Bandwidth: 3,200 bytes * 10 chunks/sec = 32 KB/s (256 kbps).
   - **Model Output Audio**:
     - Format: Raw Linear PCM 16-bit Signed Little-Endian.
     - Sample Rate: `24,000 Hz` (24 kHz).
     - Channels: `1` (Mono).
     - Delivery: Chunks of ~1,200 to ~2,400 bytes (25ms to 50ms) streamed in real-time as synthetic speech is generated.
     - Playback Bandwidth: 48 KB/s (384 kbps) during active model speech.

4. **Total Bandwidth Profile**:
   - **Uplink**: ~80 KB/s (Video @ 1 FPS) + ~32 KB/s (Audio @ 16kHz) = **~112 KB/s (~896 kbps)**.
   - **Downlink**: ~48 KB/s (Audio @ 24kHz) + <2 KB/s (Text tokens) = **~50 KB/s (~400 kbps)**.
   - **Total Network Requirement**: Approximately 1.3 Mbps aggregate bandwidth, exceptionally light and resilient across standard Wi-Fi and cellular connections.

5. **Session Duration & Context Boundaries**:
   - Gemini Multimodal Live API enforces a practical continuous session limit of **10 to 15 minutes** per WebSocket connection.
   - The desktop client should gracefully handle session renewal (closing old session and opening a fresh setup connection without interrupting the user's workflow).

---

### 1.5 Comparative Analysis: Windows Desktop vs Android Native

| Feature / Dimension | Android Native Gemini Live | Windows Desktop Custom Application |
| :--- | :--- | :--- |
| **Capture Layer** | `MediaProjection` API + `VirtualDisplay` + `ImageReader`. | Win32 GDI / `mss` / DXGI Desktop Duplication API. |
| **Window Scoping** | Android 14+ granular app-level projection token or full screen. | Win32 Window Enumeration (`EnumWindows`, `GetWindowRect`, `PrintWindow`/`BitBlt`) or full desktop monitor capture. |
| **Background Execution** | Foreground Service (`FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION`) with ongoing status bar notification. | Windows Background Thread / Asyncio Task with System Tray icon and status color indicators. |
| **Acoustic Echo Cancellation** | Hardware/Platform DSP AEC (`AcousticEchoCanceler`). | Software Push-to-Talk / Mic Mute during playback, or software AEC (`webrtcvad` / `speexdsp`) + buffer flushing on interruption. |
| **Authentication Flow** | System Google Account via Google Play Services / AccountManager (single-tap). | Google OAuth 2.0 PKCE desktop flow with local loopback server (`http://127.0.0.1:<port>`). End user logs in via default browser; app captures token. |
| **User Trigger & Control** | Long-press power button / navigation bar swipe gesture / floating assistant bubble. | Global system hotkeys (e.g. `Ctrl+Shift+G` for on-demand capture, `Ctrl+Shift+L` for live toggle) + floating lightweight GUI widget. |
| **Multi-Monitor Handling** | Not applicable (single active mobile display). | Explicit monitor selection dropdown (Monitor 1, Monitor 2, or specific Application Window). |
| **Interaction Modes** | Primarily continuous live voice session. | **Dual Mode**: (1) Continuous Live Streaming + (2) Hotkey On-Demand Snapshot with text prompt. |

---

## 2. Logic Chain

1. **Observation**: Android executes live screen sharing by capturing low-framerate (1 FPS) downscaled JPEG frames via `MediaProjection` and streaming them alongside 16kHz PCM audio to a stateful WebSocket endpoint (`BidiGenerateContent`).
   **Inference**: A desktop implementation does not need high-FPS video encoding (like H.264/WebRTC video tracks); standard JPEG snapshots at 1 FPS over WebSocket replicate the exact data protocol used by Google's native services.

2. **Observation**: Google's Gemini Multimodal Live WebSocket endpoint accepts either an API key in query parameters (`?key=...`) or an OAuth 2.0 Bearer token in the `Authorization: Bearer <token>` handshake header or `?access_token=<token>` parameter.
   **Inference**: A Windows desktop application can satisfy the user's strict requirement for Google Account sign-in (without manual API keys) by performing standard OAuth 2.0 PKCE authentication with Google Identity services and passing the resulting access token into the WebSocket connection.

3. **Observation**: Existing community solutions (such as `live-api-web-console` and `gemini-2-live-electron`) rely on browser `getDisplayMedia` or Electron, lack global hotkeys, require raw API key inputs, and lack seamless dual-mode operation (live streaming vs on-demand capture).
   **Inference**: Existing tools are insufficient to meet the user's requirements (R1, R2, R3). A custom Windows application built in Python using native capture (`mss`/`win32gui`), low-latency audio (`sounddevice`), and an OAuth 2.0 PKCE authentication loop is necessary and technically feasible.

4. **Observation**: Unlike Android phones which have built-in hardware DSP Acoustic Echo Cancellation, Windows desktop speakers output model voice that can easily re-enter the desktop microphone, causing Gemini to interrupt itself.
   **Inference**: The Windows desktop client must implement robust audio management:
   - When the server sends `interrupted: true`, immediately flush the playback buffer.
   - Provide an optional "Push-to-Talk" or "Mute mic during speech playback" mode, alongside an explicit microphone toggle switch in the UI.

5. **Observation**: Windows users frequently have sensitive information (passwords, private chats) open on secondary monitors or background windows.
   **Inference**: Window-specific capture (selecting a specific target window via `win32gui` handles) must be supported in addition to full-screen capture to preserve privacy and improve model focus.

---

## 3. Caveats

1. **API Maturity & Endpoint Stability**:
   - The Gemini Multimodal Live API is currently in `v1alpha`/`v1beta` (`gemini-2.0-flash-exp`). While the WebSocket protocol and message formats (`setup`, `realtimeInput`, `serverContent`) are established, endpoint version paths or subprotocol negotiation may evolve as Gemini 2.5/3.0 enters general availability.
2. **OAuth Scopes for AI Studio vs Vertex AI**:
   - User OAuth tokens accessing Google AI Studio APIs require appropriate Google Cloud project setup and OAuth consent screen configuration (e.g., scopes `https://www.googleapis.com/auth/generative-language` or `https://www.googleapis.com/auth/cloud-platform`). Explorer Survey 2 provides the dedicated deep dive into OAuth client configuration.
3. **Windows Audio Driver Diversity**:
   - Desktop audio configurations vary widely (USB headsets, built-in laptop mic/speakers, Bluetooth headphones with latency). The audio output loop should use dynamic sample rate conversion if the local DAC does not natively support 24,000 Hz.
4. **Window Minimization**:
   - Under Windows DWM, minimizing a window can halt its buffer rendering in standard `PrintWindow`/`BitBlt` calls. The capture module must handle minimized windows gracefully (e.g. restoring or alerting the user).

---

## 4. Conclusion

1. **Feasibility**: Live desktop screensharing with Gemini on Windows is completely feasible and can match Android's Gemini Live experience in speed, conversational responsiveness, and visual intelligence.
2. **Deficiency of Existing Tools**: No existing official or community desktop tool fulfills all user requirements:
   - Web consoles require manual API keys, have browser throttling, and lack OS-level hotkeys.
   - Existing open-source wrappers lack Google Account OAuth sign-in and dual-mode switching.
3. **Architecture Blueprint for Implementation**:
   - **Protocol**: Gemini Multimodal Live WebSocket (`wss://generativelanguage.googleapis.com/.../BidiGenerateContent`).
   - **Authentication**: OAuth 2.0 Authorization Code flow with PKCE via a local loopback server (`http://127.0.0.1:<port>`), storing tokens securely and supplying `Authorization: Bearer <token>` on handshake.
   - **Capture Engine**: `mss` for high-performance multi-monitor full screen capture; `win32gui` + `Pillow` for window-specific bounding box capture.
   - **Streaming Loop**: Asynchronous 1.0 FPS JPEG compression (quality 75, max dimension 1024px) paired with 16kHz 16-bit mono PCM microphone streaming.
   - **Audio Playback**: Streaming 24kHz PCM audio output via `sounddevice.RawOutputStream`, equipped with instantaneous buffer clearing upon `interrupted: true` server events.
   - **Dual Interaction Modes**:
     * *Mode 1 (Continuous Live)*: Real-time 1 FPS video + duplex audio loop.
     * *Mode 2 (On-Demand)*: Global hotkey (`Ctrl+Shift+S`) capturing the selected target, opening an audio/text query prompt, and receiving Gemini's response.

---

## 5. Verification Method

To independently verify the protocol findings and endpoints:

1. **WebSocket Endpoint Handshake Verification**:
   Using `wscat` or Python `websockets`, verify connection to the Generative Language Live endpoint:
   ```bash
   python -c "
   import asyncio, websockets
   async def test():
       uri = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent'
       try:
           async with websockets.connect(uri) as ws:
               print('Connected successfully')
       except Exception as e:
           print('Handshake result:', e)
   asyncio.run(test())
   "
   ```
2. **Payload Schema Validation**:
   Inspect the initial setup frame and verify that sending a properly formatted JSON payload:
   ```json
   {"setup": {"model": "models/gemini-2.0-flash-exp", "generationConfig": {"responseModalities": ["AUDIO"]}}}
   ```
   yields a `{"setupComplete": {}}` response.
3. **Capture & Audio Benchmark**:
   Run a standalone capture test with `mss` and `Pillow` to confirm that 1024px JPEG compression takes <15ms on Windows, well within the 1000ms budget for 1 FPS streaming.
