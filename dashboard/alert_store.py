"""
dashboard/alert_store.py — Persistent 7-day SQLite alert store.
All alerts are written to alerts.db in the project root.
Alerts older than 7 days are automatically pruned on startup and hourly.
"""
from __future__ import annotations
import asyncio
import sqlite3
import time
import uuid
import json
import os
import threading
from typing import List, Dict, Any

# ── DB path ───────────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "alerts.db")
_SEVEN_DAYS = 7 * 24 * 3600
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                machine_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                explanation TEXT,
                reading TEXT,
                timestamp REAL NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at REAL,
                maintenance_scheduled INTEGER DEFAULT 0
            )
        """)
        conn.commit()


def _prune_old():
    """Remove alerts older than 7 days."""
    cutoff = time.time() - _SEVEN_DAYS
    with _lock:
        with _get_conn() as conn:
            deleted = conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff,)).rowcount
            conn.commit()
    if deleted:
        import logging
        logging.getLogger(__name__).info(f"[alert_store] Pruned {deleted} alerts older than 7 days.")


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    d["acknowledged"] = bool(d["acknowledged"])
    d["maintenance_scheduled"] = bool(d["maintenance_scheduled"])
    try:
        d["reading"] = json.loads(d["reading"]) if d["reading"] else {}
    except Exception:
        d["reading"] = {}
    return d


# ── Public API ────────────────────────────────────────────────────────────────

def push_alert(machine_id: str, risk_score: float, risk_level: str,
               explanation: str, reading: dict) -> str:
    alert_id = str(uuid.uuid4())[:8]
    with _lock:
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO alerts
                   (id, machine_id, risk_score, risk_level, explanation, reading, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (alert_id, machine_id, risk_score, risk_level, explanation,
                 json.dumps(reading), time.time())
            )
            conn.commit()
    return alert_id


def get_alerts(limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def acknowledge(alert_id: str, manager: str = "Manager") -> bool:
    with _lock:
        with _get_conn() as conn:
            n = conn.execute(
                "UPDATE alerts SET acknowledged=1, acknowledged_by=?, acknowledged_at=? WHERE id=?",
                (manager, time.time(), alert_id)
            ).rowcount
            conn.commit()
    return n > 0


def schedule_maint(alert_id: str) -> bool:
    with _lock:
        with _get_conn() as conn:
            n = conn.execute(
                "UPDATE alerts SET maintenance_scheduled=1 WHERE id=?", (alert_id,)
            ).rowcount
            conn.commit()
    return n > 0


def unread_count() -> int:
    with _lock:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE acknowledged=0"
            ).fetchone()
    return row[0] if row else 0


def ack_all(manager: str = "Manager") -> int:
    now = time.time()
    with _lock:
        with _get_conn() as conn:
            n = conn.execute(
                "UPDATE alerts SET acknowledged=1, acknowledged_by=?, acknowledged_at=? WHERE acknowledged=0",
                (manager, now)
            ).rowcount
            conn.commit()
    return n


def schedule_all_critical() -> int:
    with _lock:
        with _get_conn() as conn:
            n = conn.execute(
                "UPDATE alerts SET maintenance_scheduled=1 WHERE risk_level='critical' AND maintenance_scheduled=0"
            ).rowcount
            conn.commit()
    return n


def get_stats() -> Dict[str, int]:
    with _lock:
        with _get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            unack = conn.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged=0").fetchone()[0]
            crit  = conn.execute("SELECT COUNT(*) FROM alerts WHERE risk_level='critical'").fetchone()[0]
            maint = conn.execute("SELECT COUNT(*) FROM alerts WHERE maintenance_scheduled=1").fetchone()[0]
    return {"total": total, "unack": unack, "critical": crit, "maintenance": maint}


# ── Background pruner ─────────────────────────────────────────────────────────

def _start_pruner():
    """Run pruning every hour in a daemon thread."""
    def _loop():
        while True:
            time.sleep(3600)
            try:
                _prune_old()
            except Exception:
                pass
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


# ── Init on import ────────────────────────────────────────────────────────────
_init_db()
_prune_old()
_start_pruner()

# Backward compat: expose _alerts as a live view proxy
class _AlertsProxy:
    """Backward-compatible list-like access to the SQLite store."""
    def __iter__(self):
        return iter(get_alerts(500))
    def __len__(self):
        return unread_count() + 1  # approximate

_alerts = _AlertsProxy()
