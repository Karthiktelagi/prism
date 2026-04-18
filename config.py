"""
config.py — PRISM Central Configuration
========================================
All deployment-tunable constants live here.  Import this module everywhere;
never hard-code values in business logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Machine registry
# ---------------------------------------------------------------------------
MACHINE_IDS = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]
MACHINES = MACHINE_IDS

BASELINES = {
    "CNC_01":      {"temp": 72,  "vib": 1.8, "rpm": 1480, "current": 12.5},
    "CNC_02":      {"temp": 68,  "vib": 1.5, "rpm": 1490, "current": 11.8},
    "PUMP_03":     {"temp": 55,  "vib": 2.2, "rpm": 2950, "current": 18.0},
    "CONVEYOR_04": {"temp": 45,  "vib": 0.9, "rpm": 720,  "current": 8.5},
}

SENSOR_FIELDS: List[str] = [
    "temperature_C",
    "vibration_mm_s",
    "rpm",
    "current_A",
    "status",
]

# ---------------------------------------------------------------------------
# SSE / streaming
# ---------------------------------------------------------------------------
SSE_BASE_URL: str = os.getenv(
    "PRISM_SSE_BASE_URL",
    "http://localhost:3000",          # override via env in production
)

# Convenience alias used by ingestion/*.py  (endpoint paths appended by each module)
BASE_URL = "http://localhost:3000"

# History API
HISTORY_MAX_RETRIES: int = 3          # max fetch attempts before giving up
HISTORY_RETRY_BACKOFF_S: float = 2.0  # base delay between history retries
HISTORY_TIMEOUT_S: float = 30.0       # per-attempt HTTP timeout

SSE_CONNECT_TIMEOUT_S: float = 10.0
SSE_READ_TIMEOUT_S: float = 30.0

# Exponential back-off for SSE reconnect
BACKOFF_BASE_S: float = 1.0
BACKOFF_MAX_S: float = 30.0
BACKOFF_SEQUENCE = [1, 2, 4, 8, 30]

# Seconds of silence before a fault-level risk event is raised
STREAM_SILENCE_TIMEOUT = 10
STREAM_SILENCE_TIMEOUT_S: float = 10.0

# ---------------------------------------------------------------------------
# Baseline / anomaly detection
# ---------------------------------------------------------------------------
BASELINE_WINDOW: int = 60          # number of readings used to compute μ / σ
BASELINE_MIN_SAMPLES: int = 10     # minimum readings before baseline is trusted
Z_SCORE_THRESHOLD: float = 3.0     # |z| > this → anomalous reading

# Noise filter: raise anomaly only if ≥ ANOMALY_CONFIRM_K of last
# ANOMALY_CONFIRM_N readings are anomalous
ANOMALY_CONFIRM_N: int = 3
ANOMALY_CONFIRM_K: int = 2

# ---------------------------------------------------------------------------
# Risk scoring  (rule 6)
# risk = min(100, spike_score + drift_score + compound_bonus + status_bonus)
# ---------------------------------------------------------------------------
SPIKE_SCORE_MAX: float = 40.0      # contribution cap from z-score spike
DRIFT_SCORE_MAX: float = 30.0      # contribution cap from rolling mean drift
COMPOUND_BONUS: float = 15.0       # added when ≥2 sensors anomalous simultaneously
STATUS_BONUS: float = 15.0         # added when status field indicates fault

RISK_THRESHOLDS = {
    "normal": 40,
    "watch": 60,
    "alert": 79,
    "critical": 80
}

RISK_CRITICAL: float = 80.0        # threshold → CRITICAL
RISK_HIGH: float = 60.0            # threshold → HIGH
RISK_MEDIUM: float = 40.0          # threshold → MEDIUM
RISK_LOW: float = 20.0             # threshold → LOW

# ---------------------------------------------------------------------------
# Alert / action
# ---------------------------------------------------------------------------
ALERT_API_URL: str = os.getenv(
    "PRISM_ALERT_URL",
    "http://localhost:9000/alert",
)
ALERT_COOLDOWN_SECONDS = 60
ALERT_COOLDOWN_S: float = 60.0     # max one POST /alert per machine per 60 s

# ---------------------------------------------------------------------------
# LLM explainer
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "your-key-here")
LLM_CACHE_SECONDS = 30
LLM_MODEL: str = "claude-haiku-4-5-20251001"
LLM_TIMEOUT_S: float = 15.0
LLM_MAX_TOKENS: int = 256

# ---------------------------------------------------------------------------
# Priority queue
# ---------------------------------------------------------------------------
# Higher risk score → processed first (min-heap stores negated score)
PRIORITY_QUEUE_MAXSIZE: int = 256

# ---------------------------------------------------------------------------
# Web dashboard
# ---------------------------------------------------------------------------
WEB_HOST: str = os.getenv("PRISM_WEB_HOST", "0.0.0.0")
WEB_PORT: int = int(os.getenv("PRISM_WEB_PORT", "7860"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("PRISM_LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("PRISM_LOG_FILE", "prism.log")


# ---------------------------------------------------------------------------
# Dataclass snapshots (typed, immutable views used across modules)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SensorReading:
    """A single timestamped sensor snapshot from one machine."""

    machine_id: str
    timestamp: float            # Unix epoch seconds
    temperature_C: float
    vibration_mm_s: float
    rpm: float
    current_A: float
    status: str                 # "OK" | "WARNING" | "FAULT"

    def to_dict(self) -> Dict[str, object]:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp,
            "temperature_C": self.temperature_C,
            "vibration_mm_s": self.vibration_mm_s,
            "rpm": self.rpm,
            "current_A": self.current_A,
            "status": self.status,
        }


@dataclass
class RiskEvent:
    """Enriched risk event emitted by the agent loop."""

    machine_id: str
    timestamp: float
    risk_score: float           # 0–100
    risk_level: str             # LOW / MEDIUM / HIGH / CRITICAL
    anomalous_sensors: List[str]
    spike_score: float
    drift_score: float
    compound_bonus: float
    status_bonus: float
    explanation: str = ""
    reading: SensorReading = field(default=None)  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, object]:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "anomalous_sensors": self.anomalous_sensors,
            "spike_score": self.spike_score,
            "drift_score": self.drift_score,
            "compound_bonus": self.compound_bonus,
            "status_bonus": self.status_bonus,
            "explanation": self.explanation,
        }
