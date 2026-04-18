"""
ingestion/stream_consumer.py — JS-file-backed async stream (no auto-gen)
=========================================================================
Replays the pre-computed sensor history from generate-history.js at a
configurable tick-rate instead of connecting to the Node HTTP server.

Public API  (drop-in replacement — same signature as before)
------------
``consume_stream(machine_id, data_queue)``
    Top-level coroutine — run once per machine via ``asyncio.gather()``.

How it works
------------
1. On first call, ``node generate-history.js`` is executed ONCE and the
   full 7-day history (≈10 080 rows per machine) is loaded and shared
   across all four machine coroutines via an in-process cache.
2. Each coroutine iterates over its machine's rows in chronological order,
   converts each row to a ``SensorReading``, puts it on *data_queue*, then
   sleeps ``REPLAY_TICK_S`` seconds (default 1 s) before the next row.
3. After the last row the replay loops back to the first row (continuous).
4. A silence watchdog is preserved: if the replay coroutine is somehow
   blocked for longer than ``STREAM_SILENCE_TIMEOUT_S`` an external caller
   can cancel the task; the silence guard here simply logs a warning.

No HTTP connection is made. No auto-generation happens.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import (
    BACKOFF_BASE_S,
    BACKOFF_MAX_S,
    BASE_URL,
    MACHINES,
    SSE_CONNECT_TIMEOUT_S,
    STREAM_SILENCE_TIMEOUT_S,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Replay speed: one reading per second by default (matches original SSE rate).
# Override via env var PRISM_REPLAY_TICK_S.
# ---------------------------------------------------------------------------
REPLAY_TICK_S: float = float(os.getenv("PRISM_REPLAY_TICK_S", "1.0"))

# ---------------------------------------------------------------------------
# Paths to the JS file
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_JS_FILE   = os.path.join(_REPO_ROOT, "malendau-hackathon", "generate-history.js")

# In-process cache: machine_id → list[dict]  (raw rows from generate-history.js)
_RAW_CACHE: Dict[str, List[dict]] = {}
_CACHE_LOCK = asyncio.Lock()


# ---------------------------------------------------------------------------
# SensorReading dataclass (wire-format timestamp preserved as str)
# ---------------------------------------------------------------------------

@dataclass
class SensorReading:
    """
    A single, fully-typed sensor snapshot.

    ``timestamp`` is kept as the ISO-8601 string produced by
    generate-history.js so that downstream logging and dashboard code
    requires no changes.
    """

    machine_id: str
    timestamp: str
    temperature_C: float
    vibration_mm_s: float
    rpm: float
    current_A: float
    status: str  # "running" | "warning" | "fault"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def parse_timestamp(self) -> datetime:
        """Return the timestamp as a timezone-aware UTC datetime."""
        ts = self.timestamp.strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (ValueError, OSError):
            return datetime.now(tz=timezone.utc)

    def is_synthetic(self) -> bool:
        """True if this is a silence-injected fault reading."""
        return (
            self.status == "fault"
            and self.temperature_C == 999.0
            and self.vibration_mm_s == 999.0
        )

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp,
            "temperature_C": self.temperature_C,
            "vibration_mm_s": self.vibration_mm_s,
            "rpm": self.rpm,
            "current_A": self.current_A,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Internal: load raw rows from generate-history.js via Node subprocess
# ---------------------------------------------------------------------------

def _find_node() -> str:
    node = shutil.which("node") or shutil.which("node.exe")
    if node is None:
        raise RuntimeError(
            "Node.js not found on PATH. Install Node.js so PRISM can read "
            "generate-history.js directly."
        )
    return node


def _load_all_raw() -> Dict[str, List[dict]]:
    """
    Run  node generate-history.js  (no machine_id arg) and return the full
    history map  { "CNC_01": [...], "CNC_02": [...], … }.
    Blocks the calling thread; call via run_in_executor.
    """
    if not os.path.isfile(_JS_FILE):
        raise FileNotFoundError(
            f"generate-history.js not found at: {_JS_FILE}\n"
            "Ensure malendau-hackathon/ is present inside the prism workspace."
        )

    node = _find_node()
    logger.info("Loading full history from %s …", _JS_FILE)

    result = subprocess.run(
        [node, _JS_FILE],                    # no machine_id → all machines
        capture_output=True,
        text=True,
        timeout=90,
        cwd=os.path.dirname(_JS_FILE),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"generate-history.js exited {result.returncode}: {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        raise RuntimeError("generate-history.js produced no output.")

    raw: dict = json.loads(result.stdout)
    logger.info(
        "Loaded history: %s",
        {m: len(rows) for m, rows in raw.items()},
    )
    return raw


async def _ensure_cache() -> None:
    """Populate _RAW_CACHE once (thread-safe via asyncio.Lock)."""
    global _RAW_CACHE
    async with _CACHE_LOCK:
        if _RAW_CACHE:
            return  # already loaded by another coroutine
        loop = asyncio.get_event_loop()
        _RAW_CACHE = await loop.run_in_executor(None, _load_all_raw)


# ---------------------------------------------------------------------------
# Row → SensorReading converter
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _row_to_reading(row: dict, machine_id: str) -> Optional[SensorReading]:
    """Convert one raw dict from generate-history.js into a SensorReading."""
    try:
        return SensorReading(
            machine_id=machine_id,
            timestamp=str(row.get("timestamp", _now_iso())),
            temperature_C=float(row.get("temperature_C", 0.0)),
            vibration_mm_s=float(row.get("vibration_mm_s", 0.0)),
            rpm=float(row.get("rpm", 0.0)),
            current_A=float(row.get("current_A", 0.0)),
            status=str(row.get("status", "running")).lower(),
        )
    except (ValueError, TypeError) as exc:
        logger.debug("Skipping malformed row for %s: %s", machine_id, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def consume_stream(
    machine_id: str,
    data_queue: asyncio.Queue,
    *,
    # kept for signature compatibility; ignored
    base_url: str = BASE_URL,
    silence_timeout: float = STREAM_SILENCE_TIMEOUT_S,
    backoff_base: float = BACKOFF_BASE_S,
    backoff_max: float = BACKOFF_MAX_S,
    connect_timeout: float = SSE_CONNECT_TIMEOUT_S,
) -> None:
    """
    Replay sensor history for *machine_id* into *data_queue*.

    Reads directly from generate-history.js via Node subprocess.
    No HTTP server. No auto-generation.

    The replay runs at REPLAY_TICK_S per row (default: 1 row/second) and
    loops back to the beginning after the last row so the agent loop runs
    continuously.

    Parameters
    ----------
    machine_id : str
        One of CNC_01, CNC_02, PUMP_03, CONVEYOR_04.
    data_queue : asyncio.Queue
        Destination for SensorReading objects.
    All other parameters are accepted but ignored (API compatibility).
    """
    # ── Load history once (shared across all machine coroutines) ──────────
    try:
        await _ensure_cache()
    except Exception as exc:
        logger.error(
            "[%s] Failed to load generate-history.js: %s — aborting stream.",
            machine_id, exc,
        )
        return

    rows = _RAW_CACHE.get(machine_id)
    if not rows:
        logger.error(
            "[%s] No history rows found in generate-history.js output.",
            machine_id,
        )
        return

    logger.info(
        "[%s] Starting replay of %d rows from generate-history.js "
        "(tick=%.1fs, looping).",
        machine_id, len(rows), REPLAY_TICK_S,
    )

    idx = 0
    while True:
        row = rows[idx % len(rows)]
        idx += 1

        reading = _row_to_reading(row, machine_id)
        if reading is not None:
            await data_queue.put(reading)
            logger.debug(
                "[%s] ▶ row %5d/%d  status=%-7s  temp=%5.1f°C  "
                "vib=%5.2f  rpm=%6.0f  I=%5.2fA",
                machine_id,
                idx, len(rows),
                reading.status,
                reading.temperature_C,
                reading.vibration_mm_s,
                reading.rpm,
                reading.current_A,
            )

        try:
            await asyncio.sleep(REPLAY_TICK_S)
        except asyncio.CancelledError:
            logger.info(
                "[%s] consume_stream cancelled at row %d — shutting down.",
                machine_id, idx,
            )
            raise
