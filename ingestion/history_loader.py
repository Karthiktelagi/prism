"""
ingestion/history_loader.py
============================
Loads 7-day sensor history by executing generate-history.js directly via
Node.js as a subprocess.  No HTTP server is required — the JS file is the
single source of truth.

Workflow
--------
1. Locate  malendau-hackathon/generate-history.js  relative to this file.
2. Run:  node generate-history.js <machine_id>
3. Parse the JSON written to stdout.
4. Map each record to a SensorReading dataclass.
5. Cache results in-process so repeated calls for the same machine_id
   don't re-execute Node.

Usage
-----
    from ingestion.history_loader import fetch_history
    import aiohttp

    async with aiohttp.ClientSession() as session:
        readings = await fetch_history("CNC_01", session)

(session is accepted for API-compatibility but is not used here.)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from typing import Dict, List, Optional

from config import SensorReading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_JS_FILE   = os.path.join(_REPO_ROOT, "malendau-hackathon", "generate-history.js")

# In-process cache: machine_id → list[SensorReading]
_CACHE: Dict[str, List[SensorReading]] = {}


def _find_node() -> str:
    """Return the path to the Node.js executable, or raise RuntimeError."""
    node = shutil.which("node") or shutil.which("node.exe")
    if node is None:
        raise RuntimeError(
            "Node.js is not found on PATH.  Install Node.js and make sure "
            "'node' is accessible from the terminal."
        )
    return node


def _run_js(machine_id: str) -> List[SensorReading]:
    """
    Execute  node generate-history.js <machine_id>  synchronously and parse
    the JSON output into SensorReading objects.
    """
    if not os.path.isfile(_JS_FILE):
        raise FileNotFoundError(
            f"generate-history.js not found at: {_JS_FILE}\n"
            "Make sure the malendau-hackathon folder is present inside the "
            "prism workspace."
        )

    node = _find_node()
    logger.info("Loading history for %s from %s …", machine_id, _JS_FILE)

    try:
        result = subprocess.run(
            [node, _JS_FILE, machine_id],
            capture_output=True,
            text=True,
            timeout=60,          # generous: ~10 080 rows × 4 machines
            cwd=os.path.dirname(_JS_FILE),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"node generate-history.js timed out for machine {machine_id}"
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"generate-history.js exited with code {result.returncode}: {stderr}"
        )

    if not result.stdout.strip():
        raise RuntimeError(
            f"generate-history.js produced no output for machine {machine_id}"
        )

    # --- Parse JSON ---------------------------------------------------------
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse JSON from generate-history.js: {exc}"
        ) from exc

    # Data shape: { machine_id, count, readings: [...] }  or bare list
    raw_readings: list = (
        data if isinstance(data, list) else data.get("readings", [])
    )

    readings: List[SensorReading] = []
    for r in raw_readings:
        if not isinstance(r, dict):
            continue

        # Parse ISO-8601 timestamp → Unix epoch float
        ts_raw = r.get("timestamp", 0)
        if isinstance(ts_raw, str) and "T" in ts_raw:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                timestamp = dt.timestamp()
            except Exception:
                timestamp = time.time()
        else:
            try:
                timestamp = float(ts_raw)
            except (ValueError, TypeError):
                timestamp = time.time()

        try:
            readings.append(SensorReading(
                machine_id     = str(r.get("machine_id", machine_id)),
                timestamp      = timestamp,
                temperature_C  = float(r.get("temperature_C",  0.0)),
                vibration_mm_s = float(r.get("vibration_mm_s", 0.0)),
                rpm            = float(r.get("rpm",            0.0)),
                current_A      = float(r.get("current_A",      0.0)),
                status         = str(r.get("status",           "running")),
            ))
        except Exception as parse_err:
            logger.debug("Skipping malformed history record: %s", parse_err)

    logger.info(
        "Loaded %d historical readings for %s from generate-history.js",
        len(readings), machine_id,
    )
    return readings


# ---------------------------------------------------------------------------
# Public async API (drop-in replacement for the old HTTP-based loader)
# ---------------------------------------------------------------------------

async def fetch_history(
    machine_id: str,
    session=None,          # kept for API compatibility; not used
) -> List[SensorReading]:
    """
    Return the 7-day sensor history for *machine_id* by running
    generate-history.js via Node.js.

    Results are cached for the lifetime of the process so that multiple
    agent loops calling this function don't re-execute Node.

    Parameters
    ----------
    machine_id : str
        One of CNC_01, CNC_02, PUMP_03, CONVEYOR_04.
    session :
        Ignored.  Kept so existing call-sites don't need changes.
    """
    if machine_id in _CACHE:
        logger.debug("Returning cached history for %s (%d rows)", machine_id, len(_CACHE[machine_id]))
        return _CACHE[machine_id]

    # Offload the blocking subprocess call to a thread so we don't block
    # the asyncio event loop.
    loop = asyncio.get_event_loop()
    try:
        readings = await loop.run_in_executor(None, _run_js, machine_id)
    except Exception as exc:
        logger.error("Failed to load history for %s: %s", machine_id, exc)
        return []

    _CACHE[machine_id] = readings
    return readings


def clear_cache(machine_id: Optional[str] = None) -> None:
    """
    Evict one or all machines from the in-process cache.
    Call this if you need freshly generated data mid-session.
    """
    if machine_id:
        _CACHE.pop(machine_id, None)
    else:
        _CACHE.clear()
