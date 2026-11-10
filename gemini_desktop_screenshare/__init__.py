"""
Gemini Desktop Screenshare - Windows Desktop Screen Sharing & AI Companion.
Supports continuous live screensharing & audio dialogue, plus on-demand screenshot analysis.
"""

from gemini_desktop_screenshare.config import AppConfig, load_config
from gemini_desktop_screenshare.auth import TokenStore, OAuthManager
from gemini_desktop_screenshare.capture import (
    CaptureTarget,
    ScreenCaptureEngine,
    WindowCapture,
)
from gemini_desktop_screenshare.audio import AudioPipeline
from gemini_desktop_screenshare.streaming import GeminiLiveClient
from gemini_desktop_screenshare.ondemand import OnDemandClient

__version__ = "1.0.0"

__all__ = [
    "AppConfig",
    "load_config",
    "TokenStore",
    "OAuthManager",
    "CaptureTarget",
    "ScreenCaptureEngine",
    "WindowCapture",
    "AudioPipeline",
    "GeminiLiveClient",
    "OnDemandClient",
    "__version__",
]
