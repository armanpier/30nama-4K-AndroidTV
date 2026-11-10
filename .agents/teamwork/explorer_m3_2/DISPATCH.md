# Dispatch: Milestone 3 Explorer 2 — Win32 Global Hotkeys & Window Management

## Objectives
Investigate Win32 global hotkeys and target window management for PyQt6 on Windows:
1. Implementation of system-wide hotkeys:
   - `Alt+S`: Trigger on-demand screen capture & prompt dialog.
   - `Alt+L`: Toggle live streaming session (start / stop).
   - How to register and handle Win32 `RegisterHotKey` / `UnregisterHotKey` in PyQt6 using `QAbstractNativeEventFilter` or overriding `QWidget.nativeEvent(eventType, message)`.
   - Handling `WM_HOTKEY` (0x0312), extracting `msg.lParam` and `msg.wParam`, and translating cleanly to Qt signals.
   - Fallback and error handling if a hotkey is already registered by another application.
2. Target Window Picker & Live Preview:
   - Hooking `ScreenCaptureEngine.list_windows()` into a dropdown with auto-refresh / "Refresh Windows" button.
   - Handling window title display (filtering out invisible/cloaked/tool windows, truncating long titles, preserving HWND mapping).
   - Live preview thumbnail update: Periodic timer (e.g. 1-2 FPS preview) capturing the active target and rendering to `QLabel` / `QPixmap` without degrading system responsiveness or interfering with live streaming capture.
   - Handling minimized target windows or destroyed HWNDs gracefully.

## Inputs
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\`

## Output
Write report to: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_2\handoff.md`


## 2026-11-08T14:31:45Z
You are teamwork_explorer (Win32 Hotkeys & Window Management Explorer).
Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_2\

Read your dispatch instructions and requirements:
1. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read first)
2. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md
3. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_2\DISPATCH.md
4. Existing engine modules in c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\

Investigate and produce an actionable architectural plan for:
- Implementing system-wide hotkeys in PyQt6 on Windows:
  - Alt+S for on-demand capture, Alt+L for live streaming toggle.
  - Using Win32 RegisterHotKey / UnregisterHotKey via QAbstractNativeEventFilter or nativeEvent hook.
  - Processing WM_HOTKEY (0x0312), decoding wParam/lParam, and emitting Qt signals cleanly.
  - Handling conflicts if a hotkey is already occupied.
- Target Window picker and live thumbnail rendering:
  - Interfacing ScreenCaptureEngine.list_windows() with QComboBox.
  - Handling window title formatting, filtering cloaked/tool windows, tracking HWND changes.
  - Live preview thumbnail: low-frequency timer capturing active target and displaying on QLabel/QPixmap without blocking UI.
- Recommend concrete class design and interface signatures for gemini_desktop_screenshare/ui/hotkey_manager.py.

Write your findings and recommendations to:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_2\handoff.md
Update progress.md with your liveness heartbeat. Send a message when finished.
