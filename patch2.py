"""Patch manager_html.py to add auto-redirect on 401 in fetchAlerts."""
with open('dashboard/manager_html.py', 'r', encoding='utf-8') as f:
    content = f.read()

old1 = 'async function fetchAlerts(){\n  try{\n    const r=await fetch("/api/alerts");\n    if(!r.ok){return;}'
new1 = 'async function fetchAlerts(){\n  try{\n    const r=await fetch("/api/alerts");\n    if(r.status===401||r.status===403){window.location.href="/manager/login";return;}\n    if(!r.ok){document.getElementById("alert-tbody").innerHTML="<tr class=\\"empty\\"><td colspan=\\"6\\">Session expired. <a href=\\"/manager/login\\">Click to re-login</a></td></tr>";return;}'

old2 = 'async function fetchState(){\n  try{\n    const r=await fetch("/api/state");\n    if(!r.ok){return;}'
new2 = 'async function fetchState(){\n  try{\n    const r=await fetch("/api/state");\n    if(r.status===401||r.status===403){return;}\n    if(!r.ok){return;}'

changed = content.replace(old1, new1).replace(old2, new2)

if changed == content:
    print("No change - searching for existing pattern...")
    # Print snippet around fetchAlerts
    idx = content.find("fetchAlerts")
    print(repr(content[idx:idx+200]))
else:
    with open('dashboard/manager_html.py', 'w', encoding='utf-8') as f:
        f.write(changed)
    print("Patched OK")

from dashboard.manager_html import MANAGER_HTML
print("Import OK, len:", len(MANAGER_HTML))
