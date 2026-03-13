"""Audio format utilities for CodeWhisper backend."""

import base64
import logging
logger = logging.getLogger("codewhisper")

# Audio format constants (import from config where appropriate; these document the format)
SEND_SAMPLE_RATE: int = 16000
RECEIVE_SAMPLE_RATE: int = 24000
CHANNELS: int = 1
SAMPLE_WIDTH: int = 2  # 16-bit = 2 bytes per sample
CHUNK_SIZE: int = 4096


def validate_audio_chunk(data: str) -> bytes:
    """Decode base64 audio string and validate 16-bit PCM alignment.

    Args:
        data: Base64-encoded PCM audio string as sent by the browser.

    Returns:
        Raw PCM bytes if valid.

    Raises:
        ValueError: If base64 decode fails or byte alignment is invalid.
    """
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid base64 audio data: {e}") from e

    # 16-bit PCM = 2 bytes per sample; total bytes must be even
    if len(raw) % SAMPLE_WIDTH != 0:
        raise ValueError(
            f"Invalid PCM alignment: {len(raw)} bytes (must be multiple of {SAMPLE_WIDTH})"
        )

    return raw


def encode_audio_for_client(data: bytes) -> str:
    """Encode raw PCM audio bytes as base64 for WebSocket transmission.

    Args:
        data: Raw PCM audio bytes as received from Gemini.

    Returns:
        Base64-encoded string for sending to the browser.
    """
    return base64.b64encode(data).decode("ascii")
