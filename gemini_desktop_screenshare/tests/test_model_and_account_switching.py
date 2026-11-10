"""
Unit and integration test suite for multi-account switching, model selection (Flash models and Argon),
and in-app chat in Gemini Desktop Screenshare.
"""

from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gemini_desktop_screenshare.config import (
    AVAILABLE_MODELS,
    AppConfig,
    add_or_update_account,
    delete_account,
    get_active_account,
    load_config,
    save_config,
    switch_account,
)
from gemini_desktop_screenshare.ondemand.ondemand_client import OnDemandClient


def test_model_presets_include_flash_and_argon():
    """Verifies that AVAILABLE_MODELS includes Flash models and Gemini 4 Argon."""
    model_ids = [m[1] for m in AVAILABLE_MODELS]
    labels = [m[0] for m in AVAILABLE_MODELS]

    assert any("gemini-3.5-flash" in m for m in model_ids)
    assert any("gemini-4-argon" in m for m in model_ids)
    assert any("gemini-3.8-flash" in m for m in model_ids)
    assert any("gemini-3.7-flash" in m for m in model_ids)
    assert any("gemini-3.8-live" in m for m in model_ids)

    assert any("Flash" in l for l in labels)
    assert any("Argon" in l for l in labels)


def test_multi_account_creation_and_switching(tmp_path):
    """Verifies creating multiple accounts, switching active credentials, and deletion."""
    cfg_file = tmp_path / "config.json"
    cfg = AppConfig(config_dir=tmp_path)

    # 1. Add first account (API Key)
    id1 = add_or_update_account(
        cfg, name="Personal Key", auth_type="api_key", api_key="AIzaSy1111111111"
    )
    assert cfg.active_account_id == id1
    assert cfg.api_key == "AIzaSy1111111111"
    assert len(cfg.accounts) == 1

    # 2. Add second account (Argon / Work Key)
    id2 = add_or_update_account(
        cfg, name="Work Key", auth_type="api_key", api_key="AIzaSy2222222222"
    )
    assert cfg.active_account_id == id2
    assert cfg.api_key == "AIzaSy2222222222"
    assert len(cfg.accounts) == 2

    # 3. Add third account (OAuth Client ID)
    id3 = add_or_update_account(
        cfg, name="Google Cloud OAuth", auth_type="oauth", client_id="my-client.apps.googleusercontent.com"
    )
    assert cfg.active_account_id == id3
    assert cfg.client_id == "my-client.apps.googleusercontent.com"
    assert len(cfg.accounts) == 3

    # 4. Switch back to account 1
    assert switch_account(cfg, id1) is True
    assert cfg.active_account_id == id1
    assert cfg.api_key == "AIzaSy1111111111"

    # 5. Switch to account 2
    assert switch_account(cfg, id2) is True
    assert cfg.active_account_id == id2
    assert cfg.api_key == "AIzaSy2222222222"

    # 6. Delete account 2: should auto-switch to remaining account
    assert delete_account(cfg, id2) is True
    assert len(cfg.accounts) == 2
    assert cfg.active_account_id in (id1, id3)


def test_ondemand_client_dynamic_model_url_resolution():
    """Verifies OnDemandClient dynamically resolves endpoint URLs for Flash and Argon models."""
    mock_oauth = MagicMock()
    mock_oauth.config.api_key = "test_key"
    mock_capture = MagicMock()

    client = OnDemandClient(mock_oauth, mock_capture, model="models/gemini-3.5-flash")
    url = client._resolve_url()
    assert "models/gemini-3.5-flash:generateContent" in url

    # Override with gemini-4-argon
    argon_url = client._resolve_url("models/gemini-4-argon")
    assert "models/gemini-4-argon:generateContent" in argon_url

    # Automatic models/ prefix prepending
    short_url = client._resolve_url("gemini-3.8-flash")
    assert "models/gemini-3.8-flash:generateContent" in short_url


@pytest.mark.asyncio
async def test_ondemand_query_without_screenshot():
    """Verifies query_target with include_screenshot=False executes query_text."""
    mock_oauth = MagicMock()
    mock_oauth.config.api_key = "test_key"
    mock_oauth.config.proxy = ""
    mock_capture = MagicMock()

    client = OnDemandClient(mock_oauth, mock_capture)
    client.query_text = AsyncMock(return_value="Direct chat response without image")

    # Call with include_screenshot=False
    res = await client.query_target(
        target_type="NONE",
        target_id=0,
        prompt="Tell me a joke",
        include_screenshot=False,
    )

    assert res == "Direct chat response without image"
    # Capture engine should NOT be invoked
    assert not mock_capture.capture_frame_base64.called
