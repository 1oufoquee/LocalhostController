import asyncio
import json
import os
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICES = {}
PHONE_CONNECTIONS = set()
LOCK = asyncio.Lock()
ALLOWED_KEYS = {"left", "right", "jump"}


async def send(ws, data):
    if ws and ws.client_state.name == "CONNECTED":
        await ws.send_text(json.dumps(data))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for device in DEVICES.values():
        for role in ("agent", "desktop", "phone"):
            ws = device.get(role)
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


@app.get("/api/devices")
async def list_devices():
    async with LOCK:
        return {"devices": [
            {"id": device_id, "name": device.get("name", "Мой компьютер"),
             "available": bool(device.get("agent") and device.get("desktop") and not device.get("phone"))}
            for device_id, device in DEVICES.items()
            if device.get("agent") and device.get("desktop")
        ]}


def get_device(device_id):
    try:
        return DEVICES.get(str(uuid.UUID(device_id)))
    except (ValueError, TypeError, AttributeError):
        return None


@app.websocket("/ws/agent/{device_id}")
async def agent_socket(ws: WebSocket, device_id: str):
    device_id = str(uuid.UUID(device_id))
    await ws.accept()
    async with LOCK:
        device = DEVICES.setdefault(device_id, {"name": "Мой компьютер", "agent": None, "desktop": None, "phone": None, "pending": None})
        device["agent"] = ws
    await send(ws, {"type": "agent_connected"})
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "key" and msg.get("key") in ALLOWED_KEYS and device.get("phone"):
                await send(ws, {"type": "key", "key": msg["key"], "down": bool(msg.get("down"))})
            elif msg.get("type") == "release_all":
                pass
    except WebSocketDisconnect:
        pass
    finally:
        async with LOCK:
            if device.get("agent") is ws:
                device["agent"] = None
            phone = device.get("phone")
            device["phone"] = None
            device["pending"] = None
        await send(phone, {"type": "disconnected", "reason": "Компьютер отключился"})


@app.websocket("/ws/desktop/{device_id}")
async def desktop_socket(ws: WebSocket, device_id: str):
    device_id = str(uuid.UUID(device_id))
    await ws.accept()
    async with LOCK:
        device = DEVICES.setdefault(device_id, {"name": "Мой компьютер", "agent": None, "desktop": None, "phone": None, "pending": None})
        device["desktop"] = ws
    await send(ws, {"type": "desktop_connected", "agent_online": bool(device.get("agent"))})
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "approve":
                pending = device.get("pending")
                if pending and secrets.compare_digest(str(msg.get("request_id", "")), pending["request_id"]):
                    device["phone"] = pending["phone"]
                    device["pending"] = None
                    await send(device["phone"], {"type": "approved", "device_id": device_id})
                    await send(ws, {"type": "approved_notice"})
            elif msg.get("type") == "deny":
                pending = device.get("pending")
                if pending and secrets.compare_digest(str(msg.get("request_id", "")), pending["request_id"]):
                    await send(pending["phone"], {"type": "denied"})
                    device["pending"] = None
            elif msg.get("type") == "name":
                name = str(msg.get("name", "Мой компьютер"))[:40].strip()
                device["name"] = name or "Мой компьютер"
    except WebSocketDisconnect:
        pass
    finally:
        async with LOCK:
            if device.get("desktop") is ws:
                device["desktop"] = None
            phone = device.get("phone")
            device["phone"] = None
            device["pending"] = None
        await send(phone, {"type": "disconnected", "reason": "Страница компьютера закрыта"})


@app.websocket("/ws/phone")
async def phone_socket(ws: WebSocket):
    await ws.accept()
    PHONE_CONNECTIONS.add(ws)
    current_device = None
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "find":
                async with LOCK:
                    devices = [
                        {"id": did, "name": d.get("name", "Мой компьютер"), "available": bool(d.get("agent") and d.get("desktop") and not d.get("phone"))}
                        for did, d in DEVICES.items() if d.get("agent") and d.get("desktop")
                    ]
                await send(ws, {"type": "devices", "devices": devices})
            elif msg.get("type") == "request":
                device_id = str(msg.get("device_id", ""))
                device = get_device(device_id)
                if not device or not device.get("agent") or not device.get("desktop"):
                    await send(ws, {"type": "error", "message": "Компьютер сейчас недоступен"})
                    continue
                if device.get("phone") or device.get("pending"):
                    await send(ws, {"type": "error", "message": "Компьютер уже занят"})
                    continue
                request_id = secrets.token_urlsafe(18)
                device["pending"] = {"request_id": request_id, "phone": ws}
                current_device = device_id
                await send(device["desktop"], {"type": "connection_request", "request_id": request_id})
                await send(ws, {"type": "waiting_approval", "device_id": device_id})
            elif msg.get("type") == "key" and msg.get("key") in ALLOWED_KEYS and current_device:
                device = get_device(current_device)
                if device and device.get("phone") is ws:
                    await send(device.get("agent"), {"type": "key", "key": msg["key"], "down": bool(msg.get("down"))})
            elif msg.get("type") == "release_all" and current_device:
                device = get_device(current_device)
                if device and device.get("phone") is ws:
                    await send(device.get("agent"), {"type": "release_all"})
    except WebSocketDisconnect:
        pass
    finally:
        PHONE_CONNECTIONS.discard(ws)
        if current_device:
            device = get_device(current_device)
            if device:
                if device.get("phone") is ws:
                    device["phone"] = None
                    await send(device.get("desktop"), {"type": "phone_disconnected"})
                pending = device.get("pending")
                if pending and pending.get("phone") is ws:
                    device["pending"] = None
                await send(device.get("agent"), {"type": "release_all"})
