"""Client for the CodeWhisper click agent. Routes through click_agent_bridge (WebSocket)."""

import logging

from services.click_agent_bridge import click_agent_bridge

logger = logging.getLogger(__name__)


class ClickClient:
    """Async client for the click agent via WebSocket bridge. All methods return False on failure."""

    async def check_available(self) -> bool:
        """Return True if click agent WebSocket is connected."""
        return click_agent_bridge.is_connected

    async def click(self, x: int, y: int, double: bool = False) -> bool:
        """Click or double-click at (x, y). Return True on success."""
        if not click_agent_bridge.is_connected:
            return False
        action = "double_click" if double else "click"
        result = await click_agent_bridge.send_command(action, {"x": x, "y": y})
        status = (result or {}).get("status", "")
        return "clicked" in status or "double_clicked" in status

    async def scroll(self, x: int, y: int, amount: int) -> bool:
        """Scroll at (x, y) by amount. Return True on success."""
        if not click_agent_bridge.is_connected:
            return False
        result = await click_agent_bridge.send_command("scroll", {"x": x, "y": y, "clicks": amount})
        return "scrolled" in (result or {}).get("status", "")

    async def hotkey(self, keys: list[str]) -> bool:
        """Press hotkey. Return True on success."""
        if not click_agent_bridge.is_connected:
            return False
        result = await click_agent_bridge.send_command("hotkey", {"keys": keys})
        return "pressed" in (result or {}).get("status", "")

    async def type_text(self, text: str) -> bool:
        """Type text. Return True on success."""
        if not click_agent_bridge.is_connected:
            return False
        result = await click_agent_bridge.send_command("type_text", {"text": text})
        return "typed" in (result or {}).get("status", "")
