const $ = id => document.getElementById(id);
let socket = null, room = "", left = false, right = false, jump = false, pointer = null;
const setStatus = (online, text) => { $("connection").textContent = text; $("connection").className = "pill " + (online ? "online" : "offline"); };
function sendKey(key, down) { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:"key", key, down})); }
function releaseAll(){ if(left)sendKey("left",false); if(right)sendKey("right",false); if(jump)sendKey("jump",false); left=right=jump=false; $("jump").classList.remove("pressed"); $("nub").style.transform="translate(-50%,-50%)"; }
function setDirection(x){ const nextLeft=x < -0.28, nextRight=x > 0.28; if(nextLeft!==left){left=nextLeft;sendKey("left",left)} if(nextRight!==right){right=nextRight;sendKey("right",right)} }
function connect(){
  room=$("roomCode").value.trim().toUpperCase();
  if(!/^[A-Z0-9]{6}$/.test(room)){ $("joinError").textContent="Введи 6-значный код комнаты."; return; }
  const proto=location.protocol==="https:"?"wss:":"ws:";
  socket=new WebSocket(`${proto}//${location.host}/ws/${room}/phone`);
  $("connectBtn").disabled=true; $("joinError").textContent="Подключаемся…";
  socket.onopen=()=>{ $("join").classList.add("hidden"); $("controller").classList.remove("hidden"); $("roomLabel").textContent="ROOM "+room; setStatus(true,"СЕРВЕР ПОДКЛЮЧЕН"); };
  socket.onmessage=e=>{const m=JSON.parse(e.data); if(m.type==="peer")setStatus(m.online,"ПК "+(m.online?"НА СВЯЗИ":"НЕ В СЕТИ"));};
  socket.onclose=()=>{releaseAll(); $("controller").classList.add("hidden"); $("join").classList.remove("hidden"); $("connectBtn").disabled=false; $("joinError").textContent="Соединение закрыто. Проверь код и агент на ПК."; setStatus(false,"НЕ ПОДКЛЮЧЕНО");};
  socket.onerror=()=>{ $("joinError").textContent="Не удалось подключиться. Проверь адрес сайта и код."; };
}
$("connectBtn").addEventListener("click",connect);
$("roomCode").addEventListener("input",e=>e.target.value=e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,""));
$("disconnect").addEventListener("click",()=>{releaseAll();socket?.close();});

const stick=$("stick"), nub=$("nub");
function moveStick(e){
  const r=stick.getBoundingClientRect(), cx=r.left+r.width/2, cy=r.top+r.height/2;
  const max=r.width*.29, dx=e.clientX-cx, dy=e.clientY-cy, len=Math.hypot(dx,dy), scale=len>max?max/len:1;
  const x=dx*scale,y=dy*scale;
  nub.style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px))`;
  setDirection(x/max);
}
stick.addEventListener("pointerdown",e=>{if(pointer!==null)return;pointer=e.pointerId;stick.setPointerCapture(pointer);moveStick(e);});
stick.addEventListener("pointermove",e=>{if(e.pointerId===pointer)moveStick(e);});
function endStick(e){if(e.pointerId!==pointer)return;pointer=null;setDirection(0);nub.style.transform="translate(-50%,-50%)";}
stick.addEventListener("pointerup",endStick);stick.addEventListener("pointercancel",endStick);stick.addEventListener("lostpointercapture",endStick);
const jumpBtn=$("jump");
function jumpDown(e){e.preventDefault();if(!jump){jump=true;sendKey("jump",true);jumpBtn.classList.add("pressed");}}
function jumpUp(e){e.preventDefault();if(jump){jump=false;sendKey("jump",false);jumpBtn.classList.remove("pressed");}}
jumpBtn.addEventListener("pointerdown",e=>{jumpBtn.setPointerCapture(e.pointerId);jumpDown(e);});
jumpBtn.addEventListener("pointerup",jumpUp);jumpBtn.addEventListener("pointercancel",jumpUp);jumpBtn.addEventListener("lostpointercapture",jumpUp);
document.addEventListener("visibilitychange",()=>{if(document.hidden)releaseAll();});
window.addEventListener("pagehide",releaseAll);