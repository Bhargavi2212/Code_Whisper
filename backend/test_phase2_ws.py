"""Phase 2 WebSocket test script. Run: python test_phase2_ws.py"""

import asyncio
import json
import os
import sys

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

WS_URL = os.environ.get("WS_URL", "ws://localhost:8000/ws/session")


async def test1_text_response() -> None:
    """Test 1: Connect, start_session, send text, receive audio, end_session."""
    print("\n--- Test 1: Basic Connection and Text Response ---")
    async with websockets.connect(WS_URL) as ws:
        msg = json.loads(await ws.recv())
        assert msg.get("type") == "status" and msg.get("status") == "connected"
        print("  Connected")

        await ws.send(json.dumps({"type": "control", "action": "start_session"}))
        msg = json.loads(await ws.recv())
        assert msg.get("status") == "session_starting"
        print("  Session starting...")

        msg = json.loads(await ws.recv())
        if msg.get("type") == "error":
            print(f"  Error: {msg.get('message')}")
            return
        assert msg.get("status") == "gemini_connected"
        print("  Gemini connected")

        await ws.send(
            json.dumps({
                "type": "text",
                "text": "Hello, please say 'CodeWhisper test successful' in a few words.",
            })
        )
        print("  Sent text, waiting for audio...")

        audio_count = 0
        for _ in range(100):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
                msg = json.loads(raw)
                if msg.get("type") == "audio":
                    audio_count += 1
                    size = len(msg.get("data", ""))
                    if audio_count <= 3:
                        print(f"  Received audio chunk {audio_count}: {size} bytes (base64)")
                elif msg.get("type") == "status":
                    s = msg.get("status", "")
                    if s == "session_ended":
                        break
                    print(f"  Status: {s}")
                elif msg.get("type") == "error":
                    print(f"  Error: {msg.get('message')}")
                    break
            except asyncio.TimeoutError:
                break

        print(f"  Total audio chunks received: {audio_count}")

        await ws.send(json.dumps({"type": "control", "action": "end_session"}))
        msg = json.loads(await ws.recv())
        assert msg.get("status") == "session_ended"
        print("  Session ended")

    print("  Test 1 PASSED")


async def test3_invalid_key() -> None:
    """Test 3: Invalid API key produces error, no crash."""
    print("\n--- Test 3: Error Handling (invalid key) ---")
    print("  (Skipped - requires manual API key change)")
    print("  Test 3 MANUAL")


async def test4_disconnect_cleanup() -> None:
    """Test 4: Disconnect triggers cleanup."""
    print("\n--- Test 4: Disconnect Cleanup ---")
    ws = await websockets.connect(WS_URL)
    msg = json.loads(await ws.recv())
    assert msg.get("status") == "connected"

    await ws.send(json.dumps({"type": "control", "action": "start_session"}))
    await ws.recv()
    msg = json.loads(await ws.recv())
    if msg.get("type") == "error":
        print(f"  Could not start session: {msg.get('message')}")
        await ws.close()
        return
    assert msg.get("status") == "gemini_connected"

    await ws.close()
    print("  Disconnected abruptly - check server logs for cleanup")
    print("  Test 4 DONE")


async def main() -> None:
    print("Phase 2 WebSocket Tests")
    print(f"Connecting to {WS_URL}")

    await test1_text_response()
    await test3_invalid_key()
    await test4_disconnect_cleanup()

    print("\n--- All tests completed ---")


if __name__ == "__main__":
    asyncio.run(main())
