"""Manager Dashboard HTML with charts and graphics."""

_MGR_CSS = '''
*{box-sizing:border-box;margin:0;padding:0;font-family:'Roboto',sans-serif;}
body{background:#f1f3f4;color:#202124;min-height:100vh;}
.topbar{background:#fff;border-bottom:1px solid #e0e0e0;height:64px;padding:0 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.1);}
.topbar-left{display:flex;align-items:center;gap:.75rem;}
.tlogo{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#ea4335,#fbbc04);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1rem;color:#fff;}
.ttitle{font-size:1.25rem;font-weight:500;color:#202124;}.ttitle b{color:#ea4335;}
.topbar-right{display:flex;align-items:center;gap:.75rem;}
.uchip{display:flex;align-items:center;gap:.4rem;background:#f1f3f4;border-radius:20px;padding:.35rem .85rem;font-size:.83rem;color:#3c4043;}
.tbtn{background:transparent;border:1px solid #dadce0;border-radius:4px;padding:.4rem .9rem;font-size:.82rem;color:#1a73e8;cursor:pointer;font-family:inherit;text-decoration:none;transition:background .15s;display:inline-flex;align-items:center;gap:.3rem;}
.tbtn:hover{background:#e8f0fe;}
.danger{color:#d93025;border-color:#dadce0;}.danger:hover{background:#fce8e6;}
.main{padding:1.5rem;max-width:1500px;margin:0 auto;}
/* Stats */
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin-bottom:1.5rem;}
.sc{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:1rem 1.2rem;display:flex;flex-direction:column;gap:.25rem;}
.sc-icon{font-size:1.5rem;margin-bottom:.1rem;}
.sc-label{font-size:.72rem;font-weight:500;color:#5f6368;text-transform:uppercase;letter-spacing:.5px;}
.sc-val{font-size:2rem;font-weight:400;}
.sc-change{font-size:.72rem;color:#80868b;}
.c-blue .sc-val{color:#1a73e8;}.c-red .sc-val{color:#d93025;}
.c-orange .sc-val{color:#e37400;}.c-amber .sc-val{color:#f09d00;}.c-green .sc-val{color:#188038;}
/* Layout */
.layout{display:grid;grid-template-columns:1fr 380px;gap:1.25rem;}
@media(max-width:1000px){.layout{grid-template-columns:1fr;}}
/* Panel */
.panel{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);overflow:hidden;margin-bottom:1.25rem;}
.ph{padding:.9rem 1.2rem;border-bottom:1px solid #f1f3f4;display:flex;align-items:center;justify-content:space-between;}
.ph-title{font-size:.9rem;font-weight:500;color:#202124;display:flex;align-items:center;gap:.5rem;}
.ph-actions{display:flex;gap:.5rem;}
/* Filters */
.filters{padding:.65rem 1.2rem;border-bottom:1px solid #f1f3f4;display:flex;gap:.5rem;flex-wrap:wrap;}
.fc{border:1px solid #dadce0;border-radius:16px;padding:.25rem .8rem;font-size:.76rem;color:#5f6368;cursor:pointer;background:#fff;font-family:inherit;transition:all .15s;}
.fc.active{background:#e8f0fe;border-color:#1a73e8;color:#1a73e8;font-weight:500;}
/* Table */
.tw{overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:.83rem;}
thead th{text-align:left;padding:.65rem 1rem;color:#5f6368;font-weight:500;font-size:.73rem;border-bottom:1px solid #e0e0e0;white-space:nowrap;}
tbody td{padding:.65rem 1rem;border-bottom:1px solid #f8f9fa;vertical-align:middle;}
tbody tr:hover td{background:#f8f9fa;}
.lchip{display:inline-flex;align-items:center;border-radius:12px;padding:.18rem .6rem;font-size:.7rem;font-weight:500;}
.lc{background:#fce8e6;color:#c5221f;}.la{background:#fef0e0;color:#e37400;}
.lw{background:#fef7e0;color:#f09d00;}.ln{background:#e6f4ea;color:#188038;}
.sbar{display:flex;align-items:center;gap:.5rem;}
.sb{width:50px;height:4px;background:#e0e0e0;border-radius:2px;overflow:hidden;flex-shrink:0;}
.sf{height:100%;border-radius:2px;}
.sn{font-size:.82rem;font-weight:500;}
.diag{max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#5f6368;font-size:.78rem;}
.tc{color:#80868b;font-size:.76rem;white-space:nowrap;}
.acts{display:flex;gap:.4rem;}
.ab{border:1px solid #dadce0;border-radius:4px;padding:.2rem .55rem;font-size:.7rem;cursor:pointer;font-family:inherit;background:#fff;transition:all .15s;white-space:nowrap;}
.ag{color:#188038;border-color:#34a853;}.ag:hover{background:#e6f4ea;}
.am{color:#b06000;border-color:#fbbc04;}.am:hover{background:#fef7e0;}
.ab:disabled{opacity:.4;cursor:default;}
.done{font-size:.7rem;color:#80868b;}
.empty td{text-align:center;padding:2.5rem;color:#5f6368;}
/* Charts */
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.25rem;}
@media(max-width:700px){.chart-row{grid-template-columns:1fr;}}
.chart-panel{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:1rem 1.2rem;}
.cp-title{font-size:.85rem;font-weight:500;color:#202124;margin-bottom:.85rem;}
.donut-wrap{position:relative;width:130px;height:130px;margin:0 auto .75rem;}
.donut-wrap svg{width:100%;height:100%;}
.donut-bg{fill:none;stroke:#f1f3f4;stroke-width:18;}
.donut-arc{fill:none;stroke-width:18;stroke-linecap:butt;transition:stroke-dasharray .5s ease;}
.donut-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.dc-val{font-size:1.5rem;font-weight:400;line-height:1;}
.dc-lbl{font-size:.6rem;color:#80868b;margin-top:2px;}
.legend{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;}
.leg-item{display:flex;align-items:center;gap:.3rem;font-size:.73rem;color:#5f6368;}
.leg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
/* Sidebar */
.machine-item{display:flex;align-items:center;gap:.75rem;padding:.75rem 1.1rem;border-bottom:1px solid #f8f9fa;}
.machine-item:last-child{border-bottom:none;}
.mn{font-size:.88rem;font-weight:500;flex:1;}
.mbar{flex:1;max-width:80px;height:4px;background:#e0e0e0;border-radius:2px;overflow:hidden;}
.mfill{height:100%;border-radius:2px;transition:width .5s;}
.mscore{font-size:.85rem;font-weight:500;width:34px;text-align:right;}
/* Quick actions */
.qbtn{display:flex;align-items:center;gap:.6rem;width:100%;border:none;border-radius:4px;padding:.7rem .9rem;font-size:.84rem;cursor:pointer;font-family:inherit;transition:background .15s;text-align:left;text-decoration:none;margin-bottom:.45rem;}
.qbtn:last-child{margin-bottom:0;}
.qg{background:#e6f4ea;color:#188038;}.qg:hover{background:#ceead6;}
.qa{background:#fef7e0;color:#b06000;}.qa:hover{background:#fdefc3;}
.qb{background:#e8f0fe;color:#1a73e8;}.qb:hover{background:#d2e3fc;}
.qr{background:#f1f3f4;color:#5f6368;}.qr:hover{background:#e0e0e0;}
/* Horizontal risk bars chart */
.hrbar-row{display:flex;align-items:center;gap:.75rem;margin-bottom:.6rem;}
.hrbar-label{width:90px;font-size:.8rem;color:#3c4043;text-align:right;flex-shrink:0;font-weight:500;}
.hrbar-track{flex:1;height:12px;background:#f1f3f4;border-radius:6px;overflow:hidden;}
.hrbar-fill{height:100%;border-radius:6px;transition:width .6s ease;}
.hrbar-val{width:36px;font-size:.78rem;font-weight:500;text-align:left;}
/* Toast */
.toast-wrap{position:fixed;bottom:1.5rem;right:1.5rem;display:flex;flex-direction:column;gap:.5rem;z-index:9999;}
.toast{background:#323232;color:#fff;border-radius:4px;padding:.75rem 1.1rem;font-size:.83rem;box-shadow:0 4px 12px rgba(0,0,0,.3);display:flex;align-items:center;gap:.75rem;min-width:260px;animation:ti .25s ease;}
@keyframes ti{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.tc2{margin-left:auto;cursor:pointer;color:rgba(255,255,255,.6);font-size:.9rem;}
'''

_MGR_JS = r'''
const SC={normal:"#34a853",watch:"#f09d00",alert:"#e37400",critical:"#d93025"};
let alerts=[],curFilter="all",machineState={};
let knownIds=new Set();
const CIRC=2*Math.PI*50;
let _authFailed=false;
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
async function apiFetch(url){
  const r=await fetch(url,{credentials:"same-origin"});
  if(r.status===401||r.status===403){
    if(!_authFailed){
      _authFailed=true;
      document.getElementById("alert-tbody").innerHTML='<tr class="empty"><td colspan="6" style="color:#d93025">&#9888; Session expired &mdash; <a href="/manager/login" style="color:#1a73e8">click here to re-login</a></td></tr>';
    }
    return null;
  }
  if(!r.ok)return null;
  return r.json();
}
async function fetchAlerts(){
  const data=await apiFetch("/api/alerts");
  if(!data)return;
  if(!Array.isArray(data))return;
  _authFailed=false;
  data.forEach(a=>{if(!knownIds.has(a.id)){knownIds.add(a.id);if(a.risk_score>=60)showToast(a);}});
  alerts=data;renderTable();updateStats();updateDonut();
}
async function fetchState(){
  const data=await apiFetch("/api/state");
  if(!data||data.error)return;
  machineState=data;renderMachines();renderRiskBars();
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
  if(!rows.length){tbody.innerHTML='<tr class="empty"><td colspan="6">No alerts yet. Machines stream data every second &mdash; alerts appear when risk exceeds 60.</td></tr>';return;}
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
    arc.setAttribute("stroke",s.color);
    arc.setAttribute("stroke-dasharray",(pct*CIRC)+" "+((1-pct)*CIRC));
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
async function ack(id){try{await fetch("/api/alerts/"+id+"/acknowledge",{method:"POST",credentials:"same-origin"});await fetchAlerts();}catch(e){}}
async function maint(id){try{await fetch("/api/alerts/"+id+"/maintenance",{method:"POST",credentials:"same-origin"});await fetchAlerts();}catch(e){}}
async function ackAll(){try{await fetch("/api/alerts/ack-all",{method:"POST",credentials:"same-origin"});await fetchAlerts();}catch(e){}}
async function scheduleAll(){try{await fetch("/api/alerts/schedule-all-critical",{method:"POST",credentials:"same-origin"});await fetchAlerts();}catch(e){}}
fetchAlerts();fetchState();
setInterval(fetchAlerts,3000);setInterval(fetchState,2000);
'''

MANAGER_HTML = (
    '<!DOCTYPE html><html lang="en"><head>'
    '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
    '<title>PRISM Manager</title>'
    '<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">'
    '<style>' + _MGR_CSS + '</style></head><body>'
    # Topbar
    '<div class="topbar">'
    '<div class="topbar-left"><div class="tlogo">M</div><span class="ttitle">PRISM <b>Manager</b></span></div>'
    '<div class="topbar-right">'
    '<span id="unread-pill" style="display:none;align-items:center;gap:.4rem;background:#fce8e6;border-radius:20px;padding:.3rem .8rem;">'
    '<span class="material-icons" style="font-size:.95rem;color:#d93025">notifications_active</span>'
    '<span id="unread-cnt" style="font-size:.8rem;color:#d93025;font-weight:500"></span></span>'
    '<span class="uchip"><span class="material-icons" style="font-size:1rem;color:#5f6368">account_circle</span>{{USER}}</span>'
    '<a href="/dashboard" class="tbtn"><span class="material-icons" style="font-size:.95rem">monitor</span>Dashboard</a>'
    '<a href="/manager/logout" class="tbtn danger">Sign out</a>'
    '<span id="clock" style="font-size:.8rem;color:#5f6368;margin-left:.25rem"></span>'
    '</div></div>'
    '<div class="main">'
    # Stats
    '<div class="stats-row">'
    '<div class="sc c-blue"><span class="material-icons sc-icon" style="color:#1a73e8">bar_chart</span><div class="sc-label">Total Alerts</div><div class="sc-val" id="st-t">0</div></div>'
    '<div class="sc c-red"><span class="material-icons sc-icon" style="color:#d93025">error_outline</span><div class="sc-label">Unacknowledged</div><div class="sc-val" id="st-u">0</div></div>'
    '<div class="sc c-orange"><span class="material-icons sc-icon" style="color:#e37400">warning_amber</span><div class="sc-label">Critical</div><div class="sc-val" id="st-c">0</div></div>'
    '<div class="sc c-green"><span class="material-icons sc-icon" style="color:#188038">build_circle</span><div class="sc-label">Maint. Scheduled</div><div class="sc-val" id="st-m">0</div></div>'
    '</div>'
    # Charts row
    '<div class="chart-row">'
    # Donut chart
    '<div class="chart-panel">'
    '<div class="cp-title">Alert Distribution</div>'
    '<div class="donut-wrap">'
    '<svg viewBox="0 0 120 120"><circle class="donut-bg" cx="60" cy="60" r="50"/>'
    '<circle id="darc-0" class="donut-arc" cx="60" cy="60" r="50" stroke-dasharray="0 314.16" stroke-dashoffset="0" stroke="#d93025" transform="rotate(-90 60 60)"/>'
    '<circle id="darc-1" class="donut-arc" cx="60" cy="60" r="50" stroke-dasharray="0 314.16" stroke-dashoffset="0" stroke="#e37400" transform="rotate(-90 60 60)"/>'
    '<circle id="darc-2" class="donut-arc" cx="60" cy="60" r="50" stroke-dasharray="0 314.16" stroke-dashoffset="0" stroke="#f09d00" transform="rotate(-90 60 60)"/>'
    '<circle id="darc-3" class="donut-arc" cx="60" cy="60" r="50" stroke-dasharray="0 314.16" stroke-dashoffset="0" stroke="#34a853" transform="rotate(-90 60 60)"/>'
    '</svg>'
    '<div class="donut-center"><div class="dc-val" id="d-center-val">0</div><div class="dc-lbl">Total</div></div>'
    '</div>'
    '<div class="legend">'
    '<div class="leg-item"><div class="leg-dot" style="background:#d93025"></div>Critical</div>'
    '<div class="leg-item"><div class="leg-dot" style="background:#e37400"></div>Alert</div>'
    '<div class="leg-item"><div class="leg-dot" style="background:#f09d00"></div>Watch</div>'
    '<div class="leg-item"><div class="leg-dot" style="background:#34a853"></div>Normal</div>'
    '</div></div>'
    # Risk bar chart
    '<div class="chart-panel">'
    '<div class="cp-title">Machine Risk Levels</div>'
    '<div id="risk-bars"><div style="color:#5f6368;font-size:.84rem">Loading...</div></div>'
    '</div></div>'
    # Main layout
    '<div class="layout">'
    # Alert inbox
    '<div class="panel">'
    '<div class="ph"><span class="ph-title"><span class="material-icons" style="font-size:1.1rem;color:#ea4335">inbox</span>Alert Inbox</span>'
    '<div class="ph-actions">'
    '<a href="/api/alerts/export.csv" class="tbtn" download><span class="material-icons" style="font-size:.9rem">download</span>CSV</a>'
    '<button class="tbtn" onclick="ackAll()"><span class="material-icons" style="font-size:.9rem">done_all</span>Ack All</button>'
    '</div></div>'
    '<div class="filters">'
    '<button class="fc active" onclick="setFilter(\'all\',this)">All</button>'
    '<button class="fc" onclick="setFilter(\'critical\',this)">Critical</button>'
    '<button class="fc" onclick="setFilter(\'alert\',this)">Alert</button>'
    '<button class="fc" onclick="setFilter(\'watch\',this)">Watch</button>'
    '<button class="fc" onclick="setFilter(\'unack\',this)">Unread</button>'
    '</div>'
    '<div class="tw"><table><thead><tr>'
    '<th>Level</th><th>Machine</th><th>Risk</th><th>Diagnosis</th><th>Time</th><th>Actions</th>'
    '</tr></thead><tbody id="alert-tbody"><tr class="empty"><td colspan="6">Loading...</td></tr></tbody></table></div>'
    '</div>'
    # Sidebar
    '<div>'
    '<div class="panel">'
    '<div class="ph"><span class="ph-title"><span class="material-icons" style="font-size:1.1rem;color:#1a73e8">precision_manufacturing</span>Machine Status</span></div>'
    '<div id="machine-list"></div></div>'
    '<div class="panel">'
    '<div class="ph"><span class="ph-title"><span class="material-icons" style="font-size:1.1rem;color:#188038">bolt</span>Quick Actions</span></div>'
    '<div style="padding:.75rem 1rem;">'
    '<button class="qbtn qg" onclick="ackAll()"><span class="material-icons" style="font-size:1.1rem">done_all</span>Acknowledge All Alerts</button>'
    '<button class="qbtn qa" onclick="scheduleAll()"><span class="material-icons" style="font-size:1.1rem">build</span>Schedule Critical Maintenance</button>'
    '<a href="/api/alerts/export.csv" download class="qbtn qb"><span class="material-icons" style="font-size:1.1rem">download</span>Export Alert Report (CSV)</a>'
    '<a href="/dashboard" class="qbtn qr"><span class="material-icons" style="font-size:1.1rem">monitor</span>Sensor Dashboard</a>'
    '</div></div></div></div></div>'
    '<div class="toast-wrap" id="toast-wrap"></div>'
    '<script>' + _MGR_JS + '</script>'
    '</body></html>'
)
