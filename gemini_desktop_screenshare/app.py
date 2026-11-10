"""
Main Application Entry Point and Async Worker for Gemini Desktop Screenshare.
Coordinates High-DPI PyQt6 runtime, AsyncWorker QThread running background asyncio services,
thread-safe signal routing, Win32 global hotkeys, and clean graceful shutdown.
"""

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure package root is in sys.path when invoked directly as a script
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from PIL import Image
from PyQt6.QtCore import QCoreApplication, QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from gemini_desktop_screenshare.audio.audio_pipeline import AudioPipeline
from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.config import AppConfig, load_config
from gemini_desktop_screenshare.ondemand.ondemand_client import OnDemandClient
from gemini_desktop_screenshare.streaming.live_client import GeminiLiveClient
from gemini_desktop_screenshare.ui.hotkey_manager import HotkeyManager
from gemini_desktop_screenshare.ui.main_window import MainWindow
from gemini_desktop_screenshare.ui.styles import apply_theme, configure_qt_high_dpi

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AsyncWorker: Dedicated Background Asyncio QThread
# ---------------------------------------------------------------------------
class AsyncWorker(QThread):
    """
    Dedicated background worker thread running an independent asyncio event loop.
    Coordinates OAuth PKCE, desktop screen captures, Gemini Multimodal Live WebSocket client,
    and On-Demand REST queries. All communication with PyQt6 GUI is mediated via thread-safe
    Qt signals.
    """

    # Signals emitted from background asyncio thread to PyQt6 Main Thread
    sig_auth_state_changed = pyqtSignal(bool, dict)      # (is_authenticated, user_profile)
    sig_connection_state_changed = pyqtSignal(str)       # Connection state string
    sig_text_token = pyqtSignal(str)                     # Inbound streamed text token delta
    sig_interrupted = pyqtSignal()                       # Barge-in interruption notification
    sig_turn_complete = pyqtSignal()                     # Model turn completed
    sig_preview_frame = pyqtSignal(QImage)               # Captured preview thumbnail
    sig_ondemand_result = pyqtSignal(str)                # On-demand response text
    sig_windows_enumerated = pyqtSignal(list)            # List of window metadata dicts
    sig_error = pyqtSignal(str)                          # Error notification message

    def __init__(
        self,
        config: AppConfig,
        oauth_manager: OAuthManager,
        capture_engine: ScreenCaptureEngine,
        audio_pipeline: AudioPipeline,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.oauth_manager = oauth_manager
        self.capture_engine = capture_engine
        self.audio_pipeline = audio_pipeline

        self.live_client: Optional[GeminiLiveClient] = None
        self.ondemand_client: Optional[OnDemandClient] = None

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_ready = threading.Event()
        self._is_running = True

        # Hook barge-in interruption in audio pipeline
        self._orig_interrupt = self.audio_pipeline.interrupt
        self.audio_pipeline.interrupt = self._hooked_interrupt

    def _hooked_interrupt(self) -> float:
        """Hooks audio interruption to emit sig_interrupted while executing immediate purge."""
        elapsed = self._orig_interrupt()
        self.sig_interrupted.emit()
        return elapsed

    def run(self) -> None:
        """Initializes and runs the background asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Instantiate live and on-demand clients bound to this loop
        self.live_client = GeminiLiveClient(
            oauth_manager=self.oauth_manager,
            capture_engine=self.capture_engine,
            audio_pipeline=self.audio_pipeline,
            host=self.config.live_ws_url,
            model=self.config.model,
        )
        self.ondemand_client = OnDemandClient(
            oauth_manager=self.oauth_manager,
            capture_engine=self.capture_engine,
            rest_host=self.config.rest_url,
            model=self.config.model,
        )

        self._loop_ready.set()
        logger.info("AsyncWorker asyncio event loop started.")

        try:
            if not self._is_running:
                return
            self._loop.run_forever()
        finally:
            # Drain and cancel pending tasks
            try:
                pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as e:
                logger.debug("Exception during event loop cleanup: %s", e)
            finally:
                self._loop.close()
                logger.info("AsyncWorker asyncio event loop closed.")
                cur = threading.current_thread()
                if isinstance(cur, threading._DummyThread):
                    threading._active.pop(cur.ident, None)

    def submit_coro(self, coro: Any) -> Any:
        """Schedules a coroutine thread-safely onto the background asyncio loop."""
        self._loop_ready.wait(timeout=5.0)
        if self._loop is None or not self._loop.is_running():
            raise RuntimeError("AsyncWorker event loop is not running.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # -----------------------------------------------------------------------
    # Public Controller Methods (Callable from PyQt6 GUI Thread)
    # -----------------------------------------------------------------------
    def check_initial_auth(self) -> None:
        """Verifies stored credentials and emits initial auth status."""
        is_auth = self.oauth_manager.is_authenticated()
        profile = self.oauth_manager.get_user_profile() if is_auth else {}
        self.sig_auth_state_changed.emit(is_auth, profile)

    def request_login(self, timeout: float = 120.0) -> None:
        """Launches the OAuth 2.0 PKCE loopback browser login in a thread."""
        async def _login_task():
            self.sig_connection_state_changed.emit("AUTHENTICATING")
            try:
                session = await asyncio.to_thread(
                    self.oauth_manager.start_loopback_and_login, timeout
                )
                profile = session.get("user_profile", {})
                self.sig_auth_state_changed.emit(True, profile)
                self.sig_connection_state_changed.emit("READY")
            except Exception as e:
                logger.error("OAuth login failed: %s", e)
                self.sig_auth_state_changed.emit(False, {})
                self.sig_connection_state_changed.emit("DISCONNECTED")
                self.sig_error.emit(f"Sign-in failed: {e}")

        self.submit_coro(_login_task())

    def request_signout(self) -> None:
        """Signs out the user, cancels active streams, and clears stored credentials."""
        async def _signout_task():
            if self.live_client and self.live_client.is_streaming:
                await self.live_client.stop_streaming()
            await asyncio.to_thread(self.oauth_manager.sign_out)
            self.sig_auth_state_changed.emit(False, {})
            self.sig_connection_state_changed.emit("DISCONNECTED")

        self.submit_coro(_signout_task())

    def request_refresh_token(self) -> None:
        """Refreshes the OAuth access token proactively."""
        async def _refresh_task():
            try:
                await asyncio.to_thread(self.oauth_manager.refresh_access_token)
                profile = self.oauth_manager.get_user_profile()
                self.sig_auth_state_changed.emit(True, profile)
            except Exception as e:
                logger.error("Token refresh failed: %s", e)
                self.sig_error.emit(f"Token refresh failed: {e}")

        self.submit_coro(_refresh_task())

    def request_refresh_windows(self) -> None:
        """Enumerates active top-level windows off the main thread."""
        async def _enum_task():
            try:
                windows = await asyncio.to_thread(self.capture_engine.list_windows)
                self.sig_windows_enumerated.emit(windows)
            except Exception as e:
                logger.warning("Failed to enumerate windows: %s", e)

        self.submit_coro(_enum_task())

    def start_live_streaming(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        voice_name: str = "Aoede",
        system_instruction: str = "",
    ) -> None:
        """Connects WebSocket and starts continuous 1 FPS video + 16kHz audio streaming."""
        async def _stream_task():
            self.sig_connection_state_changed.emit("CONNECTING")
            try:
                if not self.live_client.is_connected:
                    await self.live_client.connect(
                        voice_name=voice_name,
                        system_instruction=system_instruction,
                    )

                def _on_text(token: str) -> None:
                    self.sig_text_token.emit(token)

                def _on_err(err_msg: str) -> None:
                    self.sig_error.emit(err_msg)

                def _on_disc() -> None:
                    self.sig_connection_state_changed.emit("DISCONNECTED")

                await self.live_client.start_streaming(
                    target_type=target_type,
                    target_id=target_id,
                    on_text=_on_text,
                    on_error=_on_err,
                    on_disconnect=_on_disc,
                )
                self.sig_connection_state_changed.emit("STREAMING")
            except Exception as e:
                logger.error("Failed to start live streaming: %s", e)
                self.sig_connection_state_changed.emit("DISCONNECTED")
                self.sig_error.emit(f"Streaming error: {e}")

        self.submit_coro(_stream_task())

    def stop_live_streaming(self) -> None:
        """Stops continuous streaming loops and pauses microphone recording."""
        async def _stop_task():
            self.sig_connection_state_changed.emit("STOPPING")
            if self.live_client:
                await self.live_client.stop_streaming()
            self.sig_connection_state_changed.emit("READY")

        self.submit_coro(_stop_task())

    def update_model(self, model: str, rest_url: Optional[str] = None) -> None:
        """Dynamically updates the active Gemini model for both live and on-demand clients."""
        self.config.model = model
        if rest_url:
            self.config.rest_url = rest_url
        if self.live_client:
            self.live_client.set_model(model)
        if self.ondemand_client:
            self.ondemand_client.model = model
            if rest_url:
                self.ondemand_client.rest_host = rest_url
        logger.info("Updated active model to: %s", model)

    def switch_account(self, account_id: str) -> None:
        """Switches active credentials and notifies GUI."""
        from gemini_desktop_screenshare.config import switch_account as do_switch
        if do_switch(self.config, account_id):
            logger.info("Switched to account ID: %s", account_id)
            self.check_initial_auth()

    def send_live_chat_turn(
        self,
        prompt: str,
        include_screenshot: bool = True,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
    ) -> None:
        """Sends a discrete text query turn into the active Gemini Live WebSocket session."""
        async def _chat_task():
            try:
                if self.live_client and self.live_client.is_connected:
                    b64 = None
                    if include_screenshot:
                        actual_id = 0 if target_type == CaptureTarget.FULL_SCREEN else target_id
                        try:
                            b64 = await asyncio.to_thread(
                                self.capture_engine.capture_frame_base64,
                                target_type,
                                actual_id,
                                MAX_IMAGE_DIM,
                                JPEG_QUALITY,
                            )
                        except Exception as e:
                            logger.warning("Could not capture frame for live turn: %s", e)
                    await self.live_client.send_client_content(text=prompt, image_b64=b64)
                else:
                    self.sig_error.emit("Live session not connected. Connect or start live streaming first.")
            except Exception as e:
                logger.error("Failed to send live chat turn: %s", e)
                self.sig_error.emit(f"Failed to send live message: {e}")

        self.submit_coro(_chat_task())

    def query_ondemand(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        prompt: str = "Analyze this screen and describe what you observe.",
        include_screenshot: bool = True,
        model: Optional[str] = None,
    ) -> None:
        """Captures an instant snapshot (if requested) and queries Gemini REST API."""
        async def _ondemand_task():
            self.sig_connection_state_changed.emit("CAPTURING")
            try:
                result_text = await self.ondemand_client.query_target(
                    target_type=target_type,
                    target_id=target_id,
                    prompt=prompt,
                    include_screenshot=include_screenshot,
                    model=model,
                )
                self.sig_ondemand_result.emit(result_text)
                self.sig_connection_state_changed.emit("READY")
            except Exception as e:
                logger.error("On-demand query failed: %s", e)
                self.sig_connection_state_changed.emit("READY")
                self.sig_error.emit(f"On-demand capture failed: {e}")

        self.submit_coro(_ondemand_task())

    def capture_preview_frame(self, target_type: str, target_id: Any) -> None:
        """Captures a single downscaled frame for preview display in the GUI."""
        async def _preview_task():
            try:
                pil_img = await asyncio.to_thread(
                    self.capture_engine.capture_frame, target_type, target_id
                )
                # Resize for thumbnail preview
                pil_img.thumbnail((360, 240), Image.Resampling.LANCZOS)
                rgb_img = pil_img.convert("RGB")
                import io
                buf = io.BytesIO()
                rgb_img.save(buf, format="JPEG", quality=75)
                jpeg_bytes = buf.getvalue()

                qimg = QImage()
                if qimg.loadFromData(jpeg_bytes, "JPEG"):
                    self.sig_preview_frame.emit(qimg)
            except Exception as e:
                logger.debug("Preview capture skipped: %s", e)

        self.submit_coro(_preview_task())

    def set_mic_muted(self, muted: bool) -> None:
        """Toggles microphone mute state thread-safely."""
        self.audio_pipeline.set_muted(muted)

    def stop(self) -> None:
        """Shuts down background thread and closes client connections."""
        self._is_running = False
        if self.isRunning():
            self._loop_ready.wait(timeout=3.0)
        if self._loop and self._loop.is_running():
            try:
                if self.live_client and self.live_client.is_connected:
                    future = asyncio.run_coroutine_threadsafe(
                        self.live_client.disconnect(), self._loop
                    )
                    future.result(timeout=3.0)
            except Exception as e:
                logger.debug("Error disconnecting live client during worker stop: %s", e)

            self._loop.call_soon_threadsafe(self._loop.stop)

        self.wait(5000)


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
def main() -> int:
    """Configures High-DPI, starts AsyncWorker, attaches Hotkeys, and launches PyQt6 application."""
    log_dir = Path(os.path.expanduser("~")) / ".gemini_desktop_screenshare"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gemini_desktop.log"

    handlers: List[logging.Handler] = [
        logging.FileHandler(str(log_file), encoding="utf-8")
    ]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=handlers,
    )

    configure_qt_high_dpi()

    app = QApplication(sys.argv)
    app.setApplicationName("Gemini Desktop Screenshare")
    app.setOrganizationName("GeminiDesktop")
    apply_theme(app)

    config = load_config()
    oauth_manager = OAuthManager(config=config)
    capture_engine = ScreenCaptureEngine()
    audio_pipeline = AudioPipeline(
        input_rate=config.input_sample_rate,
        output_rate=config.output_sample_rate,
    )

    worker = AsyncWorker(
        config=config,
        oauth_manager=oauth_manager,
        capture_engine=capture_engine,
        audio_pipeline=audio_pipeline,
    )
    worker.start()

    hotkey_manager = HotkeyManager()
    hotkey_manager.register_default_hotkeys()

    window = MainWindow(
        worker=worker,
        config=config,
        hotkey_manager=hotkey_manager,
    )
    window.show()

    # Initial state checks
    worker.check_initial_auth()
    worker.request_refresh_windows()

    def on_quit():
        logger.info("Application shutting down; cleaning up resources...")
        hotkey_manager.unregister_all()
        window.cleanup()
        worker.stop()
        audio_pipeline.close()
        capture_engine.close()
        logger.info("Cleanup complete.")

    app.aboutToQuit.connect(on_quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
