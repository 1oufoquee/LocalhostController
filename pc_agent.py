"""Windows input bridge. It creates a stable device ID and opens the PC confirmation page."""
import argparse
import asyncio
import json
import os
import uuid
import webbrowser
from pathlib import Path

import websockets

try:
    import pydirectinput as keyboard
except ImportError:
    import pyautogui as keyboard

KEY_MAP = {"left": "a", "right": "d", "jump": "space"}
held = set()


def get_device_id():
    path = Path.home() / ".localhostcontroller_device"
    if path.exists():
        try:
            return str(uuid.UUID(path.read_text(encoding="utf-8").strip()))
        except ValueError:
            pass
    value = str(uuid.uuid4())
    path.write_text(value, encoding="utf-8")
    return value


def release_all():
    for name in list(held):
        try:
            keyboard.keyUp(KEY_MAP[name])
        except Exception:
            pass
    held.clear()


async def run(server, device_id):
    from urllib.parse import urlparse
    parsed = urlparse(server)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{scheme}://{parsed.netloc}/ws/agent/{device_id}"
    pc_page = f"{server}/?pc={device_id}"
    webbrowser.open(pc_page)
    print("PC confirmation page opened in your browser.")
    print("Keep this window running. The phone will find this PC automatically.")
    while True:
        try:
            print("Connecting to LocalhostController...")
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                print("PC ONLINE. Waiting for phone controls.")
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "key":
                        name = msg.get("key")
                        if name not in KEY_MAP:
                            continue
                        key = KEY_MAP[name]
                        if msg.get("down") and name not in held:
                            keyboard.keyDown(key)
                            held.add(name)
                        elif not msg.get("down") and name in held:
                            keyboard.keyUp(key)
                            held.discard(name)
                    elif msg.get("type") == "release_all":
                        release_all()
        except (OSError, websockets.WebSocketException) as exc:
            release_all()
            print(f"Connection lost: {exc}. Retrying in 3 seconds.")
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            release_all()
            raise


def main():
    parser = argparse.ArgumentParser(description="LocalhostController Windows agent")
    parser.add_argument("--server", required=True, help="Northflank HTTPS URL")
    args = parser.parse_args()
    device_id = get_device_id()
    try:
        asyncio.run(run(args.server.rstrip("/"), device_id))
    except KeyboardInterrupt:
        print("\\nStopping controller.")
    finally:
        release_all()


if __name__ == "__main__":
    main()
