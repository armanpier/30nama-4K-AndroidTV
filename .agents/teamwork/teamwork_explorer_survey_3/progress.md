# Progress Log

Last visited: 2026-11-08T16:41:00Z

## Status: Investigation Completed & Verified Empirically

### Completed Milestones:
1. **Windows Screen Capture Benchmarks**:
   - Discovered and solved the Windows non-interactive/isolated desktop session issue (`OpenInputDesktop` + `SetThreadDesktop`).
   - Discovered the MFC hook conflict: importing `win32ui` sets hooks that cause `SetThreadDesktop` to fail with error 170 (`ERROR_BUSY`). Pure `ctypes` GDI or calling `SetThreadDesktop` before UI initialization resolves this completely.
   - Benchmarked capture performance on host:
     - `mss`: ~21.7ms
     - `PIL.ImageGrab`: ~22.2ms
     - Pure ctypes GDI: ~29.9ms
   - Benchmarked downscaling and JPEG compression:
     - 1024x768 @ quality 70: ~110 KB frame size, ~1.9ms encoding time (OpenCV / PIL).
     - Total capture + resize + compression + base64 encoding pipeline: **~24-25ms** (<2.5% CPU at 1 FPS).
2. **Window-Specific Capture (`HWND`)**:
   - Implemented and verified `list_open_windows()` using `EnumWindows`, filtering out invisible, cloaked (virtual desktops/UWP), zero-dimension, and shell windows.
   - Used `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` to get true window rects without drop shadows.
   - Verified `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)` capturing real open application windows (e.g., V-Ray, Houdini) in ~0.3 - 2ms.
   - Handled minimized windows (`IsIconic(hwnd)`): detected off-screen coordinates `(-32000, -32000)` and established restore/focus strategy.
3. **Audio I/O Pipeline**:
   - Inspected host audio devices via `sounddevice`: 41 input/output devices across MME, DirectSound, WASAPI, and WDM-KS.
   - Verified that 16kHz 16-bit mono input (Gemini Live ingestion format) and 24kHz 16-bit mono output (Gemini Live synthesis format) are natively supported.
   - Designed and verified low-latency streaming `AudioPlayer` and `AudioRecorder`.
   - Identified critical interruption requirement: instant queue purging in `interrupt()` to stop model speech instantly (<1ms) when Gemini signals `interrupted: true`.
4. **Dual-Mode Interaction Architecture**:
   - Designed 4-tier concurrency model (UI Thread, Asyncio Live loop, Audio Capture worker, Audio Playback worker).
   - Built and verified mock Gemini Live WebSocket server and mock REST server.
   - Verified full end-to-end flow: session setup, 1 FPS live video + 16kHz audio streaming, model audio playback, on-demand screenshot analysis.
5. **Desktop UI Framework & Hotkeys**:
   - Evaluated PyQt6 vs CustomTkinter vs Tkinter.
   - Verified PyQt6 offscreen execution and thread safety (`pyqtSignal`).
   - Designed native Windows `RegisterHotKey` / `WM_HOTKEY` integration via Qt event filter for zero-overhead global hotkeys.
6. **Programmatic Testing Suite**:
   - Implemented and verified standalone local mock Gemini Live WebSocket server and mock REST server.
   - Proved reproducible offline verification without external internet or live Google credentials.
