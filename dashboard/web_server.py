import asyncio
import csv
import io
import json
import time
from datetime import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import uvicorn
from config import WEB_HOST, WEB_PORT
from dashboard.manager_html import MANAGER_HTML
from dashboard.sensor_html import SENSOR_HTML
from dashboard.login_html import operator_login_page, manager_login_page
from dashboard.auth import login, logout, require_role

app = FastAPI(title="PRISM", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

global_state = {}
_COOKIE_OP  = "prism_token"
_COOKIE_MGR = "prism_mgr_token"


def _get_token(req: Request, cookie: str):
    return req.cookies.get(cookie)

def _clean_state():
    clean = {}
    for k, v in global_state.items():
        v_copy = dict(v) if isinstance(v, dict) else {}
        reading = v_copy.get("reading")
        if reading is not None:
            if hasattr(reading, "to_dict"):
                v_copy["reading"] = reading.to_dict()
            elif hasattr(reading, "__dict__"):
                v_copy["reading"] = reading.__dict__
            elif not isinstance(reading, dict):
                v_copy.pop("reading", None)
        clean[k] = v_copy
    return clean


@app.get("/", include_in_schema=False)
async def root(request: Request):
    if require_role(_get_token(request, _COOKIE_OP), "operator"):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "machines": list(global_state.keys()), "ts": time.time()})


# ── Operator Login ────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if require_role(_get_token(request, _COOKIE_OP), "operator"):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(operator_login_page())

@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    token = login(username, password)
    if not token:
        return HTMLResponse(operator_login_page("Invalid username or password."), status_code=401)
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(_COOKIE_OP, token, httponly=True, max_age=3600, samesite="lax")
    return resp

@app.get("/logout")
async def do_logout(request: Request):
    logout(_get_token(request, _COOKIE_OP))
    resp = RedirectResponse(url="/login")
    resp.delete_cookie(_COOKIE_OP)
    return resp


# ── Manager Login ─────────────────────────────────────────────────────────────

@app.get("/manager/login", response_class=HTMLResponse)
async def manager_login_page_route(request: Request):
    if require_role(_get_token(request, _COOKIE_MGR), "manager"):
        return RedirectResponse(url="/manager")
    return HTMLResponse(manager_login_page())

@app.post("/manager/login")
async def do_manager_login(request: Request, username: str = Form(...), password: str = Form(...)):
    token = login(username, password)
    if not token:
        return HTMLResponse(manager_login_page("Invalid username or password."), status_code=401)
    from dashboard.auth import get_session
    s = get_session(token)
    if not s or s["role"] != "manager":
        return HTMLResponse(manager_login_page("Access denied. Manager credentials required."), status_code=403)
    resp = RedirectResponse(url="/manager", status_code=303)
    resp.set_cookie(_COOKIE_MGR, token, httponly=True, max_age=3600, samesite="lax")
    return resp

@app.get("/manager/logout")
async def do_manager_logout(request: Request):
    logout(_get_token(request, _COOKIE_MGR))
    resp = RedirectResponse(url="/manager/login")
    resp.delete_cookie(_COOKIE_MGR)
    return resp


# ── Sensor Dashboard ──────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    s = require_role(_get_token(request, _COOKIE_OP), "operator")
    if not s:
        return RedirectResponse(url="/login")
    return HTMLResponse(SENSOR_HTML.replace("{{USER}}", s["user"]))

@app.get("/stream")
async def sse_stream(request: Request):
    if not require_role(_get_token(request, _COOKIE_OP), "operator"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async def gen():
        while True:
            yield f"data: {json.dumps(_clean_state())}\n\n"
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/state")
async def get_state(request: Request):
    # Accept either operator or manager session
    op_session = require_role(_get_token(request, _COOKIE_OP), "operator")
    mgr_session = require_role(_get_token(request, _COOKIE_MGR), "manager")
    if not op_session and not mgr_session:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return JSONResponse(_clean_state())


# ── Manager Dashboard ─────────────────────────────────────────────────────────

@app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(request: Request):
    s = require_role(_get_token(request, _COOKIE_MGR), "manager")
    if not s:
        return RedirectResponse(url="/manager/login")
    return HTMLResponse(MANAGER_HTML.replace("{{USER}}", s["user"]))

def _check_mgr(request: Request):
    return require_role(_get_token(request, _COOKIE_MGR), "manager")

@app.get("/api/alerts")
async def get_alerts(request: Request):
    if not _check_mgr(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import get_alerts as _ga
    return JSONResponse(_ga(200))

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: Request):
    s = _check_mgr(request)
    if not s:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import acknowledge
    return JSONResponse({"ok": acknowledge(alert_id, s["user"])})

@app.post("/api/alerts/{alert_id}/maintenance")
async def schedule_maintenance_alert(alert_id: str, request: Request):
    if not _check_mgr(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import schedule_maint
    return JSONResponse({"ok": schedule_maint(alert_id)})

@app.post("/api/alerts/ack-all")
async def ack_all_alerts(request: Request):
    s = _check_mgr(request)
    if not s:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import ack_all
    count = ack_all(s["user"])
    return JSONResponse({"ok": True, "count": count})

@app.post("/api/alerts/schedule-all-critical")
async def schedule_all_critical_route(request: Request):
    if not _check_mgr(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import schedule_all_critical
    count = schedule_all_critical()
    return JSONResponse({"ok": True, "count": count})

@app.get("/api/alerts/export.csv")
async def export_alerts_csv(request: Request):
    if not _check_mgr(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import get_alerts as _ga
    alerts = _ga(500)
    buf = io.StringIO()
    fields = ["id","timestamp","machine_id","risk_level","risk_score",
              "explanation","acknowledged","acknowledged_by","acknowledged_at","maintenance_scheduled"]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for a in alerts:
        row = {k: a.get(k, "") for k in fields}
        for tf in ["timestamp","acknowledged_at"]:
            if row[tf]:
                try:
                    row[tf] = datetime.fromtimestamp(float(row[tf])).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=prism_alerts.csv"})

@app.get("/api/alerts/unread-count")
async def unread_count_api(request: Request):
    op = require_role(_get_token(request, _COOKIE_OP), "operator")
    mgr = require_role(_get_token(request, _COOKIE_MGR), "manager")
    if not op and not mgr:
        return JSONResponse({"count": 0})
    from dashboard.alert_store import unread_count
    return JSONResponse({"count": unread_count()})

@app.get("/api/alerts/stats")
async def alert_stats_api(request: Request):
    if not _check_mgr(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from dashboard.alert_store import get_stats
    return JSONResponse(get_stats())


# ── Server ────────────────────────────────────────────────────────────────────

async def start_web_server(state: dict) -> None:
    global global_state
    global_state = state
    config = uvicorn.Config(app, host=WEB_HOST, port=WEB_PORT,
                            log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    await server.serve()


