"""Gemini Live API session manager for CodeWhisper."""

import logging
from typing import Any, AsyncIterator, Optional, Union

from google import genai
from google.genai import types

from prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger("codewhisper")

# For non-live text generation use a text-capable model (live model may be audio-only).
TEXT_SUMMARY_MODEL = "gemini-2.0-flash"

SUMMARY_TEXT_PROMPT = """Generate a structured session summary for a coding session where the developer had screen share and voice support.
Use exactly these section headers (markdown ##):

## What Was Built

## Key Concepts

## Danger Zones Flagged

## Things to Review

## Next Steps

Fill each section with 1–3 concise bullet points or short sentences. Be specific if you have context; otherwise use brief placeholder content."""

# Phase 7: IDE navigation tools for Gemini Live (when click agent is available).
NAVIGATION_TOOLS: list[dict[str, Any]] = [
    {
        "name": "click_screen",
        "description": "Click at a specific position on the user's screen. Use this to click on files in the IDE file explorer, click on tabs to switch files, click on buttons, or click on any interactive element visible on screen. Provide x and y coordinates based on the screen image you see (768x768). Aim for the CENTER of the element you want to click.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Horizontal pixel position in the screen image."},
                "y": {"type": "integer", "description": "Vertical pixel position in the screen image."},
                "double": {"type": "boolean", "description": "Whether to double-click.", "default": False},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "scroll_screen",
        "description": "Scroll at a specific position on the user's screen. Use this to scroll through code in the editor to read more of a file. Negative values scroll down, positive values scroll up. Each unit is roughly 3 lines.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Horizontal pixel position for scrolling."},
                "y": {"type": "integer", "description": "Vertical pixel position for scrolling."},
                "amount": {"type": "integer", "description": "Scroll amount. Negative = down, positive = up."},
            },
            "required": ["x", "y", "amount"],
        },
    },
    {
        "name": "press_keys",
        "description": "Press a keyboard shortcut. Use this for IDE navigation shortcuts like Ctrl+P to open file picker, Ctrl+B to toggle file explorer. Always use 'ctrl' for the modifier key — the system translates to Cmd on macOS automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keys to press simultaneously. Example: [\"ctrl\", \"p\"]",
                },
            },
            "required": ["keys"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into the currently focused input. Use this after pressing Ctrl+P to type a filename in the file picker. Only use when an input field is focused.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The text to type."}},
            "required": ["text"],
        },
    },
]

# Tagged yield: relay handles by type.
ReceiveYield = Union[dict[str, Any], bytes, str]  # dict = tagged; legacy bytes/str for backward compat


class GeminiSession:
    """Manages a single Gemini Live API session."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        send_sample_rate: int = 16000,
        receive_sample_rate: int = 24000,
        system_instruction: str | None = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Initialize session config. Does not connect. If tools is provided, they are passed to Live connect (Phase 7 navigation)."""
        self._api_key = api_key
        self._model = model
        self._send_sample_rate = send_sample_rate
        self._receive_sample_rate = receive_sample_rate
        self._system_instruction = system_instruction if system_instruction is not None else SYSTEM_PROMPT
        self._tools = tools or []
        self._client: Optional[genai.Client] = None
        self._session: Any = None
        self._connect_context: Any = None

    @property
    def is_active(self) -> bool:
        """Whether the session is open and connected."""
        return self._session is not None

    async def start(self) -> None:
        """Open the Gemini Live API connection."""
        if self._session is not None:
            logger.warning("Gemini session already started")
            return

        try:
            self._client = genai.Client(api_key=self._api_key)
            config: dict[str, Any] = {
                "response_modalities": ["AUDIO"],
                "system_instruction": self._system_instruction,
                "speech_config": types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Puck",
                        )
                    ),
                ),
            }
            if self._tools:
                # One Tool with all function_declarations (per SDK / Live API docs).
                config["tools"] = [{"function_declarations": self._tools}]

            self._connect_context = self._client.aio.live.connect(
                model=self._model,
                config=config,
            )
            self._session = await self._connect_context.__aenter__()
            logger.info("Gemini Live API session started")

        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}")
            raise

    async def send_audio(self, data: bytes) -> None:
        """Send raw PCM audio bytes to Gemini. No-op if session not open."""
        if self._session is None:
            return

        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=data,
                    mime_type=f"audio/pcm;rate={self._send_sample_rate}",
                )
            )
        except Exception as e:
            logger.error(f"Failed to send audio to Gemini: {e}")
            raise

    async def send_image(self, data: str) -> None:
        """Send base64-encoded JPEG to Gemini. Placeholder for Phase 4. No-op if session not open."""
        if self._session is None:
            return

        try:
            import base64

            img_bytes = base64.b64decode(data)
            await self._session.send_realtime_input(
                media=types.Blob(data=img_bytes, mime_type="image/jpeg")
            )
        except Exception as e:
            logger.error(f"Failed to send image to Gemini: {e}")
            raise

    async def send_text(self, text: str) -> None:
        """Send text to Gemini."""
        if self._session is None:
            return

        try:
            await self._session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=text)],
                ),
                turn_complete=True,
            )
        except Exception as e:
            logger.error(f"Failed to send text to Gemini: {e}")
            raise

    async def receive_audio(self) -> AsyncIterator[ReceiveYield]:
        """Async generator yielding tagged responses: {"type": "audio", "data": bytes}, {"type": "tool_call", ...}, {"type": "turn_complete"}, {"type": "interrupted"}."""
        if self._session is None:
            return

        msg_count = 0
        total_bytes_this_turn = 0
        chunks_this_turn = 0
        try:
            async for msg in self._session.receive():
                msg_count += 1
                sc = getattr(msg, "server_content", None)
                # Top-level tool_call (e.g. Live API sends tool_call on message)
                tool_call = getattr(msg, "tool_call", None)
                if tool_call and hasattr(tool_call, "function_calls") and tool_call.function_calls:
                    for fc in tool_call.function_calls:
                        call_id = getattr(fc, "id", None) or ""
                        name = getattr(fc, "name", None) or ""
                        args = dict(getattr(fc, "args", None) or {})
                        logger.info("Gemini tool_call: %s %s", name, args)
                        yield {"type": "tool_call", "id": call_id, "name": name, "args": args}
                if sc:
                    if getattr(sc, "interrupted", False):
                        logger.info("Gemini: user interrupted (barge-in)")
                        yield {"type": "interrupted"}
                    if hasattr(sc, "model_turn") and sc.model_turn is not None:
                        mt = sc.model_turn
                        if hasattr(mt, "parts") and mt.parts:
                            for part in mt.parts:
                                # Audio
                                if hasattr(part, "inline_data") and part.inline_data is not None:
                                    data = (
                                        part.inline_data.data
                                        if hasattr(part.inline_data, "data")
                                        else part.inline_data
                                    )
                                    if data:
                                        chunks_this_turn += 1
                                        total_bytes_this_turn += len(data)
                                        yield {"type": "audio", "data": data}
                                # Tool call in part (alternate SDK shape)
                                if hasattr(part, "function_call") and part.function_call is not None:
                                    fc = part.function_call
                                    call_id = getattr(fc, "id", None) or ""
                                    name = getattr(fc, "name", None) or ""
                                    args = dict(getattr(fc, "args", None) or {})
                                    logger.info("Gemini tool_call (part): %s %s", name, args)
                                    yield {"type": "tool_call", "id": call_id, "name": name, "args": args}
                    turn_complete = getattr(sc, "turn_complete", False)
                    if turn_complete or msg_count <= 2 or msg_count % 20 == 0:
                        logger.info(
                            "Gemini msg #%s: turn_complete=%s, total_audio=%s chunks / %s bytes",
                            msg_count, turn_complete, chunks_this_turn, total_bytes_this_turn,
                        )
                    if turn_complete:
                        yield {"type": "turn_complete"}
        except Exception as e:
            logger.error("Gemini receive error (after %s msgs): %s", msg_count, e)
            raise

    async def send_tool_response(self, call_id: str, name: str, result: str | dict[str, Any]) -> None:
        """Send a single tool result back to Gemini so it can continue (Phase 7)."""
        if self._session is None:
            return
        try:
            resp = types.FunctionResponse(id=call_id, name=name, response={"result": result})
            await self._session.send_tool_response(function_responses=[resp])
            logger.info("Sent tool response for %s", name)
        except Exception as e:
            logger.error("Failed to send tool response: %s", e)
            raise

    async def stop(self) -> None:
        """Close the Gemini session."""
        if self._connect_context is not None:
            try:
                await self._connect_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing Gemini session: {e}")
            finally:
                self._connect_context = None
                self._session = None
                self._client = None
                logger.info("Gemini Live API session stopped")


async def generate_summary_text(api_key: str, model: str) -> Optional[str]:
    """Generate five-section markdown summary via non-live Gemini API (no session context)."""
    if not api_key:
        return None
    # Use text-capable model; configured model may be audio-only.
    text_model = TEXT_SUMMARY_MODEL if "audio" in model.lower() or "native" in model.lower() else model
    try:
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=text_model,
            contents=SUMMARY_TEXT_PROMPT,
        )
        if response and hasattr(response, "text") and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.error("generate_summary_text failed: %s", e)
        return None
