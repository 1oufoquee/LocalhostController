import asyncio,json,os,secrets,uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
BASE_DIR=os.path.dirname(os.path.abspath(__file__));DEVICES={};LOCK=asyncio.Lock()
ROLES={"fire","water"};ACTIONS={"left","right","jump"}
def fresh(): return {"name":"Мой компьютер","agent":None,"desktop":None,"phones":{},"pending":{}}
async def send(ws,data):
    if ws and ws.client_state.name=="CONNECTED": await ws.send_text(json.dumps(data))
def getdev(did):
    try:return DEVICES.get(str(uuid.UUID(did)))
    except (ValueError,TypeError,AttributeError):return None
@asynccontextmanager
async def lifespan(app):
    yield
    for d in DEVICES.values():
        for ws in [d["agent"],d["desktop"],*d["phones"].values()]:
            if ws:
                try:await ws.close()
                except Exception:pass
app=FastAPI(title="LocalhostController",lifespan=lifespan)
app.mount("/static",StaticFiles(directory=os.path.join(BASE_DIR,"static")),name="static")
@app.get("/")
async def index():return FileResponse(os.path.join(BASE_DIR,"static","index.html"))
@app.get("/health")
async def health():return {"status":"ok"}
@app.websocket("/ws/agent/{device_id}")
async def agent(ws:WebSocket,device_id:str):
    try:device_id=str(uuid.UUID(device_id))
    except ValueError:await ws.close(code=1008);return
    await ws.accept()
    async with LOCK:d=DEVICES.setdefault(device_id,fresh());d["agent"]=ws
    try:
        while True:await ws.receive_text()
    except WebSocketDisconnect:pass
    finally:
        async with LOCK:
            if d["agent"] is ws:d["agent"]=None
            phones=list(d["phones"].values());d["phones"].clear();d["pending"].clear()
        for p in phones:await send(p,{"type":"disconnected","reason":"Компьютер отключился"})
@app.websocket("/ws/desktop/{device_id}")
async def desktop(ws:WebSocket,device_id:str):
    try:device_id=str(uuid.UUID(device_id))
    except ValueError:await ws.close(code=1008);return
    await ws.accept()
    async with LOCK:d=DEVICES.setdefault(device_id,fresh());d["desktop"]=ws
    await send(ws,{"type":"desktop_connected","agent_online":bool(d["agent"])})
    try:
        while True:
            try:m=json.loads(await ws.receive_text())
            except (json.JSONDecodeError,TypeError):continue
            role=m.get("role")
            if m.get("type") in ("approve","deny") and role in ROLES:
                p=d["pending"].get(role)
                if p and secrets.compare_digest(str(m.get("request_id","")),p["request_id"]):
                    d["pending"].pop(role,None)
                    if m["type"]=="approve" and d["agent"] and role not in d["phones"]:
                        d["phones"][role]=p["phone"];await send(p["phone"],{"type":"approved","role":role});await send(ws,{"type":"approved_notice","role":role})
                    else:await send(p["phone"],{"type":"denied"})
    except WebSocketDisconnect:pass
    finally:
        async with LOCK:
            if d["desktop"] is ws:d["desktop"]=None
            phones=list(d["phones"].values());pending=list(d["pending"].values());d["phones"].clear();d["pending"].clear()
        for p in phones:await send(p,{"type":"disconnected","reason":"Страница компьютера закрыта"})
        for p in pending:await send(p["phone"],{"type":"disconnected","reason":"Страница компьютера закрыта"})
@app.websocket("/ws/phone")
async def phone(ws:WebSocket):
    await ws.accept();did=None;role=None
    try:
        while True:
            try:m=json.loads(await ws.receive_text())
            except (json.JSONDecodeError,TypeError):continue
            if m.get("type")=="find":
                devices=[]
                for k,d in DEVICES.items():
                    if d["agent"] and d["desktop"]:
                        devices.append({"id":k,"name":d["name"],"roles":{r:r not in d["phones"] and r not in d["pending"] for r in ROLES}})
                await send(ws,{"type":"devices","devices":devices})
            elif m.get("type")=="request":
                ndid=str(m.get("device_id",""));nr=m.get("role");d=getdev(ndid)
                if nr not in ROLES or not d or not d["agent"] or not d["desktop"]:await send(ws,{"type":"error","message":"Компьютер сейчас недоступен"});continue
                if nr in d["phones"] or nr in d["pending"]:await send(ws,{"type":"error","message":"Этот персонаж уже подключён с другого телефона"});continue
                rid=secrets.token_urlsafe(18);d["pending"][nr]={"request_id":rid,"phone":ws};did,role=ndid,nr
                await send(d["desktop"],{"type":"connection_request","request_id":rid,"role":nr});await send(ws,{"type":"waiting_approval"})
            elif m.get("type")=="key" and m.get("key") in ACTIONS and did and role:
                d=getdev(did)
                if d and d["phones"].get(role) is ws:
                    prefix="fire" if role=="fire" else "water";await send(d["agent"],{"type":"key","key":prefix+"_"+m["key"],"down":bool(m.get("down"))})
            elif m.get("type")=="release_all" and did and role:
                d=getdev(did)
                if d and d["phones"].get(role) is ws:await send(d["agent"],{"type":"release_all","role":role})
    except WebSocketDisconnect:pass
    finally:
        if did and role:
            d=getdev(did)
            if d:
                if d["phones"].get(role) is ws:d["phones"].pop(role,None);await send(d["desktop"],{"type":"phone_disconnected","role":role})
                p=d["pending"].get(role)
                if p and p["phone"] is ws:d["pending"].pop(role,None)
                await send(d["agent"],{"type":"release_all","role":role})
