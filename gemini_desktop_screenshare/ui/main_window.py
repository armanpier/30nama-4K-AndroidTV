"""
PyQt6 Main Window for Gemini Desktop Screenshare.
Implements Google Material 3 dark card-deck architecture, UI state machine with central
enablement matrix, Google OAuth account management, target window picker with minimized
window protection, live preview thumbnail, rich conversation transcript with smart auto-scroll
and barge-in interruption notice, on-demand prompt dock, and thread-safe signal coordination.
"""

import ctypes
from ctypes import wintypes
from enum import Enum, auto
import html
import logging
import re
import sys
import time
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import QEvent, QObject, QRect, QSize, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QPainter,
    QPixmap,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
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
from gemini_desktop_screenshare.config import (
    AVAILABLE_MODELS,
    AppConfig,
    DEFAULT_CLIENT_ID,
    DEFAULT_CLIENT_SECRET,
    add_or_update_account,
    delete_account,
    get_active_account,
    save_config,
    switch_account,
)
from gemini_desktop_screenshare.ui.styles import PALETTE, restyle_widget

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UI State Machine & Enablement Matrix
# ---------------------------------------------------------------------------
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
    REFRESH_TOKEN = auto()
    SELECT_MODE = auto()
    SELECT_TARGET = auto()
    REFRESH_WINDOWS = auto()
    PRIMARY_ACTION = auto()
    MIC_MUTE = auto()
    PROMPT_INPUT = auto()
    SEND_PROMPT = auto()
    CLEAR_TRANSCRIPT = auto()
    COPY_TRANSCRIPT = auto()


ENABLEMENT_MATRIX: Dict[UIAction, Dict[AppState, bool]] = {
    UIAction.SIGN_IN: {
        AppState.UNAUTHENTICATED: True,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: False,
        AppState.LIVE_STREAMING: False,
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.SIGN_OUT: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,  # Must stop streaming before signing out
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.REFRESH_TOKEN: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.SELECT_MODE: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,  # Mode locked during active live stream
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.SELECT_TARGET: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,  # Target locked during active live stream
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.REFRESH_WINDOWS: {
        AppState.UNAUTHENTICATED: True,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.PRIMARY_ACTION: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: True,   # Acts as "Stop Streaming"
        AppState.ONDEMAND_CAPTURING: False, # In-flight query running
        AppState.ERROR: False,
    },
    UIAction.MIC_MUTE: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: True,   # Always interactive during stream
        AppState.ONDEMAND_CAPTURING: True,
        AppState.ERROR: False,
    },
    UIAction.PROMPT_INPUT: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: True,   # Always interactive: allows chatting during live streaming!
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.SEND_PROMPT: {
        AppState.UNAUTHENTICATED: False,
        AppState.AUTHENTICATING: False,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: True,   # Allows sending chat turns during live streaming!
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: False,
    },
    UIAction.CLEAR_TRANSCRIPT: {
        AppState.UNAUTHENTICATED: True,
        AppState.AUTHENTICATING: True,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: False,  # Prevent clearing during active stream
        AppState.ONDEMAND_CAPTURING: False,
        AppState.ERROR: True,
    },
    UIAction.COPY_TRANSCRIPT: {
        AppState.UNAUTHENTICATED: True,
        AppState.AUTHENTICATING: True,
        AppState.AUTHENTICATED_IDLE: True,
        AppState.LIVE_STREAMING: True,
        AppState.ONDEMAND_CAPTURING: True,
        AppState.ERROR: True,
    },
}


class UIStateMachine(QObject):
    """
    Manages explicit application state transitions and enforces the enablement matrix.
    """

    state_changed = pyqtSignal(object, object)  # (old_state, new_state)

    VALID_TRANSITIONS: Dict[AppState, set[AppState]] = {
        AppState.UNAUTHENTICATED: {AppState.AUTHENTICATING, AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.AUTHENTICATING: {
            AppState.AUTHENTICATED_IDLE,
            AppState.UNAUTHENTICATED,
            AppState.ERROR,
        },
        AppState.AUTHENTICATED_IDLE: {
            AppState.UNAUTHENTICATED,
            AppState.LIVE_STREAMING,
            AppState.ONDEMAND_CAPTURING,
            AppState.ERROR,
        },
        AppState.LIVE_STREAMING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ONDEMAND_CAPTURING: {AppState.AUTHENTICATED_IDLE, AppState.ERROR},
        AppState.ERROR: {
            AppState.AUTHENTICATED_IDLE,
            AppState.UNAUTHENTICATED,
            AppState.AUTHENTICATING,
        },
    }

    def __init__(self, initial_state: AppState = AppState.UNAUTHENTICATED) -> None:
        super().__init__()
        self._state: AppState = initial_state
        self._bindings: Dict[UIAction, List[QWidget]] = {act: [] for act in UIAction}

    @property
    def state(self) -> AppState:
        return self._state

    def can_transition(self, target: AppState) -> bool:
        return target in self.VALID_TRANSITIONS.get(self._state, set())

    def transition_to(self, target: AppState) -> bool:
        if not self.can_transition(target):
            logger.warning("Illegal state transition requested: %s -> %s", self._state.name, target.name)
            return False

        old = self._state
        self._state = target
        logger.info("UI State Machine transition: %s -> %s", old.name, target.name)
        self._apply_bindings()
        self.state_changed.emit(old, target)
        return True

    def register_widget(self, action: UIAction, widget: QWidget) -> None:
        if widget not in self._bindings[action]:
            self._bindings[action].append(widget)
        enabled = ENABLEMENT_MATRIX[action].get(self._state, False)
        widget.setEnabled(enabled)

    def _apply_bindings(self) -> None:
        for action, widgets in self._bindings.items():
            enabled = ENABLEMENT_MATRIX[action].get(self._state, False)
            for w in widgets:
                try:
                    w.setEnabled(enabled)
                except RuntimeError:
                    pass  # Widget may have been deleted


# ---------------------------------------------------------------------------
# Reusable Card Frame
# ---------------------------------------------------------------------------
class CardFrame(QFrame):
    """Google Material 3 styled surface card with rounded corners and subtle border."""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setProperty("card", "true")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(8)

        if title:
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet(
                f"color: {PALETTE['TEXT_SECONDARY']}; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;"
            )
            self.layout.addWidget(lbl_title)


# ---------------------------------------------------------------------------
# High-Fidelity Gemini App Markdown, Table, Scheme & Code Renderer
# ---------------------------------------------------------------------------
def render_gemini_markdown(md_text: str) -> str:
    """
    Renders GitHub-flavored markdown tables, syntax code blocks, headings,
    blockquotes, nested lists, and inline formatting into rich HTML matching
    the official Gemini App design system.
    """
    if not md_text:
        return ""

    lines = md_text.replace("\r\n", "\n").split("\n")
    html_out = []

    in_code_block = False
    code_lang = ""
    code_lines = []

    in_table = False
    table_rows = []

    in_ul = False
    in_ol = False

    def close_lists() -> str:
        nonlocal in_ul, in_ol
        res = ""
        if in_ul:
            res += "</ul>\n"
            in_ul = False
        if in_ol:
            res += "</ol>\n"
            in_ol = False
        return res

    def close_table() -> str:
        nonlocal in_table, table_rows
        if not in_table or not table_rows:
            in_table = False
            table_rows = []
            return ""

        t_html = [
            "<div style='margin: 10px 0; overflow-x: auto;'>",
            "<table style='border-collapse: collapse; width: 100%; border: 1px solid #3c4043; border-radius: 6px; font-size: 13px;'>",
        ]
        is_first = True
        for row in table_rows:
            if all(re.match(r"^:?-+:?$", cell.strip()) for cell in row if cell.strip()):
                continue

            if is_first:
                t_html.append("<tr style='background-color: #282a2d;'>")
                for cell in row:
                    formatted_cell = format_inline(cell.strip())
                    t_html.append(f"<th style='padding: 8px 12px; border: 1px solid #3c4043; text-align: left; font-weight: 600; color: #8ab4f8;'>{formatted_cell}</th>")
                t_html.append("</tr>")
                is_first = False
            else:
                bg = "#1e1f20" if len(t_html) % 2 == 0 else "#25272a"
                t_html.append(f"<tr style='background-color: {bg};'>")
                for cell in row:
                    formatted_cell = format_inline(cell.strip())
                    t_html.append(f"<td style='padding: 8px 12px; border: 1px solid #3c4043; color: #e3e3e3;'>{formatted_cell}</td>")
                t_html.append("</tr>")
        t_html.append("</table></div>\n")
        in_table = False
        table_rows = []
        return "".join(t_html)

    def format_inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(
            r"`([^`]+)`",
            r"<code style='background-color: #282a2d; color: #99c8ff; padding: 2px 5px; border-radius: 4px; font-family: Consolas, monospace; font-size: 12px;'>\1</code>",
            text,
        )
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
        text = re.sub(r"~~([^~]+)~~", r"<del style='color: #80868b;'>\1</del>", text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # 1. Code blocks
        if line.strip().startswith("```"):
            if not in_code_block:
                html_out.append(close_lists())
                html_out.append(close_table())
                in_code_block = True
                code_lang = line.strip()[3:].strip() or "code"
                code_lines = []
            else:
                in_code_block = False
                escaped_code = html.escape("\n".join(code_lines))
                block_html = f"""
                <div style='margin: 10px 0; background-color: #161719; border: 1px solid #303134; border-radius: 8px; overflow: hidden;'>
                    <div style='background-color: #202124; padding: 4px 12px; font-size: 11px; color: #9aa0a6; font-family: monospace; border-bottom: 1px solid #303134;'>
                        <span>{code_lang.upper()}</span>
                    </div>
                    <pre style='margin: 0; padding: 12px; font-family: Consolas, \"Fira Code\", monospace; font-size: 12px; line-height: 1.5; color: #e3e3e3; white-space: pre-wrap; word-break: break-all;'>{escaped_code}</pre>
                </div>
                """
                html_out.append(block_html)
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # 2. Table detection
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            html_out.append(close_lists())
            in_table = True
            cells = [c for c in stripped.split("|")[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            html_out.append(close_table())

        # 3. Headings (#, ##, ###)
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            html_out.append(close_lists())
            level = len(heading_match.group(1))
            heading_text = format_inline(heading_match.group(2))
            font_sizes = {1: "18px", 2: "16px", 3: "14px", 4: "13px", 5: "12px", 6: "11px"}
            margin_tops = {1: "14px", 2: "12px", 3: "10px", 4: "8px", 5: "6px", 6: "4px"}
            sz = font_sizes.get(level, "13px")
            mt = margin_tops.get(level, "8px")
            html_out.append(f"<h{level} style='font-size: {sz}; font-weight: 600; color: #99c8ff; margin: {mt} 0 4px 0;'>{heading_text}</h{level}>")
            i += 1
            continue

        # 4. Horizontal Rule
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
            html_out.append(close_lists())
            html_out.append("<hr style='border: none; border-top: 1px solid #3c4043; margin: 12px 0;'/>")
            i += 1
            continue

        # 5. Blockquotes (> )
        if stripped.startswith("&gt; ") or stripped.startswith("> "):
            html_out.append(close_lists())
            quote_text = format_inline(stripped.lstrip("&gt;").lstrip(">").strip())
            html_out.append(f"""
            <div style='border-left: 3px solid #8ab4f8; background-color: #202124; padding: 6px 12px; margin: 6px 0; border-radius: 0 4px 4px 0; color: #bdc1c6; font-style: italic;'>
                {quote_text}
            </div>
            """)
            i += 1
            continue

        # 6. Unordered lists (- or *)
        ul_match = re.match(r"^[\*\-]\s+(.*)$", stripped)
        if ul_match:
            if in_ol:
                html_out.append(close_lists())
            if not in_ul:
                html_out.append("<ul style='margin: 4px 0 6px 18px; padding: 0;'>")
                in_ul = True
            item_text = format_inline(ul_match.group(1))
            html_out.append(f"<li style='margin: 2px 0; color: #e3e3e3;'>{item_text}</li>")
            i += 1
            continue

        # 7. Ordered lists (1. 2.)
        ol_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if ol_match:
            if in_ul:
                html_out.append(close_lists())
            if not in_ol:
                html_out.append("<ol style='margin: 4px 0 6px 18px; padding: 0;'>")
                in_ol = True
            item_text = format_inline(ol_match.group(2))
            html_out.append(f"<li style='margin: 2px 0; color: #e3e3e3;'>{item_text}</li>")
            i += 1
            continue

        if not stripped:
            html_out.append(close_lists())
            html_out.append("<div style='height: 6px;'></div><br/>")
        else:
            html_out.append(close_lists())
            p_text = format_inline(stripped)
            html_out.append(f"<div style='margin: 3px 0; color: #e3e3e3; line-height: 1.5;'>{p_text}</div><br/>")

        i += 1

    html_out.append(close_lists())
    html_out.append(close_table())
    return "".join(html_out)

# Backward-compatibility alias
simple_markdown_to_html = render_gemini_markdown


# ---------------------------------------------------------------------------
# Add Account Dialog
# ---------------------------------------------------------------------------
class AddAccountDialog(QDialog):
    """Dialog allowing user to add a new Gemini account or API key profile."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Add Gemini Account / API Key")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {PALETTE['BG_CARD']}; color: {PALETTE['TEXT_PRIMARY']}; }}
            QLabel {{ color: {PALETTE['TEXT_PRIMARY']}; font-size: 13px; }}
            QLineEdit {{ background-color: {PALETTE['BG_INPUT']}; color: #ffffff; border: 1px solid {PALETTE['BORDER']}; padding: 7px; border-radius: 4px; font-size: 12px; }}
            QPushButton {{ padding: 7px 16px; border-radius: 4px; font-size: 13px; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        lbl_hdr = QLabel("<b>➕ Add Gemini Account or API Key</b>")
        lbl_hdr.setStyleSheet("font-size: 15px; color: #ffffff;")
        layout.addWidget(lbl_hdr)

        layout.addWidget(QLabel("Account Friendly Name / Label:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Personal Key, Work Account, etc.")
        layout.addWidget(self.txt_name)

        layout.addWidget(QLabel("Authentication Method:"))
        self.rb_key = QRadioButton("Gemini API Key (Recommended - Instant Connection)")
        self.rb_key.setChecked(True)
        self.rb_oauth = QRadioButton("Google Cloud OAuth Client ID (For Browser Login)")
        layout.addWidget(self.rb_key)
        layout.addWidget(self.rb_oauth)

        self.key_box = QWidget()
        kb_layout = QVBoxLayout(self.key_box)
        kb_layout.setContentsMargins(0, 4, 0, 0)
        lbl_hint = QLabel("Get a free key from <a href='https://aistudio.google.com/app/apikey' style='color: #8ab4f8; text-decoration: none;'>Google AI Studio (aistudio.google.com)</a>:")
        lbl_hint.setOpenExternalLinks(True)
        kb_layout.addWidget(lbl_hint)
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("Paste Gemini API Key (AIzaSy...)")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        kb_layout.addWidget(self.txt_api_key)
        layout.addWidget(self.key_box)

        self.oauth_box = QWidget()
        ob_layout = QVBoxLayout(self.oauth_box)
        ob_layout.setContentsMargins(0, 4, 0, 0)
        lbl_ohint = QLabel("OAuth Client ID from Google Cloud Console:")
        ob_layout.addWidget(lbl_ohint)
        self.txt_client_id = QLineEdit()
        self.txt_client_id.setPlaceholderText("your-client-id.apps.googleusercontent.com")
        ob_layout.addWidget(self.txt_client_id)
        layout.addWidget(self.oauth_box)
        self.oauth_box.setVisible(False)

        self.rb_key.toggled.connect(lambda chk: self.key_box.setVisible(chk))
        self.rb_oauth.toggled.connect(lambda chk: self.oauth_box.setVisible(chk))

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Switch")
        btn_save.setStyleSheet(f"background-color: {PALETTE['PRIMARY']}; color: #ffffff; font-weight: bold;")
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _save(self) -> None:
        name = self.txt_name.text().strip() or "Gemini Account"
        if self.rb_key.isChecked():
            key = self.txt_api_key.text().strip()
            if not key:
                QMessageBox.warning(self, "Missing Key", "Please enter a Gemini API key.")
                return
            add_or_update_account(self.config, name=name, auth_type="api_key", api_key=key)
        else:
            cid = self.txt_client_id.text().strip()
            if not cid:
                QMessageBox.warning(self, "Missing Client ID", "Please enter an OAuth Client ID.")
                return
            add_or_update_account(self.config, name=name, auth_type="oauth", client_id=cid)
        self.accept()


# ---------------------------------------------------------------------------
# Settings & Credentials Dialog
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    """Dialog allowing configuration of Gemini Accounts, API Keys, and Network Proxy."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Gemini Accounts & Settings")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {PALETTE['BG_CARD']}; color: {PALETTE['TEXT_PRIMARY']}; }}
            QLabel {{ color: {PALETTE['TEXT_PRIMARY']}; font-size: 13px; }}
            QLineEdit {{ background-color: {PALETTE['BG_INPUT']}; color: #ffffff; border: 1px solid {PALETTE['BORDER']}; padding: 7px; border-radius: 4px; font-size: 12px; }}
            QPushButton {{ padding: 7px 16px; border-radius: 4px; font-size: 13px; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        lbl_title = QLabel("⚙ Settings & Gemini Accounts")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_title)

        # Accounts Management Section
        lbl_acc_hdr = QLabel("<b>1. Saved Gemini Accounts / API Keys:</b>")
        layout.addWidget(lbl_acc_hdr)

        acc_mgmt_row = QHBoxLayout()
        self.cb_settings_accounts = QComboBox()
        self.cb_settings_accounts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._populate_accounts()
        self.cb_settings_accounts.currentIndexChanged.connect(self._on_account_changed)
        acc_mgmt_row.addWidget(self.cb_settings_accounts, 1)

        btn_add_acc = QPushButton("➕ Add")
        btn_add_acc.clicked.connect(self._add_account)
        acc_mgmt_row.addWidget(btn_add_acc)

        self.btn_del_acc = QPushButton("🗑 Delete")
        self.btn_del_acc.clicked.connect(self._delete_account)
        acc_mgmt_row.addWidget(self.btn_del_acc)
        layout.addLayout(acc_mgmt_row)

        # Option 1: Gemini API Key for Active Account
        lbl_api_hdr = QLabel("<b>Active Account API Key:</b>")
        layout.addWidget(lbl_api_hdr)

        lbl_api_link = QLabel(
            "Free Gemini API key from: "
            "<a href='https://aistudio.google.com/app/apikey' style='color: #8ab4f8; text-decoration: none;'>Google AI Studio (aistudio.google.com)</a>"
        )
        lbl_api_link.setOpenExternalLinks(True)
        layout.addWidget(lbl_api_link)

        self.txt_api_key = QLineEdit(self.config.api_key or "")
        self.txt_api_key.setPlaceholderText("Paste your Gemini API key (AIzaSy...)")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        layout.addWidget(self.txt_api_key)

        layout.addSpacing(6)

        # Option 2: Google Cloud OAuth
        lbl_oauth_hdr = QLabel("<b>Google Cloud OAuth Client ID (Optional for browser sign-in):</b>")
        layout.addWidget(lbl_oauth_hdr)

        self.txt_client_id = QLineEdit(
            self.config.client_id if self.config.client_id != DEFAULT_CLIENT_ID else ""
        )
        self.txt_client_id.setPlaceholderText("your-client-id.apps.googleusercontent.com")
        layout.addWidget(self.txt_client_id)

        self.txt_client_secret = QLineEdit(
            self.config.client_secret if self.config.client_secret != DEFAULT_CLIENT_SECRET else ""
        )
        self.txt_client_secret.setPlaceholderText("Client secret (optional)")
        self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        layout.addWidget(self.txt_client_secret)

        layout.addSpacing(6)

        # Section 3: Network Proxy (Optional)
        lbl_proxy_hdr = QLabel("<b>2. Network Proxy (Auto-detected for restricted regions):</b>")
        layout.addWidget(lbl_proxy_hdr)
        lbl_proxy_hint = QLabel("e.g. <code>http://127.0.0.1:10808</code> for v2ray/xray. Leave blank for direct connection.")
        layout.addWidget(lbl_proxy_hint)

        self.txt_proxy = QLineEdit(self.config.proxy or "")
        self.txt_proxy.setPlaceholderText("http://127.0.0.1:10808")
        layout.addWidget(self.txt_proxy)

        layout.addSpacing(10)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Connect")
        btn_save.setStyleSheet(f"background-color: {PALETTE['PRIMARY']}; color: #ffffff; font-weight: bold;")
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _populate_accounts(self) -> None:
        self.cb_settings_accounts.blockSignals(True)
        self.cb_settings_accounts.clear()
        selected_idx = 0
        for idx, acc in enumerate(self.config.accounts):
            acc_id = acc.get("id", "")
            name = acc.get("name", "Account")
            atype = acc.get("auth_type", "api_key")
            label = f"👤 {name} ({atype})"
            self.cb_settings_accounts.addItem(label, acc_id)
            if acc_id == self.config.active_account_id:
                selected_idx = idx

        if self.cb_settings_accounts.count() > 0:
            self.cb_settings_accounts.setCurrentIndex(selected_idx)
        self.cb_settings_accounts.blockSignals(False)

    def _on_account_changed(self, idx: int) -> None:
        acc_id = self.cb_settings_accounts.currentData()
        if acc_id:
            switch_account(self.config, acc_id)
            self.txt_api_key.setText(self.config.api_key or "")
            cid = self.config.client_id if self.config.client_id != DEFAULT_CLIENT_ID else ""
            self.txt_client_id.setText(cid)

    def _add_account(self) -> None:
        dlg = AddAccountDialog(self.config, self)
        if dlg.exec():
            self._populate_accounts()
            self._on_account_changed(self.cb_settings_accounts.currentIndex())

    def _delete_account(self) -> None:
        acc_id = self.cb_settings_accounts.currentData()
        if not acc_id:
            return
        if len(self.config.accounts) <= 1:
            QMessageBox.information(self, "Cannot Delete", "At least one account profile must remain.")
            return
        reply = QMessageBox.question(
            self,
            "Delete Account",
            "Are you sure you want to remove this account profile?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_account(self.config, acc_id)
            self._populate_accounts()
            self._on_account_changed(self.cb_settings_accounts.currentIndex())

    def _save(self) -> None:
        api_key = self.txt_api_key.text().strip()
        client_id = self.txt_client_id.text().strip() or DEFAULT_CLIENT_ID
        client_secret = self.txt_client_secret.text().strip() or DEFAULT_CLIENT_SECRET
        proxy = self.txt_proxy.text().strip()

        self.config.api_key = api_key
        self.config.client_id = client_id
        self.config.client_secret = client_secret
        self.config.proxy = proxy

        # Update active account in accounts list as well
        active = get_active_account(self.config)
        if active:
            active["api_key"] = api_key
            if client_id != DEFAULT_CLIENT_ID:
                active["client_id"] = client_id
            if client_secret != DEFAULT_CLIENT_SECRET:
                active["client_secret"] = client_secret

        save_config(self.config)
        self.accept()


# ---------------------------------------------------------------------------
# Main Window Implementation
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    """
    Main Application Window for Gemini Desktop Screenshare.
    Coordinates UI widgets, captures, audio state, and signals with AsyncWorker.
    """

    def __init__(
        self,
        worker: Any,
        config: AppConfig,
        hotkey_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.worker = worker
        self.config = config
        self.hotkey_manager = hotkey_manager

        self.state_machine = UIStateMachine(initial_state=AppState.UNAUTHENTICATED)
        self.current_mode = "LIVE"  # "LIVE" or "ONDEMAND"
        self.active_target_type = CaptureTarget.FULL_SCREEN
        self.active_target_id: Any = 0
        self.is_muted: bool = False

        self._in_turn: bool = False
        self._current_model_tokens: List[str] = []

        self.setWindowTitle("Gemini Desktop Screenshare")
        self.setMinimumSize(1024, 720)
        self.resize(1120, 820)

        self._init_ui()
        self._register_state_machine_widgets()
        self._connect_signals()
        self._init_preview_timer()

    # -----------------------------------------------------------------------
    # UI Hierarchy Construction
    # -----------------------------------------------------------------------
    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # 1. Header Bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        lbl_app_title = QLabel("Gemini Desktop Screenshare")
        lbl_app_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_bar.addWidget(lbl_app_title)

        header_bar.addStretch()

        self.lbl_model_pill = QLabel(f"⚡ {self.config.model.split('/')[-1]}")
        self.lbl_model_pill.setStyleSheet(
            f"background-color: {PALETTE['BG_CARD']}; border: 1px solid {PALETTE['BORDER']}; "
            "border-radius: 12px; padding: 4px 12px; font-size: 11px; color: #8ab4f8; font-weight: bold;"
        )
        header_bar.addWidget(self.lbl_model_pill)

        self.lbl_status_pill = QLabel("● Signed Out")
        self.lbl_status_pill.setProperty("badge", "signed_out")
        restyle_widget(self.lbl_status_pill)
        header_bar.addWidget(self.lbl_status_pill)
        main_layout.addLayout(header_bar)

        # 2. Main Content Splitter (Left Controls Deck, Right Transcript Deck)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(8)
        content_splitter.setStyleSheet("QSplitter::handle { background: #303134; }")
        main_layout.addWidget(content_splitter, 1)

        # Left Deck: Scrollable Container (Fixed ~380px)
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
        self._build_model_card(left_layout)
        self._build_mode_card(left_layout)
        self._build_target_card(left_layout)
        self._build_controls_card(left_layout)
        self._build_preview_card(left_layout)
        left_layout.addStretch()

        scroll_area.setWidget(left_container)
        content_splitter.addWidget(scroll_area)

        # Right Deck: Interaction & Conversation Transcript
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)
        self._build_transcript_deck(right_layout)

        content_splitter.addWidget(right_container)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)

        # 3. Status Bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet(f"background-color: {PALETTE['BG_HEADER']}; color: {PALETTE['TEXT_SECONDARY']}; font-size: 11px;")
        self.setStatusBar(self.status_bar)

        self.sb_auth = QLabel("Auth: Signed Out")
        self.sb_target = QLabel("Target: Full Desktop")
        self.sb_audio = QLabel("Audio: 16kHz In / 24kHz Out")
        self.status_bar.addWidget(self.sb_auth, 2)
        self.status_bar.addWidget(self.sb_target, 3)
        self.status_bar.addWidget(self.sb_audio, 2)

    def _build_account_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_account = CardFrame(title="Gemini Account")

        # Account Switcher Row
        acc_row = QHBoxLayout()
        acc_row.setSpacing(6)
        self.cb_accounts = QComboBox()
        self.cb_accounts.setToolTip("Select or switch active Gemini account profile")
        self.cb_accounts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._populate_account_card_combo()
        self.cb_accounts.currentIndexChanged.connect(self._on_account_card_combo_changed)
        acc_row.addWidget(self.cb_accounts, 1)

        self.btn_card_add_account = QPushButton("➕")
        self.btn_card_add_account.setToolTip("Add new Gemini API Key or Account")
        self.btn_card_add_account.setFixedWidth(34)
        self.btn_card_add_account.clicked.connect(self._on_add_account_clicked)
        acc_row.addWidget(self.btn_card_add_account)
        self.card_account.layout.addLayout(acc_row)

        user_info_layout = QHBoxLayout()
        self.lbl_user_avatar = QLabel("👤")
        self.lbl_user_avatar.setStyleSheet("font-size: 22px; padding: 4px;")
        user_info_layout.addWidget(self.lbl_user_avatar)

        name_email_layout = QVBoxLayout()
        name_email_layout.setSpacing(2)
        self.lbl_user_name = QLabel("Not Signed In")
        self.lbl_user_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #e8eaed;")
        name_email_layout.addWidget(self.lbl_user_name)

        self.lbl_user_email = QLabel("Sign in to connect to Gemini Live API")
        self.lbl_user_email.setStyleSheet(f"font-size: 12px; color: {PALETTE['TEXT_SECONDARY']};")
        name_email_layout.addWidget(self.lbl_user_email)
        user_info_layout.addLayout(name_email_layout)
        user_info_layout.addStretch()

        self.card_account.layout.addLayout(user_info_layout)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_signin = QPushButton("Sign In with Google")
        self.btn_signin.setProperty("variant", "primary")
        self.btn_signin.clicked.connect(self._on_signin_clicked)
        btn_box.addWidget(self.btn_signin)

        self.btn_signout = QPushButton("Sign Out")
        self.btn_signout.clicked.connect(self._on_signout_clicked)
        self.btn_signout.setVisible(False)
        btn_box.addWidget(self.btn_signout)

        self.btn_refresh_token = QPushButton("↻ Refresh Token")
        self.btn_refresh_token.setToolTip("Proactively refresh Google OAuth access token")
        self.btn_refresh_token.clicked.connect(self._on_refresh_token_clicked)
        self.btn_refresh_token.setVisible(False)
        btn_box.addWidget(self.btn_refresh_token)

        self.btn_settings = QPushButton("⚙ Manage Accounts")
        self.btn_settings.setToolTip("Manage accounts, API keys, and network proxy")
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        btn_box.addWidget(self.btn_settings)

        self.card_account.layout.addLayout(btn_box)
        parent_layout.addWidget(self.card_account)

    def _build_model_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_model = CardFrame(title="AI Model")

        self.cb_models = QComboBox()
        self.cb_models.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        current_model = self.config.model
        selected_idx = 0
        for idx, (label, model_id, desc) in enumerate(AVAILABLE_MODELS):
            self.cb_models.addItem(f"{label}", model_id)
            self.cb_models.setItemData(idx, desc, Qt.ItemDataRole.ToolTipRole)
            if model_id == current_model or model_id.split("/")[-1] == current_model.split("/")[-1]:
                selected_idx = idx

        self.cb_models.addItem("✏ Custom Model Name...", "custom")
        self.cb_models.setCurrentIndex(selected_idx)
        self.cb_models.currentIndexChanged.connect(self._on_model_selected)
        self.card_model.layout.addWidget(self.cb_models)

        desc_text = AVAILABLE_MODELS[selected_idx][2] if selected_idx < len(AVAILABLE_MODELS) else ""
        self.lbl_model_desc = QLabel(desc_text)
        self.lbl_model_desc.setWordWrap(True)
        self.lbl_model_desc.setStyleSheet(f"color: {PALETTE['TEXT_SECONDARY']}; font-size: 11px; margin-top: 2px;")
        self.card_model.layout.addWidget(self.lbl_model_desc)

        parent_layout.addWidget(self.card_model)

    def _build_mode_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_mode = CardFrame(title="Interaction Mode")

        self.mode_group = QButtonGroup(self)
        self.rb_live = QRadioButton("Continuous Live Streaming")
        self.rb_live.setToolTip("Streams 1 FPS screen frames and bidirectional microphone/speaker audio")
        self.rb_live.setChecked(True)
        self.mode_group.addButton(self.rb_live)
        self.card_mode.layout.addWidget(self.rb_live)

        self.rb_ondemand = QRadioButton("On-Demand Screen Capture")
        self.rb_ondemand.setToolTip("Captures an instant snapshot on button trigger and sends a custom query")
        self.mode_group.addButton(self.rb_ondemand)
        self.card_mode.layout.addWidget(self.rb_ondemand)

        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        parent_layout.addWidget(self.card_mode)

    def _build_target_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_target = CardFrame(title="Capture Target")

        self.cb_target_type = QComboBox()
        self.cb_target_type.addItems(["Full Desktop (All Displays)", "Application Window"])
        self.cb_target_type.currentIndexChanged.connect(self._on_target_type_changed)
        self.card_target.layout.addWidget(self.cb_target_type)

        # Window Selection Combo & Refresh Button Row
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
        self.btn_refresh_wins.setFixedWidth(36)
        self.btn_refresh_wins.clicked.connect(self._on_refresh_windows_clicked)
        win_layout.addWidget(self.btn_refresh_wins)

        self.window_picker_row.setVisible(False)
        self.card_target.layout.addWidget(self.window_picker_row)

        parent_layout.addWidget(self.card_target)

    def _build_controls_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_controls = CardFrame(title="Session Controls")

        self.btn_primary_action = QPushButton("Start Live Streaming")
        self.btn_primary_action.setFixedHeight(44)
        self.btn_primary_action.setProperty("variant", "success")
        self.btn_primary_action.clicked.connect(self._on_primary_action_clicked)
        self.card_controls.layout.addWidget(self.btn_primary_action)

        self.btn_mic_mute = QPushButton("🎤 Microphone: Active (Unmuted)")
        self.btn_mic_mute.setFixedHeight(38)
        self.btn_mic_mute.setProperty("mic_state", "unmuted")
        restyle_widget(self.btn_mic_mute)
        self.btn_mic_mute.clicked.connect(self._on_mic_mute_clicked)
        self.card_controls.layout.addWidget(self.btn_mic_mute)

        self.lbl_hotkeys = QLabel("Hotkeys: Alt+L (Live Toggle) | Alt+S (Capture Snapshot)")
        self.lbl_hotkeys.setStyleSheet(f"color: {PALETTE['TEXT_MUTED']}; font-size: 11px;")
        self.lbl_hotkeys.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_controls.layout.addWidget(self.lbl_hotkeys)

        parent_layout.addWidget(self.card_controls)

    def _build_preview_card(self, parent_layout: QVBoxLayout) -> None:
        self.card_preview = CardFrame(title="Live Target Preview")

        self.lbl_preview = QLabel("Preview will appear here")
        self.lbl_preview.setMinimumSize(340, 192)
        self.lbl_preview.setMaximumHeight(220)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet(f"""
            background-color: {PALETTE['BG_INPUT']};
            border: 1px dashed {PALETTE['BORDER_DEFAULT']};
            border-radius: 6px;
            color: {PALETTE['TEXT_MUTED']};
            font-size: 12px;
        """)
        self.card_preview.layout.addWidget(self.lbl_preview)
        parent_layout.addWidget(self.card_preview)

    def _build_transcript_deck(self, parent_layout: QVBoxLayout) -> None:
        header_row = QHBoxLayout()
        lbl_deck_title = QLabel("Conversation & Live Transcript")
        lbl_deck_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e8eaed;")
        header_row.addWidget(lbl_deck_title)

        header_row.addStretch()

        self.btn_copy_transcript = QPushButton("Copy")
        self.btn_copy_transcript.setToolTip("Copy transcript to clipboard")
        self.btn_copy_transcript.clicked.connect(self._on_copy_transcript_clicked)
        header_row.addWidget(self.btn_copy_transcript)

        self.btn_clear_transcript = QPushButton("Clear")
        self.btn_clear_transcript.setToolTip("Clear conversation history")
        self.btn_clear_transcript.clicked.connect(self._on_clear_transcript_clicked)
        header_row.addWidget(self.btn_clear_transcript)
        parent_layout.addLayout(header_row)

        # Transcript Display
        self.txt_transcript = QTextBrowser()
        self.txt_transcript.setReadOnly(True)
        self.txt_transcript.setOpenExternalLinks(True)
        parent_layout.addWidget(self.txt_transcript, 1)

        # Smart Auto-Scroll "Jump to Latest" Button
        self.btn_jump_latest = QPushButton("↓ Jump to Latest")
        self.btn_jump_latest.setProperty("variant", "chip")
        self.btn_jump_latest.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        self.btn_jump_latest.clicked.connect(self._on_jump_latest_clicked)
        self.btn_jump_latest.setVisible(False)
        parent_layout.addWidget(self.btn_jump_latest, 0, Qt.AlignmentFlag.AlignRight)

        # On-Demand & Live Chat Prompt Dock (Always Visible)
        self.dock_prompt = QFrame()
        self.dock_prompt.setObjectName("CardFrame")
        self.dock_prompt.setProperty("card", "true")
        dock_layout = QVBoxLayout(self.dock_prompt)
        dock_layout.setContentsMargins(8, 8, 8, 8)
        dock_layout.setSpacing(6)

        # Quick Preset Chips + Screen Context Checkbox
        top_dock_row = QHBoxLayout()
        top_dock_row.setSpacing(6)
        presets = [
            ("🔍 Explain Screen", "Explain what is currently displayed on this screen."),
            ("📝 Summarize", "Summarize the key information and text shown in this window."),
            ("🐛 Detect Errors", "Identify any errors, bugs, or warnings visible in this screenshot."),
            ("🌐 Translate", "Translate the visible text into English and explain its meaning."),
        ]
        for label, query in presets:
            btn_chip = QPushButton(label)
            btn_chip.setProperty("variant", "chip")
            btn_chip.clicked.connect(lambda _, q=query: self._on_preset_chip_clicked(q))
            top_dock_row.addWidget(btn_chip)

        top_dock_row.addStretch()

        self.chk_include_screen = QCheckBox("Share Screen Context")
        self.chk_include_screen.setChecked(True)
        self.chk_include_screen.setToolTip("Attach desktop/window screen frame to your message")
        self.chk_include_screen.setStyleSheet("color: #9aa0a6; font-size: 11px;")
        top_dock_row.addWidget(self.chk_include_screen)

        dock_layout.addLayout(top_dock_row)

        # Input box + Send Button
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.txt_prompt_input = QLineEdit()
        self.txt_prompt_input.setPlaceholderText("Chat with Gemini or ask about your screen...")
        self.txt_prompt_input.returnPressed.connect(self._on_send_prompt_clicked)
        input_row.addWidget(self.txt_prompt_input, 1)

        self.btn_send_prompt = QPushButton("Send")
        self.btn_send_prompt.setProperty("variant", "primary")
        self.btn_send_prompt.clicked.connect(self._on_send_prompt_clicked)
        input_row.addWidget(self.btn_send_prompt)

        dock_layout.addLayout(input_row)

        self.dock_prompt.setVisible(True)  # Always visible for in-app chat!
        parent_layout.addWidget(self.dock_prompt)

    def _register_state_machine_widgets(self) -> None:
        """Binds UI widgets to the central State Machine enablement matrix."""
        self.state_machine.register_widget(UIAction.SIGN_IN, self.btn_signin)
        self.state_machine.register_widget(UIAction.SIGN_OUT, self.btn_signout)
        self.state_machine.register_widget(UIAction.REFRESH_TOKEN, self.btn_refresh_token)
        self.state_machine.register_widget(UIAction.SELECT_MODE, self.rb_live)
        self.state_machine.register_widget(UIAction.SELECT_MODE, self.rb_ondemand)
        self.state_machine.register_widget(UIAction.SELECT_TARGET, self.cb_target_type)
        self.state_machine.register_widget(UIAction.SELECT_TARGET, self.cb_windows)
        self.state_machine.register_widget(UIAction.REFRESH_WINDOWS, self.btn_refresh_wins)
        self.state_machine.register_widget(UIAction.PRIMARY_ACTION, self.btn_primary_action)
        self.state_machine.register_widget(UIAction.MIC_MUTE, self.btn_mic_mute)
        self.state_machine.register_widget(UIAction.PROMPT_INPUT, self.txt_prompt_input)
        self.state_machine.register_widget(UIAction.SEND_PROMPT, self.btn_send_prompt)
        self.state_machine.register_widget(UIAction.CLEAR_TRANSCRIPT, self.btn_clear_transcript)
        self.state_machine.register_widget(UIAction.COPY_TRANSCRIPT, self.btn_copy_transcript)

    # -----------------------------------------------------------------------
    # Signal Connections
    # -----------------------------------------------------------------------
    def _connect_signals(self) -> None:
        # Worker -> GUI Thread Slots
        self.worker.sig_auth_state_changed.connect(self.on_auth_state_changed)
        self.worker.sig_connection_state_changed.connect(self.on_connection_state_changed)
        self.worker.sig_text_token.connect(self.on_text_token_received)
        self.worker.sig_interrupted.connect(self.on_interrupted_received)
        self.worker.sig_turn_complete.connect(self.on_turn_complete_received)
        self.worker.sig_preview_frame.connect(self.on_preview_frame_received)
        self.worker.sig_ondemand_result.connect(self.on_ondemand_result_received)
        self.worker.sig_windows_enumerated.connect(self.on_windows_enumerated_received)
        self.worker.sig_error.connect(self.on_error_received)

        # Hotkey Manager Signals (if available)
        if self.hotkey_manager is not None:
            self.hotkey_manager.on_demand_triggered.connect(self._on_hotkey_ondemand)
            self.hotkey_manager.live_toggle_triggered.connect(self._on_hotkey_live_toggle)
            self.hotkey_manager.hotkey_conflict.connect(self._on_hotkey_conflict)

        # Scrollbar Tracking for Smart Auto-Scroll
        sb = self.txt_transcript.verticalScrollBar()
        sb.valueChanged.connect(self._on_transcript_scroll)

    def _init_preview_timer(self) -> None:
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(1500)  # 1.5s refresh when idle
        self.preview_timer.timeout.connect(self._on_preview_timer_tick)
        self.preview_timer.start()

    # -----------------------------------------------------------------------
    # Worker Inbound Slots
    # -----------------------------------------------------------------------
    @pyqtSlot(bool, dict)
    def on_auth_state_changed(self, is_authenticated: bool, profile: dict) -> None:
        """Handles authentication updates from AsyncWorker."""
        active_acc = get_active_account(self.config)
        if is_authenticated:
            name = profile.get("name") or (active_acc.get("name") if active_acc else "Google User")
            email = profile.get("email") or (active_acc.get("email") if active_acc else "Authenticated")
            self.lbl_user_name.setText(name)
            self.lbl_user_email.setText(email)
            self.btn_signin.setVisible(False)
            self.btn_signout.setVisible(True)
            self.btn_refresh_token.setVisible(True)
            self.sb_auth.setText(f"Auth: {email}")

            if self.state_machine.state in (AppState.UNAUTHENTICATED, AppState.AUTHENTICATING):
                self.state_machine.transition_to(AppState.AUTHENTICATED_IDLE)
        elif self.config.api_key:
            name = active_acc.get("name") if active_acc else "Gemini API Account"
            key_snip = f"{self.config.api_key[:6]}...{self.config.api_key[-4:]}"
            self.lbl_user_name.setText(name)
            self.lbl_user_email.setText(f"API Key: {key_snip}")
            self.btn_signin.setVisible(False)
            self.btn_signout.setVisible(True)
            self.btn_refresh_token.setVisible(False)
            self.sb_auth.setText(f"Auth: API Key ({key_snip})")

            if self.state_machine.state in (AppState.UNAUTHENTICATED, AppState.AUTHENTICATING):
                self.state_machine.transition_to(AppState.AUTHENTICATED_IDLE)
        else:
            self.lbl_user_name.setText("Not Signed In")
            self.lbl_user_email.setText("Sign in or add API key to connect")
            self.btn_signin.setVisible(True)
            self.btn_signout.setVisible(False)
            self.btn_refresh_token.setVisible(False)
            self.sb_auth.setText("Auth: Signed Out")

            if self.state_machine.state != AppState.UNAUTHENTICATED:
                self.state_machine.transition_to(AppState.UNAUTHENTICATED)

        self._populate_account_card_combo()
        self._update_primary_button_visuals()

    @pyqtSlot(str)
    def on_connection_state_changed(self, state: str) -> None:
        """Synchronizes UI state with streaming/capturing state."""
        logger.info("Connection state update: %s", state)

        if state == "AUTHENTICATING":
            if self.state_machine.can_transition(AppState.AUTHENTICATING):
                self.state_machine.transition_to(AppState.AUTHENTICATING)
            self.lbl_status_pill.setText("● Authenticating...")
            self.lbl_status_pill.setProperty("badge", "capturing")
            restyle_widget(self.lbl_status_pill)

        elif state == "CONNECTING":
            self.lbl_status_pill.setText("● Connecting...")
            self.lbl_status_pill.setProperty("badge", "capturing")
            restyle_widget(self.lbl_status_pill)
            self.btn_primary_action.setText("Connecting...")

        elif state == "STREAMING":
            if self.state_machine.can_transition(AppState.LIVE_STREAMING):
                self.state_machine.transition_to(AppState.LIVE_STREAMING)
            self.lbl_status_pill.setText("● Live Streaming")
            self.lbl_status_pill.setProperty("badge", "streaming")
            restyle_widget(self.lbl_status_pill)
            self._update_primary_button_visuals()

        elif state == "CAPTURING":
            if self.state_machine.can_transition(AppState.ONDEMAND_CAPTURING):
                self.state_machine.transition_to(AppState.ONDEMAND_CAPTURING)
            self.lbl_status_pill.setText("● Analyzing...")
            self.lbl_status_pill.setProperty("badge", "capturing")
            restyle_widget(self.lbl_status_pill)
            self.btn_primary_action.setText("Analyzing Screen...")
            self.btn_send_prompt.setText("Analyzing...")

        elif state in ("READY", "DISCONNECTED"):
            if self.state_machine.state in (AppState.LIVE_STREAMING, AppState.ONDEMAND_CAPTURING):
                self.state_machine.transition_to(AppState.AUTHENTICATED_IDLE)
            elif self.state_machine.state == AppState.AUTHENTICATING:
                self.state_machine.transition_to(
                    AppState.AUTHENTICATED_IDLE if self.btn_signout.isVisible() else AppState.UNAUTHENTICATED
                )

            is_auth = self.state_machine.state != AppState.UNAUTHENTICATED
            self.lbl_status_pill.setText("● Ready" if is_auth else "● Signed Out")
            self.lbl_status_pill.setProperty("badge", "ready" if is_auth else "signed_out")
            restyle_widget(self.lbl_status_pill)
            self._update_primary_button_visuals()
            self.btn_send_prompt.setText("Send Query")

    @pyqtSlot(str)
    def on_text_token_received(self, token: str) -> None:
        """Appends streaming text tokens cleanly."""
        if not self._in_turn:
            self._in_turn = True
            self._current_model_tokens = []
            timestamp = time.strftime("%H:%M:%S")
            self._append_html(f"""
                <div style='margin-top: 8px; margin-bottom: 2px;'>
                    <span style='color: {PALETTE["COLOR_PURPLE"]}; font-weight: bold; font-size: 11px;'>✨ Gemini &bull; {timestamp}</span>
                </div>
            """)

        # Remember whether user was anchored at bottom before appending
        was_at_bottom = not self.btn_jump_latest.isVisible()
        self._current_model_tokens.append(token)

        # Insert text into underlying document without forcing widget cursor jump
        cursor = QTextCursor(self.txt_transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)

        # If user was anchored at bottom, scroll to bottom; otherwise preserve user's scroll position
        if was_at_bottom:
            sb = self.txt_transcript.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            # User is reading past history: ensure jump button remains visible
            self.btn_jump_latest.setVisible(True)

    @pyqtSlot()
    def on_interrupted_received(self) -> None:
        """Renders visual interruption notice when user speech triggers barge-in."""
        self._in_turn = False
        self._append_html(f"""
            <div style='color: {PALETTE["COLOR_DANGER_TEXT"]}; font-style: italic; font-size: 11px; margin: 4px 0 8px 0;'>
                &mdash; ⚡ Interrupted by user speech &mdash;
            </div>
        """)

    @pyqtSlot()
    def on_turn_complete_received(self) -> None:
        """Concludes active model turn."""
        self._in_turn = False
        self._append_html("<br/>")

    @pyqtSlot(QImage)
    def on_preview_frame_received(self, qimg: QImage) -> None:
        """Renders incoming thumbnail preview frame."""
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self.lbl_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_preview.setPixmap(scaled)

    @pyqtSlot(str)
    def on_ondemand_result_received(self, result_text: str) -> None:
        """Renders structured response matching the official Gemini App card format."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_body = render_gemini_markdown(result_text)
        
        # Pretty model name display
        raw_model = getattr(self.config, "model", "gemini-3.5-flash")
        model_display = raw_model.split("/")[-1].replace("-", " ").title()

        self._append_html(f"""
            <div style='margin: 10px 0 14px 0; text-align: left;'>
                <div style='background-color: #1e1f20; border: 1px solid #3c4043; border-radius: 4px 16px 16px 16px; padding: 14px 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);'>
                    <div style='margin-bottom: 8px; border-bottom: 1px solid #2d2f31; padding-bottom: 6px;'>
                        <span style='font-size: 14px;'>✨</span>
                        <span style='font-weight: 700; color: #8ab4f8; font-size: 12px; margin-left: 4px;'>Gemini</span>
                        <span style='background-color: #282a2d; color: #c4c7c5; padding: 1px 7px; border-radius: 4px; font-size: 10px; margin-left: 6px; font-weight: 600;'>{model_display}</span>
                        <span style='color: #80868b; font-size: 11px; margin-left: 8px;'>&bull; {timestamp}</span>
                    </div>
                    <div style='color: #e3e3e3; font-size: 13px; line-height: 1.6;'>
                        {formatted_body}
                    </div>
                </div>
            </div>
        """)
        self._update_primary_button_visuals()

    @pyqtSlot(list)
    def on_windows_enumerated_received(self, windows: List[Dict[str, Any]]) -> None:
        """Populates the window selection combo box preserving selection if still valid."""
        current_hwnd = self.cb_windows.currentData()
        self.cb_windows.blockSignals(True)
        self.cb_windows.clear()

        selected_idx = 0
        for idx, win in enumerate(windows):
            hwnd = win.get("hwnd", 0)
            title = win.get("title", "")
            is_min = win.get("is_minimized", False)
            w = win.get("width", 0)
            h = win.get("height", 0)

            prefix = "🗕 [Minimized] " if is_min else "🗔 "
            truncated = (title[:40] + "...") if len(title) > 40 else title
            display_text = f"{prefix}{truncated} ({w}x{h})"

            target_spec = {
                "type": CaptureTarget.WINDOW,
                "id": hwnd,
                "title": title,
                "is_minimized": is_min,
                "width": w,
                "height": h,
            }
            self.cb_windows.addItem(display_text, target_spec)
            self.cb_windows.setItemData(
                idx,
                f"Title: {title}\nHWND: {hwnd} (0x{hwnd:08X})\nSize: {w}x{h}\nState: {'Minimized' if is_min else 'Normal'}",
                Qt.ItemDataRole.ToolTipRole,
            )

            if current_hwnd and hwnd == current_hwnd.get("id"):
                selected_idx = idx

        self.cb_windows.setCurrentIndex(selected_idx)
        self.cb_windows.blockSignals(False)

        if self.cb_windows.count() > 0 and self.active_target_type == CaptureTarget.WINDOW:
            self._on_window_selected(selected_idx)

    @pyqtSlot(str)
    def on_error_received(self, error_msg: str) -> None:
        """Renders error notification banner."""
        timestamp = time.strftime("%H:%M:%S")
        safe_msg = html.escape(error_msg)
        self._append_html(f"""
            <div style='background-color: {PALETTE["COLOR_MUTED_MIC_BG"]}; border-left: 3px solid {PALETTE["COLOR_DANGER"]}; padding: 8px 12px; margin: 6px 0; border-radius: 4px; color: {PALETTE["COLOR_DANGER_TEXT"]};'>
                <strong>⚠️ Error ({timestamp}):</strong> {safe_msg}
            </div>
        """)
        self.status_bar.showMessage(f"Error: {error_msg}", 5000)

    # -----------------------------------------------------------------------
    # User Action Handlers
    # -----------------------------------------------------------------------
    def _on_signin_clicked(self) -> None:
        if self.config.client_id == DEFAULT_CLIENT_ID and not self.config.api_key:
            reply = QMessageBox.information(
                self,
                "Authentication Setup",
                "To connect to Google Gemini, please configure your credentials:\n\n"
                "• Option 1 (Recommended): Enter a free Gemini API Key (instant connection)\n"
                "• Option 2: Enter your Google Cloud OAuth Client ID (for Google Account browser login)\n\n"
                "Would you like to open Settings now to enter your API Key or Client ID?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_settings_clicked()
            return
        self.worker.request_login()

    def _on_settings_clicked(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._populate_account_card_combo()
            self.worker.check_initial_auth()
            self.status_bar.showMessage("Credentials and accounts updated.", 3000)

    def _populate_account_card_combo(self) -> None:
        if not hasattr(self, "cb_accounts"):
            return
        self.cb_accounts.blockSignals(True)
        self.cb_accounts.clear()
        selected_idx = 0
        for idx, acc in enumerate(self.config.accounts):
            acc_id = acc.get("id", "")
            name = acc.get("name", "Account")
            atype = acc.get("auth_type", "api_key")
            key = acc.get("api_key", "")
            snippet = f" ({key[:4]}...{key[-3:]})" if key else f" ({atype})"
            self.cb_accounts.addItem(f"👤 {name}{snippet}", acc_id)
            if acc_id == self.config.active_account_id:
                selected_idx = idx

        self.cb_accounts.addItem("➕ Add Account / Key...", "add_new")
        if self.cb_accounts.count() > 1:
            self.cb_accounts.setCurrentIndex(selected_idx)
        self.cb_accounts.blockSignals(False)

    def _on_account_card_combo_changed(self, idx: int) -> None:
        val = self.cb_accounts.currentData()
        if val == "add_new":
            self._on_add_account_clicked()
            return
        if val and val != self.config.active_account_id:
            switch_account(self.config, val)
            self.worker.switch_account(val)
            self.status_bar.showMessage("Switched Gemini account.", 3000)

    def _on_add_account_clicked(self) -> None:
        dlg = AddAccountDialog(self.config, self)
        if dlg.exec():
            self._populate_account_card_combo()
            self.worker.check_initial_auth()
            self.status_bar.showMessage("Added and switched to new account.", 3000)

    def _on_model_selected(self, idx: int) -> None:
        model_id = self.cb_models.currentData()
        if model_id == "custom":
            custom_name, ok = QInputDialog.getText(
                self, "Custom Model", "Enter Gemini model name (e.g. models/gemini-3.5-flash):"
            )
            if ok and custom_name.strip():
                model_id = custom_name.strip()
                if not model_id.startswith("models/"):
                    model_id = f"models/{model_id}"
                self.cb_models.setItemText(idx, f"✏ {model_id}")
                self.cb_models.setItemData(idx, model_id)
            else:
                self.cb_models.setCurrentIndex(0)
                return

        self.config.model = model_id
        mid = model_id if model_id.startswith("models/") else f"models/{model_id}"
        self.config.rest_url = f"https://generativelanguage.googleapis.com/v1beta/{mid}:generateContent"
        if idx < len(AVAILABLE_MODELS):
            self.lbl_model_desc.setText(AVAILABLE_MODELS[idx][2])
        self.lbl_model_pill.setText(f"⚡ {model_id.split('/')[-1]}")
        save_config(self.config)
        self.worker.update_model(model_id, self.config.rest_url)
        self.status_bar.showMessage(f"AI Model switched to: {model_id}", 3000)

    def _on_signout_clicked(self) -> None:
        if self.config.api_key:
            self.config.api_key = ""
            save_config(self.config)
        self.worker.request_signout()

    def _on_refresh_token_clicked(self) -> None:
        self.worker.request_refresh_token()

    def _on_mode_changed(self) -> None:
        if self.rb_live.isChecked():
            self.current_mode = "LIVE"
        else:
            self.current_mode = "ONDEMAND"
        self.dock_prompt.setVisible(True)
        self._update_primary_button_visuals()

    def _on_target_type_changed(self, idx: int) -> None:
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
        target_spec = self.cb_windows.currentData()
        if target_spec and isinstance(target_spec, dict):
            hwnd = target_spec.get("id", 0)
            if self.active_target_type == CaptureTarget.WINDOW:
                self.active_target_id = hwnd
                title = target_spec.get("title", "")
                trunc_title = (title[:30] + "...") if len(title) > 30 else title
                self.sb_target.setText(f"Target: HWND 0x{hwnd:08X} ({trunc_title})")
                self._trigger_preview_update()

    def _on_refresh_windows_clicked(self) -> None:
        self.worker.request_refresh_windows()

    def _on_primary_action_clicked(self) -> None:
        if self.current_mode == "LIVE":
            if self.state_machine.state == AppState.LIVE_STREAMING:
                self.worker.stop_live_streaming()
            else:
                self.worker.start_live_streaming(
                    target_type=self.active_target_type,
                    target_id=self.active_target_id,
                    voice_name=self.config.voice_name,
                    system_instruction=self.config.system_instruction,
                )
        else:
            self._on_send_prompt_clicked()

    def _on_mic_mute_clicked(self) -> None:
        self.is_muted = not self.is_muted
        self.worker.set_mic_muted(self.is_muted)
        if self.is_muted:
            self.btn_mic_mute.setText("🔇 Microphone: MUTED")
            self.btn_mic_mute.setProperty("mic_state", "muted")
            self.btn_mic_mute.setProperty("muted", "true")
        else:
            self.btn_mic_mute.setText("🎤 Microphone: Active (Unmuted)")
            self.btn_mic_mute.setProperty("mic_state", "unmuted")
            self.btn_mic_mute.setProperty("muted", "false")
        restyle_widget(self.btn_mic_mute)

    def _on_send_prompt_clicked(self) -> None:
        prompt = self.txt_prompt_input.text().strip()
        if not prompt:
            prompt = "Analyze this screen and describe what you observe."

        timestamp = time.strftime("%H:%M:%S")
        include_screen = getattr(self, "chk_include_screen", None) is None or self.chk_include_screen.isChecked()

        screen_badge = ""
        if include_screen:
            target_desc = "Window" if self.active_target_type == CaptureTarget.WINDOW else "Desktop"
            screen_badge = f"<span style='background-color: rgba(255,255,255,0.2); padding: 1px 7px; border-radius: 8px; font-size: 10px; margin-left: 6px;'>📷 {target_desc} Attached</span>"

        # Gemini App styled user message bubble
        self._append_html(f"""
            <div style='margin: 10px 0 6px 0; text-align: right;'>
                <div style='display: inline-block; max-width: 82%; background: linear-gradient(135deg, #1a73e8, #174ea6); color: #ffffff; padding: 10px 16px; border-radius: 16px 16px 2px 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.25); text-align: left;'>
                    <div style='font-size: 11px; color: #d2e3fc; font-weight: 600; margin-bottom: 3px;'>
                        👤 You &bull; {timestamp} {screen_badge}
                    </div>
                    <div style='font-size: 13px; line-height: 1.4; color: #ffffff;'>
                        {html.escape(prompt)}
                    </div>
                </div>
            </div>
            <div style='margin: 4px 0 8px 0; text-align: left;'>
                <div style='display: inline-block; background-color: #1e1f20; border: 1px solid #3c4043; padding: 6px 12px; border-radius: 12px 12px 12px 2px; color: #a8c7fa; font-size: 11px;'>
                    ✨ <em>Gemini is analyzing &amp; responding...</em>
                </div>
            </div>
        """)
        self.txt_prompt_input.clear()

        # If in live mode, also notify the live WebSocket session
        if self.current_mode == "LIVE" and self.state_machine.state == AppState.LIVE_STREAMING:
            try:
                self.worker.send_live_chat_turn(
                    prompt=prompt,
                    include_screenshot=include_screen,
                    target_type=self.active_target_type,
                    target_id=self.active_target_id,
                )
            except Exception as live_err:
                logger.debug("Live chat dispatch error: %s", live_err)

        # Execute multimodal on-demand query to produce the complete rich text response
        try:
            self.worker.query_ondemand(
                target_type=self.active_target_type if include_screen else "NONE",
                target_id=self.active_target_id if include_screen else 0,
                prompt=prompt,
                include_screenshot=include_screen,
                model=self.config.model,
            )
        except TypeError:
            self.worker.query_ondemand(
                self.active_target_type if include_screen else "NONE",
                self.active_target_id if include_screen else 0,
                prompt,
            )

    def _on_preset_chip_clicked(self, query: str) -> None:
        self.txt_prompt_input.setText(query)
        self.txt_prompt_input.setFocus()

    def _on_clear_transcript_clicked(self) -> None:
        self.txt_transcript.clear()

    def _on_copy_transcript_clicked(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.txt_transcript.toPlainText())
            self.status_bar.showMessage("Transcript copied to clipboard.", 2000)

    def _on_jump_latest_clicked(self) -> None:
        sb = self.txt_transcript.verticalScrollBar()
        sb.setValue(sb.maximum())
        self.btn_jump_latest.setVisible(False)

    def _on_transcript_scroll(self, val: int) -> None:
        sb = self.txt_transcript.verticalScrollBar()
        at_bottom = val >= (sb.maximum() - 25)
        self.btn_jump_latest.setVisible(not at_bottom)

    # -----------------------------------------------------------------------
    # Hotkey Handlers
    # -----------------------------------------------------------------------
    def _on_hotkey_ondemand(self) -> None:
        """Alt+S handler: triggers on-demand capture."""
        logger.info("Alt+S hotkey triggered!")
        if self.state_machine.state in (AppState.AUTHENTICATED_IDLE, AppState.ERROR):
            # Switch to on-demand mode if not already
            if not self.rb_ondemand.isChecked():
                self.rb_ondemand.setChecked(True)
                self._on_mode_changed()
            self._on_send_prompt_clicked()

    def _on_hotkey_live_toggle(self) -> None:
        """Alt+L handler: toggles continuous live streaming."""
        logger.info("Alt+L hotkey triggered!")
        if self.state_machine.state in (AppState.AUTHENTICATED_IDLE, AppState.LIVE_STREAMING):
            # Ensure live mode is active
            if not self.rb_live.isChecked() and self.state_machine.state == AppState.AUTHENTICATED_IDLE:
                self.rb_live.setChecked(True)
                self._on_mode_changed()
            self._on_primary_action_clicked()

    def _on_hotkey_conflict(self, name: str, reason: str) -> None:
        """Displays non-blocking warning when hotkey registration is occupied."""
        msg = f"Global hotkey {name} unavailable: {reason}. You can still use the UI buttons."
        self.status_bar.showMessage(msg, 7000)
        self._append_html(f"""
            <div style='color: {PALETTE["COLOR_WARNING"]}; font-size: 11px; margin: 4px 0;'>
                ⚠️ <em>{html.escape(msg)}</em>
            </div>
        """)

    # -----------------------------------------------------------------------
    # Preview & Minimized Window UX Protection
    # -----------------------------------------------------------------------
    def _on_preview_timer_tick(self) -> None:
        if self.state_machine.state != AppState.LIVE_STREAMING:
            self._trigger_preview_update()

    def _trigger_preview_update(self) -> None:
        # Minimized window safeguard: do NOT unminimize passively in preview
        if self.active_target_type == CaptureTarget.WINDOW:
            hwnd = int(self.active_target_id) if self.active_target_id else 0
            if sys.platform == "win32" and hwnd:
                try:
                    user32 = ctypes.windll.user32
                    if user32.IsIconic(hwnd):
                        # Generate minimized window placeholder
                        qimg = self._create_placeholder_image("[Window Minimized]")
                        self.on_preview_frame_received(qimg)
                        return
                except Exception as e:
                    logger.debug("IsIconic check skipped: %s", e)

        self.worker.capture_preview_frame(self.active_target_type, self.active_target_id)

    def _create_placeholder_image(self, text: str) -> QImage:
        """Generates a clean dark placeholder thumbnail."""
        width, height = 340, 192
        img = QImage(width, height, QImage.Format.Format_RGB888)
        img.fill(QColor(PALETTE["BG_INPUT"]))
        painter = QPainter(img)
        painter.setPen(QColor(PALETTE["TEXT_MUTED"]))
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return img

    def _update_primary_button_visuals(self) -> None:
        """Updates primary button label and style based on mode and state."""
        if self.state_machine.state == AppState.LIVE_STREAMING:
            self.btn_primary_action.setText("■ Stop Live Streaming")
            self.btn_primary_action.setProperty("variant", "danger")
        elif self.current_mode == "LIVE":
            self.btn_primary_action.setText("Start Live Streaming")
            self.btn_primary_action.setProperty("variant", "success")
        else:
            self.btn_primary_action.setText("Capture Screen & Ask")
            self.btn_primary_action.setProperty("variant", "primary")
        restyle_widget(self.btn_primary_action)

    def _append_html(self, html_text: str) -> None:
        sb = self.txt_transcript.verticalScrollBar()
        was_at_bottom = sb.value() >= (sb.maximum() - 25)
        self.txt_transcript.append(html_text)
        if was_at_bottom:
            sb.setValue(sb.maximum())
            self.btn_jump_latest.setVisible(False)
        else:
            self.btn_jump_latest.setVisible(True)

    def _ensure_smart_autoscroll(self) -> None:
        sb = self.txt_transcript.verticalScrollBar()
        if not self.btn_jump_latest.isVisible():
            self.txt_transcript.ensureCursorVisible()

    # -----------------------------------------------------------------------
    # Lifecycle Cleanup
    # -----------------------------------------------------------------------
    def cleanup(self) -> None:
        """Stops timers and unhooks hotkeys upon window closing."""
        if hasattr(self, "preview_timer") and self.preview_timer.isActive():
            self.preview_timer.stop()

        # Disconnect worker signals to prevent dangling callbacks during teardown
        if hasattr(self, "worker") and self.worker is not None:
            slots = [
                (self.worker.sig_auth_state_changed, self.on_auth_state_changed),
                (self.worker.sig_connection_state_changed, self.on_connection_state_changed),
                (self.worker.sig_text_token, self.on_text_token_received),
                (self.worker.sig_interrupted, self.on_interrupted_received),
                (self.worker.sig_turn_complete, self.on_turn_complete_received),
                (self.worker.sig_preview_frame, self.on_preview_frame_received),
                (self.worker.sig_ondemand_result, self.on_ondemand_result_received),
                (self.worker.sig_windows_enumerated, self.on_windows_enumerated_received),
                (self.worker.sig_error, self.on_error_received),
            ]
            for sig, slot in slots:
                try:
                    sig.disconnect(slot)
                except Exception:
                    pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup()
        event.accept()
