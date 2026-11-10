# BRIEFING — 2026-11-08T14:37:00Z

## Mission
Investigate and architect the PyQt6 Desktop GUI, event loop integration, widget hierarchy, and thread-safe signaling for Gemini Screen Sharing.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, synthesizer
- Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\
- Original parent: d14990da-b9ef-4371-b0a5-2617d9e7778c
- Milestone: Milestone 3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Investigate clean integration between PyQt6 event loop and background asyncio event loop for GeminiLiveClient and OnDemandClient (evaluating QThread + asyncio.run() with pyqtSignal vs qasync)
- Detail main window layout structure, widget tree, and control cards (Google Account, mode selector, capture target selector, preview thumbnail, transcript panel, controls)
- Define thread-safe communication architecture (streaming tokens, audio status, connection events, capture frames)
- Concrete class designs and interface signatures for gemini_desktop_screenshare/ui/main_window.py and gemini_desktop_screenshare/app.py

## Current Parent
- Conversation ID: d14990da-b9ef-4371-b0a5-2617d9e7778c
- Updated: 2026-11-08T14:37:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`
  - Engine modules: `config.py`, `auth/oauth_manager.py`, `auth/token_store.py`, `capture/screen_capture.py`, `capture/window_capture.py`, `audio/audio_pipeline.py`, `streaming/live_client.py`, `ondemand/ondemand_client.py`
  - Python runtime: verified installed libraries (`PyQt6`, `sounddevice`, `mss`, `websockets`, `aiohttp`, `PIL`, `win32gui`)
- **Key findings**:
  - `qasync` is NOT installed in the environment (`ModuleNotFoundError`).
  - `QThread` with a dedicated `asyncio` event loop and `asyncio.run_coroutine_threadsafe` + `pyqtSignal` is completely native, zero-dependency, and isolates UI rendering from async I/O.
  - Thread synchronization: Must use `threading.Event` to ensure the background asyncio event loop is fully initialized before coroutine submission.
  - `QImage` is thread-safe and re-entrant; PIL buffers converted to `QImage(...).copy()` prevent memory corruption and can safely cross threads via `pyqtSignal(QImage)` to main thread `QPixmap.fromImage()`.
  - Barge-in interruptions from `GeminiLiveClient` can be intercepted cleanly by wrapping `AudioPipeline.interrupt()`.
  - Headless execution with `QT_QPA_PLATFORM=offscreen` verified working cleanly for unit testing.
- **Unexplored areas**: None for UI architecture; peer explorer findings in M3.2 (hotkeys) and M3.3 (styling/state machine) will integrate directly with this architecture.

## Key Decisions Made
- Selected `QThread + asyncio` with `pyqtSignal` queued connections over `qasync`.
- Designed clean separation in `gemini_desktop_screenshare/app.py` via `AsyncWorker(QThread)` managing all asynchronous and blocking engine operations.
- Designed structured card-based desktop layout for `gemini_desktop_screenshare/ui/main_window.py`.

## Artifact Index
- DISPATCH.md — Dispatch instructions and history
- BRIEFING.md — Persistent working memory and state
- progress.md — Liveness heartbeat and step tracking
- handoff.md — Comprehensive architectural handoff report
