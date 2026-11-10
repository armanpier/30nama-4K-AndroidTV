"""
Configuration module for Gemini Desktop Screenshare application.
Provides default settings, API endpoints, OAuth configurations, and audio/video parameters.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default Application Directories
DEFAULT_CONFIG_DIR = Path(os.path.expanduser("~")) / ".gemini_desktop_screenshare"
SESSION_CACHE_FILE = DEFAULT_CONFIG_DIR / "session.json"
DPAPI_BACKUP_FILE = DEFAULT_CONFIG_DIR / "token_dpapi.bin"

# OAuth 2.0 Endpoints & Defaults
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URI = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

DEFAULT_SCOPES: List[str] = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/generative-language",
]

# Client ID and Secret (Defaults can be overridden via environment variables or custom config)
DEFAULT_CLIENT_ID = os.environ.get(
    "GEMINI_DESKTOP_CLIENT_ID",
    os.environ.get("GOOGLE_CLIENT_ID", "1028741369348-sampledesktopclientid.apps.googleusercontent.com")
)
DEFAULT_CLIENT_SECRET = os.environ.get(
    "GEMINI_DESKTOP_CLIENT_SECRET",
    os.environ.get("GOOGLE_CLIENT_SECRET", "GOCSPX-sampledesktopclientsecret")
)

# Gemini Multimodal Live API (WebSocket)
DEFAULT_LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
DEFAULT_MODEL = "models/gemini-3.8-live"
DEFAULT_VOICE = "Aoede"
VALID_VOICES = ["Aoede", "Charon", "Fenrir", "Kore", "Puck"]

# Supported Models (Flash models, Argon, Pro, and Live)
AVAILABLE_MODELS = [
    ("Gemini 3.5 Flash (Recommended)", "models/gemini-3.5-flash", "High speed multimodal reasoning & screen vision"),
    ("Gemini 4 Argon", "models/gemini-4-argon", "Frontier Argon reasoning & complex analysis"),
    ("Gemini 3.8 Flash", "models/gemini-3.8-flash", "Latest Gemini 3.8 Flash series"),
    ("Gemini 3.7 Flash", "models/gemini-3.7-flash", "Gemini 3.7 hybrid reasoning Flash"),
    ("Gemini 3.1 Flash Lite", "models/gemini-3.1-flash-lite", "Ultra-fast low-latency Flash Lite"),
    ("Gemini 2.5 Pro", "models/gemini-2.5-pro", "High-capacity deep thinking Pro model"),
    ("Gemini 3.8 Live", "models/gemini-3.8-live", "Bidirectional voice and video streaming"),
]

DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a live AI desktop companion observing the user's Windows screen and listening to their microphone. "
    "Answer questions concisely and proactively alert the user to relevant visual details on screen."
)

# On-Demand REST API (Default to high-speed 3.5 Flash)
DEFAULT_REST_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

# Video & Capture Specs
VIDEO_FPS = 1.0
MAX_IMAGE_DIM = 1024
JPEG_QUALITY = 70

# Audio Specifications
AUDIO_INPUT_SAMPLE_RATE = 16000
AUDIO_INPUT_CHANNELS = 1
AUDIO_INPUT_CHUNK_MS = 100  # 1600 samples = 3200 bytes for 16-bit PCM
AUDIO_INPUT_BLOCK_SIZE = int(AUDIO_INPUT_SAMPLE_RATE * (AUDIO_INPUT_CHUNK_MS / 1000.0))

AUDIO_OUTPUT_SAMPLE_RATE = 24000
AUDIO_OUTPUT_CHANNELS = 1
AUDIO_OUTPUT_BLOCK_SIZE = 1024

# Keyring / Credential Manager Target
KEYRING_SERVICE_NAME = "GeminiDesktopScreenshare"
KEYRING_REFRESH_TOKEN_KEY = "refresh_token"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    api_key: str = ""
    proxy: str = ""
    client_id: str = DEFAULT_CLIENT_ID
    client_secret: str = DEFAULT_CLIENT_SECRET
    auth_uri: str = GOOGLE_AUTH_URI
    token_uri: str = GOOGLE_TOKEN_URI
    revoke_uri: str = GOOGLE_REVOKE_URI
    userinfo_uri: str = GOOGLE_USERINFO_URI
    scopes: List[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))
    live_ws_url: str = DEFAULT_LIVE_WS_URL
    rest_url: str = DEFAULT_REST_URL
    model: str = DEFAULT_MODEL
    voice_name: str = DEFAULT_VOICE
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION
    video_fps: float = VIDEO_FPS
    max_image_dim: int = MAX_IMAGE_DIM
    jpeg_quality: int = JPEG_QUALITY
    input_sample_rate: int = AUDIO_INPUT_SAMPLE_RATE
    output_sample_rate: int = AUDIO_OUTPUT_SAMPLE_RATE
    config_dir: Path = DEFAULT_CONFIG_DIR
    session_file: Path = SESSION_CACHE_FILE
    dpapi_file: Path = DPAPI_BACKUP_FILE
    # Multi-account support
    accounts: List[Dict[str, Any]] = field(default_factory=list)
    active_account_id: str = ""


def get_active_account(cfg: AppConfig) -> Optional[Dict[str, Any]]:
    """Retrieves the active account entry or None."""
    if not cfg.accounts:
        return None
    for acc in cfg.accounts:
        if acc.get("id") == cfg.active_account_id:
            return acc
    return cfg.accounts[0]


def switch_account(cfg: AppConfig, account_id: str) -> bool:
    """Switches active credentials to the specified account id."""
    for acc in cfg.accounts:
        if acc.get("id") == account_id:
            cfg.active_account_id = account_id
            cfg.api_key = acc.get("api_key", "")
            if acc.get("client_id"):
                cfg.client_id = acc.get("client_id", "")
            if acc.get("client_secret"):
                cfg.client_secret = acc.get("client_secret", "")
            save_config(cfg)
            return True
    return False


def add_or_update_account(
    cfg: AppConfig,
    name: str,
    auth_type: str = "api_key",
    api_key: str = "",
    client_id: str = "",
    client_secret: str = "",
    email: str = "",
    account_id: Optional[str] = None,
) -> str:
    """Adds a new account or updates an existing one and marks it active."""
    import uuid
    target_id = account_id or f"acc_{uuid.uuid4().hex[:8]}"

    account_entry = {
        "id": target_id,
        "name": name,
        "auth_type": auth_type,
        "api_key": api_key,
        "client_id": client_id,
        "client_secret": client_secret,
        "email": email or (f"api_key_{api_key[:6]}..." if api_key else ""),
    }

    # Replace if exists, else append
    existing_idx = next((i for i, a in enumerate(cfg.accounts) if a.get("id") == target_id), None)
    if existing_idx is not None:
        cfg.accounts[existing_idx] = account_entry
    else:
        cfg.accounts.append(account_entry)

    cfg.active_account_id = target_id
    cfg.api_key = api_key
    if client_id:
        cfg.client_id = client_id
    if client_secret:
        cfg.client_secret = client_secret

    save_config(cfg)
    return target_id


def delete_account(cfg: AppConfig, account_id: str) -> bool:
    """Deletes an account entry and switches to remaining account if active."""
    initial_len = len(cfg.accounts)
    cfg.accounts = [a for a in cfg.accounts if a.get("id") != account_id]
    if len(cfg.accounts) < initial_len:
        if cfg.active_account_id == account_id:
            if cfg.accounts:
                switch_account(cfg, cfg.accounts[0]["id"])
            else:
                cfg.active_account_id = ""
                cfg.api_key = ""
        save_config(cfg)
        return True
    return False


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Loads configuration from environment or an optional JSON file, with defaults."""
    cfg = AppConfig()
    cfg.api_key = os.environ.get("GEMINI_API_KEY", "")

    # Auto-detect proxy
    proxy_env = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
    if not proxy_env:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", 10808)) == 0:
                    proxy_env = "http://127.0.0.1:10808"
        except Exception:
            pass
    cfg.proxy = proxy_env

    target_path = config_path or (str(CONFIG_FILE) if CONFIG_FILE.exists() else None)
    if target_path and os.path.exists(target_path):
        import json
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except Exception:
            pass

    # Ensure accounts list is populated if an api_key or client_id exists
    if not cfg.accounts and (cfg.api_key or cfg.client_id):
        key_snippet = f"{cfg.api_key[:6]}...{cfg.api_key[-4:]}" if len(cfg.api_key) > 10 else "Default"
        acc_name = f"Key ({key_snippet})" if cfg.api_key else "OAuth Account"
        acc_id = "acc_primary"
        cfg.accounts = [{
            "id": acc_id,
            "name": acc_name,
            "auth_type": "api_key" if cfg.api_key else "oauth",
            "api_key": cfg.api_key,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "email": "gemini-api@google" if cfg.api_key else "",
        }]
        cfg.active_account_id = acc_id

    # Sync active account to cfg fields
    active = get_active_account(cfg)
    if active:
        if "api_key" in active and active["api_key"]:
            cfg.api_key = active["api_key"]
        if "client_id" in active and active["client_id"]:
            cfg.client_id = active["client_id"]
        if "client_secret" in active and active["client_secret"]:
            cfg.client_secret = active["client_secret"]

    return cfg


def save_config(cfg: AppConfig, config_path: Optional[str] = None) -> None:
    """Saves editable configuration fields to config.json."""
    import json
    if config_path:
        target = Path(config_path)
    elif hasattr(cfg, "config_dir") and cfg.config_dir and cfg.config_dir != DEFAULT_CONFIG_DIR:
        target = cfg.config_dir / "config.json"
    else:
        target = CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_key": cfg.api_key,
        "proxy": cfg.proxy,
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "model": cfg.model,
        "voice_name": cfg.voice_name,
        "system_instruction": cfg.system_instruction,
        "live_ws_url": cfg.live_ws_url,
        "rest_url": cfg.rest_url,
        "accounts": cfg.accounts,
        "active_account_id": cfg.active_account_id,
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
