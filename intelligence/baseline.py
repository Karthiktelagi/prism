"""
intelligence/baseline.py — Per-machine statistical baseline engine
==================================================================
Each physical machine gets exactly one ``MachineBaseline`` instance.
There are **no** global thresholds — all statistics are derived solely from
that machine's own sensor history (rule 3).

The baseline is built in two phases:

1. **Bulk initialisation** (``compute(readings)``) — called once with
   historical data.  Uses NumPy percentile arithmetic to compute IQR-based
   bounds and Pandas to build a sensor correlation matrix.

2. **Streaming updates** (``update_rolling(reading)``) — called on every new
   live reading to keep the CUSUM deque and rolling stats current.

Public API (spec)
-----------------
``compute(readings)``
    Bulk-initialise all per-sensor statistics from a list of readings.
``update_rolling(reading)``
    Append a live reading to the CUSUM deque; recompute rolling mean.
``get_drift(sensor)``
    Return ``(current_rolling_mean − baseline_mean) / baseline_std``.

Backward-compatible API (agent loop)
-------------------------------------
``update(sensor, value)``  ``is_ready()``  ``z_score()``  ``drift_ratio()``
``is_spike()``  ``mean()``  ``std()``  ``summary()``
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import numpy as np
import pandas as pd

from config import (
    BASELINE_MIN_SAMPLES,
    BASELINE_WINDOW,
    SENSOR_FIELDS,
    Z_SCORE_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Sensors with numerical values we can compute statistics over.
_NUMERIC_SENSORS: List[str] = [s for s in SENSOR_FIELDS if s != "status"]

#: Rolling CUSUM window size (number of recent readings kept per sensor).
_CUSUM_WINDOW: int = 30

#: Pearson |r| threshold above which two sensors are considered correlated.
_CORR_THRESHOLD: float = 0.6

#: Sigma multiplier for drift significance in ``get_drift()`` interpretation.
_DRIFT_SIGMA: float = 1.5


# ---------------------------------------------------------------------------
# SensorReading protocol — accepts both config.SensorReading (float ts)
# and ingestion.stream_consumer.SensorReading (str ts) without circular imports.
# ---------------------------------------------------------------------------

@runtime_checkable
class _ReadingLike(Protocol):
    """Structural type accepted by MachineBaseline methods."""
    machine_id: str
    temperature_C: float
    vibration_mm_s: float
    rpm: float
    current_A: float
    status: str


# ---------------------------------------------------------------------------
# Per-sensor statistics container
# ---------------------------------------------------------------------------

@dataclass
class _SensorBounds:
    """
    IQR-derived bounds and Gaussian statistics for one sensor, computed by
    ``numpy.percentile`` over the bulk history.

    Attributes
    ----------
    q1, q3 : float
        25th and 75th percentiles.
    iqr : float
        Interquartile range (Q3 − Q1).
    lower_bound : float
        Q1 − 1.5 × IQR  (Tukey fence — lower outlier threshold).
    upper_bound : float
        Q3 + 1.5 × IQR  (Tukey fence — upper outlier threshold).
    mean : float
        Arithmetic mean of the bulk history (baseline anchor for drift).
    std_dev : float
        Sample standard deviation of the bulk history.
    rolling_window : Deque[float]
        CUSUM circular buffer of the most recent ``_CUSUM_WINDOW`` values.
    rolling_mean : float
        Current mean of values in ``rolling_window``.
    """
    q1: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    mean: float = 0.0
    std_dev: float = 0.0
    rolling_window: Deque[float] = field(
        default_factory=lambda: deque(maxlen=_CUSUM_WINDOW)
    )
    rolling_mean: float = 0.0
    n_history: int = 0  # number of bulk readings used to build this stat


# ---------------------------------------------------------------------------
# Welford online tracker (used for incremental baseline before bulk is ready)
# ---------------------------------------------------------------------------

class _WelfordTracker:
    """
    Numerically stable incremental mean / variance using Welford's algorithm.
    Retained for backward-compatible ``update()`` / ``is_ready()`` / ``z_score()``
    calls from the agent loop when no bulk history has been loaded yet.
    """

    def __init__(self, maxlen: int = BASELINE_WINDOW) -> None:
        self._buf: deque = deque(maxlen=maxlen)
        self._n: int = 0
        self._mean: float = 0.0
        self._M2: float = 0.0
        self._initial_mean: Optional[float] = None

    # -- mutation -----------------------------------------------------------

    def update(self, value: float) -> None:
        if len(self._buf) == self._buf.maxlen:
            self._buf.append(value)
            self._recompute()
        else:
            self._buf.append(value)
            self._welford_update(value)
        if self._initial_mean is None and self._n >= BASELINE_MIN_SAMPLES:
            self._initial_mean = self._mean

    # -- queries ------------------------------------------------------------

    @property
    def n(self) -> int:
        return self._n

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        if self._n < 2:
            return 0.0
        return math.sqrt(max(self._M2 / (self._n - 1), 0.0))

    @property
    def initial_mean(self) -> Optional[float]:
        return self._initial_mean

    def z_score(self, value: float) -> float:
        s = self.std
        return 0.0 if s < 1e-9 else (value - self._mean) / s

    def drift_ratio(self, value: float) -> float:
        if self._initial_mean is None:
            return 0.0
        denom = max(abs(self._initial_mean), 1.0)
        return abs(value - self._initial_mean) / denom

    # -- internals ----------------------------------------------------------

    def _welford_update(self, value: float) -> None:
        self._n += 1
        delta = value - self._mean
        self._mean += delta / self._n
        self._M2 += delta * (value - self._mean)

    def _recompute(self) -> None:
        data = list(self._buf)
        self._n = len(data)
        if not data:
            self._mean = 0.0
            self._M2 = 0.0
            return
        self._mean = sum(data) / self._n
        self._M2 = sum((x - self._mean) ** 2 for x in data)


# ---------------------------------------------------------------------------
# MachineBaseline
# ---------------------------------------------------------------------------

class MachineBaseline:
    """
    Per-machine statistical baseline combining IQR bounds, Gaussian stats,
    a CUSUM rolling window, and a sensor correlation matrix.

    Lifecycle
    ---------
    1. Construct: ``baseline = MachineBaseline("CNC_01")``
    2. Bulk-init (optional, recommended): ``baseline.compute(history_readings)``
    3. Stream updates: ``baseline.update_rolling(new_reading)`` on every tick.
    4. Query:
       - ``baseline.get_drift("temperature_C")`` → normalised drift float
       - ``baseline.lower_bound["temperature_C"]`` → IQR lower fence
       - ``baseline.upper_bound["temperature_C"]`` → IQR upper fence
       - ``baseline.correlated_pairs`` → list of strongly-correlated sensor pairs

    Parameters
    ----------
    machine_id : str
        Identifier of the machine, e.g. ``"CNC_01"``.
    """

    def __init__(self, machine_id: str) -> None:
        self.machine_id = machine_id

        # Per-sensor IQR / Gaussian stats (populated by compute())
        self._bounds: Dict[str, _SensorBounds] = {
            s: _SensorBounds() for s in _NUMERIC_SENSORS
        }

        # Sensor correlation matrix — empty DataFrame until compute() is called
        self.correlation_matrix: pd.DataFrame = pd.DataFrame()

        # Correlated pairs: list of (sensor_a, sensor_b) where |r| > threshold
        self.correlated_pairs: List[Tuple[str, str]] = []

        # Welford trackers — used for backward-compat and live-only deployments
        self._trackers: Dict[str, _WelfordTracker] = {
            s: _WelfordTracker() for s in _NUMERIC_SENSORS
        }

        # Flag: has compute() been called with real bulk data?
        self._bulk_computed: bool = False

    # -----------------------------------------------------------------------
    # Spec public API — bulk initialisation
    # -----------------------------------------------------------------------

    def compute(self, readings: list) -> None:
        """
        Bulk-initialise all per-sensor statistics from a list of readings.

        For each numeric sensor this method computes:

        * **Q1, Q3, IQR** via ``numpy.percentile``
        * ``lower_bound = Q1 − 1.5 × IQR``  (Tukey lower fence)
        * ``upper_bound = Q3 + 1.5 × IQR``  (Tukey upper fence)
        * ``mean``, ``std_dev`` from the full sample
        * ``rolling_window`` — a fresh ``deque(maxlen=30)`` seeded with the
          most recent 30 readings

        The method then builds ``correlation_matrix`` as a ``pd.DataFrame``
        containing the Pearson correlation coefficients across all four numeric
        sensors, and populates ``correlated_pairs`` with every pair whose
        ``|r| > 0.6``.

        The Welford trackers are also re-seeded so that ``is_ready()``,
        ``z_score()``, and ``drift_ratio()`` remain accurate for the agent
        loop's backward-compatible call sites.

        Parameters
        ----------
        readings : list[SensorReading-like]
            Ordered list of historical sensor readings (oldest first).
            Must contain at least 4 readings; fewer will be skipped with a
            warning and the baseline left in its default state.
        """
        if len(readings) < 4:
            logger.warning(
                "[%s] compute() received only %d readings — need ≥4 for IQR; "
                "baseline left uninitialised.",
                self.machine_id,
                len(readings),
            )
            return

        # ── Build a dict of value arrays per sensor ───────────────────────
        arrays: Dict[str, np.ndarray] = {}
        for sensor in _NUMERIC_SENSORS:
            vals = []
            for r in readings:
                try:
                    vals.append(float(getattr(r, sensor, 0.0)))
                except (ValueError, TypeError):
                    vals.append(0.0)
            arrays[sensor] = np.asarray(vals, dtype=np.float64)

        # ── Per-sensor IQR stats ──────────────────────────────────────────
        for sensor, arr in arrays.items():
            q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
            iqr = q3 - q1
            b = self._bounds[sensor]
            b.q1 = q1
            b.q3 = q3
            b.iqr = iqr
            b.lower_bound = q1 - 1.5 * iqr
            b.upper_bound = q3 + 1.5 * iqr
            b.mean = float(np.mean(arr))
            b.std_dev = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            b.n_history = len(arr)

            # Seed CUSUM window with last _CUSUM_WINDOW readings
            seed = arr[-_CUSUM_WINDOW:].tolist()
            b.rolling_window = deque(seed, maxlen=_CUSUM_WINDOW)
            b.rolling_mean = float(np.mean(seed)) if seed else b.mean

            # Re-seed Welford tracker from the bulk array for compat
            tracker = self._trackers[sensor]
            tracker.__init__(maxlen=BASELINE_WINDOW)  # type: ignore[misc]
            for v in arr[-BASELINE_WINDOW:]:
                tracker.update(float(v))

            logger.debug(
                "[%s] %-16s  Q1=%.2f  Q3=%.2f  IQR=%.2f  "
                "lower=%.2f  upper=%.2f  μ=%.2f  σ=%.2f",
                self.machine_id, sensor,
                q1, q3, iqr,
                b.lower_bound, b.upper_bound,
                b.mean, b.std_dev,
            )

        # ── Correlation matrix ────────────────────────────────────────────
        df = pd.DataFrame({s: arrays[s] for s in _NUMERIC_SENSORS})
        self.correlation_matrix = df.corr(method="pearson")

        # Identify strongly correlated pairs (upper triangle only)
        self.correlated_pairs = []
        sensors = _NUMERIC_SENSORS
        for i in range(len(sensors)):
            for j in range(i + 1, len(sensors)):
                r = self.correlation_matrix.loc[sensors[i], sensors[j]]
                if abs(r) > _CORR_THRESHOLD:
                    self.correlated_pairs.append((sensors[i], sensors[j]))

        self._bulk_computed = True
        logger.info(
            "[%s] Baseline computed from %d readings. "
            "Correlated pairs (%d): %s",
            self.machine_id,
            len(readings),
            len(self.correlated_pairs),
            self.correlated_pairs,
        )

    # -----------------------------------------------------------------------
    # Spec public API — streaming update
    # -----------------------------------------------------------------------

    def update_rolling(self, reading: _ReadingLike) -> None:
        """
        Append a new live reading to each sensor's CUSUM deque and recompute
        the rolling mean.

        Also forwards the raw value to the Welford tracker so that
        ``z_score()`` / ``is_ready()`` remain accurate.

        Parameters
        ----------
        reading : SensorReading-like
            The most recent sensor snapshot to incorporate.
        """
        for sensor in _NUMERIC_SENSORS:
            try:
                value = float(getattr(reading, sensor, 0.0))
            except (ValueError, TypeError):
                continue

            b = self._bounds[sensor]
            b.rolling_window.append(value)
            if b.rolling_window:
                b.rolling_mean = sum(b.rolling_window) / len(b.rolling_window)

            # Keep Welford in sync for compat
            self._trackers[sensor].update(value)

    def get_drift(self, sensor: str) -> float:
        """
        Return the normalised drift of the current rolling mean from the
        bulk-computed baseline mean.

        Formula::

            drift = (current_rolling_mean − baseline_mean) / baseline_std

        A positive value means the rolling mean has climbed above baseline;
        negative means it has fallen.  Returns ``0.0`` if the sensor name is
        unknown, no bulk baseline exists, or ``baseline_std`` is effectively
        zero (< 1e-9).

        Parameters
        ----------
        sensor : str
            Name of the sensor, e.g. ``"temperature_C"``.

        Returns
        -------
        float
            Signed normalised drift in units of baseline standard deviations.
        """
        b = self._bounds.get(sensor)
        if b is None or b.std_dev < 1e-9:
            return 0.0
        return (b.rolling_mean - b.mean) / b.std_dev

    # -----------------------------------------------------------------------
    # Per-sensor bound accessors
    # -----------------------------------------------------------------------

    @property
    def lower_bound(self) -> Dict[str, float]:
        """Dict of sensor → IQR lower fence (Q1 − 1.5×IQR)."""
        return {s: self._bounds[s].lower_bound for s in _NUMERIC_SENSORS}

    @property
    def upper_bound(self) -> Dict[str, float]:
        """Dict of sensor → IQR upper fence (Q3 + 1.5×IQR)."""
        return {s: self._bounds[s].upper_bound for s in _NUMERIC_SENSORS}

    def is_outside_iqr(self, sensor: str, value: float) -> bool:
        """
        Return ``True`` if *value* lies outside the Tukey IQR fences for
        *sensor*.

        Falls back to a z-score threshold check when no bulk baseline has
        been computed yet.
        """
        b = self._bounds.get(sensor)
        if b is None:
            return False
        if not self._bulk_computed:
            # No IQR yet — fall back to Welford z-score
            return self.is_spike(sensor, value)
        return value < b.lower_bound or value > b.upper_bound

    def baseline_mean(self, sensor: str) -> float:
        """Return the bulk-computed mean for *sensor* (0.0 if unavailable)."""
        b = self._bounds.get(sensor)
        return b.mean if b else 0.0

    def baseline_std(self, sensor: str) -> float:
        """Return the bulk-computed std dev for *sensor* (0.0 if unavailable)."""
        b = self._bounds.get(sensor)
        return b.std_dev if b else 0.0

    def rolling_mean(self, sensor: str) -> float:
        """Return the current CUSUM rolling mean for *sensor*."""
        b = self._bounds.get(sensor)
        return b.rolling_mean if b else 0.0

    # -----------------------------------------------------------------------
    # Backward-compatible API (agent loop call sites)
    # -----------------------------------------------------------------------

    def update(self, sensor: str, value: float) -> None:
        """
        Incremental single-value feed into the Welford tracker.

        Called by the existing agent loop on every ``SensorReading``.
        Also forwards to ``update_rolling()`` internals.
        """
        if sensor in self._trackers:
            self._trackers[sensor].update(value)
            b = self._bounds[sensor]
            b.rolling_window.append(value)
            if b.rolling_window:
                b.rolling_mean = sum(b.rolling_window) / len(b.rolling_window)

    def is_ready(self) -> bool:
        """
        Return ``True`` once all sensors have enough samples for reliable
        statistics (``BASELINE_MIN_SAMPLES`` readings each).
        """
        return all(t.n >= BASELINE_MIN_SAMPLES for t in self._trackers.values())

    def z_score(self, sensor: str, value: float) -> float:
        """Return the Welford z-score for *value* on *sensor*; 0.0 if unknown."""
        t = self._trackers.get(sensor)
        return t.z_score(value) if t else 0.0

    def drift_ratio(self, sensor: str, value: float) -> float:
        """Return fractional drift from the initial-mean anchor (Welford)."""
        t = self._trackers.get(sensor)
        return t.drift_ratio(value) if t else 0.0

    def is_spike(self, sensor: str, value: float) -> bool:
        """Return ``True`` if ``|z-score| > Z_SCORE_THRESHOLD``."""
        return abs(self.z_score(sensor, value)) > Z_SCORE_THRESHOLD

    def mean(self, sensor: str) -> float:
        """Welford rolling mean for *sensor*."""
        t = self._trackers.get(sensor)
        return t.mean if t else 0.0

    def std(self, sensor: str) -> float:
        """Welford rolling std dev for *sensor*."""
        t = self._trackers.get(sensor)
        return t.std if t else 0.0

    def summary(self) -> Dict[str, Dict[str, float]]:
        """
        Return a diagnostics snapshot: for each sensor, report both the
        Welford live stats and the IQR bulk stats (when available).
        """
        out: Dict[str, Dict[str, float]] = {}
        for sensor in _NUMERIC_SENSORS:
            t = self._trackers[sensor]
            b = self._bounds[sensor]
            out[sensor] = {
                # Welford live stats
                "welford_mean": t.mean,
                "welford_std": t.std,
                "welford_n": t.n,
                # IQR bulk stats
                "baseline_mean": b.mean,
                "baseline_std": b.std_dev,
                "lower_bound": b.lower_bound,
                "upper_bound": b.upper_bound,
                "rolling_mean": b.rolling_mean,
                "drift_sigma": self.get_drift(sensor),
            }
        return out
