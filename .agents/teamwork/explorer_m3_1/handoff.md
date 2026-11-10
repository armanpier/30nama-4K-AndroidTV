# Milestone 3 Explorer 1 Investigation Report: PyQt6 UI Architecture & Asyncio Integration

**Date**: 2026-11-08T14:38:00Z  
**Author**: teamwork_explorer (PyQt6 Architecture & Asyncio Explorer)  
**Target Path**: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_1\handoff.md`

---

## 1. Observation

### 1.1 Python Environment & Dependency Inspection
Direct verification of available libraries in the workspace Python environment:
```powershell
python -c "
for mod in ['PyQt6', 'qasync', 'mss', 'sounddevice', 'websockets', 'aiohttp', 'PIL', 'win32gui']:
    try:
        __import__(mod)
        print(f'{mod}: available')
    except ImportError as e:
        print(f'{mod}: NOT available ({e})')
"
```
Output:
```
PyQt6: available
qasync: NOT available (No module named 'qasync')
mss: available
sounddevice: available
websockets: available
aiohttp: available
PIL: available
win32gui: available
```
- **Finding**: `PyQt6` is available. `qasync` is **not installed** in the virtual environment. Any solution relying on `qasync` would impose an unnecessary external dependency.

### 1.2 Core Engine Asynchronous and Threading Characteristics
1. **`gemini_desktop_screenshare.auth.oauth_manager.OAuthManager`** (`auth/oauth_manager.py:208-246`):
   - Method `start_loopback_and_login(timeout=120.0)` runs a synchronous polling loop:
     ```python
     start_time = time.time()
     while not server.done and server_thread.is_alive():
         if time.time() - start_time > timeout:
             ...
         time.sleep(0.05)
     ```
   - *Direct impact*: Calling `start_loopback_and_login()` on the PyQt6 main thread freezes the entire GUI and stops window event processing for up to 120 seconds. It **must** be executed on a background worker thread.
2. **`gemini_desktop_screenshare.streaming.live_client.GeminiLiveClient`** (`streaming/live_client.py:189-234`):
   - `start_streaming(target_type, target_id, on_text, on_error, on_disconnect)` creates three background tasks on the running asyncio loop:
     - `self._video_task = asyncio.create_task(self._video_stream_loop(...))` (captures and transmits frames at 1.0 FPS via `asyncio.to_thread`).
     - `self._audio_task = asyncio.create_task(self._audio_stream_loop(...))` (streams 16kHz PCM chunks from an `asyncio.Queue`).
     - `self._receive_task = asyncio.create_task(self._receive_loop(...))` (receives text tokens, 24kHz audio, and barge-in signals).
   - In `_receive_loop` (`streaming/live_client.py:373-375`), barge-in interruption calls `self.audio_pipeline.interrupt()`, which flushes output audio in `<0.1ms`.
   - Text parts are delivered through `on_text(part["text"])` (`streaming/live_client.py:387-388`).
3. **`gemini_desktop_screenshare.audio.audio_pipeline.AudioPipeline`** (`audio/audio_pipeline.py:85-110, 164-198`):
   - PortAudio input and output streams use low-latency C callbacks running on dedicated OS audio threads created by PortAudio/WASAPI.
   - For input: `_in_callback` receives raw microphone chunks and calls `self._record_callback(chunk)`. In `live_client.py:218`, this callback schedules `self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, chunk)`.
   - For output: `_out_callback` pulls PCM chunks from `self._output_queue`.
   - `AudioPipeline.set_muted(bool)` assigns an atomic boolean flag (`audio_pipeline.py:70`) guarded by `self._lock`.
4. **`gemini_desktop_screenshare.ondemand.ondemand_client.OnDemandClient`** (`ondemand/ondemand_client.py:40-61`):
   - `query_target()` captures a frame via `asyncio.to_thread` and performs an async POST using `aiohttp.ClientSession()`.
5. **PyQt6 Cross-Thread Execution & Memory Verification**:
   - Tested QThread execution with `asyncio.run_coroutine_threadsafe`: An `AsyncWorker(QThread)` requires an explicit `threading.Event` to guarantee the loop is active before coroutines are scheduled.
   - Tested cross-thread image passing: `QPixmap` is NOT thread-safe to create or manipulate outside the GUI thread. However, `QImage` is fully re-entrant. Creating `QImage(data, ...).copy()` ensures memory ownership and can be emitted across threads via `pyqtSignal(QImage)` to a main-thread slot that converts it to `QPixmap.fromImage(qimage)`.
   - Tested headless offscreen mode: Running with `os.environ["QT_QPA_PLATFORM"] = "offscreen"` executes PyQt6 without an active display server, confirming support for programmatic CI/test execution.

---

## 2. Logic Chain

### 2.1 Evaluation: `qasync` vs `QThread + asyncio` Loop
1. **`qasync` Evaluation**:
   - `qasync` merges Python's asyncio event loop into the Qt event loop (`QEventLoop`) on the main thread.
   - *Limitation 1 (Dependency)*: `qasync` is not installed in the active environment.
   - *Limitation 2 (UI Responsiveness)*: Because coroutines execute on the main thread, any synchronous compute step (e.g., token serialization, GDI capture handoffs, JSON parsing, crypto) pauses the Qt GUI pipeline.
   - *Limitation 3 (Thread Affinity)*: Running coroutines on the main thread blurs the distinction between UI-safe and non-UI-safe operations, increasing the risk of blocking or crashing the UI.
2. **`QThread + asyncio` Evaluation**:
   - The Qt GUI event loop remains isolated on the Main Thread (Thread 0) running at a smooth 60 FPS.
   - A dedicated `AsyncWorker(QThread)` runs its own dedicated `asyncio` event loop using standard library `asyncio` and `threading`.
   - Communication from the background thread to the GUI thread is mediated by Qt's native `pyqtSignal`. When a signal crosses thread boundaries, Qt automatically uses `Qt.ConnectionType.QueuedConnection`, marshalling arguments into a thread-safe `QEvent` posted to the main thread's event queue.
   - Communication from the GUI thread to the background asyncio thread is handled via `asyncio.run_coroutine_threadsafe(coro, loop)`, which is thread-safe and non-blocking.
   - *Conclusion*: `QThread + asyncio.run_coroutine_threadsafe + pyqtSignal` is the superior, zero-dependency, robust architecture.

### 2.2 Thread-Safe Communication Flow
1. **Streaming Text Tokens**:
   - `live_client.py` receives a text chunk -> calls `on_text(token)` in the background asyncio thread.
   - Worker invokes `self.sig_text_token.emit(token)`.
   - Qt queues this signal into the main GUI thread event loop.
   - `MainWindow.on_text_token(token)` appends the text delta using `QTextCursor.insertText()`, keeping memory usage low and eliminating UI lag.
2. **Audio Status & Barge-in Interruption**:
   - When Gemini detects user speech, it sends `interrupted: true`.
   - `live_client.py` invokes `self.audio_pipeline.interrupt()`.
   - Wrapping `audio_pipeline.interrupt()` allows the worker to emit `sig_interrupted.emit()`.
   - The GUI slot marks the transcript with an `[Interrupted by user]` notice and resets the audio visualization.
3. **Capture Preview Frames**:
   - Background worker captures or downscales a PIL Image -> converts it to `QImage(...).copy()` (to ensure independent buffer ownership) -> emits `sig_preview_frame.emit(qimage)`.
   - Main thread slot converts `QPixmap.fromImage(qimage)` and sets it on `lbl_preview_display`. This completely avoids the fatal "QPixmap outside GUI thread" crash.
4. **OAuth Login Flow**:
   - User clicks "Sign In with Google" -> UI emits `sig_login_requested`.
   - Worker submits `asyncio.to_thread(self.oauth_manager.start_loopback_and_login)` to the background loop.
   - UI displays "Waiting for Google Sign-in in your browser..." with a progress indicator, while remaining fully responsive to user interaction.
   - Upon completion, worker emits `sig_auth_state_changed.emit(True, profile)`.

### 2.3 Window Layout & Widget Hierarchy
The main window must balance dense controls (account status, mode selection, target selection, audio controls, live preview) with a clean transcript view. A two-column master-detail layout is optimal:
- **Left Column (Control Deck, fixed ~380px)**:
  1. *AccountCard*: Google profile avatar, user name, email, Sign In / Sign Out buttons.
  2. *ModeCard*: Radio toggle between "Continuous Live Stream" and "On-Demand Snapshot".
  3. *TargetCard*: Target mode picker (Full Desktop vs Window), display dropdown, window picker dropdown with refresh button.
  4. *ControlsCard*: Primary action button (Start/Stop Streaming or Capture & Ask), Microphone Mute toggle with clear visual badge, global hotkey hints.
  5. *PreviewCard*: Real-time scaled snapshot thumbnail of the active capture area.
- **Right Column (Interaction Deck, flexible width)**:
  1. *Transcript Header*: Conversation title, session badge, "Clear" button.
  2. *Transcript Panel*: Scrollable rich-text widget rendering user prompts, streaming Gemini tokens, and system notices.
  3. *On-Demand Prompt Dock*: Text input and "Send" button for submitting discrete queries.
- **Bottom Bar**: `QStatusBar` with real-time indicators for Auth, WebSocket connection, capture target, and audio rates.

---

## 3. Detailed Architectural Specifications

### 3.1 Signal & Slot Taxonomy

| Signal Name | Emitter | Payload Types | Description | Thread Transition |
|---|---|---|---|---|
| `sig_auth_state_changed` | `AsyncWorker` | `bool, dict` | Auth state (`is_authenticated`) and user profile dict (`email`, `name`, `picture`). | Worker -> Main (Queued) |
| `sig_connection_state_changed` | `AsyncWorker` | `str` | `"DISCONNECTED"`, `"CONNECTING"`, `"CONNECTED"`, `"STREAMING"`, `"STOPPING"`. | Worker -> Main (Queued) |
| `sig_text_token` | `AsyncWorker` | `str` | Text token delta received from Gemini Live WebSocket. | Worker -> Main (Queued) |
| `sig_interrupted` | `AsyncWorker` | (none) | Barge-in interruption triggered; output audio queue purged. | Worker -> Main (Queued) |
| `sig_turn_complete` | `AsyncWorker` | (none) | Gemini model turn completed (`turnComplete: true`). | Worker -> Main (Queued) |
| `sig_preview_frame` | `AsyncWorker` | `QImage` | Downscaled frame buffer ready for `QPixmap.fromImage()`. | Worker -> Main (Queued) |
| `sig_ondemand_result` | `AsyncWorker` | `str` | Full synthesized response text from on-demand multimodal query. | Worker -> Main (Queued) |
| `sig_windows_enumerated` | `AsyncWorker` | `list` | List of dicts `[{"hwnd": int, "title": str, "rect": tuple, ...}]`. | Worker -> Main (Queued) |
| `sig_error` | `AsyncWorker` | `str` | Error description for status banner or user dialog. | Worker -> Main (Queued) |

---

### 3.2 Visual Wireframe & Widget Tree Hierarchy

```
+---------------------------------------------------------------------------------------------------+
|  Gemini Desktop Screenshare                             [ ● Live Streaming ] [ _ ] [ □ ] [ X ]    |
+-------------------------------------------------------+-------------------------------------------+
|  LEFT CONTROL DECK (Fixed 380px)                      |  RIGHT INTERACTION DECK (Expanding)       |
|                                                       |                                           |
|  [ AccountCard ]                                      |  Conversation & Live Transcript   [Clear] |
|  +-------------------------------------------------+  |  +-------------------------------------+  |
|  | [Avatar] John Doe (john.doe@gmail.com)          |  |  | [14:02:11] Connected to Gemini Live  |  |
|  | [ Sign Out ]             [ Refresh Token ]      |  |  |                                     |  |
|  +-------------------------------------------------+  |  | [User]: What is in this code file?   |  |
|                                                       |  |                                     |  |
|  [ ModeCard ]                                         |  | [Gemini]: In this file, you have    |  |
|  +-------------------------------------------------+  |  | an AsyncWorker QThread coordinating |  |
|  | (o) Continuous Live Stream (1 FPS + 16kHz Audio)|  |  | the background asyncio event loop...|  |
|  | ( ) On-Demand Snapshot Query                    |  |  |                                     |  |
|  +-------------------------------------------------+  |  | [Interrupted by user speech]        |  |
|                                                       |  |                                     |  |
|  [ TargetCard ]                                       |  |                                     |  |
|  +-------------------------------------------------+  |  |                                     |  |
|  | Target: [ Application Window               v ]  |  |  |                                     |  |
|  | Window: [ Visual Studio Code - app.py      v ]  |  |  |                                     |  |
|  |         [ Refresh Windows (↻) ]                 |  |  |                                     |  |
|  +-------------------------------------------------+  |  |                                     |  |
|                                                       |  |                                     |  |
|  [ ControlsCard ]                                     |  |                                     |  |
|  +-------------------------------------------------+  |  |                                     |  |
|  | [ ■ STOP STREAMING ] (Alt+L)                    |  |  |                                     |  |
|  | [ 🎤 Microphone: ACTIVE (Unmuted) ]             |  |  +-------------------------------------+  |
|  +-------------------------------------------------+  |                                           |
|                                                       |  [ On-Demand Prompt Dock ]                |
|  [ PreviewCard ]                                      |  +-------------------------------------+  |
|  +-------------------------------------------------+  |  | Ask Gemini: [What is this window?]  |  |
|  | [ Scaled 320x180 Live Capture Thumbnail       ] |  |  | [ Send Prompt (Enter) ]             |  |
|  |                                                 |  |  +-------------------------------------+  |
|  +-------------------------------------------------+  |                                           |
+-------------------------------------------------------+-------------------------------------------+
| Status: Connected | Target: HWND 0x00120F4 | Audio: 16kHz In / 24kHz Out | Token: Valid (54m left) |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Concrete Class Design & Interface Signatures

### 4.1 `gemini_desktop_screenshare/app.py`
The application orchestrator initializes Qt, sets up DPI scaling, spawns the `AsyncWorker(QThread)` with an isolated asyncio event loop, wires signals and slots to `MainWindow`, and provides clean shutdown handling.

```python
"""
Main application entry point for Gemini Desktop Screenshare.
Initializes High-DPI Qt runtime, manages the AsyncWorker QThread, and coordinates
lifecycles between PyQt6 and background asyncio services.
"""

import asyncio
import logging
import os
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

from PIL import Image
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline
from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.config import AppConfig, load_config
from gemini_desktop_screenshare.ondemand.ondemand_client import OnDemandClient
from gemini_desktop_screenshare.streaming.live_client import GeminiLiveClient
from gemini_desktop_screenshare.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class AsyncWorker(QThread):
    """
    Dedicated background worker thread running an independent asyncio event loop.
    Coordinates OAuth, screen capture, Gemini Live WebSocket, and OnDemand REST queries.
    All communication with the PyQt6 GUI is mediated via thread-safe pyqtSignal events.
    """

    # Signals emitted to PyQt6 Main Thread
    sig_auth_state_changed = pyqtSignal(bool, dict)      # (is_authenticated, user_profile)
    sig_connection_state_changed = pyqtSignal(str)       # Connection state string
    sig_text_token = pyqtSignal(str)                     # Streamed text token delta
    sig_interrupted = pyqtSignal()                       # Barge-in interruption notification
    sig_turn_complete = pyqtSignal()                     # Model turn completed
    sig_preview_frame = pyqtSignal(QImage)               # Captured preview thumbnail
    sig_ondemand_result = pyqtSignal(str)                # On-demand response text
    sig_windows_enumerated = pyqtSignal(list)            # List of window metadata dicts
    sig_error = pyqtSignal(str)                          # Error notification message

    def __init__(
        self,
        config: AppConfig,
        oauth_manager: OAuthManager,
        capture_engine: ScreenCaptureEngine,
        audio_pipeline: AudioPipeline,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.oauth_manager = oauth_manager
        self.capture_engine = capture_engine
        self.audio_pipeline = audio_pipeline

        self.live_client: Optional[GeminiLiveClient] = None
        self.ondemand_client: Optional[OnDemandClient] = None

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_ready = threading.Event()
        self._is_running = True

        # Hook barge-in interruption in audio pipeline
        self._orig_interrupt = self.audio_pipeline.interrupt
        self.audio_pipeline.interrupt = self._hooked_interrupt

    def _hooked_interrupt(self) -> float:
        """Hooks audio interruption to emit sig_interrupted while executing immediate purge."""
        elapsed = self._orig_interrupt()
        self.sig_interrupted.emit()
        return elapsed

    def run(self) -> None:
        """Initializes and runs the background asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Initialize clients bound to this loop
        self.live_client = GeminiLiveClient(
            oauth_manager=self.oauth_manager,
            capture_engine=self.capture_engine,
            audio_pipeline=self.audio_pipeline,
            host=self.config.live_ws_url,
            model=self.config.model,
        )
        self.ondemand_client = OnDemandClient(
            oauth_manager=self.oauth_manager,
            capture_engine=self.capture_engine,
            rest_host=self.config.rest_url,
            model=self.config.model,
        )

        self._loop_ready.set()
        logger.info("AsyncWorker event loop started.")

        try:
            self._loop.run_forever()
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.close()
            logger.info("AsyncWorker event loop closed.")

    def submit_coro(self, coro: Any) -> Any:
        """Schedules a coroutine thread-safely onto the background asyncio loop."""
        self._loop_ready.wait(timeout=5.0)
        if self._loop is None or not self._loop.is_running():
            raise RuntimeError("AsyncWorker event loop is not running.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # --------------------------------------------------------------------------
    # Public Controller Methods (Callable from PyQt6 GUI Thread)
    # --------------------------------------------------------------------------

    def check_initial_auth(self) -> None:
        """Verifies cached credentials on startup and emits current auth status."""
        is_auth = self.oauth_manager.is_authenticated()
        profile = self.oauth_manager.get_user_profile() if is_auth else {}
        self.sig_auth_state_changed.emit(is_auth, profile)

    def request_login(self, timeout: float = 120.0) -> None:
        """Launches the OAuth 2.0 PKCE loopback browser login in a thread."""
        async def _login_task():
            self.sig_connection_state_changed.emit("AUTHENTICATING")
            try:
                session = await asyncio.to_thread(self.oauth_manager.start_loopback_and_login, timeout)
                profile = session.get("user_profile", {})
                self.sig_auth_state_changed.emit(True, profile)
                self.sig_connection_state_changed.emit("READY")
            except Exception as e:
                logger.error("OAuth login failed: %s", e)
                self.sig_auth_state_changed.emit(False, {})
                self.sig_connection_state_changed.emit("DISCONNECTED")
                self.sig_error.emit(f"Sign-in failed: {e}")

        self.submit_coro(_login_task())

    def request_signout(self) -> None:
        """Signs the user out and clears stored tokens."""
        async def _signout_task():
            if self.live_client and self.live_client.is_streaming:
                await self.live_client.stop_streaming()
            await asyncio.to_thread(self.oauth_manager.sign_out)
            self.sig_auth_state_changed.emit(False, {})
            self.sig_connection_state_changed.emit("DISCONNECTED")

        self.submit_coro(_signout_task())

    def request_refresh_token(self) -> None:
        """Refreshes the OAuth access token proactively."""
        async def _refresh_task():
            try:
                await asyncio.to_thread(self.oauth_manager.refresh_access_token)
                profile = self.oauth_manager.get_user_profile()
                self.sig_auth_state_changed.emit(True, profile)
            except Exception as e:
                self.sig_error.emit(f"Token refresh failed: {e}")

        self.submit_coro(_refresh_task())

    def request_refresh_windows(self) -> None:
        """Enumerates active windows off the main thread."""
        async def _enum_task():
            try:
                windows = await asyncio.to_thread(self.capture_engine.list_windows)
                self.sig_windows_enumerated.emit(windows)
            except Exception as e:
                logger.warning("Failed to enumerate windows: %s", e)

        self.submit_coro(_enum_task())

    def start_live_streaming(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        voice_name: str = "Aoede",
        system_instruction: str = "",
    ) -> None:
        """Connects WebSocket and starts continuous 1 FPS video + 16kHz audio streaming."""
        async def _stream_task():
            self.sig_connection_state_changed.emit("CONNECTING")
            try:
                if not self.live_client.is_connected:
                    await self.live_client.connect(voice_name=voice_name, system_instruction=system_instruction)

                def _on_text(token: str) -> None:
                    self.sig_text_token.emit(token)

                def _on_err(err_msg: str) -> None:
                    self.sig_error.emit(err_msg)

                def _on_disc() -> None:
                    self.sig_connection_state_changed.emit("DISCONNECTED")

                await self.live_client.start_streaming(
                    target_type=target_type,
                    target_id=target_id,
                    on_text=_on_text,
                    on_error=_on_err,
                    on_disconnect=_on_disc,
                )
                self.sig_connection_state_changed.emit("STREAMING")
            except Exception as e:
                logger.error("Failed to start live streaming: %s", e)
                self.sig_connection_state_changed.emit("DISCONNECTED")
                self.sig_error.emit(f"Failed to start streaming: {e}")

        self.submit_coro(_stream_task())

    def stop_live_streaming(self) -> None:
        """Stops continuous streaming loops and pauses microphone recording."""
        async def _stop_task():
            self.sig_connection_state_changed.emit("STOPPING")
            if self.live_client:
                await self.live_client.stop_streaming()
            self.sig_connection_state_changed.emit("READY")

        self.submit_coro(_stop_task())

    def query_ondemand(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        prompt: str = "Analyze this screen and describe what you observe.",
    ) -> None:
        """Captures an instant snapshot and queries Gemini REST API."""
        async def _ondemand_task():
            self.sig_connection_state_changed.emit("CAPTURING")
            try:
                result_text = await self.ondemand_client.query_target(
                    target_type=target_type,
                    target_id=target_id,
                    prompt=prompt,
                )
                self.sig_ondemand_result.emit(result_text)
                self.sig_connection_state_changed.emit("READY")
            except Exception as e:
                logger.error("On-demand query failed: %s", e)
                self.sig_connection_state_changed.emit("READY")
                self.sig_error.emit(f"On-demand capture failed: {e}")

        self.submit_coro(_ondemand_task())

    def capture_preview_frame(self, target_type: str, target_id: Any) -> None:
        """Captures a single downscaled frame for preview display in the GUI."""
        async def _preview_task():
            try:
                pil_img = await asyncio.to_thread(
                    self.capture_engine.capture_frame, target_type, target_id
                )
                # Resize for thumbnail preview
                pil_img.thumbnail((360, 240), Image.Resampling.LANCZOS)
                rgb_img = pil_img.convert("RGB")
                data = rgb_img.tobytes("raw", "RGB")
                # Construct owned QImage
                qimg = QImage(
                    data, rgb_img.width, rgb_img.height, rgb_img.width * 3, QImage.Format.Format_RGB888
                ).copy()
                self.sig_preview_frame.emit(qimg)
            except Exception as e:
                logger.debug("Preview capture skipped: %s", e)

        self.submit_coro(_preview_task())

    def set_mic_muted(self, muted: bool) -> None:
        """Toggles microphone mute state thread-safely."""
        self.audio_pipeline.set_muted(muted)

    def stop(self) -> None:
        """Shuts down the background thread cleanly."""
        self._is_running = False
        if self._loop and self._loop.is_running():
            # Disconnect live client if open
            if self.live_client and self.live_client.is_connected:
                asyncio.run_coroutine_threadsafe(self.live_client.disconnect(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(5000)


def main() -> int:
    """Application entry point configuring High-DPI, starting QThread, and launching MainWindow."""
    # Configure High-DPI Awareness
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Gemini Desktop Screenshare")
    app.setOrganizationName("GeminiDesktop")

    config = load_config()
    oauth_manager = OAuthManager(config=config)
    capture_engine = ScreenCaptureEngine()
    audio_pipeline = AudioPipeline(
        input_rate=config.input_sample_rate,
        output_rate=config.output_sample_rate,
    )

    worker = AsyncWorker(
        config=config,
        oauth_manager=oauth_manager,
        capture_engine=capture_engine,
        audio_pipeline=audio_pipeline,
    )
    worker.start()

    window = MainWindow(worker=worker, config=config)
    window.show()

    # Initial state checks
    worker.check_initial_auth()
    worker.request_refresh_windows()

    def on_quit():
        window.cleanup()
        worker.stop()
        audio_pipeline.close()
        capture_engine.close()

    app.aboutToQuit.connect(on_quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

---

### 4.2 `gemini_desktop_screenshare/ui/main_window.py`
The primary window provides modern card-based deck controls, thread-safe signal bindings, a rich markdown/HTML conversation transcript, responsive target pickers, and live thumbnail preview updates.

```python
"""
PyQt6 Main Window for Gemini Desktop Screenshare.
Implements dark-mode card deck layout, Google account management, target selection,
preview updates, streaming transcript rendering, and session control actions.
"""

import html
import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QFont, QIcon, QImage, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget
from gemini_desktop_screenshare.config import AppConfig

logger = logging.getLogger(__name__)


class CardFrame(QFrame):
    """Reusable styled surface card with rounded corners and subtle border."""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setStyleSheet("""
            #CardFrame {
                background-color: #292a2d;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(8)

        if title:
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet("color: #9aa0a6; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
            self.layout.addWidget(lbl_title)


class MainWindow(QMainWindow):
    """
    Main Application Window for Gemini Desktop Screenshare.
    Coordinates UI widgets and connects to AsyncWorker via Qt signals.
    """

    def __init__(self, worker: Any, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.worker = worker
        self.config = config

        self.is_authenticated = False
        self.is_streaming = False
        self.is_muted = False
        self.current_mode = "LIVE"  # "LIVE" or "ONDEMAND"
        self.active_target_type = CaptureTarget.FULL_SCREEN
        self.active_target_id: Any = 0

        self.setWindowTitle("Gemini Desktop Screenshare")
        self.setMinimumSize(1024, 720)
        self.resize(1120, 800)

        self._init_ui()
        self._connect_signals()
        self._init_preview_timer()

    def _init_ui(self) -> None:
        """Builds the main window layout hierarchy."""
        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: #202124; color: #e8eaed;")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. Header Bar
        # ----------------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        lbl_app_title = QLabel("Gemini Desktop Screenshare")
        lbl_app_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_bar.addWidget(lbl_app_title)

        header_bar.addStretch()

        self.lbl_status_pill = QLabel("● Disconnected")
        self.lbl_status_pill.setStyleSheet("""
            background-color: #3c4043;
            color: #bdc1c6;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        """)
        header_bar.addWidget(self.lbl_status_pill)
        main_layout.addLayout(header_bar)

        # ----------------------------------------------------------------------
        # 2. Main Content Splitter (Left Controls Deck, Right Transcript Deck)
        # ----------------------------------------------------------------------
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(8)
        content_splitter.setStyleSheet("QSplitter::handle { background: #303134; }")
        main_layout.addWidget(content_splitter, 1)

        # Left Deck (Scrollable Container)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFixedWidth(380)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(12)

        # Left Cards
        self._build_account_card(left_layout)
        self._build_mode_card(left_layout)
        self._build_target_card(left_layout)
        self._build_controls_card(left_layout)
        self._build_preview_card(left_layout)
        left_layout.addStretch()

        scroll_area.setWidget(left_container)
        content_splitter.addWidget(scroll_area)

        # Right Deck (Conversation & Transcript)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)
        self._build_transcript_deck(right_layout)

        content_splitter.addWidget(right_container)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)

        # ----------------------------------------------------------------------
        # 3. Status Bar
        # ----------------------------------------------------------------------
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: #171717; color: #9aa0a6; font-size: 11px;")
        self.setStatusBar(self.status_bar)

        self.sb_auth = QLabel("Auth: Checking...")
        self.sb_target = QLabel("Target: Full Desktop")
        self.sb_audio = QLabel("Audio: 16kHz In / 24kHz Out")
        self.status_bar.addWidget(self.sb_auth, 1)
        self.status_bar.addWidget(self.sb_target, 2)
        self.status_bar.addWidget(self.sb_audio, 1)

    # --------------------------------------------------------------------------
    # Subcomponent Card Builders
    # --------------------------------------------------------------------------

    def _build_account_card(self, parent_layout: QVBoxLayout) -> None:
        """Constructs the Google Account card."""
        self.card_account = CardFrame(title="Google Account")

        self.lbl_user_name = QLabel("Not Signed In")
        self.lbl_user_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #e8eaed;")
        self.card_account.layout.addWidget(self.lbl_user_name)

        self.lbl_user_email = QLabel("Sign in to connect to Gemini Live API")
        self.lbl_user_email.setStyleSheet("font-size: 12px; color: #9aa0a6;")
        self.card_account.layout.addWidget(self.lbl_user_email)

        # Sign in / Sign out buttons
        btn_box = QHBoxLayout()
        self.btn_signin = QPushButton("Sign In with Google")
        self.btn_signin.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: #ffffff; font-weight: bold;
                padding: 6px 14px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #1b66ca; }
        """)
        self.btn_signin.clicked.connect(self._on_signin_clicked)
        btn_box.addWidget(self.btn_signin)

        self.btn_signout = QPushButton("Sign Out")
        self.btn_signout.setStyleSheet("""
            QPushButton {
                background-color: #3c4043; color: #e8eaed;
                padding: 6px 12px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #5f6368; }
        """)
        self.btn_signout.clicked.connect(self._on_signout_clicked)
        self.btn_signout.setVisible(False)
        btn_box.addWidget(self.btn_signout)

        self.btn_refresh_token = QPushButton("↻ Refresh")
        self.btn_refresh_token.setToolTip("Proactively refresh Google OAuth access token")
        self.btn_refresh_token.setStyleSheet("""
            QPushButton {
                background-color: #3c4043; color: #e8eaed;
                padding: 6px 10px; border-radius: 4px; border: none;
            }
        """)
        self.btn_refresh_token.clicked.connect(self._on_refresh_token_clicked)
        self.btn_refresh_token.setVisible(False)
        btn_box.addWidget(self.btn_refresh_token)

        self.card_account.layout.addLayout(btn_box)
        parent_layout.addWidget(self.card_account)

    def _build_mode_card(self, parent_layout: QVBoxLayout) -> None:
        """Constructs the interaction mode selector card."""
        card_mode = CardFrame(title="Interaction Mode")

        self.mode_group = QButtonGroup(self)
        self.rb_live = QRadioButton("Continuous Live Streaming")
        self.rb_live.setToolTip("Streams 1 FPS screen frames and bidirectional microphone/speaker audio")
        self.rb_live.setChecked(True)
        self.mode_group.addButton(self.rb_live)
        card_mode.layout.addWidget(self.rb_live)

        self.rb_ondemand = QRadioButton("On-Demand Screen Capture")
        self.rb_ondemand.setToolTip("Captures an instant snapshot on button trigger and sends a custom query")
        self.mode_group.addButton(self.rb_ondemand)
        card_mode.layout.addWidget(self.rb_ondemand)

        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        parent_layout.addWidget(card_mode)

    def _build_target_card(self, parent_layout: QVBoxLayout) -> None:
        """Constructs the capture target selector card."""
        card_target = CardFrame(title="Capture Target")

        self.cb_target_type = QComboBox()
        self.cb_target_type.addItems(["Full Desktop (All Displays)", "Application Window"])
        self.cb_target_type.currentIndexChanged.connect(self._on_target_type_changed)
        card_target.layout.addWidget(self.cb_target_type)

        # Window selection combo & refresh button
        self.window_picker_row = QWidget()
        win_layout = QHBoxLayout(self.window_picker_row)
        win_layout.setContentsMargins(0, 0, 0, 0)
        win_layout.setSpacing(6)

        self.cb_windows = QComboBox()
        self.cb_windows.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cb_windows.currentIndexChanged.connect(self._on_window_selected)
        win_layout.addWidget(self.cb_windows)

        self.btn_refresh_wins = QPushButton("↻")
        self.btn_refresh_wins.setToolTip("Refresh active application windows")
        self.btn_refresh_wins.setFixedWidth(32)
        self.btn_refresh_wins.clicked.connect(self._on_refresh_windows_clicked)
        win_layout.addWidget(self.btn_refresh_wins)

        self.window_picker_row.setVisible(False)
        card_target.layout.addWidget(self.window_picker_row)

        parent_layout.addWidget(card_target)

    def _build_controls_card(self, parent_layout: QVBoxLayout) -> None:
        """Constructs session control buttons."""
        card_controls = CardFrame(title="Session Controls")

        self.btn_primary_action = QPushButton("Start Live Streaming")
        self.btn_primary_action.setFixedHeight(44)
        self.btn_primary_action.setStyleSheet("""
            QPushButton {
                background-color: #34a853; color: #ffffff; font-weight: bold; font-size: 14px;
                border-radius: 6px; border: none;
            }
            QPushButton:hover { background-color: #2d9247; }
            QPushButton:disabled { background-color: #3c4043; color: #70757a; }
        """)
        self.btn_primary_action.setEnabled(False)  # Requires auth
        self.btn_primary_action.clicked.connect(self._on_primary_action_clicked)
        card_controls.layout.addWidget(self.btn_primary_action)

        self.btn_mic_mute = QPushButton("🎤 Microphone: Active")
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.setFixedHeight(36)
        self.btn_mic_mute.setStyleSheet("""
            QPushButton {
                background-color: #3c4043; color: #e8eaed; font-weight: 500;
                border-radius: 4px; border: none;
            }
            QPushButton:checked {
                background-color: #c5221f; color: #ffffff;
            }
        """)
        self.btn_mic_mute.toggled.connect(self._on_mic_mute_toggled)
        card_controls.layout.addWidget(self.btn_mic_mute)

        lbl_hotkeys = QLabel("Hotkeys: Alt+L (Live Toggle) | Alt+S (Capture Snapshot)")
        lbl_hotkeys.setStyleSheet("color: #70757a; font-size: 11px; text-align: center;")
        lbl_hotkeys.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_controls.layout.addWidget(lbl_hotkeys)

        parent_layout.addWidget(card_controls)

    def _build_preview_card(self, parent_layout: QVBoxLayout) -> None:
        """Constructs the live preview thumbnail card."""
        card_preview = CardFrame(title="Live Target Preview")

        self.lbl_preview = QLabel("Preview will appear here")
        self.lbl_preview.setMinimumSize(320, 180)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("""
            background-color: #171717;
            border: 1px dashed #3c4043;
            border-radius: 4px;
            color: #70757a;
            font-size: 12px;
        """)
        card_preview.layout.addWidget(self.lbl_preview)
        parent_layout.addWidget(card_preview)

    def _build_transcript_deck(self, parent_layout: QVBoxLayout) -> None:
        """Constructs the right transcript area and on-demand prompt input."""
        header_row = QHBoxLayout()
        lbl_deck_title = QLabel("Conversation & Live Transcript")
        lbl_deck_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e8eaed;")
        header_row.addWidget(lbl_deck_title)

        header_row.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #303134; color: #9aa0a6; border: 1px solid #3c4043;
                border-radius: 4px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #3c4043; color: #e8eaed; }
        """)
        btn_clear.clicked.connect(self._on_clear_transcript_clicked)
        header_row.addWidget(btn_clear)
        parent_layout.addLayout(header_row)

        # Transcript display
        self.txt_transcript = QTextBrowser()
        self.txt_transcript.setReadOnly(True)
        self.txt_transcript.setOpenExternalLinks(True)
        self.txt_transcript.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1f20;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 12px;
                color: #e8eaed;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        parent_layout.addWidget(self.txt_transcript, 1)

        # On-Demand Prompt Input Box (visible in On-Demand Mode)
        self.dock_prompt = QFrame()
        self.dock_prompt.setStyleSheet("""
            QFrame {
                background-color: #292a2d;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        dock_layout = QHBoxLayout(self.dock_prompt)
        dock_layout.setContentsMargins(8, 4, 8, 4)
        dock_layout.setSpacing(8)

        self.txt_prompt_input = QLineEdit()
        self.txt_prompt_input.setPlaceholderText("Ask Gemini about your screen (e.g. 'Summarize this window')...")
        self.txt_prompt_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f20; color: #ffffff; border: 1px solid #3c4043;
                border-radius: 4px; padding: 8px 12px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #1a73e8; }
        """)
        self.txt_prompt_input.returnPressed.connect(self._on_send_prompt_clicked)
        dock_layout.addWidget(self.txt_prompt_input, 1)

        self.btn_send_prompt = QPushButton("Send")
        self.btn_send_prompt.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: #ffffff; font-weight: bold;
                padding: 8px 16px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #1b66ca; }
        """)
        self.btn_send_prompt.clicked.connect(self._on_send_prompt_clicked)
        dock_layout.addWidget(self.btn_send_prompt)

        self.dock_prompt.setVisible(False)  # Hidden by default in Live mode
        parent_layout.addWidget(self.dock_prompt)

    # --------------------------------------------------------------------------
    # Signal Connections
    # --------------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Binds AsyncWorker signals to main window slots."""
        self.worker.sig_auth_state_changed.connect(self.on_auth_state_changed)
        self.worker.sig_connection_state_changed.connect(self.on_connection_state_changed)
        self.worker.sig_text_token.connect(self.on_text_token_received)
        self.worker.sig_interrupted.connect(self.on_interrupted_received)
        self.worker.sig_turn_complete.connect(self.on_turn_complete_received)
        self.worker.sig_preview_frame.connect(self.on_preview_frame_received)
        self.worker.sig_ondemand_result.connect(self.on_ondemand_result_received)
        self.worker.sig_windows_enumerated.connect(self.on_windows_enumerated_received)
        self.worker.sig_error.connect(self.on_error_received)

    def _init_preview_timer(self) -> None:
        """Starts a low-rate preview timer (1.5s interval) to refresh thumbnail when idle."""
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(1500)
        self.preview_timer.timeout.connect(self._on_preview_timer_tick)
        self.preview_timer.start()

    # --------------------------------------------------------------------------
    # Slots (Handling Incoming Worker Signals)
    # --------------------------------------------------------------------------

    @pyqtSlot(bool, dict)
    def on_auth_state_changed(self, is_authenticated: bool, profile: dict) -> None:
        """Updates user profile display and button states."""
        self.is_authenticated = is_authenticated
        if is_authenticated:
            name = profile.get("name", "Google User")
            email = profile.get("email", "Authenticated")
            self.lbl_user_name.setText(name)
            self.lbl_user_email.setText(email)
            self.btn_signin.setVisible(False)
            self.btn_signout.setVisible(True)
            self.btn_refresh_token.setVisible(True)
            self.btn_primary_action.setEnabled(True)
            self.sb_auth.setText(f"Auth: {email}")
        else:
            self.lbl_user_name.setText("Not Signed In")
            self.lbl_user_email.setText("Sign in to connect to Gemini Live API")
            self.btn_signin.setVisible(True)
            self.btn_signout.setVisible(False)
            self.btn_refresh_token.setVisible(False)
            self.btn_primary_action.setEnabled(False)
            self.sb_auth.setText("Auth: Not Signed In")

    @pyqtSlot(str)
    def on_connection_state_changed(self, state: str) -> None:
        """Updates the status pill and action button state."""
        logger.info("Connection state: %s", state)
        if state == "STREAMING":
            self.is_streaming = True
            self.lbl_status_pill.setText("● Live Streaming")
            self.lbl_status_pill.setStyleSheet("background-color: #137333; color: #e6f4ea; padding: 4px 12px; border-radius: 12px; font-weight: bold;")
            self.btn_primary_action.setText("Stop Live Streaming")
            self.btn_primary_action.setStyleSheet("background-color: #d93025; color: #ffffff; font-weight: bold; border-radius: 6px; border: none;")
            self.btn_primary_action.setEnabled(True)
            self.rb_live.setEnabled(False)
            self.rb_ondemand.setEnabled(False)
            self.cb_target_type.setEnabled(False)
            self.cb_windows.setEnabled(False)
        elif state == "CONNECTING":
            self.lbl_status_pill.setText("● Connecting...")
            self.lbl_status_pill.setStyleSheet("background-color: #e37400; color: #fef7e0; padding: 4px 12px; border-radius: 12px;")
            self.btn_primary_action.setEnabled(False)
        elif state == "CAPTURING":
            self.lbl_status_pill.setText("● Analyzing Screen...")
            self.lbl_status_pill.setStyleSheet("background-color: #1a73e8; color: #ffffff; padding: 4px 12px; border-radius: 12px;")
            self.btn_primary_action.setEnabled(False)
        else:  # READY / DISCONNECTED
            self.is_streaming = False
            self.lbl_status_pill.setText("● Ready" if self.is_authenticated else "● Disconnected")
            self.lbl_status_pill.setStyleSheet("background-color: #3c4043; color: #bdc1c6; padding: 4px 12px; border-radius: 12px;")
            self._update_primary_button_for_mode()
            self.btn_primary_action.setEnabled(self.is_authenticated)
            self.rb_live.setEnabled(True)
            self.rb_ondemand.setEnabled(True)
            self.cb_target_type.setEnabled(True)
            self.cb_windows.setEnabled(True)

    @pyqtSlot(str)
    def on_text_token_received(self, token: str) -> None:
        """Appends streaming text tokens cleanly with automatic scroll locking."""
        cursor = self.txt_transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.txt_transcript.setTextCursor(cursor)
        self.txt_transcript.ensureCursorVisible()

    @pyqtSlot()
    def on_interrupted_received(self) -> None:
        """Renders visual interruption notice when barge-in occurs."""
        self._append_html("<div style='color: #f28b82; font-style: italic; margin: 4px 0;'>[Interrupted by user speech]</div>")

    @pyqtSlot()
    def on_turn_complete_received(self) -> None:
        """Inserts spacing after completed model turns."""
        self._append_html("<br/>")

    @pyqtSlot(QImage)
    def on_preview_frame_received(self, qimg: QImage) -> None:
        """Renders scaled preview pixmap to QLabel."""
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self.lbl_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_preview.setPixmap(scaled)

    @pyqtSlot(str)
    def on_ondemand_result_received(self, result_text: str) -> None:
        """Renders the completed on-demand Gemini query response."""
        safe_text = html.escape(result_text).replace("\n", "<br/>")
        self._append_html(f"""
            <div style='background-color: #292a2d; border-left: 3px solid #1a73e8; padding: 8px 12px; margin: 6px 0; border-radius: 4px;'>
                <strong style='color: #8ab4f8;'>Gemini:</strong><br/>
                {safe_text}
            </div>
        """)

    @pyqtSlot(list)
    def on_windows_enumerated_received(self, windows: List[Dict[str, Any]]) -> None:
        """Populates the window picker dropdown with active HWNDs and titles."""
        self.cb_windows.blockSignals(True)
        self.cb_windows.clear()
        for win in windows:
            title = win.get("title", "")
            hwnd = win.get("hwnd", 0)
            display_title = (title[:40] + "...") if len(title) > 40 else title
            self.cb_windows.addItem(f"{display_title} [{hwnd}]", hwnd)
        self.cb_windows.blockSignals(False)

        if windows:
            self._on_window_selected(0)

    @pyqtSlot(str)
    def on_error_received(self, error_msg: str) -> None:
        """Displays error notice in transcript and status bar."""
        self._append_html(f"<div style='color: #ea4335; font-weight: bold;'>⚠️ Error: {html.escape(error_msg)}</div>")

    # --------------------------------------------------------------------------
    # User Action Handlers (Emitters to Worker)
    # --------------------------------------------------------------------------

    def _on_signin_clicked(self) -> None:
        self.worker.request_login()

    def _on_signout_clicked(self) -> None:
        self.worker.request_signout()

    def _on_refresh_token_clicked(self) -> None:
        self.worker.request_refresh_token()

    def _on_mode_changed(self) -> None:
        """Switches between Continuous Live Streaming and On-Demand Snapshot modes."""
        if self.rb_live.isChecked():
            self.current_mode = "LIVE"
            self.dock_prompt.setVisible(False)
        else:
            self.current_mode = "ONDEMAND"
            self.dock_prompt.setVisible(True)
        self._update_primary_button_for_mode()

    def _update_primary_button_for_mode(self) -> None:
        if self.current_mode == "LIVE":
            self.btn_primary_action.setText("Start Live Streaming")
            self.btn_primary_action.setStyleSheet("""
                QPushButton {
                    background-color: #34a853; color: #ffffff; font-weight: bold; font-size: 14px;
                    border-radius: 6px; border: none;
                }
                QPushButton:hover { background-color: #2d9247; }
                QPushButton:disabled { background-color: #3c4043; color: #70757a; }
            """)
        else:
            self.btn_primary_action.setText("Capture Screen & Ask")
            self.btn_primary_action.setStyleSheet("""
                QPushButton {
                    background-color: #1a73e8; color: #ffffff; font-weight: bold; font-size: 14px;
                    border-radius: 6px; border: none;
                }
                QPushButton:hover { background-color: #1b66ca; }
                QPushButton:disabled { background-color: #3c4043; color: #70757a; }
            """)

    def _on_target_type_changed(self, idx: int) -> None:
        """Toggles between desktop capture and specific window capture."""
        if idx == 0:
            self.active_target_type = CaptureTarget.FULL_SCREEN
            self.active_target_id = 0
            self.window_picker_row.setVisible(False)
            self.sb_target.setText("Target: Full Desktop")
        else:
            self.active_target_type = CaptureTarget.WINDOW
            self.window_picker_row.setVisible(True)
            self.worker.request_refresh_windows()
        self._trigger_preview_update()

    def _on_window_selected(self, idx: int) -> None:
        """Updates active target HWND when a window is chosen."""
        hwnd = self.cb_windows.currentData()
        if hwnd:
            self.active_target_id = hwnd
            title = self.cb_windows.currentText()
            self.sb_target.setText(f"Target: HWND {hwnd} ({title})")
            self._trigger_preview_update()

    def _on_refresh_windows_clicked(self) -> None:
        self.worker.request_refresh_windows()

    def _on_primary_action_clicked(self) -> None:
        """Handles primary button clicks based on current mode and state."""
        if self.current_mode == "LIVE":
            if not self.is_streaming:
                self.worker.start_live_streaming(
                    target_type=self.active_target_type,
                    target_id=self.active_target_id,
                    voice_name=self.config.voice_name,
                    system_instruction=self.config.system_instruction,
                )
            else:
                self.worker.stop_live_streaming()
        else:
            self._on_send_prompt_clicked()

    def _on_mic_mute_toggled(self, checked: bool) -> None:
        """Toggles microphone mute state."""
        self.is_muted = checked
        self.worker.set_mic_muted(checked)
        if checked:
            self.btn_mic_mute.setText("🔇 Microphone: MUTED")
        else:
            self.btn_mic_mute.setText("🎤 Microphone: Active")

    def _on_send_prompt_clicked(self) -> None:
        """Submits an on-demand prompt query with screenshot snapshot."""
        prompt = self.txt_prompt_input.text().strip()
        if not prompt:
            prompt = "Analyze this screen and describe what you observe."

        self._append_html(f"""
            <div style='background-color: #174ea6; color: #e8eaed; padding: 6px 12px; margin: 4px 0; border-radius: 4px; text-align: right;'>
                <strong>You:</strong> {html.escape(prompt)}
            </div>
        """)
        self.txt_prompt_input.clear()

        self.worker.query_ondemand(
            target_type=self.active_target_type,
            target_id=self.active_target_id,
            prompt=prompt,
        )

    def _on_clear_transcript_clicked(self) -> None:
        self.txt_transcript.clear()

    def _on_preview_timer_tick(self) -> None:
        """Periodic thumbnail refresh when live streaming is not actively transmitting."""
        if not self.is_streaming:
            self._trigger_preview_update()

    def _trigger_preview_update(self) -> None:
        self.worker.capture_preview_frame(self.active_target_type, self.active_target_id)

    def _append_html(self, html_text: str) -> None:
        """Appends HTML content to the transcript view."""
        self.txt_transcript.append(html_text)
        self.txt_transcript.ensureCursorVisible()

    def cleanup(self) -> None:
        """Stops timers and releases resources upon window close."""
        if hasattr(self, "preview_timer") and self.preview_timer.isActive():
            self.preview_timer.stop()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles window close event."""
        self.cleanup()
        event.accept()
```

---

## 5. Caveats
1. **DPI Awareness Handshake**: On multi-monitor setups with mismatched scaling (e.g. 100% and 150%), `ctypes.windll.shcore.SetProcessDpiAwareness(2)` in `window_capture.py` handles Win32 bounds. In PyQt6, `QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)` must be called before `QApplication` instantiation to ensure clean window font rendering.
2. **Audio Callback Independence**: `AudioPipeline` uses PortAudio C threads. Muting does not shut down the audio stream; it injects silence bytes (`b'\x00'*3200`). This ensures zero PortAudio driver renegotiation latency.
3. **Global Hotkeys Integration**: Global hotkeys (`Alt+L` and `Alt+S`) investigated by Explorer 2 require Win32 `RegisterHotKey`. They interface with `MainWindow` by invoking `_on_primary_action_clicked()` (for `Alt+L`) and `_on_send_prompt_clicked()` (for `Alt+S`), maintaining a decoupled architecture.
4. **QSS Styling Integration**: Explorer 3 defines `gemini_desktop_screenshare/ui/styles.py`. `app.py` applies `app.setStyleSheet(DARK_STYLESHEET)`, styled to match the Google Material dark theme palette (#202124 background, #292a2d surface, #1a73e8 primary blue).

---

## 6. Conclusion
1. **Architecture Decoupling**: Combining PyQt6's main event loop with a dedicated `AsyncWorker(QThread)` running standard library `asyncio` achieves complete isolation between 60 FPS GUI rendering and network/WebSocket I/O.
2. **Elimination of `qasync`**: `qasync` is not present in the runtime, risks UI stalls during frame processing, and is completely unneeded. Native `QThread` + `pyqtSignal` is robust and self-contained.
3. **Thread Safety & Zero GDI Leaks**: Passing `QImage(...).copy()` across threads eliminates memory ownership issues and prevents fatal cross-thread `QPixmap` crashes. Hooking `audio_pipeline.interrupt()` surfaces barge-in signals instantly to the transcript without touching the streaming engine internals.
4. **Concrete Implementation Readiness**: The class designs, widget hierarchy, and interface contracts for `app.py` and `ui/main_window.py` are fully specified and ready for implementation in Milestone 3.

---

## 7. Verification Method

### 7.1 Automated Headless Verification
To verify that the PyQt6 GUI architecture, widget tree, signal wiring, and background thread mechanisms work without requiring a physical monitor or human user clicks:

1. **Verify Headless Offscreen Mode**:
   ```powershell
   python -c "
   import os, sys
   os.environ['QT_QPA_PLATFORM'] = 'offscreen'
   from PyQt6.QtWidgets import QApplication
   from gemini_desktop_screenshare.app import AsyncWorker
   from gemini_desktop_screenshare.ui.main_window import MainWindow
   from gemini_desktop_screenshare.config import load_config
   from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
   from gemini_desktop_screenshare.capture.screen_capture import ScreenCaptureEngine
   from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline

   app = QApplication.instance() or QApplication(sys.argv)
   config = load_config()
   oauth = OAuthManager(config=config)
   capture = ScreenCaptureEngine()
   audio = AudioPipeline()
   worker = AsyncWorker(config, oauth, capture, audio)
   worker.start()

   win = MainWindow(worker=worker, config=config)
   win.show()
   assert win.isVisible()
   print('UI Initialized Headless Successfully!')

   win.cleanup()
   worker.stop()
   audio.close()
   capture.close()
   print('Shutdown Clean!')
   "
   ```

2. **Verify Signal Emission & Text Streaming Slot**:
   ```powershell
   python -c "
   import os, sys, time
   os.environ['QT_QPA_PLATFORM'] = 'offscreen'
   from PyQt6.QtWidgets import QApplication
   from PyQt6.QtGui import QImage
   from gemini_desktop_screenshare.app import AsyncWorker
   from gemini_desktop_screenshare.config import load_config
   from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
   from gemini_desktop_screenshare.capture.screen_capture import ScreenCaptureEngine
   from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline

   app = QApplication.instance() or QApplication(sys.argv)
   worker = AsyncWorker(load_config(), OAuthManager(), ScreenCaptureEngine(), AudioPipeline())
   worker.start()

   received = []
   worker.sig_text_token.connect(lambda t: received.append(t))

   def emit_from_thread():
       worker.sig_text_token.emit('token_1')
       worker.sig_text_token.emit('token_2')

   worker.submit_coro(asyncio.to_thread(emit_from_thread))
   time.sleep(0.2)
   app.processEvents()

   assert received == ['token_1', 'token_2'], f'Tokens not received properly: {received}'
   print('Cross-thread signal verification passed!')
   worker.stop()
   "
   ```

3. **Invalidation Conditions**:
   - If `qasync` is reintroduced as a required dependency.
   - If `QPixmap` is constructed in a background thread instead of `QImage`.
   - If synchronous calls like `OAuthManager.start_loopback_and_login()` are invoked on the GUI thread.
