"""Login page HTML — Google Material Design 3 theme."""


def _make_login(role: str, error: str = "") -> str:
    is_mgr = (role == "manager")
    if is_mgr:
        primary       = "#d93025"
        primary_light = "#fce8e6"
        icon_bg       = "#d93025"
        btn_bg        = "#d93025"
        btn_hover     = "#c5221f"
        role_label    = "Manager Portal"
        icon_letter   = "M"
        action        = "/manager/login"
        alt_href      = "/login"
        alt_text      = "Operator Sign in"
        hint_user     = "manager  or  admin"
        hint_pass     = "manager@123  or  admin@prism"
        chip_color    = "#d93025"
        chip_bg       = "#fce8e6"
    else:
        primary       = "#1a73e8"
        primary_light = "#e8f0fe"
        icon_bg       = "#1a73e8"
        btn_bg        = "#1a73e8"
        btn_hover     = "#1558b0"
        role_label    = "Operator Sign in"
        icon_letter   = "P"
        action        = "/login"
        alt_href      = "/manager/login"
        alt_text      = "Manager Portal"
        hint_user     = "operator"
        hint_pass     = "prism2024"
        chip_color    = "#1a73e8"
        chip_bg       = "#e8f0fe"

    err_block = "block" if error else "none"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>PRISM &mdash; {role_label}</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Google+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'Roboto',sans-serif;}}
body{{min-height:100vh;background:#f1f3f4;display:flex;flex-direction:column;align-items:center;justify-content:center;}}
.topbar{{width:100%;background:#fff;border-bottom:1px solid #e0e0e0;padding:.75rem 2rem;display:flex;align-items:center;gap:.6rem;position:fixed;top:0;left:0;box-shadow:0 1px 3px rgba(0,0,0,.08);}}
.topbar-logo{{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#4285f4,#34a853,#fbbc04,#ea4335);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;color:#fff;}}
.topbar-name{{font-size:1.1rem;font-weight:500;color:#202124;letter-spacing:-.3px;}}
.topbar-name span{{color:{primary};}}
.card{{background:#fff;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.12),0 4px 20px rgba(0,0,0,.06);padding:2.5rem 2.5rem 2rem;width:100%;max-width:400px;margin-top:64px;}}
.card-header{{text-align:center;margin-bottom:1.75rem;}}
.logo-circle{{width:56px;height:56px;border-radius:50%;background:{icon_bg};display:flex;align-items:center;justify-content:center;font-size:1.5rem;font-weight:700;color:#fff;margin:0 auto .85rem;box-shadow:0 2px 8px rgba(0,0,0,.2);}}
.card-header h1{{font-size:1.5rem;font-weight:400;color:#202124;margin-bottom:.3rem;}}
.card-header p{{font-size:.85rem;color:#5f6368;}}
.role-chip{{display:inline-block;background:{chip_bg};color:{chip_color};border-radius:16px;padding:.25rem .85rem;font-size:.75rem;font-weight:500;margin-top:.6rem;}}
.error-box{{background:#fce8e6;border:1px solid #f28b82;border-radius:4px;padding:.7rem .85rem;font-size:.84rem;color:#c5221f;margin-bottom:1.2rem;display:{err_block};display:flex;align-items:center;gap:.5rem;}}
.field{{margin-bottom:1.1rem;}}
label{{display:block;font-size:.78rem;font-weight:500;color:#3c4043;margin-bottom:.45rem;}}
input{{width:100%;background:#fff;border:1px solid #dadce0;border-radius:4px;padding:.7rem .9rem;color:#202124;font-size:.9rem;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s;}}
input:hover{{border-color:#bdc1c6;}}
input:focus{{border-color:{primary};border-width:2px;box-shadow:0 0 0 0 transparent;padding:.65rem .85rem;}}
.btn-row{{display:flex;justify-content:space-between;align-items:center;margin-top:1.5rem;}}
.alt-link{{font-size:.85rem;color:{primary};text-decoration:none;font-weight:500;transition:text-decoration .1s;}}
.alt-link:hover{{text-decoration:underline;}}
.submit-btn{{background:{btn_bg};color:#fff;border:none;border-radius:4px;padding:.65rem 1.5rem;font-size:.9rem;font-weight:500;font-family:inherit;cursor:pointer;transition:background .2s,box-shadow .2s;letter-spacing:.25px;}}
.submit-btn:hover{{background:{btn_hover};box-shadow:0 1px 4px rgba(0,0,0,.25);}}
.submit-btn:active{{box-shadow:none;}}
.divider{{border:none;border-top:1px solid #e0e0e0;margin:1.4rem 0;}}
.hint-box{{background:#f8f9fa;border-radius:4px;padding:.7rem .85rem;font-size:.78rem;color:#5f6368;line-height:1.7;}}
.hint-box strong{{color:#3c4043;font-weight:500;}}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-logo">P</div>
  <span class="topbar-name">PRISM<span> Monitor</span></span>
</div>
<div class="card">
  <div class="card-header">
    <div class="logo-circle">{icon_letter}</div>
    <h1>Sign in to PRISM</h1>
    <p>Predictive Risk Intelligence &amp; Sensor Monitor</p>
    <div class="role-chip">{role_label}</div>
  </div>
  <div class="error-box" id="err"><span>&#9888;</span> {error}</div>
  <form method="POST" action="{action}">
    <div class="field">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" placeholder="Enter your username" required autocomplete="username">
    </div>
    <div class="field">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" placeholder="Enter your password" required autocomplete="current-password">
    </div>
    <div class="btn-row">
      <a href="{alt_href}" class="alt-link">{alt_text}</a>
      <button type="submit" class="submit-btn">Sign in</button>
    </div>
  </form>
  <hr class="divider">
  <div class="hint-box">
    <strong>Demo credentials</strong><br>
    Username: <strong>{hint_user}</strong><br>
    Password: <strong>{hint_pass}</strong>
  </div>
</div>
</body>
</html>"""


def operator_login_page(error: str = "") -> str:
    return _make_login("operator", error)


def manager_login_page(error: str = "") -> str:
    return _make_login("manager", error)
