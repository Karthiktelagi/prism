"""Live API diagnostic — runs against the running server."""
import urllib.request
import urllib.parse
import json
import http.cookiejar

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# 1. Login as manager
data = urllib.parse.urlencode({"username": "manager", "password": "manager@123"}).encode()
req = urllib.request.Request("http://localhost:7860/manager/login", data=data,
                              headers={"Content-Type": "application/x-www-form-urlencoded"})
try:
    r = opener.open(req)
    print("Login status:", r.status)
except Exception as e:
    print("Login result:", e.code if hasattr(e, 'code') else e)

cookies = {c.name: c.value for c in jar}
print("Cookies set:", list(cookies.keys()))

# 2. Hit /api/alerts
try:
    r2 = opener.open("http://localhost:7860/api/alerts")
    body = r2.read().decode()
    data2 = json.loads(body)
    print("GET /api/alerts status:", r2.status, "| count:", len(data2))
    if data2:
        print("First alert:", data2[0]["machine_id"], data2[0]["risk_level"], data2[0]["risk_score"])
    else:
        print("-> EMPTY ARRAY returned")
except Exception as e:
    print("GET /api/alerts error:", e.code if hasattr(e, 'code') else e)
    try:
        print("Response body:", e.read().decode())
    except Exception:
        pass

# 3. Hit /api/state
try:
    r3 = opener.open("http://localhost:7860/api/state")
    body3 = json.loads(r3.read().decode())
    print("GET /api/state status:", r3.status, "| machines:", list(body3.keys()))
except Exception as e:
    print("GET /api/state error:", e.code if hasattr(e, 'code') else e)

# 4. Check DB directly
from dashboard.alert_store import get_alerts, get_stats
stats = get_stats()
print("DB stats:", stats)
alerts = get_alerts(3)
print("DB alerts (first 3):", [(a["machine_id"], a["risk_level"]) for a in alerts])
