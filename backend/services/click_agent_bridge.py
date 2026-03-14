"""Singleton WebSocket bridge to the click agent. Tools call this for click/scroll/hotkey/type commands."""

import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

CLICK_AGENT_ACTIONS = [
    "click",
    "double_click",
    "scroll",
    "hotkey",
    "type_text",
    "health",
]


class ClickAgentBridge:
    """Manages the click agent WebSocket connection. Singleton instance."""

    def __init__(self) -> None:
        self._websocket: Any = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    @property
    def is_connected(self) -> bool:
        """True if click agent WebSocket is connected."""
        return self._websocket is not None

    def set_connection(self, websocket: Any) -> None:
        """Store the click agent WebSocket when it connects."""
        self._websocket = websocket
        logger.info("Click agent bridge: connection set")

    def clear_connection(self) -> None:
        """Clear the reference when click agent disconnects."""
        self._websocket = None
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(ConnectionError("Click agent disconnected"))
        self._pending.clear()
        logger.info("Click agent bridge: connection cleared")

    async def send_command(self, action: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Send a command to the click agent and await the response. Timeout 5s. Returns response dict or None on failure."""
        if self._websocket is None:
            return None
        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._pending[request_id] = fut
        try:
            await self._websocket.send_json({
                "type": "command",
                "requestId": request_id,
                "action": action,
                "params": params,
            })
            result = await asyncio.wait_for(fut, timeout=5.0)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            logger.warning("Click agent send_command timed out: %s", action)
            return None
        except Exception as e:
            self._pending.pop(request_id, None)
            logger.warning("Click agent send_command failed: %s - %s", action, e)
            return None
        finally:
            self._pending.pop(request_id, None)

    def handle_message(self, message: dict[str, Any]) -> None:
        """Process incoming message from click agent. Resolve pending Future with response dict."""
        request_id = message.get("requestId")
        if request_id and request_id in self._pending:
            fut = self._pending[request_id]
            if not fut.done():
                # Pass full response dict (status, x, y, etc.) so ClickClient can check status
                fut.set_result(dict(message))


click_agent_bridge = ClickAgentBridge()
