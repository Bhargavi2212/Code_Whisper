#!/usr/bin/env python3
"""
CodeWhisper Click Agent — runs on host (not in Docker).
Listens on 127.0.0.1:8001 for click/scroll/hotkey/type commands; executes via pyautogui.
"""

import sys
import time
import logging
from typing import Any

import pyautogui
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Failsafe: move mouse to corner to stop. Keep enabled.
pyautogui.FAILSAFE = True

# Rate limit: max 2 actions per second
MIN_INTERVAL = 0.5  # seconds between requests
_last_action_time: float = 0.0

# Platform for /health and hotkey mapping
def _platform() -> str:
    p = sys.platform
    if p == "win32":
        return "windows"
    if p == "darwin":
        return "darwin"
    return "linux"


def _rate_limit() -> None:
    global _last_action_time
    now = time.monotonic()
    elapsed = now - _last_action_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_action_time = time.monotonic()


def _map_hotkey_keys(keys: list[str]) -> list[str]:
    """On macOS, map 'ctrl' to 'command' for IDE shortcuts."""
    if _platform() != "darwin":
        return keys
    return ["command" if k.lower() == "ctrl" else k for k in keys]


# Request models
class ClickBody(BaseModel):
    x: int
    y: int


class ScrollBody(BaseModel):
    x: int
    y: int
    clicks: int


class HotkeyBody(BaseModel):
    keys: list[str]


class TypeTextBody(BaseModel):
    text: str


app = FastAPI(title="CodeWhisper Click Agent")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "platform": _platform()}


@app.post("/click")
def click(body: ClickBody) -> dict[str, Any]:
    _rate_limit()
    x, y = body.x, body.y
    pyautogui.click(x, y)
    logging.info("CLICK at (%s, %s)", x, y)
    return {"status": "clicked", "x": x, "y": y}


@app.post("/double_click")
def double_click(body: ClickBody) -> dict[str, Any]:
    _rate_limit()
    x, y = body.x, body.y
    pyautogui.doubleClick(x, y)
    logging.info("DOUBLE_CLICK at (%s, %s)", x, y)
    return {"status": "double_clicked", "x": x, "y": y}


@app.post("/scroll")
def scroll(body: ScrollBody) -> dict[str, Any]:
    _rate_limit()
    x, y, clicks = body.x, body.y, body.clicks
    pyautogui.moveTo(x, y)
    pyautogui.scroll(clicks)
    logging.info("SCROLL at (%s, %s) by %s", x, y, clicks)
    return {"status": "scrolled", "clicks": clicks}


@app.post("/hotkey")
def hotkey(body: HotkeyBody) -> dict[str, Any]:
    _rate_limit()
    keys = _map_hotkey_keys(body.keys)
    pyautogui.hotkey(*keys)
    logging.info("HOTKEY %s", "+".join(keys))
    return {"status": "pressed", "keys": body.keys}


@app.post("/type_text")
def type_text(body: TypeTextBody) -> dict[str, Any]:
    _rate_limit()
    text = body.text
    try:
        pyautogui.typewrite(text, interval=0.02)
    except Exception:
        pyautogui.write(text)
    logging.info("TYPED %s", repr(text[:50] + ("..." if len(text) > 50 else "")))
    return {"status": "typed", "text": text}


def _print_banner(port: int) -> None:
    plat = _platform()
    plat_label = {"windows": "Windows", "darwin": "macOS", "linux": "Linux"}.get(plat, plat)
    print(
        """
+==========================================+
|  CodeWhisper Click Agent                 |
|  Running on: %-26s |
|  Port: %-34s |
|                                          |
|  SAFETY: Move mouse to any screen        |
|  corner to emergency stop.               |
|  Press Ctrl+C to quit.                   |
+==========================================+
"""
        % (plat_label, port)
    )
    if plat == "windows":
        print("Click Agent running on Windows. No additional setup needed.")
    elif plat == "darwin":
        print(
            "Click Agent running on macOS. Grant Accessibility permissions: "
            "System Preferences → Privacy & Security → Accessibility → enable Terminal/Python."
        )
    else:
        print("Click Agent running on Linux (X11). Install xdotool: sudo apt install xdotool")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    port = 8001
    _print_banner(port)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
