"""Windows key bridge for the phone gamepad."""
import argparse
import asyncio
import json
import os
import urllib.parse
import websockets

try:
    import pydirectinput as keyboard
except ImportError:
    import pyautogui as keyboard

KEY_MAP = {"left": "a", "right": "d", "jump": "space"}
held = set()


def release_all():
    for name in list(held):
        try:
            keyboard.keyUp(KEY_MAP[name])
        except Exception:
            pass
    held.clear()


async def run(server, token):
    parsed = urllib.parse.urlparse(server)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    url = f"{scheme}://{parsed.netloc}/ws/pc?token={urllib.parse.quote(token)}"
    while True:
        try:
            print(f"Connecting to controller at {server} ...")
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                print("CONNECTED. Keep this window open while playing.")
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
            print(f"Connection lost: {exc}. Retry in 3 seconds.")
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            release_all()
            raise


def main():
    parser = argparse.ArgumentParser(description="LocalhostController Windows agent")
    parser.add_argument("--server", required=True, help="Northflank HTTPS URL")
    parser.add_argument("--token", default=os.getenv("PC_AGENT_TOKEN"), help="PC_AGENT_TOKEN from Northflank")
    args = parser.parse_args()
    if not args.token:
        parser.error("Pass --token or set PC_AGENT_TOKEN environment variable")
    try:
        asyncio.run(run(args.server.rstrip("/"), args.token))
    except KeyboardInterrupt:
        print("\nStopping controller.")
    finally:
        release_all()


if __name__ == "__main__":
    main()
