const $=id=>document.getElementById(id);
let socket=null,left=false,right=false,jump=false,pointer=null,phoneToken=decodeURIComponent(location.hash.slice(1));
const setStatus=(online,text)=>{$("connection").textContent=text;$("connection").className="pill "+(online?"online":"offline");$("pcStatus").textContent=online?"ПК НА СВЯЗИ":"ОЖИДАНИЕ ПК"};
function sendKey(key,down){if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:"key",key,down}))}
function releaseAll(){if(left)sendKey("left",false);if(right)sendKey("right",false);if(jump)sendKey("jump",false);left=right=jump=false;$("jump").classList.remove("pressed");$("nub").style.transform="translate(-50%,-50%)";if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:"release_all"}))}
function setDirection(x){const l=x<-.28,r=x>.28;if(l!==left){left=l;sendKey("left",l)}if(r!==right){right=r;sendKey("right",r)}}
function connect(){if(!phoneToken){setStatus(false,"НУЖНА ССЫЛКА");$("message").textContent="Открой ссылку контроллера с ключом доступа в конце адреса."; $("message").classList.remove("hidden");return}
const proto=location.protocol==="https:"?"wss:":"ws:";socket=new WebSocket(`${proto}//${location.host}/ws/phone?token=${encodeURIComponent(phoneToken)}`);
socket.onopen=()=>{setStatus(false,"СЕРВЕР ПОДКЛЮЧЕН");$("message").classList.add("hidden")};
socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.type==="peer")setStatus(m.online,m.online?"ПК НА СВЯЗИ":"ОЖИДАНИЕ ПК")};
socket.onclose=()=>{releaseAll();setStatus(false,"НЕТ СВЯЗИ");setTimeout(connect,2500)};
socket.onerror=()=>setStatus(false,"ПЕРЕПОДКЛЮЧЕНИЕ…")}
const stick=$("stick"),nub=$("nub");
function moveStick(e){const r=stick.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,max=r.width*.29,dx=e.clientX-cx,dy=e.clientY-cy,len=Math.hypot(dx,dy),scale=len>max?max/len:1,x=dx*scale,y=dy*scale;nub.style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px))`;setDirection(x/max)}
stick.addEventListener("pointerdown",e=>{if(pointer!==null)return;pointer=e.pointerId;stick.setPointerCapture(pointer);moveStick(e)});
stick.addEventListener("pointermove",e=>{if(e.pointerId===pointer)moveStick(e)});
function endStick(e){if(e.pointerId!==pointer)return;pointer=null;setDirection(0);nub.style.transform="translate(-50%,-50%)"}
stick.addEventListener("pointerup",endStick);stick.addEventListener("pointercancel",endStick);stick.addEventListener("lostpointercapture",endStick);
const jb=$("jump");function down(e){e.preventDefault();if(!jump){jump=true;sendKey("jump",true);jb.classList.add("pressed")}}function up(e){e.preventDefault();if(jump){jump=false;sendKey("jump",false);jb.classList.remove("pressed")}}
jb.addEventListener("pointerdown",e=>{jb.setPointerCapture(e.pointerId);down(e)});jb.addEventListener("pointerup",up);jb.addEventListener("pointercancel",up);jb.addEventListener("lostpointercapture",up);
document.addEventListener("visibilitychange",()=>{if(document.hidden)releaseAll()});window.addEventListener("pagehide",releaseAll);connect();