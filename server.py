import asyncio
import json
import os
import secrets
import string
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOMS = {}
ROOM_LOCK = asyncio.Lock()
KEYS = {"left": "a", "right": "d", "jump": "space"}


def make_code():
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


async def send_json(ws, payload):
    await ws.send_text(json.dumps(payload))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for room in ROOMS.values():
        for ws in (room.get("phone"), room.get("pc")):
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass


app = FastAPI(title="LocalhostController", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/room")
async def create_room():
    async with ROOM_LOCK:
        code = make_code()
        while code in ROOMS:
            code = make_code()
        ROOMS[code] = {"phone": None, "pc": None, "token": secrets.token_urlsafe(24)}
        return {"code": code, "token": ROOMS[code]["token"]}


@app.websocket("/ws/{code}/{role}")
async def websocket_endpoint(ws: WebSocket, code: str, role: str, token: str = ""):
    if role not in ("phone", "pc"):
        await ws.close(code=1008)
        return
    room = ROOMS.get(code.upper())
    if not room or (role == "pc" and not secrets.compare_digest(token, room["token"])):
        await ws.close(code=1008)
        return

    await ws.accept()
    # A room has one controller and one local PC agent.
    old = room.get(role)
    if old and old is not ws:
        try:
            await old.close(code=4001)
        except Exception:
            pass
    room[role] = ws
    await send_json(ws, {"type": "connected", "role": role})

    other_role = "pc" if role == "phone" else "phone"
    if room.get(other_role):
        await send_json(room[other_role], {"type": "peer", "online": True})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if role == "phone":
                if msg.get("type") not in ("key", "release_all"):
                    continue
                # Whitelist only the three game controls. Never accept arbitrary key names.
                if msg.get("type") == "key" and msg.get("key") not in ("left", "right", "jump"):
                    continue
                peer = room.get("pc")
                if peer:
                    await send_json(peer, msg)
            else:
                if msg.get("type") == "status" and room.get("phone"):
                    await send_json(room["phone"], msg)
    except WebSocketDisconnect:
        pass
    finally:
        if room.get(role) is ws:
            room[role] = None
        if role == "phone" and room.get("pc"):
            try:
                await send_json(room["pc"], {"type": "release_all"})
            except Exception:
                pass
        if room.get(other_role):
            try:
                await send_json(room[other_role], {"type": "peer", "online": False})
            except Exception:
                pass
        if not room.get("phone") and not room.get("pc"):
            ROOMS.pop(code.upper(), None)
