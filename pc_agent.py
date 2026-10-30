"""Windows input bridge for both Fireboy and Watergirl phone controllers."""
import argparse,asyncio,json,uuid,webbrowser
from pathlib import Path
import websockets
try:import pydirectinput as keyboard
except ImportError:import pyautogui as keyboard
KEY_MAP={"water_left":"a","water_right":"d","water_jump":"w","fire_left":"left","fire_right":"right","fire_jump":"up"}
held=set()
def get_device_id():
 p=Path.home()/".localhostcontroller_device"
 if p.exists():
  try:return str(uuid.UUID(p.read_text(encoding="utf-8").strip()))
  except ValueError:pass
 value=str(uuid.uuid4());p.write_text(value,encoding="utf-8");return value
def release_all(role=None):
 for n in list(held):
  if role and not n.startswith(role+"_"):continue
  try:keyboard.keyUp(KEY_MAP[n])
  except Exception:pass
  held.discard(n)
async def run(server,did):
 from urllib.parse import urlparse
 p=urlparse(server);scheme="wss" if p.scheme=="https" else "ws";url=f"{scheme}://{p.netloc}/ws/agent/{did}"
 webbrowser.open(f"{server}/?pc={did}");print("PC page opened. Waiting for both phone players.")
 while True:
  try:
   print("Connecting...")
   async with websockets.connect(url,ping_interval=20,ping_timeout=20) as ws:
    print("PC ONLINE. Fire and Water can connect.")
    async for raw in ws:
     m=json.loads(raw)
     if m.get("type")=="key":
      n=m.get("key")
      if n not in KEY_MAP:continue
      k=KEY_MAP[n]
      if m.get("down") and n not in held:keyboard.keyDown(k);held.add(n)
      elif not m.get("down") and n in held:keyboard.keyUp(k);held.discard(n)
     elif m.get("type")=="release_all":release_all(m.get("role"))
  except (OSError,websockets.WebSocketException) as e:
   release_all();print(f"Connection lost: {e}. Retry in 3 seconds.");await asyncio.sleep(3)
  except asyncio.CancelledError:release_all();raise
def main():
 p=argparse.ArgumentParser();p.add_argument("--server",required=True);a=p.parse_args()
 try:asyncio.run(run(a.server.rstrip("/"),get_device_id()))
 except KeyboardInterrupt:print("\nStopping.")
 finally:release_all()
if __name__=="__main__":main()
