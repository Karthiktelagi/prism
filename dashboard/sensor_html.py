"""Sensor Dashboard HTML with circular gauges."""

_SENSOR_CSS = '''
*{box-sizing:border-box;margin:0;padding:0;font-family:'Roboto',sans-serif;}
body{background:#f1f3f4;color:#202124;min-height:100vh;}
.topbar{background:#fff;border-bottom:1px solid #e0e0e0;height:64px;padding:0 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.1);}
.topbar-left{display:flex;align-items:center;gap:.75rem;}
.tlogo{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#4285f4,#34a853,#fbbc04,#ea4335);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1rem;color:#fff;}
.ttitle{font-size:1.25rem;font-weight:500;color:#202124;}.ttitle b{color:#1a73e8;}
.topbar-right{display:flex;align-items:center;gap:.75rem;}
.uchip{display:flex;align-items:center;gap:.4rem;background:#f1f3f4;border-radius:20px;padding:.35rem .85rem;font-size:.83rem;color:#3c4043;}
.livechip{display:flex;align-items:center;gap:.4rem;border-radius:20px;padding:.35rem .85rem;font-size:.82rem;background:#e6f4ea;color:#188038;border:1px solid #ceead6;}
.ldot{width:8px;height:8px;border-radius:50%;background:#34a853;animation:pd 1.5s ease infinite;}
.ldot.off{background:#ea4335;animation:none;}
@keyframes pd{0%,100%{opacity:1}50%{opacity:.4}}
.tbtn{background:transparent;border:1px solid #dadce0;border-radius:4px;padding:.4rem .9rem;font-size:.82rem;color:#1a73e8;cursor:pointer;font-family:inherit;text-decoration:none;transition:background .15s;display:inline-flex;align-items:center;gap:.3rem;}
.tbtn:hover{background:#e8f0fe;}
.mgrbtn{border-color:#ea4335;color:#d93025;}.mgrbtn:hover{background:#fce8e6;}
.mbadge{background:#ea4335;color:#fff;border-radius:10px;padding:.1rem .4rem;font-size:.68rem;font-weight:700;display:none;}
.signout{color:#5f6368;border-color:#dadce0;}.signout:hover{background:#f1f3f4;color:#3c4043;}
.main{padding:1.5rem;max-width:1500px;margin:0 auto;}
.srow{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem;}
.sc{flex:1;min-width:130px;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:1rem 1.2rem;}
.slabel{font-size:.73rem;font-weight:500;color:#5f6368;text-transform:uppercase;letter-spacing:.5px;margin-bottom:.25rem;}
.sval{font-size:2rem;font-weight:400;}
.sn .sval{color:#188038;}.sw .sval{color:#f09d00;}.sa .sval{color:#e37400;}.sk .sval{color:#d93025;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1.25rem;}
.mc{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);overflow:hidden;transition:box-shadow .2s;}
.mc:hover{box-shadow:0 2px 10px rgba(0,0,0,.15);}
.mind{height:4px;background:#34a853;transition:background .4s;}
.mc[data-level=watch] .mind{background:#fbbc04;}
.mc[data-level=alert] .mind{background:#fa7b17;}
.mc[data-level=critical] .mind{background:#ea4335;animation:cpa .8s ease-in-out infinite alternate;}
@keyframes cpa{from{opacity:.6}to{opacity:1}}
.mbody{padding:1rem 1.1rem;}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.75rem;}
.mid{font-size:1rem;font-weight:500;}.mst{font-size:.72rem;color:#5f6368;}
.lchip{display:inline-block;border-radius:12px;padding:.2rem .6rem;font-size:.7rem;font-weight:500;}
.cn{background:#e6f4ea;color:#188038;}.cw{background:#fef7e0;color:#f09d00;}
.ca{background:#fef0e0;color:#e37400;}.ck{background:#fce8e6;color:#d93025;}
/* circular gauge */
.gauge-section{display:flex;align-items:center;gap:1rem;margin-bottom:.85rem;}
.gauge-wrap{position:relative;width:100px;height:100px;flex-shrink:0;}
.gauge-wrap svg{width:100%;height:100%;}
.gauge-bg{fill:none;stroke:#f1f3f4;stroke-width:10;}
.gauge-arc{fill:none;stroke-width:10;stroke-linecap:round;transition:stroke-dasharray .6s ease,stroke .4s;transform-origin:center;transform:rotate(-90deg);}
.gauge-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.g-pct{font-size:1.2rem;font-weight:700;line-height:1;}
.g-lbl{font-size:.58rem;color:#80868b;text-transform:uppercase;letter-spacing:.5px;margin-top:1px;}
.gauge-meta{flex:1;}
.gm-label{font-size:.68rem;font-weight:500;color:#5f6368;text-transform:uppercase;letter-spacing:.5px;}
.gm-val{font-size:1.6rem;font-weight:300;color:#202124;line-height:1.2;}
.gm-sub{font-size:.72rem;color:#80868b;}
/* sensor tiles */
.stiles{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin-bottom:.8rem;}
.st{background:#f8f9fa;border-radius:6px;padding:.55rem .7rem;border:1px solid #f1f3f4;}
.st.ano{background:#fce8e6;border-color:#f28b82;}
.stn{font-size:.63rem;font-weight:500;color:#5f6368;text-transform:uppercase;letter-spacing:.4px;}
.stv{font-size:1.05rem;font-weight:300;color:#202124;}
.stu{font-size:.63rem;color:#80868b;margin-left:1px;}
.stag{display:inline-block;margin-top:.15rem;font-size:.6rem;font-weight:500;padding:.1rem .35rem;border-radius:8px;}
.spike{background:#fce8e6;color:#c5221f;}.drift{background:#fef7e0;color:#b06000;}.ok{background:#e6f4ea;color:#188038;}
.expl{background:#f8f9fa;border-radius:6px;padding:.6rem .75rem;font-size:.78rem;color:#5f6368;line-height:1.5;border-left:3px solid #1a73e8;}
.cfoot{display:flex;justify-content:space-between;margin-top:.65rem;font-size:.7rem;color:#80868b;}
'''

_SENSOR_JS = '''
const SC={normal:"#34a853",watch:"#f09d00",alert:"#e37400",critical:"#d93025"};
const CIRC=2*Math.PI*40;
setInterval(()=>{document.getElementById("clock").textContent=new Date().toLocaleTimeString("en-GB",{hour12:false});},1000);
function gc(s){if(s>=80)return SC.critical;if(s>=60)return SC.alert;if(s>=40)return SC.watch;return SC.normal;}
function tag(n,sp,dr){
  if(sp.includes(n))return'<span class="stag spike">SPIKE</span>';
  if(dr.includes(n))return'<span class="stag drift">DRIFT</span>';
  return'<span class="stag ok">OK</span>';
}
function renderCards(state){
  const cont=document.getElementById("cards");
  let ct={normal:0,watch:0,alert:0,critical:0};
  for(const [mid,data] of Object.entries(state)){
    const level=(data.risk_level||"normal").toLowerCase();
    const score=Number(data.risk_score||0);
    const r=data.reading||{};
    const sp=data.spike_sensors||[];
    const dr=data.drift_sensors||[];
    if(ct[level]!==undefined)ct[level]++;
    const temp=r.temperature_C!=null?Number(r.temperature_C).toFixed(1):"--";
    const vib=r.vibration_mm_s!=null?Number(r.vibration_mm_s).toFixed(2):"--";
    const rpm=r.rpm!=null?Math.round(r.rpm):"--";
    const curr=r.current_A!=null?Number(r.current_A).toFixed(1):"--";
    const ts=data.timestamp?new Date(data.timestamp*1000).toLocaleTimeString("en-GB"):"--";
    const col=gc(score);
    const dashFill=(score/100)*CIRC;
    const dashGap=CIRC-dashFill;
    let card=document.getElementById("c-"+mid);
    if(!card){
      card=document.createElement("div");
      card.className="mc";card.id="c-"+mid;
      card.innerHTML=`<div class="mind"></div><div class="mbody">
        <div class="card-top"><div><div class="mid">${mid}</div><div class="mst"></div></div><span class="lchip"></span></div>
        <div class="gauge-section">
          <div class="gauge-wrap">
            <svg viewBox="0 0 100 100">
              <circle class="gauge-bg" cx="50" cy="50" r="40"/>
              <circle class="gauge-arc" cx="50" cy="50" r="40" stroke-dasharray="0 251.2"/>
            </svg>
            <div class="gauge-center"><span class="g-pct">0</span><span class="g-lbl">Risk</span></div>
          </div>
          <div class="gauge-meta"><div class="gm-label">Risk Score</div><div class="gm-val">0</div><div class="gm-sub">out of 100</div></div>
        </div>
        <div class="stiles">
          <div class="st" id="t-${mid}-T"><div class="stn">Temperature</div><div class="stv">--<span class="stu">°C</span></div><span class="stag ok">OK</span></div>
          <div class="st" id="t-${mid}-V"><div class="stn">Vibration</div><div class="stv">--<span class="stu">mm/s</span></div><span class="stag ok">OK</span></div>
          <div class="st" id="t-${mid}-R"><div class="stn">Speed</div><div class="stv">--<span class="stu">RPM</span></div><span class="stag ok">OK</span></div>
          <div class="st" id="t-${mid}-C"><div class="stn">Current</div><div class="stv">--<span class="stu">A</span></div><span class="stag ok">OK</span></div>
        </div>
        <div class="expl">Awaiting analysis...</div>
        <div class="cfoot"><span>Alerts: 0</span><span></span></div>
      </div>`;
      cont.appendChild(card);
    }
    card.setAttribute("data-level",level);
    const b=card.querySelector(".mbody");
    b.querySelector(".mst").textContent=(r.status||"unknown").toUpperCase();
    const chip=b.querySelector(".lchip");
    chip.className="lchip c"+level.charAt(0);
    chip.textContent=level+" · "+score.toFixed(1);
    const arc=b.querySelector(".gauge-arc");
    arc.setAttribute("stroke-dasharray",dashFill+" "+dashGap);
    arc.setAttribute("stroke",col);
    b.querySelector(".g-pct").textContent=score.toFixed(0)+"%";
    b.querySelector(".g-pct").style.color=col;
    b.querySelector(".gm-val").textContent=score.toFixed(1);
    b.querySelector(".gm-val").style.color=col;
    // tiles
    function setTile(id,val,unit,key){
      const t=document.getElementById("t-"+mid+"-"+id);
      if(!t)return;
      t.className="st"+(sp.includes(key)||dr.includes(key)?" ano":"");
      t.querySelector(".stv").innerHTML=val+'<span class="stu">'+unit+'</span>';
      t.querySelector(".stag").outerHTML=tag(key,sp,dr);
    }
    setTile("T",temp,"°C","temperature_C");
    setTile("V",vib,"mm/s","vibration_mm_s");
    setTile("R",rpm,"RPM","rpm");
    setTile("C",curr,"A","current_A");
    b.querySelector(".expl").textContent=data.explanation||"Awaiting diagnostic analysis...";
    const foot=b.querySelectorAll(".cfoot span");
    foot[0].textContent="Alerts: "+(data.alerts_fired||0);
    foot[1].textContent="Updated: "+ts;
  }
  document.getElementById("cnt-n").textContent=ct.normal;
  document.getElementById("cnt-w").textContent=ct.watch;
  document.getElementById("cnt-a").textContent=ct.alert;
  document.getElementById("cnt-k").textContent=ct.critical;
}
async function pollUnread(){
  try{const r=await fetch("/api/alerts/unread-count");const d=await r.json();
  const b=document.getElementById("mgr-badge");
  if(d.count>0){b.style.display="inline-block";b.textContent=d.count;}else b.style.display="none";}catch(_){}
}
setInterval(pollUnread,5000);pollUnread();
const es=new EventSource("/stream");
es.onopen=()=>{document.getElementById("ldot").classList.remove("off");document.getElementById("ltxt").textContent="Live";};
es.onerror=()=>{document.getElementById("ldot").classList.add("off");document.getElementById("ltxt").textContent="Reconnecting...";};
es.onmessage=(e)=>{try{renderCards(JSON.parse(e.data));}catch(_){}};
'''

SENSOR_HTML = (
    '<!DOCTYPE html><html lang="en"><head>'
    '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
    '<title>PRISM &mdash; Live Dashboard</title>'
    '<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">'
    '<style>' + _SENSOR_CSS + '</style></head><body>'
    '<div class="topbar">'
    '<div class="topbar-left"><div class="tlogo">P</div>'
    '<span class="ttitle">PRISM <b>Monitor</b></span></div>'
    '<div class="topbar-right">'
    '<span class="uchip"><span class="material-icons" style="font-size:1rem;color:#5f6368">account_circle</span>{{USER}}</span>'
    '<a href="/manager/login" class="tbtn mgrbtn" id="mgr-btn">'
    '<span class="material-icons" style="font-size:.95rem">notifications</span>Manager'
    '<span class="mbadge" id="mgr-badge">0</span></a>'
    '<div class="livechip"><span class="ldot" id="ldot"></span><span id="ltxt">Connecting...</span></div>'
    '<span style="font-size:.8rem;color:#5f6368" id="clock"></span>'
    '<a href="/logout" class="tbtn signout"><span class="material-icons" style="font-size:.95rem">logout</span>Sign out</a>'
    '</div></div>'
    '<div class="main">'
    '<div class="srow">'
    '<div class="sc sn"><div class="slabel">Normal</div><div class="sval" id="cnt-n">0</div></div>'
    '<div class="sc sw"><div class="slabel">Watch</div><div class="sval" id="cnt-w">0</div></div>'
    '<div class="sc sa"><div class="slabel">Alert</div><div class="sval" id="cnt-a">0</div></div>'
    '<div class="sc sk"><div class="slabel">Critical</div><div class="sval" id="cnt-k">0</div></div>'
    '</div>'
    '<div class="grid" id="cards"></div>'
    '</div>'
    '<script>' + _SENSOR_JS + '</script>'
    '</body></html>'
)
