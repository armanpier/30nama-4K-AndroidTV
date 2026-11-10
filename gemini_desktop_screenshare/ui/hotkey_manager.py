"""
Win32 Global Hotkey Manager and Native Event Filter for Gemini Desktop Screenshare.
Registers system-wide hotkeys (Alt+S for on-demand capture, Alt+L for live streaming toggle)
via user32.RegisterHotKey, intercepts WM_HOTKEY events using QAbstractNativeEventFilter,
and handles conflicts gracefully (ERROR_HOTKEY_ALREADY_REGISTERED = 1409).
"""

import ctypes
from ctypes import wintypes
import logging
import sys
from typing import Any, Callable, Dict, Optional, Tuple

import PyQt6.sip as sip
from PyQt6.QtCore import QAbstractNativeEventFilter, QByteArray, QCoreApplication, QObject, pyqtSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Win32 Constants
# ---------------------------------------------------------------------------
WM_HOTKEY: int = 0x0312

MOD_ALT: int = 0x0001
MOD_CONTROL: int = 0x0002
MOD_SHIFT: int = 0x0004
MOD_WIN: int = 0x0008
MOD_NOREPEAT: int = 0x4000  # Prevents repeated events on key hold (Windows 7+)

VK_S: int = 0x53  # ord('S') - On-Demand screen capture trigger
VK_L: int = 0x4C  # ord('L') - Live streaming toggle

HOTKEY_ID_ONDEMAND: int = 1001  # Alt + S
HOTKEY_ID_LIVE: int = 1002      # Alt + L

ERROR_HOTKEY_ALREADY_REGISTERED: int = 1409


class Win32HotkeyFilter(QAbstractNativeEventFilter):
    """
    QAbstractNativeEventFilter implementation that intercepts Windows generic messages
    at the application message pump level and decodes WM_HOTKEY notifications.
    """

    def __init__(self, callback: Callable[[int, int], None]) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(
        self,
        event_type: QByteArray | bytes | bytearray | memoryview | str,
        message: sip.voidptr,
    ) -> Tuple[bool, int]:
        """
        Intercepts native Windows events. If WM_HOTKEY arrives, extracts wParam (hotkey_id)
        and lParam (key modifiers & vk) and dispatches to callback.
        """
        # Convert QByteArray or string to bytes for uniform matching
        if isinstance(event_type, QByteArray):
            type_bytes = bytes(event_type.data())
        elif isinstance(event_type, str):
            type_bytes = event_type.encode("latin-1")
        else:
            type_bytes = bytes(event_type)

        if type_bytes == b"windows_generic_MSG":
            try:
                msg_addr = int(message)
                if msg_addr != 0:
                    msg = wintypes.MSG.from_address(msg_addr)
                    if msg.message == WM_HOTKEY:
                        hotkey_id = int(msg.wParam)
                        lparam = int(msg.lParam)
                        self._callback(hotkey_id, lparam)
                        # Consume event so it doesn't propagate further
                        return True, 0
            except Exception as e:
                logger.debug("Exception decoding native WM_HOTKEY event: %s", e)

        return False, 0


class HotkeyManager(QObject):
    """
    Manages system-wide global hotkeys using Win32 RegisterHotKey / UnregisterHotKey.
    Dispatches signals to Qt UI when Alt+S or Alt+L is pressed globally.
    """

    on_demand_triggered = pyqtSignal()
    live_toggle_triggered = pyqtSignal()
    hotkey_registered = pyqtSignal(str, int)  # (name, hotkey_id)
    hotkey_conflict = pyqtSignal(str, str)    # (name, reason)
    hotkey_unregistered = pyqtSignal(str, int) # (name, hotkey_id)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        target_hwnd: Optional[int] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._target_hwnd = target_hwnd
        self._registered: Dict[int, Dict[str, Any]] = {}
        self._enabled: bool = True
        self._filter: Optional[Win32HotkeyFilter] = None

        self._user32 = None
        self._kernel32 = None
        self._setup_win32_api()
        self._install_filter()

    def _setup_win32_api(self) -> None:
        """Sets up explicit 64-bit ctypes prototypes for Win32 hotkey functions."""
        if sys.platform != "win32":
            return

        try:
            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32

            # Configure explicit 64-bit argtypes and restype
            self._user32.RegisterHotKey.argtypes = [
                wintypes.HWND,
                ctypes.c_int,
                wintypes.UINT,
                wintypes.UINT,
            ]
            self._user32.RegisterHotKey.restype = wintypes.BOOL

            self._user32.UnregisterHotKey.argtypes = [
                wintypes.HWND,
                ctypes.c_int,
            ]
            self._user32.UnregisterHotKey.restype = wintypes.BOOL

            self._kernel32.GetLastError.argtypes = []
            self._kernel32.GetLastError.restype = wintypes.DWORD
        except Exception as e:
            logger.warning("Could not configure Win32 hotkey API: %s", e)

    def _install_filter(self) -> None:
        """Installs native event filter on QCoreApplication instance."""
        self._filter = Win32HotkeyFilter(self._handle_native_hotkey)
        app = QCoreApplication.instance()
        if app:
            app.installNativeEventFilter(self._filter)

    def _handle_native_hotkey(self, hotkey_id: int, lparam: int) -> None:
        """Dispatches hotkey ID to corresponding Qt signal."""
        if not self._enabled:
            return

        logger.debug("Handling native hotkey event (id=%d, lparam=0x%08X)", hotkey_id, lparam)
        if hotkey_id == HOTKEY_ID_ONDEMAND:
            self.on_demand_triggered.emit()
        elif hotkey_id == HOTKEY_ID_LIVE:
            self.live_toggle_triggered.emit()

    def register_default_hotkeys(self) -> Dict[str, bool]:
        """
        Registers the default application hotkeys:
        - Alt+S: On-demand screen capture trigger (0x4001, 0x53)
        - Alt+L: Continuous live streaming toggle (0x4001, 0x4C)
        """
        status: Dict[str, bool] = {}
        status["Alt+S"] = self.register_hotkey(
            HOTKEY_ID_ONDEMAND,
            MOD_ALT | MOD_NOREPEAT,
            VK_S,
            "Alt+S",
        )
        status["Alt+L"] = self.register_hotkey(
            HOTKEY_ID_LIVE,
            MOD_ALT | MOD_NOREPEAT,
            VK_L,
            "Alt+L",
        )
        return status

    def register_hotkey(
        self,
        hotkey_id: int,
        modifiers: int,
        vk_code: int,
        name: str,
    ) -> bool:
        """
        Registers a hotkey with the Win32 OS.
        Handles conflict code 1409 (ERROR_HOTKEY_ALREADY_REGISTERED) gracefully.
        """
        if sys.platform != "win32" or self._user32 is None:
            self._registered[hotkey_id] = {"name": name, "mod": modifiers, "vk": vk_code}
            self.hotkey_registered.emit(name, hotkey_id)
            return True

        # Unregister prior registration if present
        if hotkey_id in self._registered:
            self.unregister_hotkey(hotkey_id)

        res = self._user32.RegisterHotKey(
            self._target_hwnd,
            hotkey_id,
            modifiers,
            vk_code,
        )

        if not res:
            err = self._kernel32.GetLastError()
            if err == ERROR_HOTKEY_ALREADY_REGISTERED:
                reason = "Hotkey already registered by another application."
            else:
                reason = f"Win32 RegisterHotKey error code {err}."
            logger.warning("Failed to register hotkey %s (%s): %s", name, hotkey_id, reason)
            self.hotkey_conflict.emit(name, reason)
            return False

        self._registered[hotkey_id] = {"name": name, "mod": modifiers, "vk": vk_code}
        logger.info("Successfully registered global hotkey %s (id=%d)", name, hotkey_id)
        self.hotkey_registered.emit(name, hotkey_id)
        return True

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        """Unregisters an individual hotkey by ID."""
        if hotkey_id not in self._registered:
            return False

        info = self._registered.pop(hotkey_id)
        name = info["name"]

        if sys.platform == "win32" and self._user32 is not None:
            try:
                self._user32.UnregisterHotKey(self._target_hwnd, hotkey_id)
            except Exception as e:
                logger.debug("Error unregistering hotkey %s: %s", name, e)

        logger.info("Unregistered global hotkey %s (id=%d)", name, hotkey_id)
        self.hotkey_unregistered.emit(name, hotkey_id)
        return True

    def unregister_all(self) -> None:
        """Unregisters all active hotkeys and cleans up the native event filter."""
        for hotkey_id in list(self._registered.keys()):
            self.unregister_hotkey(hotkey_id)

        if self._filter:
            app = QCoreApplication.instance()
            if app:
                try:
                    app.removeNativeEventFilter(self._filter)
                except Exception:
                    pass
            self._filter = None

    def set_enabled(self, enabled: bool) -> None:
        """Enables or disables dispatching of hotkey triggers."""
        self._enabled = enabled

    def simulate_hotkey(self, hotkey_id: int) -> bool:
        """
        Simulates hotkey trigger programmatically for automated tests without physical keypresses.
        """
        if hotkey_id in self._registered and self._enabled:
            self._handle_native_hotkey(hotkey_id, 0)
            return True
        return False
