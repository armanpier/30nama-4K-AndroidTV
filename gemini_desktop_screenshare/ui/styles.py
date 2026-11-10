"""
Google Material 3 Dark theme stylesheets and styling utilities for Gemini Desktop Screenshare.
Provides modern dark mode palette, card styling, buttons, status badges, dynamic property
selectors, and crisp High-DPI scaling setup.
"""

from typing import Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

# ---------------------------------------------------------------------------
# Google Material 3 Dark Palette
# ---------------------------------------------------------------------------
PALETTE: Dict[str, str] = {
    # Surfaces & Backgrounds
    "BG_WINDOW": "#202124",         # Main window dark background
    "BG_SURFACE": "#292a2d",        # Card deck surfaces
    "BG_CARD": "#292a2d",           # Alias for card deck surface
    "BG_SURFACE_HOVER": "#35363a",  # Card / panel hover
    "BG_SURFACE_ACTIVE": "#3c4043", # Active container
    "BG_INPUT": "#1e1f20",          # Recessed text inputs / transcripts
    "BG_HEADER": "#171717",         # Deep header / footer bar

    # Borders & Dividers
    "BORDER_DEFAULT": "#3c4043",    # Default subtle outline
    "BORDER": "#3c4043",            # Alias for default border
    "BORDER_HOVER": "#5f6368",      # Elevated border
    "BORDER_FOCUS": "#8ab4f8",      # High-visibility Google Blue focus ring

    # Brand & Semantic Accents
    "PRIMARY_BLUE": "#1a73e8",      # Primary action button
    "PRIMARY": "#1a73e8",           # Alias for primary
    "PRIMARY_BLUE_HOVER": "#1b66ca",# Primary hover
    "PRIMARY_BLUE_PRESSED": "#185abc", # Primary pressed
    "PRIMARY_BLUE_TEXT": "#8ab4f8", # Accent blue for dark mode typography

    "COLOR_SUCCESS": "#34a853",     # Google Green (ready/live)
    "COLOR_SUCCESS_HOVER": "#2d9247",
    "COLOR_SUCCESS_TEXT": "#81c995",

    "COLOR_DANGER": "#d93025",      # Google Red (stop/danger)
    "COLOR_DANGER_HOVER": "#b3261e",
    "COLOR_DANGER_TEXT": "#f28b82",

    "COLOR_MUTED_MIC": "#ea4335",   # Mic muted indicator
    "COLOR_MUTED_MIC_BG": "#3c1b1b",# Mic muted card/button background

    "COLOR_WARNING": "#fbbc04",     # Google Yellow
    "COLOR_PURPLE": "#c58af9",      # Gemini AI purple

    # Typography
    "TEXT_PRIMARY": "#e8eaed",      # Primary high-contrast text
    "TEXT_SECONDARY": "#9aa0a6",    # Medium contrast labels / metadata
    "TEXT_MUTED": "#70757a",        # Low contrast hints
    "TEXT_DISABLED": "#5f6368",     # Disabled control text
}

# ---------------------------------------------------------------------------
# Comprehensive QSS Stylesheet
# ---------------------------------------------------------------------------
DARK_STYLESHEET: str = f"""
/* Global Window & Font Defaults */
QMainWindow, QWidget#centralWidget {{
    background-color: {PALETTE["BG_WINDOW"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* Cards and Panels */
QFrame#CardFrame, QFrame[card="true"] {{
    background-color: {PALETTE["BG_SURFACE"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 8px;
    padding: 10px;
}}

/* Header Bar & Separators */
QFrame#HeaderBar {{
    background-color: {PALETTE["BG_HEADER"]};
    border-bottom: 1px solid {PALETTE["BORDER_DEFAULT"]};
}}

QSplitter::handle {{
    background-color: {PALETTE["BORDER_DEFAULT"]};
    width: 2px;
}}

/* Push Buttons */
QPushButton {{
    background-color: {PALETTE["BG_SURFACE_ACTIVE"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {PALETTE["BG_SURFACE_HOVER"]};
    border-color: {PALETTE["BORDER_FOCUS"]};
}}

QPushButton:pressed {{
    background-color: {PALETTE["BG_SURFACE_ACTIVE"]};
}}

QPushButton:disabled {{
    background-color: {PALETTE["BG_WINDOW"]};
    color: {PALETTE["TEXT_DISABLED"]};
    border-color: {PALETTE["BORDER_DEFAULT"]};
}}

/* Button Variants */
QPushButton[variant="primary"] {{
    background-color: {PALETTE["PRIMARY_BLUE"]};
    color: #ffffff;
    font-weight: 600;
    border: none;
}}

QPushButton[variant="primary"]:hover {{
    background-color: {PALETTE["PRIMARY_BLUE_HOVER"]};
}}

QPushButton[variant="primary"]:pressed {{
    background-color: {PALETTE["PRIMARY_BLUE_PRESSED"]};
}}

QPushButton[variant="success"] {{
    background-color: {PALETTE["COLOR_SUCCESS"]};
    color: #ffffff;
    font-weight: 600;
    border: none;
}}

QPushButton[variant="success"]:hover {{
    background-color: {PALETTE["COLOR_SUCCESS_HOVER"]};
}}

QPushButton[variant="danger"] {{
    background-color: {PALETTE["COLOR_DANGER"]};
    color: #ffffff;
    font-weight: 600;
    border: none;
}}

QPushButton[variant="danger"]:hover {{
    background-color: {PALETTE["COLOR_DANGER_HOVER"]};
}}

QPushButton[variant="chip"] {{
    background-color: {PALETTE["BG_WINDOW"]};
    color: {PALETTE["TEXT_SECONDARY"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
}}

QPushButton[variant="chip"]:hover {{
    background-color: {PALETTE["BG_SURFACE_HOVER"]};
    color: {PALETTE["PRIMARY_BLUE_TEXT"]};
    border-color: {PALETTE["BORDER_FOCUS"]};
}}

/* Dynamic Microphone States */
QPushButton[mic_state="unmuted"], QPushButton[muted="false"] {{
    background-color: {PALETTE["BG_SURFACE"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    color: {PALETTE["TEXT_PRIMARY"]};
}}

QPushButton[mic_state="unmuted"]:hover, QPushButton[muted="false"]:hover {{
    border-color: {PALETTE["COLOR_SUCCESS_TEXT"]};
    color: {PALETTE["COLOR_SUCCESS_TEXT"]};
}}

QPushButton[mic_state="muted"], QPushButton[muted="true"] {{
    background-color: {PALETTE["COLOR_MUTED_MIC_BG"]};
    border: 1px solid {PALETTE["COLOR_MUTED_MIC"]};
    color: {PALETTE["COLOR_DANGER_TEXT"]};
    font-weight: bold;
}}

QPushButton[mic_state="muted"]:hover, QPushButton[muted="true"]:hover {{
    background-color: #4e1c1c;
}}

/* Dynamic Status Badges */
QLabel[badge="ready"] {{
    background-color: #133a22;
    color: {PALETTE["COLOR_SUCCESS_TEXT"]};
    border: 1px solid {PALETTE["COLOR_SUCCESS"]};
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}}

QLabel[badge="streaming"] {{
    background-color: #172b4d;
    color: {PALETTE["PRIMARY_BLUE_TEXT"]};
    border: 1px solid {PALETTE["PRIMARY_BLUE"]};
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}}

QLabel[badge="capturing"] {{
    background-color: #3d3314;
    color: #fdd663;
    border: 1px solid {PALETTE["COLOR_WARNING"]};
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}}

QLabel[badge="error"] {{
    background-color: {PALETTE["COLOR_MUTED_MIC_BG"]};
    color: {PALETTE["COLOR_DANGER_TEXT"]};
    border: 1px solid {PALETTE["COLOR_DANGER"]};
    border-radius: 12px;
    padding: 3px 12px;
    font-weight: bold;
    font-size: 11px;
}}

QLabel[badge="signed_out"], QLabel[badge="disconnected"] {{
    background-color: {PALETTE["BG_SURFACE_ACTIVE"]};
    color: {PALETTE["TEXT_SECONDARY"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
}}

/* Radio Buttons */
QRadioButton {{
    color: {PALETTE["TEXT_PRIMARY"]};
    spacing: 8px;
    font-size: 13px;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 9px;
    border: 2px solid {PALETTE["BORDER_DEFAULT"]};
    background-color: {PALETTE["BG_WINDOW"]};
}}

QRadioButton::indicator:hover {{
    border-color: {PALETTE["BORDER_FOCUS"]};
}}

QRadioButton::indicator:checked {{
    border-color: {PALETTE["PRIMARY_BLUE"]};
    background-color: {PALETTE["PRIMARY_BLUE"]};
}}

QRadioButton::indicator:disabled {{
    border-color: {PALETTE["TEXT_DISABLED"]};
    background-color: {PALETTE["BG_SURFACE"]};
}}

/* Combo Boxes (Dropdowns) */
QComboBox {{
    background-color: {PALETTE["BG_INPUT"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}}

QComboBox:hover {{
    border-color: {PALETTE["BORDER_FOCUS"]};
}}

QComboBox:disabled {{
    background-color: {PALETTE["BG_SURFACE"]};
    color: {PALETTE["TEXT_DISABLED"]};
    border-color: {PALETTE["BORDER_DEFAULT"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {PALETTE["BG_SURFACE"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    selection-background-color: {PALETTE["PRIMARY_BLUE"]};
    selection-color: #ffffff;
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 4px;
    padding: 4px;
}}

/* Line Edits & Text Browsers */
QLineEdit {{
    background-color: {PALETTE["BG_INPUT"]};
    color: #ffffff;
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 2px solid {PALETTE["BORDER_FOCUS"]};
}}

QLineEdit:disabled {{
    background-color: {PALETTE["BG_SURFACE"]};
    color: {PALETTE["TEXT_DISABLED"]};
}}

QTextBrowser {{
    background-color: {PALETTE["BG_INPUT"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    border: 1px solid {PALETTE["BORDER_DEFAULT"]};
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    line-height: 1.5;
}}

/* Scroll Bars (Slim Modern Google Style) */
QScrollBar:vertical {{
    background-color: {PALETTE["BG_WINDOW"]};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {PALETTE["BORDER_DEFAULT"]};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {PALETTE["BORDER_FOCUS"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {PALETTE["BG_WINDOW"]};
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {PALETTE["BORDER_DEFAULT"]};
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {PALETTE["BORDER_FOCUS"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {PALETTE["BG_HEADER"]};
    color: {PALETTE["TEXT_SECONDARY"]};
    font-size: 11px;
    border-top: 1px solid {PALETTE["BORDER_DEFAULT"]};
}}

/* Tooltips */
QToolTip {{
    background-color: {PALETTE["BG_SURFACE"]};
    color: {PALETTE["TEXT_PRIMARY"]};
    border: 1px solid {PALETTE["BORDER_HOVER"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def configure_qt_high_dpi() -> None:
    """Configures high-DPI scaling policy for crisp font rendering on Windows."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def apply_theme(app: QApplication) -> None:
    """Applies high-DPI configuration and Google Material 3 dark stylesheet to QApplication."""
    configure_qt_high_dpi()
    app.setStyleSheet(DARK_STYLESHEET)


def restyle_widget(widget: QWidget) -> None:
    """Forces dynamic property stylesheet re-evaluation on a widget without flashing."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
