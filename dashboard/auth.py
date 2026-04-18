"""
dashboard/auth.py — Session-based authentication with SQLite persistence.
Sessions survive server restarts and expire after SESSION_TTL seconds.
"""
from __future__ import annotations
import time
import uuid
import sqlite3
import os
import threading
from typing import Dict, Optional

# ── Credentials ───────────────────────────────────────────────────────────────
USERS: Dict[str, tuple] = {
    "operator":  ("prism2024",   "operator"),
    "manager":   ("manager@123", "manager"),
    "admin":     ("admin@prism", "manager"),
}

SESSION_TTL = 3600 * 8  # 8 hours

# ── SQLite session store ──────────────────────────────────────────────────────
_DB = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.db")
_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(_DB), exist_ok=True)
    c = sqlite3.connect(_DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at REAL NOT NULL
        )""")
        # Clean expired sessions on startup
        c.execute("DELETE FROM sessions WHERE created_at < ?", (time.time() - SESSION_TTL,))
        c.commit()


def login(username: str, password: str) -> Optional[str]:
    entry = USERS.get(username)
    if not entry or entry[0] != password:
        return None
    token = str(uuid.uuid4())
    with _lock:
        with _conn() as c:
            c.execute("INSERT OR REPLACE INTO sessions (token,user,role,created_at) VALUES (?,?,?,?)",
                      (token, username, entry[1], time.time()))
            c.commit()
    return token


def get_session(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    with _lock:
        with _conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    if time.time() - row["created_at"] > SESSION_TTL:
        logout(token)
        return None
    return {"user": row["user"], "role": row["role"], "created_at": row["created_at"]}


def logout(token: Optional[str]) -> None:
    if not token:
        return
    with _lock:
        with _conn() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))
            c.commit()


def require_role(token: Optional[str], role: str) -> Optional[dict]:
    s = get_session(token)
    if not s:
        return None
    if role == "operator":
        return s  # all authenticated users can see operator dashboard
    if role == "manager":
        return s if s["role"] == "manager" else None
    return None


_init()
