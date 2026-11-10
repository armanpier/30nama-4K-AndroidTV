"""
Token storage module for Windows Credential Manager and DPAPI persistence.
Provides secure storage of OAuth refresh tokens and session metadata.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try importing win32crypt for DPAPI
try:
    import win32crypt
    HAS_WIN32CRYPT = True
except ImportError:
    win32crypt = None
    HAS_WIN32CRYPT = False

# Try importing keyring
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    keyring = None
    HAS_KEYRING = False


class TokenStore:
    """
    Manages secure token persistence on Windows using:
    1. Windows Credential Manager (via keyring/WinVaultKeyring) for refresh tokens.
    2. Windows DPAPI (via win32crypt) as a secure encrypted file fallback.
    3. Session JSON cache for user profile and temporary access token data.
    """

    def __init__(
        self,
        service_name: str = "GeminiDesktopScreenshare",
        refresh_token_key: str = "refresh_token",
        config_dir: Optional[Path] = None,
    ):
        self.service_name = service_name
        self.refresh_token_key = refresh_token_key
        if config_dir is not None:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(os.path.expanduser("~")) / ".gemini_desktop_screenshare"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.config_dir / "session.json"
        self.dpapi_file = self.config_dir / "token_dpapi.bin"

    # --------------------------------------------------------------------------
    # DPAPI Helper Methods
    # --------------------------------------------------------------------------
    def _dpapi_protect(self, data: bytes, description: str = "GeminiDesktopScreenshare") -> bytes:
        """Encrypts data using Windows DPAPI."""
        if not HAS_WIN32CRYPT:
            raise RuntimeError("win32crypt is not available on this platform.")
        # CryptProtectData(DataIn, Description, OptionalEntropy, Reserved, PromptStruct, Flags)
        return win32crypt.CryptProtectData(data, description, None, None, None, 0)

    def _dpapi_unprotect(self, encrypted_data: bytes) -> bytes:
        """Decrypts data using Windows DPAPI."""
        if not HAS_WIN32CRYPT:
            raise RuntimeError("win32crypt is not available on this platform.")
        # Mandatory engineering directive: explicit call with (data, None, None, None, 0)
        desc, decrypted_bytes = win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)
        return decrypted_bytes

    # --------------------------------------------------------------------------
    # Refresh Token Management
    # --------------------------------------------------------------------------
    def save_refresh_token(self, refresh_token: str) -> None:
        """
        Saves the refresh token securely in Windows Credential Manager.
        Also backs up to a DPAPI-encrypted file.
        """
        if not refresh_token:
            raise ValueError("refresh_token cannot be empty.")

        saved_in_keyring = False
        if HAS_KEYRING:
            try:
                keyring.set_password(self.service_name, self.refresh_token_key, refresh_token)
                saved_in_keyring = True
                logger.info("Refresh token saved successfully to Windows Credential Manager via keyring.")
            except Exception as e:
                logger.warning("Failed to store refresh token in keyring: %s", e)

        # Save DPAPI backup as well for resilience
        if HAS_WIN32CRYPT:
            try:
                encrypted_bytes = self._dpapi_protect(refresh_token.encode("utf-8"))
                with open(self.dpapi_file, "wb") as f:
                    f.write(encrypted_bytes)
                logger.info("Refresh token saved to DPAPI encrypted storage at %s.", self.dpapi_file)
            except Exception as e:
                logger.warning("Failed to store refresh token in DPAPI: %s", e)
                if not saved_in_keyring:
                    raise RuntimeError(f"Could not persist refresh token in keyring or DPAPI: {e}")

    def get_refresh_token(self) -> Optional[str]:
        """
        Retrieves the refresh token from Windows Credential Manager or DPAPI fallback.
        """
        # 1. Try Windows Credential Manager
        if HAS_KEYRING:
            try:
                token = keyring.get_password(self.service_name, self.refresh_token_key)
                if token:
                    return token
            except Exception as e:
                logger.warning("Failed to retrieve token from keyring: %s", e)

        # 2. Try DPAPI fallback file
        if HAS_WIN32CRYPT and self.dpapi_file.exists():
            try:
                with open(self.dpapi_file, "rb") as f:
                    encrypted_bytes = f.read()
                decrypted_bytes = self._dpapi_unprotect(encrypted_bytes)
                return decrypted_bytes.decode("utf-8")
            except Exception as e:
                logger.warning("Failed to decrypt DPAPI token: %s", e)

        return None

    def delete_refresh_token(self) -> None:
        """Deletes the refresh token from Windows Credential Manager and DPAPI backup."""
        if HAS_KEYRING:
            try:
                keyring.delete_password(self.service_name, self.refresh_token_key)
                logger.info("Deleted refresh token from Windows Credential Manager.")
            except Exception as e:
                logger.debug("Keyring delete ignored: %s", e)

        if self.dpapi_file.exists():
            try:
                self.dpapi_file.unlink()
                logger.info("Deleted DPAPI encrypted token backup.")
            except Exception as e:
                logger.warning("Failed to delete DPAPI file: %s", e)

    # --------------------------------------------------------------------------
    # Session JSON Cache Management
    # --------------------------------------------------------------------------
    def save_session(self, session_data: Dict[str, Any]) -> None:
        """
        Saves user profile and access token metadata to session.json.
        """
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
            logger.info("Session data saved to %s", self.session_file)
        except Exception as e:
            logger.error("Failed to save session data: %s", e)
            raise

    def get_session(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached session data from session.json.
        """
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to read session data: %s", e)
            return None

    def clear_session(self) -> None:
        """Clears session.json and deletes persistent refresh tokens."""
        self.delete_refresh_token()
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                logger.info("Session cache cleared.")
            except Exception as e:
                logger.warning("Failed to delete session file: %s", e)
