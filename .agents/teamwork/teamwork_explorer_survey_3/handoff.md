# Windows Desktop Screen Capture, Audio Architecture, UI Framework, and Testing Strategy Report

**Working Directory**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3`  
**Author**: Explorer Survey 3 (Windows Capture & Audio Architecture Researcher)  
**Parent Caller**: `d14990da-b9ef-4371-b0a5-2617d9e7778c`  
**Date**: 2026-11-08

---

## 1. Observation

### 1.1 Python Environment & Package Availability
Direct system probe via `python -m pip list` on Windows host running Python 3.11.0 revealed:
- **PyQt6 (6.11.0)** and **PyQt6-Qt6 (6.11.2)** are installed and functional.
- **customtkinter (6.0.0)** is installed and functional.
- **pywin32 (312)** and **pywinauto (0.6.9)** are installed.
- **pillow (12.3.0)** and **opencv-python (5.0.0.93)** are installed.
- **websockets (16.1.1)** and **aiohttp (3.14.4)** are installed.
- **google-genai (2.28.0)** and **google-auth (2.59.1)** are installed.
- **sounddevice (0.5.6)**, **pyaudio (0.2.14)**, and **mss (10.2.0)** installed cleanly via wheels with zero native compiler dependencies.

### 1.2 Windows Desktop & Session Isolation Discovery
When running full screen capture in non-interactive/isolated desktops (e.g. `exebox-ZM7XDF67UPUH73IO4JSM7HABHT`), initial runs of `PIL.ImageGrab` and `mss` produced:
```
PIL.ImageGrab failed: OSError: screen grab failed
MSS failed: ScreenShotError: Windows graphics function failed: BitBlt
```
System investigation via Win32 ctypes revealed:
```python
Process Session ID: 1
Thread Desktop Handle: 432
Desktop Name: exebox-ZM7XDF67UPUH73IO4JSM7HABHT
Screen Metrics SM_CXSCREEN=1920, SM_CYSCREEN=1080
```
When calling `user32.OpenInputDesktop(0, False, 0x01FF)` and `user32.SetThreadDesktop(h_input)`:
- If called **after** `import win32ui`: failed with Windows Error 170 (`ERROR_BUSY: The requested resource is in use`), because MFC/win32ui hooks bind windows to the current desktop.
- If called **before** UI/MFC initialization or in a dedicated capture thread: succeeded with result `1` (`OpenInputDesktop handle=284, SetThreadDesktop result=1`), enabling 100% reliable screen capture across all tools (`mss`, `PIL`, GDI).

### 1.3 Full-Screen Capture & Downscaling Benchmarks
Empirical measurements on 1920x1080 display (`benchmark_capture.py`):
- **Raw Full Screen Capture**:
  - `mss.MSS().grab()`: **21.73 ms** avg (min 15.42 ms, max 31.41 ms)
  - `PIL.ImageGrab.grab()`: **22.21 ms** avg (min 16.22 ms, max 32.39 ms)
  - Pure ctypes GDI (`BitBlt` + `GetDIBits`): **29.92 ms** avg
- **Downscaling & JPEG Encoding Benchmarks**:
  - Target `(1024, 768)`:
    - Resize time: OpenCV Linear **0.74 ms** | PIL Bilinear **9.97 ms**
    - Quality 60: PIL = 93.8 KB (1.84 ms) | OpenCV = 107.0 KB (1.76 ms)
    - Quality 70: PIL = 110.4 KB (1.92 ms) | OpenCV = 125.2 KB (1.84 ms)
    - Quality 80: PIL = 135.8 KB (1.95 ms) | OpenCV = 152.6 KB (2.00 ms)
  - Target `(960, 540)`:
    - Quality 70: PIL = 73.4 KB (1.24 ms)
  - Target `(1280, 720)`:
    - Quality 70: PIL = 125.7 KB (2.17 ms)
- **Total Pipeline Execution Time**:
  - Capture (~21 ms) + OpenCV resize (0.7 ms) + JPEG Q70 encode (1.9 ms) + Base64 encode (<0.1 ms) = **~24 ms total pipeline latency per frame**.
  - At 1 FPS (1 frame every 1000 ms), CPU duty cycle is **<2.5%** on a single thread.

### 1.4 Window-Specific Capture (`HWND`) & Minimized State Handling
Tested in `test_window_capture.py`:
- `EnumWindows` successfully filtered open windows using `IsWindowVisible()`, `GetWindowTextLengthW() > 0`, and `dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED) == 0`.
- Accurate geometry obtained via `dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS)`:
  - Non-minimized window (e.g. `Houdini Indie`, `V-Ray Frame Buffer`): rect `(0, 0, 1920, 1040)`.
  - Minimized windows (e.g. `Task Manager`, `qBittorrent`): detected via `user32.IsIconic(hwnd) == True`, rect `(-31993, -32000, -31847, -31972)`.
- `user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)` captured the full contents of application windows in **0.29 ms to 2.1 ms**, even when obscured or layered.

### 1.5 Audio Devices, Formats, and Playback Interruption
Tested in `test_audio_pipeline.py`:
- `sounddevice.query_devices()` identified 41 input/output device interfaces across MME, DirectSound, WASAPI, and WDM-KS.
- Hardware configuration:
  - Input: Default device (Virtual Mic / Realtek) natively supports `16000 Hz, 1 channel, int16` (Gemini Live ingestion specification).
  - Output: Default device (Realtek Audio) natively supports `24000 Hz, 1 channel, int16` (Gemini Live response specification).
- Buffer interruption experiment:
  - When Gemini signals `interrupted: true`, immediately draining the audio queue (`queue.get_nowait()` loop) in `AudioPlayer.interrupt()` flushed 5 queued chunks from 5 to 0 instantly (<0.1 ms), preventing audio overrun.

### 1.6 Dual-Mode Flow & Mock Servers
Tested in `mock_gemini_server.py`, `test_mock_rest_server.py`, and `test_dual_mode_flow.py`:
- Local WebSocket server running on `ws://127.0.0.1:8991`:
  - Acknowledged `setup` message with `setupComplete`.
  - Ingested 4 continuous live frames (1024x768 JPEG @ Q70, ~110 KB each) + 16kHz audio chunks.
  - Streamed back 24kHz audio chunks and textual model turns.
  - Successfully received and processed on-demand snapshot + prompt (`client_content.turns`).
- Local REST server on `http://127.0.0.1:8992`:
  - Validated `Authorization: Bearer <token>`.
  - Parsed `inline_data` JPEG payload + user prompt text, returning `candidates[0].content.parts[0].text`.

---

## 2. Logic Chain

```
[Observation 1.1, 1.2: Host Python environment & isolated desktop error]
         |
         v
[Insight: Non-interactive desktops block GDI unless OpenInputDesktop + SetThreadDesktop is invoked before UI hooks]
         |
         v
[Observation 1.3: mss + OpenCV resize + JPEG Q70 = 24ms per frame, 110KB payload]
         |
         v
[Logic: 110KB/s at 1 FPS uses <2.5% CPU and ~880 kbps bandwidth, ideal for Gemini Live WebSocket rate limits]
         |
         v
[Observation 1.4: PrintWindow(PW_RENDERFULLCONTENT) captures specific HWND in ~1ms without screen occlusion]
         |
         v
[Logic: Dual capture modes (Full Desktop via mss, Specific Window via PrintWindow) cover all user scenarios]
         |
         v
[Observation 1.5: sounddevice handles 16kHz PCM input and 24kHz PCM output; immediate queue draining stops speech in <1ms]
         |
         v
[Logic: Audio pipeline guarantees low latency and instantaneous barge-in interruption handling]
         |
         v
[Observation 1.6: Local mock WebSocket and REST servers successfully validated dual-mode communication offline]
         |
         v
[Conclusion: Full technical blueprint established for Windows capture, audio pipeline, PyQt6 UI, and mock testing]
```

---

## 3. Caveats

1. **Hardware-Accelerated / DRM-Protected Windows**:
   Certain applications (e.g. Netflix in Edge, protected video players) block GDI `PrintWindow` or return black surfaces. For general desktop applications (browsers, IDEs, office apps, terminals, games in windowed/borderless mode), `PrintWindow(PW_RENDERFULLCONTENT)` and `mss` function reliably. If a specific window renders black via `PrintWindow`, bringing it to the foreground (`user32.SetForegroundWindow(hwnd)`) and cropping from full screen capture serves as an automatic fallback.
2. **Minimized Windows**:
   Windows pushes minimized windows to coordinates `(-32000, -32000)` and suspends their DWM redraw surface. Capturing a minimized window requires restoring it (`ShowWindow(hwnd, SW_RESTORE)` or `SW_SHOWNOACTIVATE`).
3. **DXGI Desktop Duplication vs. mss**:
   DXGI Desktop Duplication achieves 60+ FPS with GPU memory copies, but throws `DXGI_ERROR_ACCESS_LOST` on UAC popups, resolution shifts, or screen locks, requiring COM interface reinitialization. Because Gemini Live strictly operates at **~1 FPS**, `mss` (21ms CPU time per second) is far more stable, portable, and maintainable than DXGI.

---

## 4. Conclusion & Recommended Architecture

### 4.1 Component Design Blueprint

```
+-----------------------------------------------------------------------------------+
|                                  PyQt6 Desktop GUI                                 |
|  - Google Account Sign-In / OAuth Status Indicator                                |
|  - Target Selector: [Full Screen / HWND Window Dropdown] (DwmGetWindowAttribute)   |
|  - Mode Selector: [Continuous Live Streaming <-> On-Demand Snapshot Capture]      |
|  - Mic Toggle: [Mute / Unmute]                                                    |
|  - Live Preview Thumbnail (QLabel + QPixmap)                                      |
|  - Live Transcript / Response Text Area                                           |
|  - Global Hotkey Listener: WM_HOTKEY (Alt+S / Ctrl+Shift+S)                       |
+-----------------------------------------------------------------------------------+
           |                                                      ^
           | (Qt Signals / Thread-safe Queues)                    | (Qt Signals)
           v                                                      |
+-----------------------------------------------------------------------------------+
|                        Asyncio Background Orchestrator                            |
|                                                                                   |
|  +---------------------------+             +-----------------------------------+  |
|  | Screen Capture Worker     |             | Audio Capture Worker (Microphone) |  |
|  | - Desktop: mss.MSS()      |             | - sounddevice.RawInputStream      |  |
|  | - Window: PrintWindow()   |             | - 16kHz, 16-bit Mono PCM          |  |
|  | - Resize: 1024x768        |             | - 100ms chunks (3200 bytes)       |  |
|  | - JPEG: Quality 70        |             | - Mute -> send silence            |  |
|  | - Rate: 1.0 FPS           |             +-----------------------------------+  |
|  +---------------------------+                               |                    |
|                |                                             |                    |
|                v                                             v                    |
|      [realtime_input (JPEG)]                       [realtime_input (PCM)]         |
|                \                                             /                    |
|                 +-------------------------------------------+                     |
|                                       |                                           |
|                                       v                                           |
|              +-------------------------------------------------+                  |
|              |         Gemini Multimodal Live WebSocket         |                  |
|              |      wss://generativelanguage.googleapis.com     |                  |
|              +-------------------------------------------------+                  |
|                                       |                                           |
|                                       v                                           |
|       +---------------------------------------------------------------+           |
|       | Inbound Message Dispatcher                                    |           |
|       | - "serverContent.modelTurn.parts":                            |           |
|       |     * text -> emit to UI transcript                           |           |
|       |     * audio/pcm (24kHz) -> push to Audio Playback Queue       |           |
|       | - "serverContent.interrupted: true":                          |           |
|       |     * call AudioPlayer.interrupt() -> flush buffer (<1ms)     |           |
|       +---------------------------------------------------------------+           |
|                                       |                                           |
|                                       v                                           |
|                      +-----------------------------------+                        |
|                      | Audio Playback Worker (Speaker)   |                        |
|                      | - sounddevice.RawOutputStream     |                        |
|                      | - 24kHz, 16-bit Mono PCM          |                        |
|                      | - Instant queue flush on barge-in |                        |
|                      +-----------------------------------+                        |
+-----------------------------------------------------------------------------------+
```

### 4.2 Detailed Specifications

#### 1. Capture Pipeline Specification
- **Engine**: `mss.MSS()` for Full Desktop; `user32.PrintWindow(hwnd, hdc, 2)` for Window capture.
- **Desktop Session Hook**: In background capture worker, ensure attachment via:
  ```python
  user32 = ctypes.windll.user32
  h_input = user32.OpenInputDesktop(0, False, 0x01FF)
  if h_input:
      user32.SetThreadDesktop(h_input)
  ```
- **Window Enumeration**:
  ```python
  # Filter visible, non-empty, uncloaked windows
  dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, byref(cloaked), sizeof(cloaked))
  # True bounds without transparent drop shadows:
  dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, byref(rect), sizeof(rect))
  ```
- **Image Pipeline**:
  - Resolution: Downscale source (e.g. 1920x1080) to **1024x768** maintaining aspect ratio with letterboxing or linear scaling.
  - Format: JPEG, quality = **70**.
  - Output payload size: **~110 KB** per frame.
  - Streaming rate: **1 frame per second** (1.0s interval).

#### 2. Audio Pipeline Specification
- **Microphone Input**:
  - Sample Rate: **16000 Hz**
  - Channels: **1 (Mono)**
  - Format: **16-bit signed integer (int16), little-endian**
  - Block size: **1600 samples (100 ms)**
  - Encoded: Base64 raw bytes inside `media_chunks` (`mime_type: "audio/pcm;rate=16000"`).
- **Speaker Playback**:
  - Sample Rate: **24000 Hz**
  - Channels: **1 (Mono)**
  - Format: **16-bit signed integer (int16), little-endian**
  - Output Stream: `sounddevice.RawOutputStream(samplerate=24000, channels=1, dtype='int16', blocksize=1024)`.
- **Interruption (Barge-in) Handling**:
  - On receipt of `{"serverContent": {"interrupted": true}}`:
    ```python
    def interrupt(self):
        self.interrupted.set()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    ```

#### 3. Dual-Mode Operation Specification
- **Mode 1 (Continuous Live)**:
  - WebSocket connection to Gemini Live.
  - Audio streaming continuously every 100 ms.
  - Video frame sent every 1000 ms (1 FPS).
  - Bi-directional audio responses played through speaker as received.
- **Mode 2 (On-Demand Capture)**:
  - Hotkey (`Alt+S`) or UI button click triggers single snapshot.
  - High quality JPEG (Quality 85).
  - Can be sent via REST `generateContent` or as a turn within the live session.
  - Text answer displayed in UI, optional TTS speech playback.

#### 4. GUI & Global Hotkey Specification
- **Framework**: PyQt6.
- **Styling**: Modern dark theme (QSS with dark gray `#1e1e1e` backgrounds, rounded cards, blue accent `#1a73e8`).
- **Global Hotkey Registration**:
  ```python
  # Register Alt+S (0x0001 = MOD_ALT, 0x53 = 'S')
  ctypes.windll.user32.RegisterHotKey(int(self.winId()), 100, 0x0001, 0x53)
  ```
  Intercepted via `nativeEvent()` on `WM_HOTKEY` (message `0x0312`).

---

## 5. Verification Method

To independently reproduce and verify all findings on Windows, execute the following commands in powershell:

### 5.1 Verification Commands
```powershell
# 1. Verify Screen Capture & Downscaling Benchmark
python c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3\benchmark_capture.py

# 2. Verify Window Enumeration and HWND Capture Probe
python c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3\test_window_capture.py

# 3. Verify Audio Capture & Playback Interruption Buffer Logic
python c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3\test_audio_pipeline.py

# 4. Verify End-to-End Dual-Mode WebSocket Flow against Mock Server
python c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3\test_dual_mode_flow.py

# 5. Verify On-Demand REST Mock Multimodal Server
python c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\teamwork_explorer_survey_3\test_mock_rest_server.py
```

### 5.2 Files to Inspect
- `benchmark_capture.py`: Performance numbers for MSS vs PIL vs GDI, downscaling and compression metrics.
- `test_window_capture.py`: Window filtering, HWND detection, and `PrintWindow` implementation.
- `test_audio_pipeline.py`: Low-latency 16kHz capture and 24kHz playback classes with instant queue purge.
- `mock_gemini_server.py`: Local offline WebSocket mock implementation of the Gemini Multimodal Live protocol.
- `test_dual_mode_flow.py`: Full end-to-end integration test demonstrating continuous 1 FPS streaming and on-demand capture.
- `test_mock_rest_server.py`: Local offline REST mock for `generateContent` multimodal requests.

### 5.3 Invalidation Conditions
- If `benchmark_capture.py` fails with BitBlt error: check if `SetThreadDesktop` was called before importing UI packages.
- If audio stream check fails: check if Windows audio service is running or if audio devices are disabled.
- If WebSocket port 8991 is occupied: configure `port` argument in `MockGeminiLiveServer`.
