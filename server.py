import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PC_TOKEN = os.getenv("PC_AGENT_TOKEN", "")
PHONE_TOKEN = os.getenv("PHONE_TOKEN", "")
CLIENTS = {"phone": None, "pc": None}
LOCK = asyncio.Lock()
ALLOWED_KEYS = {"left", "right", "jump"}


async def send(ws, data):
    if ws and ws.client_state.name == "CONNECTED":
        await ws.send_text(json.dumps(data))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for ws in CLIENTS.values():
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


@app.websocket("/ws/{role}")
async def websocket_endpoint(ws: WebSocket, role: str, token: str = ""):
    if role not in ("phone", "pc"):
        await ws.close(code=1008)
        return
    expected = PHONE_TOKEN if role == "phone" else PC_TOKEN
    if not expected or not secrets.compare_digest(token, expected):
        await ws.close(code=1008)
        return

    await ws.accept()
    async with LOCK:
        previous = CLIENTS[role]
        CLIENTS[role] = ws
    if previous and previous is not ws:
        try:
            await previous.close(code=4001)
        except Exception:
            pass

    await send(ws, {"type": "connected", "role": role})
    other = CLIENTS["pc" if role == "phone" else "phone"]
    if other:
        await send(other, {"type": "peer", "online": True})
    if role == "phone":
        await send(ws, {"type": "peer", "online": bool(CLIENTS["pc"])})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if role == "phone":
                if msg.get("type") == "release_all":
                    target = CLIENTS["pc"]
                    await send(target, {"type": "release_all"})
                elif msg.get("type") == "key" and msg.get("key") in ALLOWED_KEYS:
                    await send(CLIENTS["pc"], {
                        "type": "key",
                        "key": msg["key"],
                        "down": bool(msg.get("down")),
                    })
    except WebSocketDisconnect:
        pass
    finally:
        async with LOCK:
            if CLIENTS[role] is ws:
                CLIENTS[role] = None
        if role == "phone":
            await send(CLIENTS["pc"], {"type": "release_all"})
        await send(CLIENTS["pc" if role == "phone" else "phone"], {"type": "peer", "online": False})
