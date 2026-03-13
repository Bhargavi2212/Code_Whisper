"""
HTTP client for the CodeWhisper click agent (runs on host).
Uses CLICK_AGENT_URL if set; else host.docker.internal:8001 in Docker, localhost:8001 locally.
"""

import logging
import os
import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0


def _default_base_url() -> str:
    url = os.environ.get("CLICK_AGENT_URL", "").strip()
    if url:
        return url.rstrip("/")
    # In Docker, agent runs on host
    if os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER"):
        return "http://host.docker.internal:8001"
    return "http://localhost:8001"


class ClickClient:
    """Async HTTP client for the click agent. All methods catch errors and return False on failure."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or _default_base_url()).rstrip("/")
        self._timeout = DEFAULT_TIMEOUT

    async def check_available(self) -> bool:
        """GET /health. Return True if status 200 and body has status ok."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base}/health")
                if response.status_code != 200:
                    return False
                data = response.json()
                return data.get("status") == "ok"
        except Exception as e:
            logger.warning("Click agent check failed: %s", e)
            return False

    async def click(self, x: int, y: int, double: bool = False) -> bool:
        """POST /click or /double_click. Return True on success."""
        path = "/double_click" if double else "/click"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base}{path}", json={"x": x, "y": y})
                return response.status_code == 200
        except Exception as e:
            logger.warning("Click agent %s failed: %s", path, e)
            return False

    async def scroll(self, x: int, y: int, amount: int) -> bool:
        """POST /scroll with x, y, clicks. Return True on success."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base}/scroll",
                    json={"x": x, "y": y, "clicks": amount},
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Click agent scroll failed: %s", e)
            return False

    async def hotkey(self, keys: list[str]) -> bool:
        """POST /hotkey. Return True on success."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base}/hotkey", json={"keys": keys})
                return response.status_code == 200
        except Exception as e:
            logger.warning("Click agent hotkey failed: %s", e)
            return False

    async def type_text(self, text: str) -> bool:
        """POST /type_text. Return True on success."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base}/type_text", json={"text": text})
                return response.status_code == 200
        except Exception as e:
            logger.warning("Click agent type_text failed: %s", e)
            return False
