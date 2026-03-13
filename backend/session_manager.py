"""Session lifecycle manager. Coordinates WebSocket and Gemini session."""

import asyncio
import logging
from typing import Any, Optional

from fastapi import WebSocket

from config import Settings
from click_client import ClickClient
from gemini_session import GeminiSession, generate_summary_text, NAVIGATION_TOOLS
from audio_handler import encode_audio_for_client, validate_audio_chunk
from frame_handler import encode_frame_for_gemini, resize_frame, validate_frame
from prompts.system_prompt import SYSTEM_PROMPT, SECTION_8_IDE_NAVIGATION

logger = logging.getLogger("codewhisper")

# Prompt to trigger spoken summary over live session (system prompt defines the content).
SPOKEN_SUMMARY_PROMPT = (
    "The user has clicked End Session. Deliver the session summary now as in your instructions: "
    "what was built, key concepts, danger zones flagged, things to review, next steps. "
    "Be specific to this session. Keep it to 1–2 minutes, then a short closing."
)


def _map_coords(x: int, y: int, screen_width: int, screen_height: int) -> tuple[int, int]:
    """Map 768x768 frame coords to real screen pixels."""
    real_x = int(x * (screen_width / 768))
    real_y = int(y * (screen_height / 768))
    return real_x, real_y


class SessionManager:
    """Manages one CodeWhisper session: browser WebSocket and Gemini session."""

    def __init__(self, websocket: WebSocket, settings: Settings) -> None:
        """Initialize with WebSocket and settings. Does not start Gemini."""
        self._websocket = websocket
        self._settings = settings
        self._click_client = ClickClient()
        self._screen_width = 1920
        self._screen_height = 1080
        self._gemini_session: Optional[GeminiSession] = None
        self._relay_task: Optional[asyncio.Task] = None
        self._stopped = False
        self._summary_requested = False
        self._summary_turn_done: Optional[asyncio.Event] = None
        self._audio_chunks_received = 0
        self._frames_received = 0

    async def start(
        self,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> None:
        """Open Gemini session and start relay task. Send gemini_connected or error."""
        if self._stopped:
            return
        if screen_width is not None:
            self._screen_width = screen_width
        if screen_height is not None:
            self._screen_height = screen_height
        try:
            if not self._settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set")
            agent_available = await self._click_client.check_available()
            if agent_available:
                logger.info("Click agent available; enabling navigation tools and Section 8")
            else:
                logger.info("Click agent not available; navigation disabled")
            system_instruction = SYSTEM_PROMPT + (SECTION_8_IDE_NAVIGATION if agent_available else "")
            tools = list(NAVIGATION_TOOLS) if agent_available else []
            self._gemini_session = GeminiSession(
                api_key=self._settings.gemini_api_key,
                model=self._settings.gemini_model,
                send_sample_rate=self._settings.send_sample_rate,
                receive_sample_rate=self._settings.receive_sample_rate,
                system_instruction=system_instruction,
                tools=tools if agent_available else None,
            )
            await self._gemini_session.start()
            logger.info("Session start: Gemini connected")
            await self._gemini_session.send_text(
                "The session just started. Say one short sentence: you're here and ready — they can share their screen when ready."
            )
            self._relay_task = asyncio.create_task(self._relay_gemini_to_browser())
            await self._websocket.send_json({
                "type": "status",
                "status": "gemini_connected",
            })
        except Exception as e:
            logger.error("Failed to start Gemini: %s", e)
            err_msg = "Failed to connect to Gemini. Check your API key."
            if "rate" in str(e).lower() or "quota" in str(e).lower():
                err_msg = "Rate limit or quota exceeded."
            try:
                await self._websocket.send_json({"type": "error", "message": err_msg})
            except Exception:
                pass

    async def handle_audio(self, data: str) -> None:
        """Validate base64 audio and forward to Gemini."""
        if self._gemini_session is None or not self._gemini_session.is_active:
            return
        try:
            raw = validate_audio_chunk(data)
            self._audio_chunks_received += 1
            if self._audio_chunks_received <= 2:
                logger.info("Received audio chunk #%s from client (%s bytes)", self._audio_chunks_received, len(raw))
            await self._gemini_session.send_audio(raw)
        except ValueError as e:
            logger.warning(f"Malformed audio chunk: {e}")

    async def handle_frame(self, data: str) -> None:
        """Validate and process frame, forward to Gemini."""
        if self._gemini_session is None or not self._gemini_session.is_active:
            return
        image_bytes = validate_frame(data)
        if image_bytes is None:
            logger.debug("Invalid frame skipped")
            return
        try:
            self._frames_received += 1
            if self._frames_received <= 3:
                logger.info("Received frame #%s from client, forwarding to Gemini", self._frames_received)
            image_bytes = resize_frame(image_bytes, 768)
            base64_str = encode_frame_for_gemini(image_bytes)
            await self._gemini_session.send_image(base64_str)
        except Exception as e:
            logger.warning(f"Frame forward failed: {e}")
            try:
                await self._websocket.send_json({
                    "type": "error",
                    "message": "Frame processing failed.",
                })
            except Exception:
                pass

    async def handle_switch_mode(self, mode: str) -> None:
        """Send mode switch instruction to Gemini and optionally notify frontend."""
        mode_labels = {
            "sportscaster": "Sportscaster",
            "catchup": "Catch-Up",
            "review": "Review",
        }
        label = mode_labels.get(mode, mode)
        text = f"The user has switched to {label} mode. Please adjust your behavior accordingly."
        await self.handle_text(text)

    async def handle_text(self, text: str) -> None:
        """Forward text to Gemini."""
        if self._gemini_session is None or not self._gemini_session.is_active:
            return
        if not text:
            return
        try:
            await self._gemini_session.send_text(text)
        except Exception as e:
            logger.error("Failed to send text: %s", e)

    async def _handle_tool_call(self, chunk: dict[str, Any]) -> None:
        """Execute navigation tool via ClickClient and send result back to Gemini."""
        call_id = chunk.get("id", "")
        name = chunk.get("name", "")
        args = chunk.get("args") or {}
        if not name or self._gemini_session is None or not self._gemini_session.is_active:
            return
        result_msg = "Done."
        try:
            if name == "click_screen":
                x = int(args.get("x", 0))
                y = int(args.get("y", 0))
                double = bool(args.get("double", False))
                rx, ry = _map_coords(x, y, self._screen_width, self._screen_height)
                ok = await self._click_client.click(rx, ry, double=double)
                result_msg = "Clicked successfully." if ok else "Agent unavailable."
            elif name == "scroll_screen":
                x = int(args.get("x", 0))
                y = int(args.get("y", 0))
                amount = int(args.get("amount", 0))
                rx, ry = _map_coords(x, y, self._screen_width, self._screen_height)
                ok = await self._click_client.scroll(rx, ry, amount)
                result_msg = "Scrolled." if ok else "Agent unavailable."
            elif name == "press_keys":
                keys = args.get("keys") or []
                ok = await self._click_client.hotkey(keys)
                result_msg = "Keys pressed." if ok else "Agent unavailable."
            elif name == "type_text":
                text = args.get("text") or ""
                ok = await self._click_client.type_text(text)
                result_msg = "Typed." if ok else "Agent unavailable."
            else:
                result_msg = "Unknown tool."
        except Exception as e:
            logger.warning("Tool %s failed: %s", name, e)
            result_msg = "Agent unavailable."
        try:
            await self._gemini_session.send_tool_response(call_id, name, result_msg)
        except Exception as e:
            logger.error("Failed to send tool response: %s", e)
        try:
            await self._websocket.send_json({"type": "action", "name": name, "result": result_msg})
        except Exception:
            pass

    async def _relay_gemini_to_browser(self) -> None:
        """Read audio from Gemini and send to browser. Loop so we keep listening for every turn (like Live Gemini)."""
        if self._gemini_session is None:
            return
        turn_number = 0
        try:
            while not self._stopped and self._gemini_session is not None and self._gemini_session.is_active:
                turn_number += 1
                audio_chunks_this_turn = 0
                async for chunk in self._gemini_session.receive_audio():
                    # Tagged format from Phase 7
                    if isinstance(chunk, dict):
                        kind = chunk.get("type")
                        if kind == "audio":
                            data = chunk.get("data")
                            if isinstance(data, bytes):
                                audio_chunks_this_turn += 1
                                if turn_number <= 2 and audio_chunks_this_turn <= 2:
                                    logger.info("Relay turn %s: audio chunk #%s (%s bytes)", turn_number, audio_chunks_this_turn, len(data))
                                await self._websocket.send_json({
                                    "type": "audio",
                                    "data": encode_audio_for_client(data),
                                })
                        elif kind == "tool_call":
                            await self._handle_tool_call(chunk)
                        elif kind == "turn_complete":
                            logger.info(
                                "Relay: turn %s complete — sent %s audio chunks to browser",
                                turn_number, audio_chunks_this_turn,
                            )
                            if self._summary_requested and self._summary_turn_done is not None:
                                self._summary_turn_done.set()
                            await self._websocket.send_json({"type": "status", "status": "gemini_listening"})
                            break
                        elif kind == "interrupted":
                            await self._websocket.send_json({"type": "status", "status": "interrupted"})
                        continue
                    # Legacy: bytes or str
                    if isinstance(chunk, bytes):
                        audio_chunks_this_turn += 1
                        if turn_number <= 2 and audio_chunks_this_turn <= 2:
                            logger.info("Relay turn %s: audio chunk #%s (%s bytes)", turn_number, audio_chunks_this_turn, len(chunk))
                        await self._websocket.send_json({
                            "type": "audio",
                            "data": encode_audio_for_client(chunk),
                        })
                    elif chunk == "turn_complete":
                        logger.info(
                            "Relay: turn %s complete — sent %s audio chunks to browser",
                            turn_number, audio_chunks_this_turn,
                        )
                        if self._summary_requested and self._summary_turn_done is not None:
                            self._summary_turn_done.set()
                        await self._websocket.send_json({"type": "status", "status": "gemini_listening"})
                        break
                    elif chunk == "interrupted":
                        await self._websocket.send_json({"type": "status", "status": "interrupted"})
                # receive_audio() iterator ended (one turn done). Loop again to listen for next turn.
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Gemini relay error: {e}")
            if not self._stopped:
                err_str = str(e).lower()
                if "1011" in err_str or "keepalive" in err_str or "timeout" in err_str:
                    msg = "Connection timed out. Click Start Session to reconnect."
                else:
                    msg = "Gemini connection lost."
                try:
                    await self._websocket.send_json({
                        "type": "error",
                        "message": msg,
                    })
                except Exception:
                    pass

    async def end_session_with_summary(self) -> None:
        """Request spoken summary, relay audio, get text summary, send to browser, then stop."""
        if self._stopped or self._gemini_session is None or not self._gemini_session.is_active:
            await self.stop()
            return
        self._summary_requested = True
        self._summary_turn_done = asyncio.Event()
        try:
            # 1. Request spoken summary; relay will stream audio to browser
            await self._gemini_session.send_text(SPOKEN_SUMMARY_PROMPT)
            logger.info("Summary: requested spoken summary, waiting for turn complete")
            # 2. Wait for spoken summary turn to complete (relay sets _summary_turn_done)
            try:
                await asyncio.wait_for(self._summary_turn_done.wait(), timeout=90.0)
            except asyncio.TimeoutError:
                logger.warning("Summary: spoken turn wait timed out after 90s")
            # 3. Request text summary (non-live API, ~30s timeout)
            summary_text = "Summary unavailable."
            try:
                summary_text = await asyncio.wait_for(
                    generate_summary_text(
                        api_key=self._settings.gemini_api_key,
                        model=self._settings.gemini_model,
                    ),
                    timeout=30.0,
                ) or summary_text
            except asyncio.TimeoutError:
                logger.warning("Summary: text generation timed out after 30s")
            except Exception as e:
                logger.error("Summary: text generation failed: %s", e)
            # 4. Send summary to browser
            try:
                await self._websocket.send_json({"type": "summary", "text": summary_text})
            except Exception as e:
                logger.error("Summary: failed to send to browser: %s", e)
        finally:
            self._summary_requested = False
            self._summary_turn_done = None
            await self.stop()

    async def stop(self) -> None:
        """Cancel relay, stop Gemini, send session_ended. Idempotent."""
        if self._stopped:
            return
        self._stopped = True
        if self._relay_task is not None:
            self._relay_task.cancel()
            try:
                await self._relay_task
            except asyncio.CancelledError:
                pass
            self._relay_task = None
        if self._gemini_session is not None:
            await self._gemini_session.stop()
            self._gemini_session = None
        try:
            await self._websocket.send_json({
                "type": "status",
                "status": "session_ended",
            })
        except Exception:
            pass
        logger.info("Session ended")
