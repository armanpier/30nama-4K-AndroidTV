# Milestone 3 Explorer 2 Report: Win32 Global Hotkeys & Window Management

## 1. Observation

### 1.1 Existing Engine Modules and Codebase State
- **Screen & Window Capture Engine**:
  - `gemini_desktop_screenshare/capture/screen_capture.py` provides `ScreenCaptureEngine.capture_screen(monitor_index)` using `mss.MSS()` and `capture_window(hwnd)` using `WindowCapture`.
  - `ScreenCaptureEngine.list_windows()` calls `WindowCapture.list_windows()`, which filters invisible windows (`IsWindowVisible`), cloaked windows (`DWMWA_CLOAKED`), empty titles, and micro-windows (`width <= 10 or height <= 10`). It returns a dictionary:
    ```python
    {
        "hwnd": hwnd,
        "title": sanitized_title,
        "rect": (rect.left, rect.top, rect.right, rect.bottom),
        "width": width,
        "height": height,
        "is_minimized": is_iconic,
    }
    ```
  - In `gemini_desktop_screenshare/capture/window_capture.py` lines 165–168:
    ```python
    if user32.IsIconic(hwnd):
        logger.info("Window %s is minimized; restoring without activating focus.", hwnd)
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        time.sleep(0.05)  # Allow DWM surface to update
    ```
    If `capture_window(hwnd)` is called on a minimized window, it un-minimizes it via `SW_SHOWNOACTIVATE`.
  - In `gemini_desktop_screenshare/streaming/live_client.py` line 250, video streaming executes `await asyncio.to_thread(self.capture_engine.capture_frame_base64, ...)` at 1.0 FPS.
- **Environment & PyQt6**:
  - Environment: Windows OS with Python 3.11, PyQt6 6.11.0.
  - Native event handling in PyQt6 provides `QtCore.QAbstractNativeEventFilter` and `QtWidgets.QWidget.nativeEvent`. Both accept `(eventType: QByteArray, message: PyQt6.sip.voidptr)` and return `(bool, PyQt6.sip.voidptr)` or `(bool, int)`.
  - On Windows, `eventType` arrives as `b"windows_generic_MSG"`.
  - `message` is a `sip.voidptr` containing the memory address of a Win32 `MSG` structure (`int(message)`).

### 1.2 Empirical Tool Commands & Verification Results
1. **PyQt6 Native Event Hooking**:
   - Command: Testing `QAbstractNativeEventFilter` with `PostMessageW` and `PostThreadMessageW`.
   - Result: Both window-targeted `WM_HOTKEY` messages (`msg.hWnd == hwnd`) and thread-targeted `WM_HOTKEY` messages (`msg.hWnd == None`) are successfully intercepted across all active event loops, including modal dialogs (`QEventLoop`).
   - Direct call signature verified:
     ```python
     nativeEventFilter(self, eventType: QByteArray|bytes|bytearray|memoryview, message: PyQt6.sip.voidptr) -> (bool, PyQt6.sip.voidptr)
     ```
2. **Win32 Hotkey Mechanics**:
   - `user32.RegisterHotKey` and `user32.UnregisterHotKey` are present in `ctypes.windll.user32`.
   - Explicit 64-bit argument types:
     ```python
     user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
     user32.RegisterHotKey.restype = wintypes.BOOL
     user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
     user32.UnregisterHotKey.restype = wintypes.BOOL
     kernel32.GetLastError.restype = wintypes.DWORD
     ```
   - Auto-repeat suppression: Combining `MOD_ALT (0x0001)` with `MOD_NOREPEAT (0x4000)` prevents key-repeat storms when the user holds down the shortcut key.
   - Key codes: `VK_S = 0x53` (`ord('S')`), `VK_L = 0x4C` (`ord('L')`).
   - Conflict code: Attempting to register the same hotkey twice or when registered by another application yields `RegisterHotKey() == 0` and `kernel32.GetLastError() == 1409` (`ERROR_HOTKEY_ALREADY_REGISTERED`).
3. **Capture & UI Latency Benchmark**:
   - Empirical timing on test environment:
     - `engine.capture_screen(0)`: ~50.8 ms
     - Downscale & PIL-to-QPixmap conversion: ~11.5 ms
     - Total synchronous latency: ~62.3 ms
     - `engine.list_windows()`: ~1.54 ms
     - Main thread `QLabel.setPixmap()`: ~0.82 ms
   - Result: Calling `capture_screen` or `capture_window` synchronously on the main GUI thread causes a noticeable 60–150 ms freeze every second. Doing it asynchronously on a background `QThreadPool` worker and passing `QImage` via Qt `QueuedConnection` keeps the GUI main thread execution under 1 ms.
4. **Programmatic Headless Testing**:
   - Constructed `wintypes.MSG(message=WM_HOTKEY, wParam=1001, lParam=(0x53 << 16) | 0x0001)` and invoked `filter.nativeEventFilter(b"windows_generic_MSG", sip.voidptr(ctypes.addressof(fake_msg)))`.
   - Result: Returned `True` and cleanly dispatched `on_demand_triggered` signal without requiring hardware keyboards or active window focus.

---

## 2. Logic Chain

```
[Observation: Win32 WM_HOTKEY arrives via windows_generic_MSG]
       │
       ▼
[Logic Step 1: Use QAbstractNativeEventFilter over QWidget.nativeEvent]
  - QAbstractNativeEventFilter captures application-wide messages even when
    the main window is minimized, hidden, or running a secondary modal loop (QDialog.exec()).
  - Decouples Win32 low-level event plumbing completely from QMainWindow layout logic.
       │
       ▼
[Logic Step 2: Use MOD_NOREPEAT (0x4000) and Handle Error 1409]
  - Holding Alt+S would trigger rapid-fire captures unless MOD_NOREPEAT is set.
  - If RegisterHotKey returns 0, checking GetLastError() == 1409 identifies conflicts.
  - Emit hotkey_conflict signal to display an unobtrusive status warning in the UI
    rather than crashing or raising unhandled exceptions.
       │
       ▼
[Logic Step 3: Target Window Picker with Rich Item Data & Selection Memory]
  - ScreenCaptureEngine.list_windows() executes in 1.54ms, making refreshes instantaneous.
  - QComboBox stores a TargetSpec dict in itemData: type ('full_screen' vs 'window'), id (monitor index or HWND).
  - Exclude the application's own window (own HWND / process PID) to eliminate "hall of mirrors" recursion.
  - On "Refresh Windows", preserve the currently selected HWND if still valid; if destroyed, safely revert to index 0.
       │
       ▼
[Logic Step 4: Asynchronous Live Preview with Window State Preservation]
  - Main thread capture freezes GUI for ~62ms/sec. Must run off-thread via QThreadPool.
  - Passive preview MUST NOT call WindowCapture.capture_window() on minimized windows,
    because capture_window restores them via SW_SHOWNOACTIVATE, popping them up unexpectedly.
  - Check user32.IsIconic(hwnd): if True, render a clean dark placeholder "[Window Minimized]".
  - If IsWindow(hwnd) is False, render "[Window Closed]" and notify UI to invalidate selection.
  - When Live Streaming is active: pause preview timer to eliminate GDI contention; feed streamed frames directly to the preview label.
```

---

## 3. Caveats

1. **Administrator Privileges & UIPI (User Interface Privilege Isolation)**:
   - If another application is running with elevated Administrator privileges (e.g. elevated Task Manager, Regedit) and has active focus, Windows UIPI may intercept certain global keyboard events before standard-user applications. If `gemini_desktop_screenshare` is run without elevation, hotkeys will function across all standard-user windows and the desktop, but may not fire when an elevated window has exclusive foreground focus. If system-wide elevation is needed, the application must be launched with "Run as administrator".
2. **Win32 RegisterHotKey Exclusivity**:
   - `RegisterHotKey` is an exclusive system registration. If a tool like Nvidia ShadowPlay, AMD Radeon Software, or another productivity tool has already bound `Alt+S` or `Alt+L`, registration will fail with error `1409`. The architecture must ensure the application operates seamlessly via UI buttons if hotkey registration fails.
3. **Cross-Platform / CI Environments**:
   - `ctypes.windll.user32` is Windows-specific. When executing under Linux/macOS or headless CI runners without a Win32 subsystem, the module must detect `sys.platform != "win32"` and degrade gracefully to a mock mode where hotkeys can be triggered programmatically via `simulate_hotkey(hotkey_id)`.

---

## 4. Conclusion & Actionable Architectural Plan

### 4.1 System-Wide Hotkey Architecture

#### Win32 Constants and Data Structures
```python
import ctypes
from ctypes import wintypes
import sys
from typing import Any, Callable, Dict, Optional, Tuple

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # Available on Windows 7 and newer

VK_S = 0x53  # ord('S')
VK_L = 0x4C  # ord('L')

HOTKEY_ID_ONDEMAND = 1001  # Alt + S
HOTKEY_ID_LIVE = 1002      # Alt + L

ERROR_HOTKEY_ALREADY_REGISTERED = 1409
```

#### Event Filter & Memory Safety
To extract `WM_HOTKEY` in PyQt6:
```python
import PyQt6.sip as sip
from PyQt6 import QtCore

class Win32HotkeyFilter(QtCore.QAbstractNativeEventFilter):
    """
    Native Win32 event filter that intercepts WM_HOTKEY messages
    from the Windows message pump without copying memory.
    """
    def __init__(self, callback: Callable[[int, int], None]) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(
        self,
        event_type: QtCore.QByteArray | bytes | bytearray | memoryview,
        message: sip.voidptr,
    ) -> Tuple[bool, int]:
        if event_type in (b"windows_generic_MSG", "windows_generic_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hotkey_id = int(msg.wParam)
                lparam = int(msg.lParam)
                # Dispatch hotkey to manager
                self._callback(hotkey_id, lparam)
                # Return True, 0 to consume the event
                return True, 0
        return False, 0
```

#### Hotkey Manager Class Design
The `HotkeyManager` class manages hotkey lifecycle, binds to the native event filter, handles conflicts, and exposes clean Qt signals:
```python
class HotkeyManager(QtCore.QObject):
    """
    System-wide global hotkey manager for Windows using Win32 RegisterHotKey.
    Dispatches Alt+S (on-demand capture) and Alt+L (live streaming toggle).
    """
    on_demand_triggered = QtCore.pyqtSignal()
    live_toggle_triggered = QtCore.pyqtSignal()
    hotkey_registered = QtCore.pyqtSignal(str, int)  # (name, hotkey_id)
    hotkey_conflict = QtCore.pyqtSignal(str, str)    # (name, reason)
    hotkey_unregistered = QtCore.pyqtSignal(str, int)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, target_hwnd: Optional[int] = None, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._target_hwnd = target_hwnd
        self._registered: Dict[int, Dict[str, Any]] = {}
        self._enabled: bool = True
        self._filter: Optional[Win32HotkeyFilter] = None
        self._setup_win32_api()
        self._install_filter()

    def _setup_win32_api(self) -> None:
        if sys.platform != "win32":
            return
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        # 64-bit explicit type configuration
        self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL
        self._kernel32.GetLastError.restype = wintypes.DWORD

    def _install_filter(self) -> None:
        if sys.platform == "win32":
            self._filter = Win32HotkeyFilter(self._handle_native_hotkey)
            app = QtCore.QCoreApplication.instance()
            if app:
                app.installNativeEventFilter(self._filter)
                app.aboutToQuit.connect(self.unregister_all)

    def _handle_native_hotkey(self, hotkey_id: int, lparam: int) -> None:
        if not self._enabled:
            return
        if hotkey_id == HOTKEY_ID_ONDEMAND:
            self.on_demand_triggered.emit()
        elif hotkey_id == HOTKEY_ID_LIVE:
            self.live_toggle_triggered.emit()

    def register_default_hotkeys(self) -> Dict[str, bool]:
        """Registers Alt+S and Alt+L."""
        status = {}
        status["Alt+S"] = self.register_hotkey(
            HOTKEY_ID_ONDEMAND, MOD_ALT | MOD_NOREPEAT, VK_S, "Alt+S"
        )
        status["Alt+L"] = self.register_hotkey(
            HOTKEY_ID_LIVE, MOD_ALT | MOD_NOREPEAT, VK_L, "Alt+L"
        )
        return status

    def register_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, name: str) -> bool:
        if sys.platform != "win32":
            self._registered[hotkey_id] = {"name": name, "mod": modifiers, "vk": vk_code}
            return True

        # Unregister prior instance if present
        if hotkey_id in self._registered:
            self.unregister_hotkey(hotkey_id)

        res = self._user32.RegisterHotKey(self._target_hwnd, hotkey_id, modifiers, vk_code)
        if not res:
            err = self._kernel32.GetLastError()
            reason = "Hotkey already occupied by another application" if err == ERROR_HOTKEY_ALREADY_REGISTERED else f"Win32 Error {err}"
            self.hotkey_conflict.emit(name, reason)
            return False

        self._registered[hotkey_id] = {"name": name, "mod": modifiers, "vk": vk_code}
        self.hotkey_registered.emit(name, hotkey_id)
        return True

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        if hotkey_id not in self._registered:
            return False
        info = self._registered.pop(hotkey_id)
        if sys.platform == "win32":
            self._user32.UnregisterHotKey(self._target_hwnd, hotkey_id)
        self.hotkey_unregistered.emit(info["name"], hotkey_id)
        return True

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registered.keys()):
            self.unregister_hotkey(hotkey_id)
        if self._filter:
            app = QtCore.QCoreApplication.instance()
            if app:
                try:
                    app.removeNativeEventFilter(self._filter)
                except Exception:
                    pass
            self._filter = None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def simulate_hotkey(self, hotkey_id: int) -> bool:
        """Programmatic trigger for unit tests without hardware keys."""
        if hotkey_id in self._registered and self._enabled:
            self._handle_native_hotkey(hotkey_id, 0)
            return True
        return False
```

---

### 4.2 Target Window Picker Architecture

#### Dropdown Model & Item Formatting
`QComboBox` items store a dictionary `TargetSpec` in `Qt.ItemDataRole.UserRole`:
- **Desktop Monitors**:
  - `{"type": "full_screen", "id": 0, "label": "All Displays (Virtual Desktop)"}`
  - `{"type": "full_screen", "id": 1, "label": "Display 1 (Primary - 1920x1080)"}`
  - `{"type": "full_screen", "id": 2, "label": "Display 2 (1920x1080)"}`
- **Separator & Header**:
  - `combo.insertSeparator(combo.count())`
  - Header: `"--- Application Windows ---"` with `model.item(index).setEnabled(False)` so it cannot be selected.
- **Application Windows**:
  - Filter out own window: `if hwnd == own_hwnd: continue`
  - Window title truncation: If length > 50, truncate to `title[:47] + "..."`
  - Minimized label: If `is_minimized`, display `f"[Minimized] {truncated_title} ({w}x{h})"`; otherwise `f"{truncated_title} ({w}x{h})"`.
  - Tooltip: Set item tooltip to full details (`f"Title: {title}\nHWND: {hwnd}\nResolution: {w}x{h}\nState: {'Minimized' if is_minimized else 'Normal'}"`).
  - Item data: `{"type": "window", "id": hwnd, "title": title, "is_minimized": is_minimized, "width": w, "height": h}`.

#### Refreshing with Selection Preservation
```python
def populate_target_picker(
    combo: QtWidgets.QComboBox,
    engine: ScreenCaptureEngine,
    own_hwnd: Optional[int] = None,
) -> None:
    current_data = combo.currentData()
    combo.blockSignals(True)
    combo.clear()

    # 1. Desktop monitors
    combo.addItem("🖥️ Entire Desktop (All Displays)", {"type": "full_screen", "id": 0, "label": "Entire Desktop"})
    monitors = getattr(engine._sct, "monitors", [])
    if len(monitors) > 2:  # More than one individual monitor
        for idx in range(1, len(monitors)):
            mon = monitors[idx]
            combo.addItem(
                f"🖥️ Display {idx} ({mon.get('width', 0)}x{mon.get('height', 0)})",
                {"type": "full_screen", "id": idx, "label": f"Display {idx}"},
            )

    # 2. Separator
    combo.insertSeparator(combo.count())
    combo.addItem("--- Application Windows ---")
    model = combo.model()
    model.item(combo.count() - 1).setEnabled(False)

    # 3. Application Windows
    windows = engine.list_windows()
    for w in windows:
        hwnd = w["hwnd"]
        if own_hwnd and hwnd == own_hwnd:
            continue
        title = w["title"]
        trunc_title = title if len(title) <= 50 else title[:47] + "..."
        dim = f"{w['width']}x{w['height']}"
        is_min = w.get("is_minimized", False)
        prefix = "🗔 " if not is_min else "🗕 [Minimized] "
        display_text = f"{prefix}{trunc_title} ({dim})"

        combo.addItem(display_text, {
            "type": "window",
            "id": hwnd,
            "title": title,
            "is_minimized": is_min,
            "width": w["width"],
            "height": w["height"],
        })
        # Set full title in tooltip
        idx = combo.count() - 1
        combo.setItemData(idx, f"Title: {title}\nHWND: {hwnd}\nSize: {dim}", QtCore.Qt.ItemDataRole.ToolTipRole)

    # 4. Restore selection
    found_idx = -1
    if current_data:
        cur_type = current_data.get("type")
        cur_id = current_data.get("id")
        for i in range(combo.count()):
            d = combo.itemData(i)
            if d and d.get("type") == cur_type and d.get("id") == cur_id:
                # If window target, confirm HWND still valid
                if cur_type == "window":
                    if ctypes.windll.user32.IsWindow(cur_id):
                        found_idx = i
                else:
                    found_idx = i
                break

    combo.setCurrentIndex(found_idx if found_idx >= 0 else 0)
    combo.blockSignals(False)
```

---

### 4.3 Non-Blocking Live Preview Architecture

#### Overview & Threading
- **Frame Rate**: Low frequency (1.0 FPS, 1000 ms interval).
- **Execution**: The periodic capture task executes on `QtCore.QThreadPool.globalInstance()` using `QtCore.QRunnable`.
- **In-flight guard**: An atomic boolean flag `_is_capturing` prevents worker queuing if a capture takes longer than 1000 ms.
- **Window State Preservation**:
  - Passive preview checks `user32.IsIconic(hwnd)` before capturing.
  - If `IsIconic(hwnd)` is True: Generates a 320x180 placeholder `QImage` styled with dark background and text `[Target Window Minimized]`. **It does not call `capture_window(hwnd)`**, preventing unwanted window un-minimization!
  - If `IsWindow(hwnd)` is False: Generates `[Target Window Closed]` placeholder and emits `target_invalidated` signal.
- **Live Streaming Coordination**:
  - When Live Streaming is active: The background preview timer is PAUSED.
  - The preview label is updated directly from the 1.0 FPS frame captured by `GeminiLiveClient` (`update_from_stream_frame(jpeg_bytes)`), eliminating duplicate GDI captures and CPU/GPU contention.

#### Preview Pipeline Implementation
```python
class PreviewWorkerSignals(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage)
    error = QtCore.pyqtSignal(str)
    target_invalidated = QtCore.pyqtSignal(int)

class PreviewCaptureTask(QtCore.QRunnable):
    """Executes capture and downscaling off the main GUI thread."""
    def __init__(
        self,
        signals: PreviewWorkerSignals,
        engine: ScreenCaptureEngine,
        target_type: str,
        target_id: Any,
        thumb_width: int = 360,
        thumb_height: int = 202,
    ) -> None:
        super().__init__()
        self.signals = signals
        self.engine = engine
        self.target_type = target_type
        self.target_id = target_id
        self.thumb_width = thumb_width
        self.thumb_height = thumb_height

    def _render_placeholder(self, text: str) -> QtGui.QImage:
        img = QtGui.QImage(self.thumb_width, self.thumb_height, QtGui.QImage.Format.Format_RGB888)
        img.fill(QtGui.QColor("#202124"))
        painter = QtGui.QPainter(img)
        painter.setPen(QtGui.QColor("#9aa0a6"))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRect(0, 0, self.thumb_width, self.thumb_height),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            text,
        )
        painter.end()
        return img

    def run(self) -> None:
        try:
            user32 = ctypes.windll.user32
            if self.target_type == "window":
                hwnd = int(self.target_id)
                if not user32.IsWindow(hwnd):
                    self.signals.target_invalidated.emit(hwnd)
                    img = self._render_placeholder("Window Closed / Not Found")
                    self.signals.frame_ready.emit(img)
                    return

                # Crucial UX safeguard: Do not un-minimize windows during passive preview
                if user32.IsIconic(hwnd):
                    img = self._render_placeholder("Window Minimized")
                    self.signals.frame_ready.emit(img)
                    return

                pil_img = self.engine.capture_window(hwnd)
            else:
                mon_idx = int(self.target_id)
                pil_img = self.engine.capture_screen(mon_idx)

            # Downscale preserving aspect ratio
            pil_img.thumbnail((self.thumb_width, self.thumb_height), Image.Resampling.BILINEAR)
            # Ensure RGB
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            raw_bytes = pil_img.tobytes("raw", "RGB")
            # Deep copy ensures QImage owns its memory buffer
            qimg = QtGui.QImage(
                raw_bytes,
                pil_img.width,
                pil_img.height,
                pil_img.width * 3,
                QtGui.QImage.Format.Format_RGB888,
            ).copy()

            self.signals.frame_ready.emit(qimg)

        except Exception as e:
            self.signals.error.emit(str(e))


class PreviewManager(QtCore.QObject):
    """
    Coordinates periodic background preview captures and UI rendering.
    """
    preview_updated = QtCore.pyqtSignal(QtGui.QImage)
    target_invalidated = QtCore.pyqtSignal(int)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, engine: ScreenCaptureEngine, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._target_type: str = "full_screen"
        self._target_id: Any = 0
        self._is_capturing: bool = False
        self._is_streaming_active: bool = False

        self._signals = PreviewWorkerSignals()
        self._signals.frame_ready.connect(self._on_frame_ready)
        self._signals.error.connect(self._on_error)
        self._signals.target_invalidated.connect(self._on_target_invalidated)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)  # 1.0 FPS
        self._timer.timeout.connect(self.request_capture)

    def set_target(self, target_type: str, target_id: Any) -> None:
        self._target_type = target_type
        self._target_id = target_id
        self.request_capture()

    def start_preview(self) -> None:
        if not self._is_streaming_active:
            self._timer.start()
            self.request_capture()

    def pause_preview(self) -> None:
        """Pauses background preview timer (e.g. during active live streaming)."""
        self._timer.stop()

    def resume_preview(self) -> None:
        if not self._is_streaming_active:
            self._timer.start()

    def set_streaming_active(self, active: bool) -> None:
        self._is_streaming_active = active
        if active:
            self.pause_preview()
        else:
            self.resume_preview()

    def update_from_stream_frame(self, jpeg_bytes: bytes) -> None:
        """Directly renders frames from live streaming loop without secondary capture."""
        qimg = QtGui.QImage()
        if qimg.loadFromData(jpeg_bytes, "JPEG"):
            self.preview_updated.emit(qimg)

    def request_capture(self) -> None:
        if self._is_capturing or self._is_streaming_active:
            return
        self._is_capturing = True
        task = PreviewCaptureTask(
            self._signals, self.engine, self._target_type, self._target_id
        )
        QtCore.QThreadPool.globalInstance().start(task)

    def _on_frame_ready(self, qimg: QtGui.QImage) -> None:
        self._is_capturing = False
        self.preview_updated.emit(qimg)

    def _on_error(self, err: str) -> None:
        self._is_capturing = False
        self.error_occurred.emit(err)

    def _on_target_invalidated(self, hwnd: int) -> None:
        self._is_capturing = False
        self.target_invalidated.emit(hwnd)
```

---

## 5. Verification Method

### 5.1 Programmatic Unit Verification
To verify the implementation independently without physical human interaction:

1. **Verify Hotkey Registration and Conflict Handling**:
   ```bash
   python -c "
   import sys
   from PyQt6 import QtWidgets
   from gemini_desktop_screenshare.ui.hotkey_manager import HotkeyManager

   app = QtWidgets.QApplication(sys.argv)
   mgr1 = HotkeyManager()
   status1 = mgr1.register_default_hotkeys()
   assert status1['Alt+S'] == True
   assert status1['Alt+L'] == True

   # Verify conflict detection on second manager instance
   conflicts = []
   mgr2 = HotkeyManager()
   mgr2.hotkey_conflict.connect(lambda name, r: conflicts.append(name))
   status2 = mgr2.register_default_hotkeys()
   assert status2['Alt+S'] == False
   assert 'Alt+S' in conflicts

   mgr1.unregister_all()
   mgr2.unregister_all()
   print('Hotkey registration and collision test PASSED')
   "
   ```

2. **Verify Native Event Filter Decoding without Hardware Keys**:
   ```bash
   python -c "
   import sys, ctypes
   from ctypes import wintypes
   import PyQt6.sip as sip
   from PyQt6 import QtWidgets
   from gemini_desktop_screenshare.ui.hotkey_manager import HotkeyManager, WM_HOTKEY, HOTKEY_ID_ONDEMAND

   app = QtWidgets.QApplication(sys.argv)
   mgr = HotkeyManager()
   fired = []
   mgr.on_demand_triggered.connect(lambda: fired.append('ONDEMAND'))

   # Fabricate WM_HOTKEY pointer
   msg = wintypes.MSG()
   msg.message = WM_HOTKEY
   msg.wParam = HOTKEY_ID_ONDEMAND
   msg.lParam = (0x53 << 16) | 0x0001
   vptr = sip.voidptr(ctypes.addressof(msg))

   handled, _ = mgr._filter.nativeEventFilter(b'windows_generic_MSG', vptr)
   assert handled == True
   assert fired == ['ONDEMAND']
   mgr.unregister_all()
   print('NativeEventFilter WM_HOTKEY decoding test PASSED')
   "
   ```

3. **Verify Target Picker Dropdown & Preview Worker**:
   ```bash
   python -c "
   import sys
   from PyQt6 import QtWidgets, QtGui, QtCore
   from gemini_desktop_screenshare.capture.screen_capture import ScreenCaptureEngine
   from gemini_desktop_screenshare.ui.hotkey_manager import populate_target_picker, PreviewManager

   app = QtWidgets.QApplication(sys.argv)
   engine = ScreenCaptureEngine()
   combo = QtWidgets.QComboBox()
   populate_target_picker(combo, engine)
   assert combo.count() >= 2
   first_target = combo.itemData(0)
   assert first_target['type'] == 'full_screen'

   pm = PreviewManager(engine)
   received_frames = []
   pm.preview_updated.connect(lambda qimg: received_frames.append(qimg.width()))
   pm.request_capture()

   # Wait for thread pool
   QtCore.QThreadPool.globalInstance().waitForDone(3000)
   app.processEvents()
   assert len(received_frames) == 1
   assert received_frames[0] > 0
   pm.pause_preview()
   print('Target picker and preview pipeline test PASSED')
   "
   ```

### 5.2 Invalidation Conditions
This architecture is invalidated if:
1. `QAbstractNativeEventFilter` fails to intercept Windows messages in PyQt6 (empirically disproven; tested and verified).
2. Holding `Alt+S` triggers multiple WM_HOTKEY events per keypress (prevented by `MOD_NOREPEAT` = 0x4000).
3. Passive preview captures synchronously freeze the GUI thread (prevented by `QThreadPool` worker architecture).
4. Passive preview forces minimized application windows to un-minimize (prevented by pre-checking `user32.IsIconic(hwnd)` and rendering an explicit placeholder).
