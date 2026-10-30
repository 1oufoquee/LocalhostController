"""Windows bridge: receives secure room commands and sends key-down/up to the game."""
import argparse
import asyncio
import json
import os
import sys
import urllib.parse

import websockets

try:
    import pydirectinput as keyboard
except ImportError:
    import pyautogui as keyboard


KEY_MAP = {"left": "a", "right": "d", "jump": "space"}
held = set()


def release_all():
    for key in list(held):
        try:
            keyboard.keyUp(KEY_MAP[key])
        except Exception:
            pass
    held.clear()


async def run(server, code, token):
    parsed = urllib.parse.urlparse(server)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    url = f"{scheme}://{parsed.netloc}/ws/{code}/pc?token={urllib.parse.quote(token)}"
    print(f"Connecting to room {code} at {server} ...")
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        print("CONNECTED. Keep this window open while playing.")
        print("Phone controls: left/right = A/D, jump = Space.")
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "key":
                name = msg.get("key")
                if name not in KEY_MAP:
                    continue
                down = bool(msg.get("down"))
                key = KEY_MAP[name]
                if down and name not in held:
                    keyboard.keyDown(key)
                    held.add(name)
                elif not down and name in held:
                    keyboard.keyUp(key)
                    held.discard(name)
            elif msg.get("type") == "release_all":
                release_all()


def main():
    p = argparse.ArgumentParser(description="LocalhostController PC agent")
    p.add_argument("--server", default=os.getenv("CONTROLLER_URL", "https://localhostcontroller.onrender.com"), help="Public site URL")
    p.add_argument("--code", required=True, help="6-character room code")
    p.add_argument("--token", required=True, help="Room token shown by room creator")
    args = p.parse_args()
    try:
        asyncio.run(run(args.server.rstrip("/"), args.code.upper(), args.token))
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        release_all()


if __name__ == "__main__":
    main()
