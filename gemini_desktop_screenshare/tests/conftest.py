"""
Pytest configuration and global fixtures for Gemini Desktop Screenshare test suite.
Configures headless Qt environment before any Qt modules are imported.
"""

import os
import sys

# Ensure headless Qt platform for all test environments (Windows, CI, headless)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provides an isolated temporary configuration directory."""
    cfg_dir = tmp_path / "gemini_test_config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return str(cfg_dir)
