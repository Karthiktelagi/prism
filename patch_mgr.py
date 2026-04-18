"""Script to patch manager_html.py JS section."""
with open('dashboard/manager_html.py', 'r', encoding='utf-8') as f:
    content = f.read()

NEW_JS = r"""'''
const SC={normal:"#34a853",watch:"#f09d00",alert:"#e37400",critical:"#d93025"};
let alerts=[],curFilter="all",machineState={};
let knownIds=new Set();
const CIRC=2*Math.PI*50;
setInterval(()=>{const el=document.getElementById("clock");if(el)el.textContent=new Date().toLocaleTimeString("en-GB",{hour12:false});},1000);
function gc(s){if(s>=80)return SC.critical;if(s>=60)return SC.alert;if(s>=40)return SC.watch;return SC.normal;}
function lclass(l){const m={critical:"lc",alert:"la",watch:"lw",normal:"ln"};return m[l]||"ln";}
function fmtTime(ts){const d=new Date(ts*1000);return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short"})+" "+d.toLocaleTimeString("en-GB",{hour12:false,hour:"2-digit",minute:"2-digit"});}
function showToast(a){
  const w=document.getElementById("toast-wrap");if(!w)return;
  const t=document.createElement("div");t.className="toast";
  t.innerHTML='<span class="material-icons" style="color:'+gc(a.risk_score)+';font-size:1.1rem">warning</span><div><strong>'+a.machine_id+'</strong> &mdash; '+a.risk_level.toUpperCase()+' ('+a.risk_score.toFixed(1)+')</div><span class="tc2" onclick="this.parentElement.remove()">&#x2715;</span>';
  w.insertBefore(t,w.firstChild);
  setTimeout(()=>{if(t.parentElement)t.remove();},6000);
  while(w.children.length>4)w.removeChild(w.lastChild);
}
async function fetchAlerts(){
  try{
    const r=await fetch("/api/alerts");
    if(!r.ok){return;}
    const data=await r.json();
    if(!Array.isArray(data))return;
    data.forEach(a=>{if(!knownIds.has(a.id)){knownIds.add(a.id);if(a.risk_score>=60)showToast(a);}});
    alerts=data;renderTable();updateStats();updateDonut();
  }catch(e){console.error("fetchAlerts",e);}
}
async function fetchState(){
  try{
    const r=await fetch("/api/state");
    if(!r.ok){return;}
    const data=await r.json();
    if(data&&typeof data==="object"&&!data.error){
      machineState=data;renderMachines();renderRiskBars();
    }
  }catch(e){console.error("fetchState",e);}
}
function setFilter(f,btn){
  curFilter=f;
  document.querySelectorAll(".fc").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");renderTable();
}
function filteredAlerts(){
  if(curFilter==="unack")return alerts.filter(a=>!a.acknowledged);
  if(curFilter==="all")return alerts;
  return alerts.filter(a=>a.risk_level===curFilter);
}
function renderTable(){
  const tbody=document.getElementById("alert-tbody");if(!tbody)return;
  const rows=filteredAlerts();
  if(!rows.length){tbody.innerHTML='<tr class="empty"><td colspan="6">No alerts yet — machine data streams in every second.</td></tr>';return;}
  tbody.innerHTML=rows.map(a=>{
    const col=gc(a.risk_score);
    const ackBtn=a.acknowledged?'<span class="done">&#10003; Acked</span>':'<button class="ab ag" onclick="ack(\''+a.id+'\')">Acknowledge</button>';
    const maintBtn=a.maintenance_scheduled?'<span class="done">&#128295;</span>':'<button class="ab am" onclick="maint(\''+a.id+'\')">&#128295; Maint</button>';
    return '<tr><td><span class="lchip '+lclass(a.risk_level)+'">'+a.risk_level+'</span></td>'+
      '<td><strong>'+a.machine_id+'</strong></td>'+
      '<td><div class="sbar"><div class="sb"><div class="sf" style="width:'+Math.min(100,a.risk_score)+'%;background:'+col+'"></div></div>'+
      '<span class="sn" style="color:'+col+'">'+a.risk_score.toFixed(1)+'</span></div></td>'+
      '<td><div class="diag" title="'+a.explanation+'">'+a.explanation+'</div></td>'+
      '<td><span class="tc">'+fmtTime(a.timestamp)+'</span></td>'+
      '<td><div class="acts">'+ackBtn+maintBtn+'</div></td></tr>';
  }).join("");
}
function updateStats(){
  const total=alerts.length,unack=alerts.filter(a=>!a.acknowledged).length;
  const crit=alerts.filter(a=>a.risk_level==="critical").length;
  const maint=alerts.filter(a=>a.maintenance_scheduled).length;
  const el=id=>document.getElementById(id);
  if(el("st-t"))el("st-t").textContent=total;
  if(el("st-u"))el("st-u").textContent=unack;
  if(el("st-c"))el("st-c").textContent=crit;
  if(el("st-m"))el("st-m").textContent=maint;
  const up=el("unread-pill");
  if(up){if(unack>0){up.style.display="flex";if(el("unread-cnt"))el("unread-cnt").textContent=unack+" Unread";}else up.style.display="none";}
}
function updateDonut(){
  const segs=[
    {val:alerts.filter(a=>a.risk_level==="critical").length,color:"#d93025"},
    {val:alerts.filter(a=>a.risk_level==="alert").length,color:"#e37400"},
    {val:alerts.filter(a=>a.risk_level==="watch").length,color:"#f09d00"},
    {val:alerts.filter(a=>a.risk_level==="normal").length,color:"#34a853"}
  ];
  const total=alerts.length||1;
  let cumDeg=-90;
  segs.forEach((s,i)=>{
    const arc=document.getElementById("darc-"+i);if(!arc)return;
    const pct=s.val/total;
    const fill=pct*CIRC;
    arc.setAttribute("stroke",s.color);
    arc.setAttribute("stroke-dasharray",fill+" "+(CIRC-fill));
    arc.setAttribute("transform","rotate("+cumDeg+" 60 60)");
    cumDeg+=pct*360;
  });
  const cv=document.getElementById("d-center-val");
  if(cv)cv.textContent=alerts.length;
}
function renderMachines(){
  const ml=document.getElementById("machine-list");if(!ml)return;
  const entries=Object.entries(machineState);
  if(!entries.length){ml.innerHTML='<div style="padding:.75rem 1rem;color:#5f6368;font-size:.85rem">Waiting for machine data...</div>';return;}
  ml.innerHTML=entries.map(([mid,d])=>{
    const score=Number(d.risk_score||0),col=gc(score);
    const level=(d.risk_level||"normal").toLowerCase();
    return '<div class="machine-item"><div class="mn">'+mid+'</div>'+
      '<div class="mbar"><div class="mfill" style="width:'+score+'%;background:'+col+'"></div></div>'+
      '<span class="mscore" style="color:'+col+'">'+score.toFixed(0)+'</span>'+
      '<span class="lchip '+lclass(level)+'" style="font-size:.65rem;padding:.12rem .45rem">'+level+'</span></div>';
  }).join("");
}
function renderRiskBars(){
  const cont=document.getElementById("risk-bars");if(!cont)return;
  const entries=Object.entries(machineState);
  if(!entries.length){cont.innerHTML='<div style="color:#5f6368;font-size:.84rem">Waiting for machine data...</div>';return;}
  cont.innerHTML=entries.map(([mid,d])=>{
    const score=Number(d.risk_score||0),col=gc(score);
    return '<div class="hrbar-row"><div class="hrbar-label">'+mid+'</div>'+
      '<div class="hrbar-track"><div class="hrbar-fill" style="width:'+score+'%;background:'+col+'"></div></div>'+
      '<span class="hrbar-val" style="color:'+col+'">'+score.toFixed(0)+'</span></div>';
  }).join("");
}
async function ack(id){try{await fetch("/api/alerts/"+id+"/acknowledge",{method:"POST"});await fetchAlerts();}catch(e){}}
async function maint(id){try{await fetch("/api/alerts/"+id+"/maintenance",{method:"POST"});await fetchAlerts();}catch(e){}}
async function ackAll(){try{await fetch("/api/alerts/ack-all",{method:"POST"});await fetchAlerts();}catch(e){}}
async function scheduleAll(){try{await fetch("/api/alerts/schedule-all-critical",{method:"POST"});await fetchAlerts();}catch(e){}}
fetchAlerts();fetchState();
setInterval(fetchAlerts,3000);setInterval(fetchState,2000);
'''"""

# Find and replace the _MGR_JS block
import re
# Match from _MGR_JS = ''' to the closing '''
pattern = r"_MGR_JS = '''.*?'''"
new_content = re.sub(pattern, "_MGR_JS = " + NEW_JS, content, flags=re.DOTALL)

if new_content == content:
    print("ERROR: Pattern not found!")
else:
    with open('dashboard/manager_html.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("OK, wrote", len(new_content), "chars")

# Verify
from dashboard.manager_html import MANAGER_HTML
print("Import OK, len:", len(MANAGER_HTML))
print("Has fetchAlerts:", "fetchAlerts" in MANAGER_HTML)
print("Has curFilter:", "curFilter" in MANAGER_HTML)
print("Has error handling:", "r.ok" in MANAGER_HTML)
