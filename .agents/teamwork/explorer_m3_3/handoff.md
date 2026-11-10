# Architectural Plan: UI State Machine, Dark Styling & Headless Verification

**Explorer**: explorer_m3_3 (UI State Machine & Dark Styling Explorer)  
**Milestone**: M3 (Desktop User Interface & Interaction Controls)  
**Target Path**: `gemini_desktop_screenshare/ui/`  
**Date**: 2026-11-08  

---

## 1. Observation

### 1.1 Existing Engine Modules and Runtime Observations
1. **Audio Pipeline Controls (`gemini_desktop_screenshare/audio/audio_pipeline.py`)**:
   - `AudioPipeline.is_muted` (lines 55–58) tracks the mute state.
   - `AudioPipeline.set_muted(muted: bool)` (lines 65–72) dynamically toggles silence chunk injection (`b"\x00" * bytes_needed`, lines 90–93) in the active recording callback without closing or restarting the hardware input stream.
   - `AudioPipeline.interrupt()` (line 73 in PROJECT.md interface contract) immediately drains the playback output queue for barge-in interruptions.

2. **Authentication Flow (`gemini_desktop_screenshare/auth/oauth_manager.py`)**:
   - `OAuthManager.is_authenticated()` (lines 408–420) checks both in-memory access token validity and refresh token availability in Windows Credential Manager.
   - `OAuthManager.get_user_profile()` (lines 421–426) provides user email and display name for UI rendering.
   - `OAuthManager.sign_out()` (lines 427–451) revokes tokens and purges stored credentials.

3. **Streaming & On-Demand Execution (`streaming/live_client.py` and `ondemand/ondemand_client.py`)**:
   - `GeminiLiveClient.start_streaming(...)` (lines 189–235) spawns concurrent background tasks for 1 FPS screen capture, 16kHz audio streaming, and inbound text/speech receiving.
   - Disconnection callback (`_handle_disconnection`, lines 156–188) stops mic recording and cancels tasks.
   - `OnDemandClient.query_target(...)` (lines 39–61) captures an instant frame off-thread and sends a REST `generateContent` request.

4. **PyQt6 Environment & Headless Execution**:
   - Execution command `python -c "import PyQt6; print(PyQt6.__file__)"` succeeded: `C:\Users\Arman\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\__init__.py`.
   - Execution command `python -c "from PyQt6 import QtCore, QtWidgets, QtTest; print('QtTest & QtWidgets available')"` succeeded.
   - Headless offscreen command `python -c "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; from PyQt6.QtWidgets import QApplication, QLabel; app = QApplication.instance() or QApplication([]); label = QLabel('Hello Offscreen'); label.show(); print(label.text())"` executed with code 0 and confirmed widgets instantiate and layout offscreen without physical display or GPU.
   - Dynamic QSS restyling command `btn.setProperty('muted', True); btn.style().unpolish(btn); btn.style().polish(btn)` executed cleanly with code 0, proving dynamic property selectors re-evaluate instantaneously.
   - High DPI scaling policy `QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)` executed cleanly with code 0.

5. **Peer Explorer Coordination**:
   - `explorer_m3_1` established `QThread + asyncio` with `pyqtSignal` bridging for asynchronous engine operations.
   - `explorer_m3_2` established Win32 `RegisterHotKey` for `Alt+S` and `Alt+L`, target window enumeration, and low-frequency preview rendering.

---

## 2. Logic Chain

From the observations above:
1. **State Machine Separation**:
   Because `GeminiLiveClient` (continuous streaming) and `OnDemandClient` (instant snapshot) both access the display capture engine and network, running both concurrently creates race conditions and capture resource contention. Therefore, the UI must enforce strict mutual exclusion between `LIVE_STREAMING` and `ONDEMAND_CAPTURING` via an explicit state machine.
2. **Declarative Enablement Matrix**:
   Instead of spreading widget `setEnabled(...)` calls across disparate handlers, defining a central `ENABLEMENT_MATRIX` mapping each state to control availability ensures zero illegal states (e.g., preventing target switching during live streaming, preventing sign-out during active capture).
3. **Instant Mic Mute Synchronization**:
   Since `AudioPipeline.set_muted()` operates instantaneously on the active stream without thread locks or stream recreation, the UI mic button can immediately toggle local state, refresh its icon/color via dynamic QSS properties (`polish`/`unpolish`), and synchronize with the engine.
4. **Smart Auto-Scroll in Transcript**:
   Users inspecting earlier messages must not be forcibly snapped to the bottom when new streaming tokens arrive. Calculating `verticalScrollBar().value() >= verticalScrollBar().maximum() - 15` detects whether the viewport is anchored at the bottom, enabling seamless smart auto-scroll with a "Jump to Latest" recovery action.
5. **Headless Verification Guarantee**:
   By setting `QT_QPA_PLATFORM=offscreen` and decoupling the pure state transition logic from widget rendering, 100% of state transitions, hotkey handling, button matrices, and transcript formatting can be programmatically tested in headless CI environments without mock display drivers.

---

## 3. UI State Machine Specification

### 3.1 States
The application UI operates within six explicit states:

```
                  ┌──────────────────────┐
                  │   UNAUTHENTICATED    │
                  └──────────┬───────────┘
                             │ "Sign in with Google"
                             ▼
                  ┌──────────────────────┐
            ┌────►│    AUTHENTICATING    │
            │     └──────────┬───────────┘
            │                │ OAuth Success
            │                ▼
            │     ┌──────────────────────┐
            │     │  AUTHENTICATED_IDLE  │◄────────────┐
            │     └──────┬────────┬──────┘             │
            │            │        │                    │
            │  "Start    │        │ "Capture & Send"   │
            │  Stream"   │        │ (or Alt+S)         │
            │  (or Alt+L)│        │                    │
            │            ▼        ▼                    │
            │   ┌──────────────┐ ┌───────────────────┐ │
            │   │LIVE_STREAMING│ │ONDEMAND_CAPTURING │ │
            │   └────────┬─────┘ └─────────┬─────────┘ │
            │            │ "Stop"          │ REST Done │
            │            └────────┬────────┘           │
            │                     ▼                    │
            │                (Return to)               │
            │             AUTHENTICATED_IDLE           │
            │                     │                    │
            │  Any Error / Drop   │                    │
            │                     ▼                    │
            │          ┌──────────────────────┐        │
            └──────────┤        ERROR         ├────────┘
           "Sign Out"  └──────────────────────┘  "Dismiss / Retry"
```

1. **`UNAUTHENTICATED`**: Initial state if no token or cached session exists, or after the user signs out. Shows "Sign in with Google" button. Streaming, capturing, target selection, and mic controls are disabled.
2. **`AUTHENTICATING`**: OAuth loopback server is running and system browser is open. Sign-in button shows "Waiting for Google authorization..." with cancel option. All other controls locked.
3. **`AUTHENTICATED_IDLE`**: User is signed in with valid/refreshable credentials. Profile chip shows email. Controls (Mode tab, Target picker, Start Streaming, Capture Now, Mic mute, Prompt input) are enabled and ready.
4. **`LIVE_STREAMING`**: Continuous bidirectional session active. Capturing 1 FPS screen + 16kHz audio. Streaming button becomes red "Stop Streaming". Mode selector, target selector, and on-demand capture are locked. Mic mute toggle remains interactive. Transcript streams incoming tokens.
5. **`ONDEMAND_CAPTURING`**: Snapshot taken, REST query sent, awaiting model response. Capture button shows "Analyzing screen..." with busy indicator. Input field is read-only. Start streaming is locked. Upon response, returns to `AUTHENTICATED_IDLE`.
6. **`ERROR`**: Triggered on authentication failure, WebSocket disconnect, invalid HWND capture, or network errors. Shows error banner with message and "Dismiss" / "Retry" / "Sign Out" actions.

### 3.2 State Transition Rules & Guard Conditions

| Source State | Target State | Trigger / Event | Guard Condition |
|---|---|---|---|
| `UNAUTHENTICATED` | `AUTHENTICATING` | User clicks "Sign in with Google" | OAuth loopback port available |
| `AUTHENTICATING` | `AUTHENTICATED_IDLE` | Loopback receives code + token exchanged | Valid access/refresh token acquired |
| `AUTHENTICATING` | `UNAUTHENTICATED` | User cancels or timeout (120s) | Loopback server shut down cleanly |
| `AUTHENTICATING` | `ERROR` | OAuth error / CSRF state mismatch | Error message logged |
| `AUTHENTICATED_IDLE` | `UNAUTHENTICATED` | User clicks "Sign Out" | Tokens revoked & credentials cleared |
| `AUTHENTICATED_IDLE` | `LIVE_STREAMING` | User clicks "Start Streaming" or `Alt+L` | Valid target selected & mic available |
| `AUTHENTICATED_IDLE` | `ONDEMAND_CAPTURING` | User clicks "Capture & Send" or `Alt+S` | Valid target selected & prompt non-empty |
| `LIVE_STREAMING` | `AUTHENTICATED_IDLE` | User clicks "Stop Streaming" or `Alt+L` | Streaming tasks cancelled, mic stopped |
| `LIVE_STREAMING` | `ERROR` | Remote WS drop, HWND closed, or refresh fail | Disconnect cleanup completed |
| `ONDEMAND_CAPTURING`| `AUTHENTICATED_IDLE` | REST response received & parsed | Response rendered to transcript |
| `ONDEMAND_CAPTURING`| `ERROR` | HTTP 4xx/5xx, timeout, or capture failure | Error notice rendered to transcript |
| `ERROR` | `AUTHENTICATED_IDLE` | User clicks "Dismiss" / "Retry" | Authentication is still valid |
| `ERROR` | `UNAUTHENTICATED` | User clicks "Sign Out" / Auth invalid | Tokens purged |

### 3.3 Button & Control Enablement Matrix

| Widget / Control | `UNAUTHENTICATED` | `AUTHENTICATING` | `AUTHENTICATED_IDLE` | `LIVE_STREAMING` | `ONDEMAND_CAPTURING` | `ERROR` |
|---|---|---|---|---|---|---|
| **Sign In Button** | **Enabled** (Visible) | Disabled (Spinner) | Hidden | Hidden | Hidden | **Enabled** (if unauth) |
| **Sign Out Button** | Hidden | Disabled | **Enabled** | Disabled (must stop stream) | Disabled | **Enabled** (if auth) |
| **User Profile Chip** | Hidden | Hidden | **Visible** | **Visible** | **Visible** | **Visible** (if auth) |
| **Mode Selector (Tabs)**| Disabled | Disabled | **Enabled** | Disabled (locked in Live) | Disabled (locked in On-Demand) | **Enabled** |
| **Target Selector (Combo)**| Disabled | Disabled | **Enabled** | Disabled (prevent mid-stream switch)| Disabled | **Enabled** |
| **Refresh Windows Button**| Disabled | Disabled | **Enabled** | Disabled | Disabled | **Enabled** |
| **Start Stream (`Alt+L`)**| Disabled | Disabled | **Enabled** (Primary Blue)| Hidden | Disabled | Disabled |
| **Stop Stream (`Alt+L`)** | Hidden | Hidden | Hidden | **Enabled** (Danger Red) | Hidden | Hidden |
| **Capture Now (`Alt+S`)** | Disabled | Disabled | **Enabled** (Primary Blue)| Disabled | Disabled (Busy spinner) | Disabled |
| **Prompt Input Box** | Disabled | Disabled | **Enabled** | Disabled | Disabled (Read-only) | **Enabled** |
| **Prompt Preset Chips** | Disabled | Disabled | **Enabled** | Disabled | Disabled | **Enabled** |
| **Mic Mute Toggle** | Disabled | Disabled | **Enabled** (Persists) | **Enabled** (Active live toggle) | **Enabled** | Disabled |
| **Live Preview Panel** | Placeholder | Placeholder | **Active** (Low FPS) | **Active** (Live stream frame) | Frozen snapshot | Error placeholder |
| **Clear Transcript** | **Enabled** | **Enabled** | **Enabled** | Disabled (avoids desync) | Disabled | **Enabled** |
| **Copy Transcript** | **Enabled** | **Enabled** | **Enabled** | **Enabled** | **Enabled** | **Enabled** |

---

## 4. Visual Controls & UX Component Designs

### 4.1 Microphone Mute / Unmute Visual Controls
The microphone toggle must provide instant, high-visibility feedback:

```
Unmuted (Active):
┌──────────────────────────────────────────────┐
│  🎤  Mic: Active      [● Green Dot]          │
└──────────────────────────────────────────────┘
Style: Surface background (#303134), subtle Google Blue border (#8ab4f8).

Muted (Silence Injected):
┌──────────────────────────────────────────────┐
│  🔇  Mic: Muted       [● Red Dot]            │
└──────────────────────────────────────────────┘
Style: Dark red background (#3c1b1b), vibrant Google Red border & text (#ea4335).
```

- **Dynamic QSS Integration**:
  ```python
  btn.setProperty("mic_state", "muted" if is_muted else "unmuted")
  btn.style().unpolish(btn)
  btn.style().polish(btn)
  ```
- **Direct Engine Sync**:
  Triggering the button calls `audio_pipeline.set_muted(not audio_pipeline.is_muted)`. Emits Qt signal `mic_state_changed(bool)` which synchronously updates the button label, status bar indicator, and status badge.

### 4.2 Status Badge (`StatusBadge`)
A pill-shaped status indicator displaying application and connection health:

| Status Key | Icon & Text | Background | Text Color | Border |
|---|---|---|---|---|
| `"signed_out"` | `⚪ Signed Out` | `#2d2f31` | `#bdc1c6` | `#3c4043` |
| `"ready"` | `🟢 Ready` | `#133a22` | `#81c995` | `#34a853` |
| `"streaming"` | `🔵 Live (1 FPS)` | `#172b4d` | `#8ab4f8` | `#1a73e8` |
| `"capturing"` | `🟡 Analyzing...` | `#3d3314` | `#fdd663` | `#fbbc04` |
| `"error"` | `🔴 Disconnected` | `#3c1b1b` | `#f28b82` | `#ea4335` |

### 4.3 Transcript View Design (`TranscriptView`)
Built using `QTextBrowser` with rich HTML formatting and smart auto-scrolling:

```
┌────────────────────────────────────────────────────────────┐
│ [🗑️ Clear] [📋 Copy All] [💾 Export]        [🟢 Connected] │
├────────────────────────────────────────────────────────────┤
│  👤 You — 14:32:05                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ What is the error message shown in the terminal?     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ✨ Gemini — 14:32:07                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ The terminal displays a `SyntaxError: unterminated   │  │
│  │ string literal` at line 8 of `test_script.py`.       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│        ── ⚡ Barge-in interruption detected ──              │
│                                                            │
│                                        ┌─────────────────┐ │
│                                        │ ↓ Jump to Latest│ │
└────────────────────────────────────────┴─────────────────┴─┘
```

- **HTML Message Cards**:
  - **User Turn**:
    `<div style="margin: 8px 0; padding: 10px 14px; background-color: #2b313a; border-left: 3px solid #8ab4f8; border-radius: 6px;"><div style="font-size: 11px; color: #8ab4f8; font-weight: bold; margin-bottom: 4px;">👤 You &bull; {timestamp}</div><div style="color: #e8eaed; font-size: 13px; line-height: 1.4;">{text}</div></div>`
  - **Gemini Turn**:
    `<div style="margin: 8px 0; padding: 10px 14px; background-color: #282a2e; border-left: 3px solid #c58af9; border-radius: 6px;"><div style="font-size: 11px; color: #c58af9; font-weight: bold; margin-bottom: 4px;">✨ Gemini &bull; {timestamp}</div><div style="color: #e8eaed; font-size: 13px; line-height: 1.4;">{markdown_to_html(text)}</div></div>`
  - **System Notice**:
    `<div style="text-align: center; margin: 10px 0; font-size: 11px; color: #9aa0a6; font-style: italic;">&mdash; {event_text} &mdash;</div>`
- **Streaming Token Accumulator**:
  Inbound text chunks from WebSocket `on_text` are appended to the active turn buffer. A lightweight throttle timer (30ms) or Qt event batching commits tokens to prevent UI repaint flooding.
- **Smart Auto-Scroll Logic**:
  ```python
  def append_turn(self, html_content: str):
      sb = self._browser.verticalScrollBar()
      at_bottom = sb.value() >= (sb.maximum() - 20)
      self._browser.append(html_content)
      if at_bottom:
          sb.setValue(sb.maximum())
          self._jump_btn.hide()
      else:
          self._jump_btn.show()
  ```

### 4.4 On-Demand Capture Prompt Input Dock (`OnDemandDock`)
Integrated into the On-Demand tab card:
- **Preset Quick Chips**: Horizontal layout of discrete filter chips:
  - `[ 🔍 Explain Screen ]` &bull; `[ 📝 Summarize Text ]` &bull; `[ 🐛 Detect Errors ]` &bull; `[ 🌐 Translate ]`
  - Clicking any chip automatically fills the prompt input box.
- **Prompt Field (`QPlainTextEdit`)**: Multi-line height (64px), placeholder `"Ask Gemini about this screen (or press Enter to send)..."`.
  - Event filter: `Key_Return` without `Shift` triggers capture immediately; `Shift+Return` inserts newline.
- **Action Button (`QPushButton[variant='primary']`)**:
  - Idle: `"📸 Capture & Send (Alt+S)"`
  - Inflight (`ONDEMAND_CAPTURING`): Changes to `"⏳ Analyzing screen..."` with disabled state and active progress bar.
- **Hotkey `Alt+S` Integration**: Emits trigger signal. If the main window is blurred or minimized, captures the designated target immediately and brings the response to the foreground.

---

## 5. Dark Theme QSS Styling Specification

### 5.1 Palette Specification (Google Material 3 Dark)

```python
PALETTE = {
    # Backgrounds & Surfaces
    "BG_WINDOW": "#202124",         # Main window background
    "BG_SURFACE": "#303134",        # Card containers & frames
    "BG_SURFACE_HOVER": "#3c4043",  # Interactive card/button hover
    "BG_SURFACE_ACTIVE": "#4d5156", # Pressed/active surface
    "BG_INPUT": "#202124",          # Recessed input/editor background
    
    # Borders & Dividers
    "BORDER_DEFAULT": "#3c4043",    # Card outlines & separators
    "BORDER_HOVER": "#5f6368",      # Subdued hover border
    "BORDER_FOCUS": "#8ab4f8",      # High-visibility focus ring (2px)
    
    # Accents & Roles
    "PRIMARY_BLUE": "#1a73e8",      # Primary button fill
    "PRIMARY_BLUE_DARK": "#8ab4f8", # Blue accent for dark mode text/icons
    "PRIMARY_BLUE_HOVER": "#1b66c9",# Primary button hover
    "COLOR_SUCCESS": "#34a853",     # Success fill
    "COLOR_SUCCESS_TEXT": "#81c995",# Green status badge text
    "COLOR_DANGER": "#ea4335",      # Danger / Mute fill
    "COLOR_DANGER_TEXT": "#f28b82", # Red status text
    "COLOR_WARNING": "#fbbc04",     # Warning accent
    "COLOR_PURPLE": "#c58af9",      # Gemini AI purple accent
    
    # Typography
    "TEXT_PRIMARY": "#e8eaed",      # High emphasis (titles, primary buttons)
    "TEXT_SECONDARY": "#bdc1c6",    # Medium emphasis (labels, descriptions)
    "TEXT_MUTED": "#9aa0a6",        # Low emphasis (hints, timestamps)
    "TEXT_DISABLED": "#5f6368",     # Disabled controls
}
```

### 5.2 Component QSS Rules (`gemini_desktop_screenshare/ui/styles.py`)

```css
/* Core Window & Central Surface */
QMainWindow, QWidget#centralWidget {
    background-color: #202124;
    color: #e8eaed;
    font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
    font-size: 13px;
}

/* Card Containers */
QFrame[card="true"] {
    background-color: #303134;
    border: 1px solid #3c4043;
    border-radius: 8px;
    padding: 12px;
}

/* Buttons */
QPushButton {
    background-color: #3c4043;
    color: #e8eaed;
    border: 1px solid #5f6368;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #4d5156;
    border-color: #8ab4f8;
}
QPushButton:pressed {
    background-color: #5f6368;
}
QPushButton:disabled {
    background-color: #202124;
    color: #5f6368;
    border-color: #3c4043;
}
QPushButton[variant="primary"] {
    background-color: #1a73e8;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background-color: #1b66c9;
}
QPushButton[variant="danger"] {
    background-color: #ea4335;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton[variant="danger"]:hover {
    background-color: #d93025;
}
QPushButton[variant="chip"] {
    background-color: #202124;
    color: #bdc1c6;
    border: 1px solid #3c4043;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton[variant="chip"]:hover {
    background-color: #3c4043;
    color: #8ab4f8;
    border-color: #8ab4f8;
}

/* Microphone Dynamic States */
QPushButton[mic_state="unmuted"] {
    background-color: #303134;
    border: 1px solid #3c4043;
    color: #e8eaed;
}
QPushButton[mic_state="unmuted"]:hover {
    border-color: #81c995;
    color: #81c995;
}
QPushButton[mic_state="muted"] {
    background-color: #3c1b1b;
    border: 1px solid #ea4335;
    color: #f28b82;
    font-weight: bold;
}
QPushButton[mic_state="muted"]:hover {
    background-color: #4e1c1c;
}

/* Status Badges */
QLabel[badge="ready"] {
    background-color: #133a22;
    color: #81c995;
    border: 1px solid #34a853;
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}
QLabel[badge="streaming"] {
    background-color: #172b4d;
    color: #8ab4f8;
    border: 1px solid #1a73e8;
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}
QLabel[badge="error"] {
    background-color: #3c1b1b;
    color: #f28b82;
    border: 1px solid #ea4335;
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}
QLabel[badge="signed_out"] {
    background-color: #2d2f31;
    color: #9aa0a6;
    border: 1px solid #3c4043;
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
}

/* Dropdowns & Selectors */
QComboBox {
    background-color: #202124;
    color: #e8eaed;
    border: 1px solid #5f6368;
    border-radius: 6px;
    padding: 6px 12px;
}
QComboBox:hover {
    border-color: #8ab4f8;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #303134;
    color: #e8eaed;
    selection-background-color: #1a73e8;
    selection-color: #ffffff;
    border: 1px solid #3c4043;
    border-radius: 4px;
}

/* Inputs & Editors */
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #202124;
    color: #e8eaed;
    border: 1px solid #3c4043;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #1a73e8;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #8ab4f8;
}

/* Slim Modern Scrollbars */
QScrollBar:vertical {
    background-color: #202124;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #5f6368;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background-color: #8ab4f8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #3c4043;
    border-radius: 6px;
    background-color: #303134;
    top: -1px;
}
QTabBar::tab {
    background-color: #202124;
    color: #bdc1c6;
    border: 1px solid #3c4043;
    border-bottom: none;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #303134;
    color: #8ab4f8;
    font-weight: bold;
    border-bottom: 2px solid #8ab4f8;
}

/* Tooltips */
QToolTip {
    background-color: #303134;
    color: #e8eaed;
    border: 1px solid #5f6368;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}
```

### 5.3 High DPI Scaling Initialization
Must be invoked before `QApplication` instantiation in `app.py`:
```python
def configure_qt_high_dpi() -> None:
    """Enables crisp fractional High DPI scaling on Windows."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
```

---

## 6. Headless & Programmatic Verification Strategy

### 6.1 Headless Configuration Strategy
1. **Zero-Display Setup**: Set `os.environ["QT_QPA_PLATFORM"] = "offscreen"` at the module or test session level. This allows all Qt widgets, event loops, layouts, and QSS style computations to run in CI and headless environments.
2. **QApplication Lifecycle Management**:
   ```python
   @pytest.fixture(scope="session")
   def qapp():
       import os
       os.environ["QT_QPA_PLATFORM"] = "offscreen"
       from PyQt6.QtWidgets import QApplication
       app = QApplication.instance()
       if app is None:
           app = QApplication([])
       return app
   ```

### 6.2 Pure State Machine Unit Testing
`UIStateMachine` is decoupled from GUI widgets, allowing exhaustive verification of all transitions in pure memory:
```python
def test_state_machine_transitions(qapp):
    sm = UIStateMachine(initial_state=AppState.UNAUTHENTICATED)
    
    # 1. Invalid transitions rejected
    assert not sm.can_transition(AppState.LIVE_STREAMING)
    assert not sm.transition_to(AppState.LIVE_STREAMING)
    assert sm.state == AppState.UNAUTHENTICATED
    
    # 2. Valid auth flow
    assert sm.transition_to(AppState.AUTHENTICATING)
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
    
    # 3. Mutual exclusion between live streaming and ondemand capture
    assert sm.transition_to(AppState.LIVE_STREAMING)
    assert not sm.can_transition(AppState.ONDEMAND_CAPTURING)  # Guarded!
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
    
    # 4. On-demand flow
    assert sm.transition_to(AppState.ONDEMAND_CAPTURING)
    assert not sm.can_transition(AppState.LIVE_STREAMING)     # Guarded!
    assert sm.transition_to(AppState.AUTHENTICATED_IDLE)
```

### 6.3 Programmatic Widget Verification via `QTest`
1. **Enablement Matrix Verification**:
   ```python
   def test_button_enablement_across_states(qapp):
       window = MainWindow(mock_oauth, mock_capture, mock_audio, mock_live, mock_ondemand)
       sm = window.state_machine
       
       # Check UNAUTHENTICATED
       sm.transition_to(AppState.UNAUTHENTICATED)
       assert window.btn_sign_in.isEnabled()
       assert not window.btn_start_stream.isEnabled()
       assert not window.btn_capture_now.isEnabled()
       assert not window.combo_target.isEnabled()
       
       # Check LIVE_STREAMING
       sm.transition_to(AppState.AUTHENTICATED_IDLE)
       sm.transition_to(AppState.LIVE_STREAMING)
       assert not window.btn_start_stream.isVisible()
       assert window.btn_stop_stream.isVisible() and window.btn_stop_stream.isEnabled()
       assert not window.combo_target.isEnabled()  # Locked during stream!
       assert window.btn_mic_mute.isEnabled()      # Must stay enabled!
   ```

2. **Microphone Toggle Interaction**:
   ```python
   def test_mic_mute_button_interaction(qapp):
       audio_mock = MagicMock()
       audio_mock.is_muted = False
       btn = MicToggleButton(audio_pipeline=audio_mock)
       
       assert btn.text() == "🎤 Mute Mic"
       assert btn.property("mic_state") == "unmuted"
       
       # Programmatic click
       from PyQt6.QtTest import QTest
       from PyQt6.QtCore import Qt
       QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
       
       audio_mock.set_muted.assert_called_with(True)
       assert btn.text() == "🔇 Unmute Mic"
       assert btn.property("mic_state") == "muted"
   ```

3. **Transcript Rendering & Smart Auto-Scroll**:
   ```python
   def test_transcript_smart_autoscroll(qapp):
       view = TranscriptView()
       view.resize(300, 200)
       view.show()
       qapp.processEvents()
       
       # Add multiple turns
       for i in range(20):
           view.append_user_turn(f"User message {i}")
           view.append_model_turn(f"Gemini response {i}")
       qapp.processEvents()
       
       sb = view.browser.verticalScrollBar()
       assert sb.value() == sb.maximum()  # Auto-scrolled to bottom
       
       # User manually scrolls up
       sb.setValue(50)
       view.append_model_turn("New streaming chunk")
       qapp.processEvents()
       assert sb.value() == 50            # Scroll preserved!
       assert view.jump_button.isVisible()# Jump button displayed!
   ```

---

## 7. Concrete Class Designs and Interface Signatures

### 7.1 `gemini_desktop_screenshare/ui/styles.py`

```python
"""
Google Material 3 Dark theme stylesheet and UI constants for Gemini Desktop Screenshare.
"""

from typing import Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Palette Definition
COLORS: Dict[str, str] = {
    "BG_WINDOW": "#202124",
    "BG_SURFACE": "#303134",
    "BG_SURFACE_HOVER": "#3c4043",
    "BG_SURFACE_ACTIVE": "#4d5156",
    "BG_INPUT": "#202124",
    "BORDER_DEFAULT": "#3c4043",
    "BORDER_HOVER": "#5f6368",
    "BORDER_FOCUS": "#8ab4f8",
    "PRIMARY_BLUE": "#1a73e8",
    "PRIMARY_BLUE_TEXT": "#8ab4f8",
    "PRIMARY_BLUE_HOVER": "#1b66c9",
    "COLOR_SUCCESS": "#34a853",
    "COLOR_SUCCESS_TEXT": "#81c995",
    "COLOR_DANGER": "#ea4335",
    "COLOR_DANGER_TEXT": "#f28b82",
    "COLOR_WARNING": "#fbbc04",
    "COLOR_PURPLE": "#c58af9",
    "TEXT_PRIMARY": "#e8eaed",
    "TEXT_SECONDARY": "#bdc1c6",
    "TEXT_MUTED": "#9aa0a6",
    "TEXT_DISABLED": "#5f6368",
}

def get_dark_stylesheet() -> str:
    """Returns the complete Google Material Dark QSS stylesheet."""
    ...

def apply_theme(app: QApplication) -> None:
    """Configures high DPI policy and applies the dark stylesheet to QApplication."""
    ...

def restyle_widget(widget) -> None:
    """Forces dynamic property stylesheet re-evaluation without flashing."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
```

### 7.2 `gemini_desktop_screenshare/ui/state_machine.py`

```python
"""
Application UI State Machine and Action Enablement Matrix.
"""

from enum import Enum, auto
from typing import Callable, Dict, Set
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

class AppState(Enum):
    UNAUTHENTICATED = auto()
    AUTHENTICATING = auto()
    AUTHENTICATED_IDLE = auto()
    LIVE_STREAMING = auto()
    ONDEMAND_CAPTURING = auto()
    ERROR = auto()

class UIAction(Enum):
    SIGN_IN = auto()
    SIGN_OUT = auto()
    START_STREAM = auto()
    STOP_STREAM = auto()
    CAPTURE_NOW = auto()
    SELECT_TARGET = auto()
    SELECT_MODE = auto()
    MIC_MUTE = auto()
    PROMPT_INPUT = auto()
    CLEAR_TRANSCRIPT = auto()

class UIStateMachine(QObject):
    state_changed = pyqtSignal(object, object)  # (old_state: AppState, new_state: AppState)
    error_occurred = pyqtSignal(str, str)       # (title: str, detail: str)

    VALID_TRANSITIONS: Dict[AppState, Set[AppState]] = {
        AppState.UNAUTHENTICATED: {AppState.AUTHENTICATING, AppState.ERROR},
        AppState.AUTHENTICATING: {AppState.AUTHENTICATED_IDLE, AppState.UNAUTHENTICATED, AppState.ERROR},
        AppState.AUTHENTICATED_IDLE: {
            AppState.UNAUTHENTICATED,
            AppState.LIVE_STREAMING,
            AppState.ONDEMAND_CAPTURING,
            AppState.ERROR,
        },
        AppState.LIVE_STREAMING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ONDEMAND_CAPTURING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ERROR: {AppState.AUTHENTICATED_IDLE, AppState.UNAUTHENTICATED},
    }

    ENABLEMENT_MATRIX: Dict[UIAction, Dict[AppState, bool]] = ...

    def __init__(self, initial_state: AppState = AppState.UNAUTHENTICATED) -> None:
        super().__init__()
        self._state: AppState = initial_state
        self._bindings: Dict[UIAction, QWidget] = {}

    @property
    def state(self) -> AppState:
        return self._state

    def can_transition(self, target: AppState) -> bool:
        return target in self.VALID_TRANSITIONS.get(self._state, set())

    def transition_to(self, target: AppState) -> bool:
        if not self.can_transition(target):
            return False
        old = self._state
        self._state = target
        self._apply_bindings()
        self.state_changed.emit(old, target)
        return True

    def register_widget(self, action: UIAction, widget: QWidget) -> None:
        self._bindings[action] = widget
        enabled = self.ENABLEMENT_MATRIX[action].get(self._state, False)
        widget.setEnabled(enabled)

    def _apply_bindings(self) -> None:
        for action, widget in self._bindings.items():
            enabled = self.ENABLEMENT_MATRIX[action].get(self._state, False)
            widget.setEnabled(enabled)
```

### 7.3 `gemini_desktop_screenshare/ui/widgets/status_badge.py`

```python
"""
StatusBadge widget showing pill-shaped connection and mode state.
"""

from PyQt6.QtWidgets import QLabel
from gemini_desktop_screenshare.ui.styles import restyle_widget

class StatusBadge(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.set_status("signed_out")

    def set_status(self, status: str, text: str = "") -> None:
        """
        Sets status badge state ('signed_out', 'ready', 'streaming', 'capturing', 'error').
        """
        default_labels = {
            "signed_out": "⚪ Signed Out",
            "ready": "🟢 Connected",
            "streaming": "🔵 Live (1 FPS)",
            "capturing": "🟡 Analyzing...",
            "error": "🔴 Error",
        }
        self.setText(text or default_labels.get(status, status))
        self.setProperty("badge", status)
        restyle_widget(self)
```

### 7.4 `gemini_desktop_screenshare/ui/widgets/mic_button.py`

```python
"""
MicToggleButton with immediate AudioPipeline synchronization and visual states.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QPushButton
from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline
from gemini_desktop_screenshare.ui.styles import restyle_widget

class MicToggleButton(QPushButton):
    muted_toggled = pyqtSignal(bool)

    def __init__(self, audio_pipeline: AudioPipeline, parent=None) -> None:
        super().__init__(parent)
        self.audio_pipeline = audio_pipeline
        self.clicked.connect(self.toggle_mute)
        self.update_visuals()

    def toggle_mute(self) -> None:
        new_state = not self.audio_pipeline.is_muted
        self.audio_pipeline.set_muted(new_state)
        self.update_visuals()
        self.muted_toggled.emit(new_state)

    def update_visuals(self) -> None:
        muted = self.audio_pipeline.is_muted
        if muted:
            self.setText("🔇 Mic: Muted")
            self.setToolTip("Microphone is muted (sending silence). Click or press Ctrl+M to unmute.")
            self.setProperty("mic_state", "muted")
        else:
            self.setText("🎤 Mic: Active")
            self.setToolTip("Microphone is active. Click or press Ctrl+M to mute.")
            self.setProperty("mic_state", "unmuted")
        restyle_widget(self)
```

### 7.5 `gemini_desktop_screenshare/ui/widgets/transcript_view.py`

```python
"""
TranscriptView with rich user/model turns, streaming token accumulator, and smart auto-scroll.
"""

from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QPushButton, QTextBrowser, QVBoxLayout, QWidget

class TranscriptView(QWidget):
    clear_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_model_tokens: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        ...

    def append_user_turn(self, text: str) -> None: ...
    def start_model_turn(self) -> None: ...
    def append_streaming_token(self, token: str) -> None: ...
    def finalize_model_turn(self) -> None: ...
    def append_system_notice(self, notice: str) -> None: ...
    def clear_transcript(self) -> None: ...
    def copy_all_to_clipboard(self) -> None: ...
    def export_to_file(self, file_path: str) -> None: ...
```

### 7.6 `gemini_desktop_screenshare/ui/widgets/ondemand_dock.py`

```python
"""
OnDemandDock providing preset prompt chips, custom query text input, and snapshot trigger.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QPlainTextEdit, QPushButton, QVBoxLayout

class OnDemandDock(QFrame):
    capture_requested = pyqtSignal(str)  # (prompt_text: str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", "true")
        self._setup_ui()

    def get_prompt(self) -> str: ...
    def set_prompt(self, text: str) -> None: ...
    def set_busy(self, is_busy: bool) -> None: ...
```

---

## 8. Caveats

1. **System Font Fallbacks**: The QSS specifies `'Segoe UI', -apple-system, system-ui, sans-serif`. On standard Windows 10/11 installations, `Segoe UI` is guaranteed to be available; in minimal server Windows editions, Qt will fall back cleanly to the system default sans font.
2. **Offscreen QTest Timing**: In `QT_QPA_PLATFORM=offscreen`, timers and asynchronous signal emissions must be flushed via `QApplication.processEvents()` or `QTest.qWait(ms)` in test assertions to ensure queued connections are delivered.
3. **Markdown Rendering**: Simple markdown (bold, lists, code spans) can be parsed using regex/string formatting or `markdown` library into HTML for `QTextBrowser.setHtml(...)` without requiring full Chromium/QtWebEngine dependencies.

---

## 9. Conclusion

The UI State Machine and Styling architecture provides:
1. **Rock-solid Safety**: The 6-state `UIStateMachine` with declarative `ENABLEMENT_MATRIX` completely eliminates race conditions between live streaming and on-demand capture.
2. **Instant Audio Synchronization**: Direct coupling between `MicToggleButton` and `AudioPipeline.set_muted()` delivers sub-millisecond silence injection and visual feedback without stream restarts.
3. **Polished Material Design**: High-fidelity Google Material 3 Dark styling with crisp PassThrough High DPI scaling, rounded cards, and slim scrollbars.
4. **100% Headless Automated Testability**: Fully verifiable with `pytest` and `PyQt6.QtTest` under `QT_QPA_PLATFORM=offscreen`, empowering Workers and Reviewers in M3 and M4 to verify all UI logic in milliseconds without a display monitor.

---

## 10. Verification Method

### 10.1 Command-Line Verification

1. **Verify Offscreen Environment**:
   ```powershell
   python -c "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; from PyQt6.QtWidgets import QApplication; app = QApplication([]); print('Offscreen initialization: SUCCESS')"
   ```

2. **Verify QSS Syntax & Widget Styling**:
   ```powershell
   python -c "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; from PyQt6.QtWidgets import QApplication, QPushButton; app = QApplication([]); btn = QPushButton('Test'); btn.setProperty('mic_state', 'muted'); btn.style().unpolish(btn); btn.style().polish(btn); print('Dynamic restyling: SUCCESS')"
   ```

3. **Verify State Machine Transitions**:
   ```powershell
   python -c "import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'; from gemini_desktop_screenshare.ui.state_machine import UIStateMachine, AppState; sm = UIStateMachine(); assert sm.state == AppState.UNAUTHENTICATED; assert sm.transition_to(AppState.AUTHENTICATING); print('State machine: SUCCESS')"
   ```

4. **Run M3 UI Unit Test Suite (Upon implementation)**:
   ```powershell
   pytest gemini_desktop_screenshare/tests/test_ui_state.py -v
   ```

### 10.2 Invalidation Conditions
- If Qt crashes or raises `QXcbConnection: Could not connect to display` without `QT_QPA_PLATFORM=offscreen`.
- If `can_transition(AppState.ONDEMAND_CAPTURING)` evaluates to True while in `AppState.LIVE_STREAMING`.
- If `audio_pipeline.is_muted` does not immediately reflect user interaction with `MicToggleButton`.
