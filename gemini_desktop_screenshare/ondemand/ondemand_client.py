"""
On-Demand Screen Capture and Multimodal Query Client.
Takes instantaneous snapshots of the full desktop or selected application window,
formats multimodal inline JPEG payloads with user queries, executes requests via
REST generateContent (or WebSocket), and parses structured Gemini responses.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
import aiohttp

from gemini_desktop_screenshare.auth.oauth_manager import OAuthManager
from gemini_desktop_screenshare.capture.screen_capture import CaptureTarget, ScreenCaptureEngine
from gemini_desktop_screenshare.config import DEFAULT_REST_URL, JPEG_QUALITY, MAX_IMAGE_DIM

logger = logging.getLogger(__name__)


class OnDemandClient:
    """
    Client for on-demand screenshot analysis with Gemini models.
    Authenticates via OAuth 2.0 Bearer tokens and executes multimodal REST queries.
    """

    def __init__(
        self,
        oauth_manager: OAuthManager,
        capture_engine: ScreenCaptureEngine,
        rest_host: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.oauth_manager = oauth_manager
        self.capture_engine = capture_engine
        self.rest_host = rest_host or DEFAULT_REST_URL
        self.model = model

    def _resolve_url(self, model: Optional[str] = None) -> str:
        """Determines the REST URL based on specified or configured model."""
        if self.rest_host and ("127.0.0.1" in self.rest_host or "localhost" in self.rest_host):
            return self.rest_host
        target_model = model or self.model or ""
        target_model = target_model.strip()

        # models/gemini-3.8-live only supports live bidi WebSocket; fall back to 3.5-flash for REST
        if not target_model or "live" in target_model.lower():
            target_model = "models/gemini-3.5-flash"

        if target_model != "custom":
            mid = target_model
            # If model is a full URL, use it directly
            if mid.startswith("http://") or mid.startswith("https://"):
                return mid
            if not mid.startswith("models/"):
                mid = f"models/{mid}"
            return f"https://generativelanguage.googleapis.com/v1beta/{mid}:generateContent"
        return self.rest_host

    async def query_target(
        self,
        target_type: str = CaptureTarget.FULL_SCREEN,
        target_id: Any = 0,
        prompt: str = "Analyze this screen and describe what you observe.",
        include_screenshot: bool = True,
        model: Optional[str] = None,
    ) -> str:
        """
        Captures an instant snapshot of the specified target (full screen or HWND) if requested,
        submits it alongside the user prompt to Gemini REST generateContent,
        and returns the model's synthesized text response.
        """
        if not include_screenshot:
            return await self.query_text(prompt, model=model)

        # 1. Capture snapshot in thread pool
        logger.info("Capturing on-demand snapshot (type=%s, id=%s)...", target_type, target_id)
        b64_frame = await asyncio.to_thread(
            self.capture_engine.capture_frame_base64,
            target_type,
            target_id,
            MAX_IMAGE_DIM,
            JPEG_QUALITY,
        )

        return await self.query_image(b64_frame, prompt, model=model)

    async def query_text(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Executes a pure text query against the selected Gemini model without screen attachment.
        """
        token = ""
        rest_url = self._resolve_url(model)
        headers = {"Content-Type": "application/json"}
        api_key = getattr(getattr(self.oauth_manager, "config", None), "api_key", "")
        if api_key:
            sep = "&" if "?" in rest_url else "?"
            rest_url = f"{rest_url}{sep}key={api_key}"
        else:
            try:
                token = self.oauth_manager.get_valid_access_token()
            except Exception as e:
                logger.warning("Could not retrieve OAuth access token: %s", e)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 2048,
            },
        }

        proxy_url = getattr(getattr(self.oauth_manager, "config", None), "proxy", None) or None
        logger.info("Submitting text query to %s (proxy=%s)", rest_url, proxy_url)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(rest_url, json=payload, headers=headers, proxy=proxy_url) as response:
                status = response.status
                resp_text = await response.text()

                if status != 200:
                    logger.error("Text query failed (HTTP %s): %s", status, resp_text)
                    # Resilient fallback if requested model is rate-limited (e.g. Free Tier limit 0 on Argon) or unsupported
                    fallback_model = "models/gemini-3.5-flash"
                    if status in (429, 404, 400) and (model != fallback_model and self.model != fallback_model):
                        logger.warning("Model %s failed with HTTP %s; falling back to %s...", model or self.model, status, fallback_model)
                        return await self.query_text(prompt, model=fallback_model)
                    raise RuntimeError(f"Gemini error (HTTP {status}): {resp_text}")

                try:
                    resp_json = json.loads(resp_text)
                except Exception as e:
                    logger.error("Failed to parse JSON response: %s", e)
                    return resp_text

                return self._parse_gemini_response(resp_json)

    async def query_image(self, image_b64: str, prompt: str, model: Optional[str] = None) -> str:
        """
        Submits a base64-encoded JPEG image with a user prompt to Gemini REST API.
        """
        # 2. Retrieve valid Bearer access token or append API key
        token = ""
        rest_url = self._resolve_url(model)
        headers = {
            "Content-Type": "application/json",
        }
        api_key = getattr(getattr(self.oauth_manager, "config", None), "api_key", "")
        if api_key:
            sep = "&" if "?" in rest_url else "?"
            rest_url = f"{rest_url}{sep}key={api_key}"
        else:
            try:
                token = self.oauth_manager.get_valid_access_token()
            except Exception as e:
                logger.warning("Could not retrieve OAuth access token: %s", e)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        # 3. Construct Gemini Multimodal REST payload
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_b64,
                            }
                        },
                        {
                            "text": prompt,
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            },
        }

        # 4. Execute asynchronous HTTP POST
        proxy_url = getattr(getattr(self.oauth_manager, "config", None), "proxy", None) or None
        logger.info("Submitting multimodal query to %s (proxy=%s)", rest_url, proxy_url)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(rest_url, json=payload, headers=headers, proxy=proxy_url) as response:
                status = response.status
                resp_text = await response.text()

                if status != 200:
                    logger.error("On-demand request failed (HTTP %s): %s", status, resp_text)
                    # Resilient fallback if requested model is rate-limited (e.g. Free Tier limit 0 on Argon) or unsupported
                    fallback_model = "models/gemini-3.5-flash"
                    if status in (429, 404, 400) and (model != fallback_model and self.model != fallback_model):
                        logger.warning("Model %s failed with HTTP %s; falling back to %s...", model or self.model, status, fallback_model)
                        return await self.query_image(image_b64, prompt, model=fallback_model)
                    raise RuntimeError(f"Gemini REST error (HTTP {status}): {resp_text}")

                try:
                    resp_json = json.loads(resp_text)
                except Exception as e:
                    logger.error("Failed to parse JSON response: %s", e)
                    return resp_text

                return self._parse_gemini_response(resp_json)

    def _parse_gemini_response(self, resp_json: Dict[str, Any]) -> str:
        """Parses candidates and text parts from Gemini API response JSON."""
        if "error" in resp_json:
            error_details = resp_json["error"]
            raise RuntimeError(f"Gemini API returned error: {error_details}")

        candidates = resp_json.get("candidates", [])
        if not candidates:
            return "No candidates returned by Gemini."

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        texts = [p.get("text", "") for p in parts if "text" in p]
        full_text = "".join(texts).strip()
        return full_text or "Empty response received."
