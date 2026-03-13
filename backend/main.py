"""FastAPI application entry point for CodeWhisper backend."""

import json
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("codewhisper")

# Startup: log whether Gemini API key is set (diagnostic for "not responding")
logger.info(
    "CodeWhisper backend starting: GEMINI_API_KEY set=%s, model=%s",
    bool(settings.gemini_api_key),
    settings.gemini_model,
)

# Create FastAPI app
app = FastAPI(
    title="CodeWhisper",
    description="Real-time AI coding companion",
    version="1.0.0",
)

# CORS for development (frontend on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "codewhisper-backend",
        "gemini_model": settings.gemini_model,
        "gemini_api_key_set": bool(settings.gemini_api_key),
    }


@app.websocket("/ws/session")
async def websocket_session(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for CodeWhisper sessions."""
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session_manager = SessionManager(websocket, settings)

    try:
        await websocket.send_json({
            "type": "status",
            "status": "connected",
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "unknown")

            logger.debug(f"Received message type: {msg_type}")

            if msg_type == "control":
                action = message.get("action")
                if action == "start_session":
                    logger.info("Session start requested")
                    await websocket.send_json({
                        "type": "status",
                        "status": "session_starting",
                    })
                    screen_width = message.get("screen_width")
                    screen_height = message.get("screen_height")
                    await session_manager.start(
                        screen_width=int(screen_width) if screen_width is not None else None,
                        screen_height=int(screen_height) if screen_height is not None else None,
                    )

                elif action == "end_session":
                    logger.info("Session end requested")
                    await session_manager.end_session_with_summary()
                    break

                elif action == "switch_mode":
                    mode = message.get("mode")
                    if mode and mode in ("sportscaster", "catchup", "review"):
                        await session_manager.handle_switch_mode(mode)

            elif msg_type == "audio":
                await session_manager.handle_audio(message.get("data", ""))

            elif msg_type == "frame":
                await session_manager.handle_frame(message.get("data", ""))

            elif msg_type == "text":
                await session_manager.handle_text(message.get("text", ""))

            else:
                logger.warning(f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid message format",
            })
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        await session_manager.stop()
        logger.info("WebSocket connection closed")


# Serve React static files in production
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
