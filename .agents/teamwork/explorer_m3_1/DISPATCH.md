# Dispatch: Milestone 3 Explorer 1 — PyQt6 UI Architecture & Asyncio Integration

## Objectives
Investigate PyQt6 GUI architecture for the Windows desktop Gemini screen sharing application:
1. How to cleanly integrate the PyQt6 event loop with the background asyncio event loop for `GeminiLiveClient` and `OnDemandClient` (e.g. via `qasync` or dedicated background QThread running `asyncio.run()` with thread-safe `pyqtSignal` bridging).
2. UI layout and widget hierarchy:
   - Google Account card (sign-in status, email/name display, sign-in/sign-out buttons, refresh trigger).
   - Mode selector (Live Streaming vs On-Demand Capture).
   - Capture target selector (Full Desktop dropdown, individual displays, and application window picker with window titles & HWNDs).
   - Live preview thumbnail panel.
   - Live transcript & response panel (scrollable rich text displaying user queries and Gemini streaming text responses).
   - Control buttons: Start/Stop Streaming, Capture Now, Microphone Mute toggle with clear visual feedback.
3. Thread safety: Ensuring audio playback callbacks, live frame capture, and WebSocket events never block or access Qt widgets directly outside the main GUI thread.

## Inputs
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\`

## Output
Write report to: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\handoff.md`

## 2026-11-08T14:31:36Z
You are teamwork_explorer (PyQt6 Architecture & Asyncio Explorer).
Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\

Read your dispatch instructions and requirements:
1. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read first)
2. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md
3. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\DISPATCH.md
4. Existing engine modules in c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\

Investigate and produce an actionable architectural plan for the PyQt6 Desktop GUI:
- Clean integration between PyQt6 event loop and background asyncio event loop for GeminiLiveClient and OnDemandClient (evaluating QThread + asyncio.run() with pyqtSignal vs qasync).
- Main window layout structure, widget tree, and control cards.
- Thread-safe communication architecture: passing streaming text tokens, audio status, connection events, and capture frames across threads to Qt UI components without UI lockups.
- Recommend concrete class design and interface signatures for gemini_desktop_screenshare/ui/main_window.py and gemini_desktop_screenshare/app.py.

Write your findings and recommendations to:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\handoff.md
Update progress.md with your liveness heartbeat. Send a message when finished.
