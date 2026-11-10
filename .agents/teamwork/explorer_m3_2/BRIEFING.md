# BRIEFING — 2026-11-08T14:42:00Z

## Mission
Investigate Win32 system-wide hotkeys (Alt+S, Alt+L) and target window picker/live preview for PyQt6, producing an actionable architectural plan for gemini_desktop_screenshare.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, synthesizer
- Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_2
- Original parent: d14990da-b9ef-4371-b0a5-2617d9e7778c
- Milestone: M3 (Desktop User Interface & Interaction Controls)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Focus on Win32 global hotkeys (RegisterHotKey/UnregisterHotKey via PyQt6), target window picker integration with ScreenCaptureEngine, and live preview thumbnail pipeline
- Ensure zero interference between low-frequency preview rendering and active live streaming or on-demand capture
- Ensure proper cleanup of Win32 hotkeys and GDI resources to prevent leaks or system locks

## Current Parent
- Conversation ID: d14990da-b9ef-4371-b0a5-2617d9e7778c
- Updated: 2026-11-08T14:31:45Z

## Investigation State
- **Explored paths**:
  - `gemini_desktop_screenshare/capture/screen_capture.py`
  - `gemini_desktop_screenshare/capture/window_capture.py`
  - `gemini_desktop_screenshare/streaming/live_client.py`
  - `gemini_desktop_screenshare/config.py`
  - Win32 API (`RegisterHotKey`, `UnregisterHotKey`, `WM_HOTKEY`, `wintypes.MSG`, `GetLastError`)
  - PyQt6 `QAbstractNativeEventFilter` vs `QWidget.nativeEvent`
  - `QThreadPool`, `QRunnable`, `QImage` memory safety, `QPixmap`
- **Key findings**:
  - `QAbstractNativeEventFilter` cleanly captures both window messages and thread messages (`hWnd=None`) across all event loops.
  - Using `MOD_NOREPEAT` (0x4000) with `MOD_ALT` (0x0001) prevents key-repeat storms when holding Alt+S.
  - Conflict code `1409` (`ERROR_HOTKEY_ALREADY_REGISTERED`) cleanly caught via `GetLastError()`.
  - Preview captures take ~60ms; running them synchronously on main GUI freezes the UI. Asynchronous worker on `QThreadPool` with queued `QImage` emission keeps main GUI 100% fluid (<1ms UI cost).
  - Passive preview must check `user32.IsIconic(hwnd)` and render a placeholder rather than un-minimizing the target window.
  - Programmatic testing is 100% viable in pytest by directly passing simulated `MSG` pointers to `nativeEventFilter`.
- **Unexplored areas**:
  - None. All dispatch questions fully answered with empirical verification.

## Key Decisions Made
- Architecture for `gemini_desktop_screenshare/ui/hotkey_manager.py` finalized with `Win32HotkeyFilter` and `HotkeyManager` classes.
- Target window picker uses `QComboBox` with rich item data and selection preservation across refreshes.
- Live preview uses low-frequency `QTimer` (1 FPS) + `QThreadPool` task when idle, pausing during live streaming to eliminate capture contention.

## Artifact Index
- `.agents/teamwork/explorer_m3_2/DISPATCH.md` — Dispatch instructions
- `.agents/teamwork/explorer_m3_2/BRIEFING.md` — Persistent working memory
- `.agents/teamwork/explorer_m3_2/progress.md` — Liveness heartbeat and status
- `.agents/teamwork/explorer_m3_2/handoff.md` — Final 5-component investigation report
