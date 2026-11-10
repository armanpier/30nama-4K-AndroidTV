"""
PyQt6 User Interface package for Gemini Desktop Screenshare.
Exports MainWindow, HotkeyManager, UIStateMachine, AppState, UIAction,
and Material 3 dark styling utilities.
"""

from gemini_desktop_screenshare.ui.hotkey_manager import (
    ERROR_HOTKEY_ALREADY_REGISTERED,
    HOTKEY_ID_LIVE,
    HOTKEY_ID_ONDEMAND,
    MOD_ALT,
    MOD_NOREPEAT,
    VK_L,
    VK_S,
    WM_HOTKEY,
    HotkeyManager,
    Win32HotkeyFilter,
)
from gemini_desktop_screenshare.ui.main_window import (
    ENABLEMENT_MATRIX,
    AppState,
    CardFrame,
    MainWindow,
    UIAction,
    UIStateMachine,
    simple_markdown_to_html,
)
from gemini_desktop_screenshare.ui.styles import (
    DARK_STYLESHEET,
    PALETTE,
    apply_theme,
    configure_qt_high_dpi,
    restyle_widget,
)

__all__ = [
    "MainWindow",
    "CardFrame",
    "UIStateMachine",
    "AppState",
    "UIAction",
    "ENABLEMENT_MATRIX",
    "simple_markdown_to_html",
    "HotkeyManager",
    "Win32HotkeyFilter",
    "WM_HOTKEY",
    "HOTKEY_ID_ONDEMAND",
    "HOTKEY_ID_LIVE",
    "MOD_ALT",
    "MOD_NOREPEAT",
    "VK_S",
    "VK_L",
    "ERROR_HOTKEY_ALREADY_REGISTERED",
    "DARK_STYLESHEET",
    "PALETTE",
    "apply_theme",
    "restyle_widget",
    "configure_qt_high_dpi",
]
