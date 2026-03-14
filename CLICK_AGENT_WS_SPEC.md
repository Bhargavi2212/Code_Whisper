# Click Agent WebSocket Redesign

> **What this changes:** The click agent currently runs as a Flask HTTP server on localhost:8001. The backend sends HTTP POST requests to it. This only works when both run on the same machine.
> **What it becomes:** The click agent becomes a WebSocket CLIENT that connects to the backend (local or Cloud Run). The backend routes tool calls through this WebSocket. Full navigation works from the hosted Cloud Run app.
> **Time estimate:** 2-3 hours

---

## Current Architecture (HTTP — local only)

```
Backend (Docker/Cloud Run)  --HTTP POST-->  Click Agent (Flask on localhost:8001)
```

Problem: Cloud Run can't reach localhost:8001 on the user's machine.

## New Architecture (WebSocket — works everywhere)

```
Click Agent (user's machine)  --WebSocket-->  Backend (localhost OR Cloud Run)
```

The click agent connects OUTBOUND to the backend. No firewall issues. Works with localhost during dev AND with Cloud Run URL in production. Same pattern as the code watcher.

---

## Files to Change

### 1. NEW: backend/services/click_agent_bridge.py

Same pattern as extension_bridge.py. A singleton service that manages the click agent WebSocket connection.

**What it does:**
- Stores the click agent WebSocket reference when it connects
- Clears it when it disconnects
- Exposes is_connected property
- send_command(action, params) → sends command, awaits response with requestId and timeout
- handle_message(message) → resolves pending Futures when responses arrive

**The code is nearly identical to extension_bridge.py.** Copy that file and modify:
- Rename class to ClickAgentBridge
- Rename singleton to click_agent_bridge
- The command format sent to the click agent:
```json
{"type": "command", "requestId": "abc123", "action": "click", "params": {"x": 300, "y": 451}}
```
- The response format received from the click agent:
```json
{"requestId": "abc123", "status": "clicked", "x": 300, "y": 451}
```

Actions: "click", "double_click", "scroll", "hotkey", "type_text", "health"

### 2. MODIFY: backend/main.py

Add a new WebSocket endpoint: /ws/click-agent

```python
@app.websocket("/ws/click-agent")
async def websocket_click_agent(websocket: WebSocket) -> None:
    """WebSocket for the click agent. Register with click_agent_bridge on connect."""
    await websocket.accept()
    click_agent_bridge.set_connection(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            click_agent_bridge.handle_message(msg)
    except WebSocketDisconnect:
        pass
    finally:
        click_agent_bridge.clear_connection()
```

Update the health endpoint to check click_agent_bridge.is_connected instead of making an HTTP call.

### 3. MODIFY: backend/services/click_client.py → DELETE or REPLACE

The current click_client.py sends HTTP requests to localhost:8001. Replace it entirely.

The new click_client.py should route through click_agent_bridge instead of HTTP:

```python
class ClickClient:
    async def check_available(self) -> bool:
        return click_agent_bridge.is_connected

    async def click(self, x, y, double=False) -> bool:
        action = "double_click" if double else "click"
        result = await click_agent_bridge.send_command(action, {"x": x, "y": y})
        return "clicked" in result or "double_clicked" in result

    async def scroll(self, x, y, amount) -> bool:
        result = await click_agent_bridge.send_command("scroll", {"x": x, "y": y, "clicks": amount})
        return "scrolled" in result

    async def hotkey(self, keys) -> bool:
        result = await click_agent_bridge.send_command("hotkey", {"keys": keys})
        return "pressed" in result

    async def type_text(self, text) -> bool:
        result = await click_agent_bridge.send_command("type_text", {"text": text})
        return "typed" in result
```

No HTTP, no httpx. Everything goes through the WebSocket bridge.

### 4. MODIFY: backend/requirements.txt

Remove httpx — it's no longer needed (click client no longer makes HTTP calls).

Actually, keep httpx if anything else uses it. Check. If only click_client.py used it, remove it.

### 5. MODIFY: click_agent.py

This is the biggest change. Replace the Flask HTTP server with a WebSocket client.

**Current:** Flask app on localhost:8001, receives HTTP POST, calls pyautogui.
**New:** WebSocket client that connects to the backend, receives commands via WebSocket, calls pyautogui, sends results back via WebSocket.

**The new structure:**

```python
#!/usr/bin/env python3
"""
CodeWhisper Click Agent — connects to backend via WebSocket.
Receives click/scroll/hotkey/type commands; executes via pyautogui.
Works with local backend OR Cloud Run.
"""

import argparse
import asyncio
import json
import sys
import time
import logging

import pyautogui
import websockets

# --- All existing pyautogui logic stays the same ---
# pyautogui.FAILSAFE = True
# MIN_INTERVAL = 0.5
# _platform() function
# _rate_limit() function  
# _map_hotkey_keys() function
# All the actual click/scroll/hotkey/type execution functions

# --- New: WebSocket client instead of Flask server ---

DEFAULT_WS_URL = "ws://localhost:8000/ws/click-agent"

async def handle_command(action, params):
    """Execute a command and return the result dict."""
    _rate_limit()
    
    if action == "health":
        return {"status": "ok", "platform": _platform()}
    
    elif action == "click":
        x, y = params["x"], params["y"]
        pyautogui.click(x, y)
        logging.info("CLICK at (%s, %s)", x, y)
        return {"status": "clicked", "x": x, "y": y}
    
    elif action == "double_click":
        x, y = params["x"], params["y"]
        pyautogui.doubleClick(x, y)
        logging.info("DOUBLE_CLICK at (%s, %s)", x, y)
        return {"status": "double_clicked", "x": x, "y": y}
    
    elif action == "scroll":
        x, y, clicks = params["x"], params["y"], params["clicks"]
        pyautogui.moveTo(x, y)
        pyautogui.scroll(clicks)
        logging.info("SCROLL at (%s, %s) by %s", x, y, clicks)
        return {"status": "scrolled", "clicks": clicks}
    
    elif action == "hotkey":
        keys = _map_hotkey_keys(params["keys"])
        pyautogui.hotkey(*keys)
        logging.info("HOTKEY %s", "+".join(keys))
        return {"status": "pressed", "keys": params["keys"]}
    
    elif action == "type_text":
        text = params["text"]
        try:
            pyautogui.typewrite(text, interval=0.02)
        except Exception:
            pyautogui.write(text)
        logging.info("TYPED %s", repr(text[:50]))
        return {"status": "typed", "text": text}
    
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


async def run_click_agent(backend_url):
    """Connect to backend WebSocket and process commands."""
    while True:
        try:
            async with websockets.connect(backend_url, ping_interval=20, ping_timeout=10) as ws:
                log_ts(f"CONNECTED to backend at {backend_url}")
                
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    
                    if msg.get("type") != "command":
                        continue
                    
                    request_id = msg.get("requestId")
                    action = msg.get("action", "")
                    params = msg.get("params") or {}
                    
                    try:
                        result = await handle_command(action, params)
                    except Exception as e:
                        result = {"status": "error", "message": str(e)}
                        logging.error("Command %s failed: %s", action, e)
                    
                    # Send result back with requestId
                    response = {"requestId": request_id, **result}
                    await ws.send(json.dumps(response))
                    
        except (OSError, websockets.InvalidStatusCode, websockets.ConnectionClosed) as e:
            log_ts(f"Backend not available ({e}), retrying in 5s...")
        except Exception as e:
            log_ts(f"Error: {e}. Retrying in 5s...")
        
        await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="CodeWhisper Click Agent")
    parser.add_argument(
        "--backend-url",
        default=None,
        help=f"WebSocket URL for the backend (default: {DEFAULT_WS_URL})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for local backend (builds ws://localhost:PORT/ws/click-agent)"
    )
    args = parser.parse_args()
    
    if args.backend_url:
        backend_url = args.backend_url
    elif args.port:
        backend_url = f"ws://localhost:{args.port}/ws/click-agent"
    else:
        backend_url = DEFAULT_WS_URL
    
    _print_banner(backend_url)
    
    try:
        asyncio.run(run_click_agent(backend_url))
    except KeyboardInterrupt:
        log_ts("Quit.")


if __name__ == "__main__":
    main()
```

**Key changes from current click_agent.py:**
- Remove Flask, FastAPI, uvicorn imports and app
- Add websockets import
- Add --backend-url argument
- Replace HTTP endpoints with handle_command(action, params) function
- Add WebSocket client loop (same pattern as code_watcher.py)
- Keep ALL pyautogui logic unchanged
- Keep failsafe, rate limiting, platform detection, key mapping unchanged
- Keep the banner (update to show backend URL instead of port)

**Dependencies change:**
- Remove: flask (or fastapi+uvicorn for the click agent)
- Add: websockets
- Keep: pyautogui, pillow

Update the click agent requirements. The current run_click_agent.bat installs fastapi and uvicorn — change to websockets.

### 6. MODIFY: run_click_agent.bat

```bat
@echo off
python -m pip install pyautogui websockets --quiet
python click_agent.py
```

### 7. MODIFY: docker-compose.yml (optional)

If there's a click-agent service defined, update it to use WebSocket instead of HTTP. Currently there isn't one in docker-compose.yml, so no change needed.

### 8. MODIFY: backend/services/__init__.py

Add the click_agent_bridge import:
```python
from .click_agent_bridge import click_agent_bridge
```

### 9. VERIFY: backend/codewhisper/tools.py

The tool functions call ClickClient methods. ClickClient now routes through click_agent_bridge instead of HTTP. The tool function signatures DON'T change. The tools.py file should not need changes IF the ClickClient interface stays the same (check_available, click, scroll, hotkey, type_text all return the same types).

Verify that the ClickClient import path is correct after the rewrite.

### 10. MODIFY: .env.example

Remove CLICK_AGENT_URL (no longer needed — click agent connects via WebSocket, not HTTP).

### 11. MODIFY: backend/config.py

Remove click_agent_url setting (no longer needed).

---

## How It Works End-to-End (Cloud Run)

**User setup:**
```bash
# Terminal 1: Code watcher pointing at Cloud Run
pip install watchdog websockets
python code_watcher.py /path/to/project --backend-url wss://codewhisper-xxxxx.run.app/ws/extension

# Terminal 2: Click agent pointing at Cloud Run
pip install pyautogui websockets
python click_agent.py --backend-url wss://codewhisper-xxxxx.run.app/ws/click-agent

# Browser: open the Cloud Run URL
# Click Start Session, share full screen, allow mic
```

**What happens:**
1. Browser connects to Cloud Run via WebSocket (/ws/session) — voice + screen frames
2. Code watcher connects to Cloud Run via WebSocket (/ws/extension) — file data + commands
3. Click agent connects to Cloud Run via WebSocket (/ws/click-agent) — click commands
4. ADK agents on Cloud Run process everything:
   - Audio + screen frames from browser → Gemini Live API
   - File data from code watcher → injected into Gemini context
   - Tool calls from Gemini → routed to code watcher (file ops) or click agent (screen ops)
5. CodeWhisper narrates, opens files, clicks on Cursor's panel — all from the cloud

**Graceful degradation still works:**
- No code watcher → file tools return "Extension not connected"
- No click agent → click tools return "Click agent not available"
- Neither → pure voice + screen share mode
- All three connected → full experience

---

## Updated User Setup in README

### Try it online (full features with local helpers)

```bash
# 1. Open the app in your browser
# Visit: https://codewhisper-xxxxx.run.app

# 2. Connect your project files (new terminal)
pip install watchdog websockets
python code_watcher.py /path/to/your/project --backend-url wss://codewhisper-xxxxx.run.app/ws/extension

# 3. Enable IDE navigation (new terminal, optional)
pip install pyautogui websockets
python click_agent.py --backend-url wss://codewhisper-xxxxx.run.app/ws/click-agent

# 4. Click Start Session in the browser, share your full screen, allow mic
```

### Run fully local

```bash
docker compose up
python code_watcher.py /path/to/project
python click_agent.py
# Open http://localhost:3000
```

---

## Acceptance Criteria

- [ ] click_agent.py connects to backend via WebSocket (not Flask HTTP)
- [ ] click_agent.py accepts --backend-url flag for Cloud Run URL
- [ ] click_agent.py retries connection every 5s if backend unavailable
- [ ] Backend has /ws/click-agent endpoint
- [ ] click_agent_bridge.py manages the WebSocket (same pattern as extension_bridge)
- [ ] ClickClient routes through bridge instead of HTTP
- [ ] Tool calls from Gemini reach the click agent via WebSocket and return results
- [ ] pyautogui executes clicks/scrolls/hotkeys correctly (unchanged behavior)
- [ ] Full flow works: Cloud Run → click agent on user's machine → pyautogui clicks
- [ ] Full flow works: localhost backend → click agent → pyautogui clicks
- [ ] Code watcher works with Cloud Run URL (already does, just verify)
- [ ] Graceful degradation: no click agent connected → tools return appropriate message
- [ ] Flask/fastapi/uvicorn removed from click agent dependencies
- [ ] httpx removed from backend if only click_client used it

---

## Cursor Prompt

```
Read this spec. We are redesigning the click agent to connect to the backend via WebSocket instead of running as an HTTP server. This enables full IDE navigation from the Cloud Run hosted app.

Changes needed:

1. Create backend/services/click_agent_bridge.py — copy extension_bridge.py pattern, rename for click agent
2. Add /ws/click-agent WebSocket endpoint in backend/main.py
3. Rewrite backend/services/click_client.py to route through click_agent_bridge instead of HTTP
4. Rewrite click_agent.py — replace Flask HTTP server with WebSocket client (same pattern as code_watcher.py). Keep ALL pyautogui logic unchanged. Add --backend-url flag.
5. Update backend/services/__init__.py to export click_agent_bridge
6. Update run_click_agent.bat to install websockets instead of fastapi
7. Remove httpx from backend/requirements.txt if nothing else uses it
8. Update health endpoint in main.py to check click_agent_bridge.is_connected

Do NOT change: pyautogui logic, tool function signatures, agent prompts, frontend, code watcher.
```
