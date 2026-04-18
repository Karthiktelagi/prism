"""
intelligence/anomaly_detector.py — Stateful per-machine anomaly detection
==========================================================================
Detects two classes of sensor anomalies:

**Spikes** — individual readings that cross the IQR Tukey fences computed by
``MachineBaseline.compute()``.  A sensor is only *confirmed* spiking when at
least 2 of its last 3 readings are outside the fence (noise filter).

**Drift** — sustained shift of the rolling mean away from the bulk baseline.
A sensor is flagged for drift when ``baseline.get_drift(sensor)`` exceeds
``±1.5 σ`` for **10 or more consecutive readings**.

**Compound faults** — two or more sensors spike simultaneously *and* they are
identified as a correlated pair in ``baseline.correlated_pairs``.

Public API (spec)
-----------------
``AnomalyResult``
    Dataclass returned by ``detect()``.
``AnomalyDetector(baseline)``
    Single-argument constructor (spec).
``detect(readings: deque[SensorReading]) -> AnomalyResult``
    Analyse a sliding window and return a fully populated ``AnomalyResult``.

Backward-compatible API (agent loop)
--------------------------------------
``AnomalyDetector(machine_id, baseline, noise_filter)``
    Three-argument constructor used by the existing ``MachineAgent``.
``process(reading) -> AnomalyReport``
    Single-reading pipeline; feeds the internal window and calls ``detect()``.
``AnomalyReport`` / ``SensorAnomaly``
    Legacy dataclasses consumed by ``RiskScorer.score()``.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from config import SENSOR_FIELDS
from intelligence.baseline import MachineBaseline
from utils.logger import get_logger
from utils.noise_filter import NoiseFilter

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Sensors with numeric values (exclude categorical "status").
_NUMERIC_SENSORS: List[str] = [s for s in SENSOR_FIELDS if s != "status"]

#: Noise-filter window: flag as spiking only if ≥ _SPIKE_K of last _SPIKE_N
#: readings are outside IQR bounds.
_SPIKE_N: int = 3
_SPIKE_K: int = 2

#: Drift persistence threshold — consecutive readings required for drift flag.
_DRIFT_STREAK_MIN: int = 10

#: Drift sigma threshold — ``|get_drift()| > this`` triggers a drift count.
_DRIFT_SIGMA_THRESHOLD: float = 1.5


# ---------------------------------------------------------------------------
# SensorReading structural type — accepts both wire-format and config variants
# ---------------------------------------------------------------------------

@runtime_checkable
class _ReadingLike(Protocol):
    """Structural type satisfied by all SensorReading variants in PRISM."""
    machine_id: str
    temperature_C: float
    vibration_mm_s: float
    rpm: float
    current_A: float
    status: str


# ---------------------------------------------------------------------------
# Spec dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AnomalyResult:
    """
    Result of one ``detect()`` call — summarises all anomaly findings for a
    sliding window of sensor readings.

    Attributes
    ----------
    spike_sensors : list[str]
        Sensors confirmed as spiking (≥2 of their last 3 readings outside the
        IQR Tukey fences).
    drift_sensors : list[str]
        Sensors whose rolling mean has deviated > 1.5 σ for 10+ consecutive
        readings.
    compound : bool
        ``True`` if two or more *correlated* sensors are spiking simultaneously
        (as defined by ``MachineBaseline.correlated_pairs``).
    compound_pairs : list[tuple[str, str]]
        The specific correlated pairs that are simultaneously spiking.
        Empty when ``compound`` is ``False``.
    max_deviation : float
        The worst-case deviation magnitude across all numeric sensors in the
        most recent reading of the window.  Computed as the maximum absolute
        IQR-normalised distance from the nearest fence, or the absolute
        z-score when no IQR fence is available.
    """
    spike_sensors: List[str]
    drift_sensors: List[str]
    compound: bool
    compound_pairs: List[Tuple[str, str]]
    max_deviation: float


# ---------------------------------------------------------------------------
# Backward-compatible legacy dataclasses (consumed by RiskScorer)
# ---------------------------------------------------------------------------

@dataclass
class SensorAnomaly:
    """Per-sensor detail within a legacy ``AnomalyReport``."""
    sensor: str
    value: float
    z_score: float
    drift_ratio: float
    is_spike: bool
    is_confirmed: bool  # passed the noise filter?


@dataclass
class AnomalyReport:
    """
    Full anomaly report for one ``SensorReading``.

    ``confirmed_anomalies`` lists sensors that are both individually anomalous
    AND confirmed by the noise filter (≥ K of last N readings flagged).

    This dataclass is consumed directly by ``RiskScorer.score()``.
    """
    machine_id: str
    timestamp: float
    reading: object  # SensorReading from config or stream_consumer
    sensor_details: Dict[str, SensorAnomaly] = field(default_factory=dict)
    confirmed_anomalies: List[str] = field(default_factory=list)
    status_fault: bool = False
    baseline_ready: bool = False


# ---------------------------------------------------------------------------
# AnomalyDetector
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """
    Per-machine stateful anomaly detector.

    Combines IQR-bounds spike detection, rolling-drift detection, compound
    multi-sensor flagging, and an internal noise filter — all derived solely
    from the machine's own ``MachineBaseline`` instance.

    Supports two calling conventions:

    **Spec API (new)**::

        detector = AnomalyDetector(baseline)
        result: AnomalyResult = detector.detect(readings_deque)

    **Agent-loop API (backward-compatible)**::

        detector = AnomalyDetector(machine_id, baseline, noise_filter)
        report: AnomalyReport = detector.process(reading)

    Parameters
    ----------
    machine_id_or_baseline : str | MachineBaseline
        When called with one argument (spec): the ``MachineBaseline`` instance.
        When called with three arguments (compat): the machine ID string.
    baseline : MachineBaseline | None
        The machine's baseline; ``None`` only in the single-argument form.
    noise_filter : NoiseFilter | None
        External noise filter for the ``process()`` path; ignored internally
        by ``detect()`` which manages its own per-sensor deques.
    """

    def __init__(
        self,
        machine_id_or_baseline,
        baseline: Optional[MachineBaseline] = None,
        noise_filter: Optional[NoiseFilter] = None,
    ) -> None:
        # ── Handle both calling conventions ──────────────────────────────
        if isinstance(machine_id_or_baseline, MachineBaseline):
            # Single-arg spec call: AnomalyDetector(baseline)
            self._baseline: MachineBaseline = machine_id_or_baseline
            self.machine_id: str = self._baseline.machine_id
            self._noise_filter: Optional[NoiseFilter] = None
        else:
            # Three-arg compat call: AnomalyDetector(machine_id, baseline, nf)
            self.machine_id = str(machine_id_or_baseline)
            if baseline is None:
                raise ValueError(
                    "baseline must be supplied when machine_id is given as first arg."
                )
            self._baseline = baseline
            self._noise_filter = noise_filter

        # ── Internal noise filter: per-sensor deque of recent IQR verdicts ─
        # Tracks the last _SPIKE_N boolean results (True = outside IQR bounds)
        # independently of the external NoiseFilter used by process().
        self._spike_windows: Dict[str, Deque[bool]] = {
            s: deque(maxlen=_SPIKE_N) for s in _NUMERIC_SENSORS
        }

        # ── Drift streak counters: consecutive readings above threshold ────
        self._drift_streak: Dict[str, int] = {s: 0 for s in _NUMERIC_SENSORS}

        # ── Internal sliding window for process() → detect() bridge ───────
        # Sized to hold enough readings for the noise filter (_SPIKE_N)
        # plus extra context for drift evaluation.
        self._window: Deque[object] = deque(maxlen=max(_SPIKE_N, _DRIFT_STREAK_MIN))

    # -----------------------------------------------------------------------
    # Spec public API
    # -----------------------------------------------------------------------

    def detect(self, readings: Deque) -> AnomalyResult:
        """
        Analyse a sliding window of sensor readings and return an
        ``AnomalyResult``.

        **Spike detection** (noise-filtered IQR):
            For each numeric sensor, the last ``_SPIKE_N`` (3) readings in the
            window are evaluated against the IQR Tukey fences.  The sensor is
            added to ``spike_sensors`` only if at least ``_SPIKE_K`` (2) of
            those readings are outside the fence.  This suppresses single-shot
            transient glitches.

        **Drift detection** (sustained rolling-mean deviation):
            ``baseline.get_drift(sensor)`` is called for the most recent
            reading.  The internal streak counter for that sensor is
            incremented when ``|drift| > 1.5 σ`` and reset to zero when the
            drift falls below threshold.  The sensor is added to
            ``drift_sensors`` when its streak reaches or exceeds
            ``_DRIFT_STREAK_MIN`` (10) consecutive readings.

        **Compound detection**:
            If two or more sensors are in ``spike_sensors`` and they also
            appear as a pair in ``baseline.correlated_pairs``, the result is
            marked ``compound=True`` and the specific pairs are listed in
            ``compound_pairs``.

        **Max deviation**:
            The signed distance of each sensor's most recent value from the
            nearest IQR boundary, expressed in IQR units.  If no IQR fence
            exists (baseline not yet computed), falls back to the absolute
            z-score.  ``max_deviation`` is the maximum across all sensors.

        Parameters
        ----------
        readings : collections.deque
            Ordered window of recent ``SensorReading``-like objects
            (oldest first, newest last).  Must contain at least one reading.

        Returns
        -------
        AnomalyResult
        """
        if not readings:
            return AnomalyResult(
                spike_sensors=[],
                drift_sensors=[],
                compound=False,
                compound_pairs=[],
                max_deviation=0.0,
            )

        latest = readings[-1]  # most recent reading
        recent_3 = list(readings)[-_SPIKE_N:]  # last 3 for noise filter

        # ── Baseline update ───────────────────────────────────────────────
        self._baseline.update_rolling(latest)

        spike_sensors: List[str] = []
        drift_sensors: List[str] = []
        max_deviation: float = 0.0

        for sensor in _NUMERIC_SENSORS:
            # ── Spike noise filter ────────────────────────────────────────
            iqr_flags: List[bool] = []
            for r in recent_3:
                try:
                    val = float(getattr(r, sensor, 0.0))
                except (ValueError, TypeError):
                    val = 0.0
                iqr_flags.append(self._baseline.is_outside_iqr(sensor, val))

            # Confirmed spike: ≥ K of last N readings outside IQR
            is_spike_confirmed = sum(iqr_flags) >= _SPIKE_K
            if is_spike_confirmed:
                spike_sensors.append(sensor)

            # ── Drift streak tracking ─────────────────────────────────────
            drift_val = self._baseline.get_drift(sensor)
            if abs(drift_val) > _DRIFT_SIGMA_THRESHOLD:
                self._drift_streak[sensor] += 1
            else:
                self._drift_streak[sensor] = 0  # reset on recovery

            if self._drift_streak[sensor] >= _DRIFT_STREAK_MIN:
                drift_sensors.append(sensor)

            # ── Per-sensor max deviation ──────────────────────────────────
            try:
                latest_val = float(getattr(latest, sensor, 0.0))
            except (ValueError, TypeError):
                latest_val = 0.0

            deviation = self._sensor_deviation(sensor, latest_val)
            if deviation > max_deviation:
                max_deviation = deviation

        # ── Compound detection ────────────────────────────────────────────
        spike_set = set(spike_sensors)
        compound_pairs: List[Tuple[str, str]] = [
            (a, b)
            for (a, b) in self._baseline.correlated_pairs
            if a in spike_set and b in spike_set
        ]
        compound = len(compound_pairs) > 0

        return AnomalyResult(
            spike_sensors=spike_sensors,
            drift_sensors=drift_sensors,
            compound=compound,
            compound_pairs=compound_pairs,
            max_deviation=round(max_deviation, 4),
        )

    # -----------------------------------------------------------------------
    # Backward-compatible API (agent loop → RiskScorer pipeline)
    # -----------------------------------------------------------------------

    def process(self, reading) -> AnomalyReport:
        """
        Process a single sensor reading through the full anomaly pipeline.

        This method is retained for backward compatibility with the existing
        ``agent_loop.py`` / ``RiskScorer`` pipeline.  Internally it:

        1. Appends *reading* to the internal sliding window.
        2. Updates the ``MachineBaseline`` Welford tracker.
        3. Calls ``detect(self._window)`` to get the ``AnomalyResult``.
        4. Wraps the result in a legacy ``AnomalyReport`` that satisfies
           ``RiskScorer.score()``.

        Parameters
        ----------
        reading : SensorReading-like
            The most recent sensor snapshot from any PRISM ``SensorReading``
            variant.

        Returns
        -------
        AnomalyReport
            Legacy report consumed by ``RiskScorer.score()``.
        """
        self._window.append(reading)

        # Resolve timestamp — handle both float (config) and str (stream)
        raw_ts = getattr(reading, "timestamp", None)
        try:
            timestamp = float(raw_ts)
        except (ValueError, TypeError):
            timestamp = time.time()

        status_str = str(getattr(reading, "status", "")).upper()
        status_fault = status_str in ("FAULT", "fault")

        # ── Run the spec detect() over the internal window ────────────────
        result = self.detect(self._window)

        # ── Build per-sensor detail for RiskScorer ────────────────────────
        report = AnomalyReport(
            machine_id=self.machine_id,
            timestamp=timestamp,
            reading=reading,
            status_fault=status_fault,
            baseline_ready=self._baseline.is_ready(),
        )

        confirmed_set = set(result.spike_sensors)  # noise-filtered spikes

        for sensor in _NUMERIC_SENSORS:
            try:
                value = float(getattr(reading, sensor, 0.0))
            except (ValueError, TypeError):
                value = 0.0

            z = self._baseline.z_score(sensor, value)
            dr = self._baseline.drift_ratio(sensor, value)
            is_spike_raw = self._baseline.is_outside_iqr(sensor, value)
            is_confirmed = sensor in confirmed_set

            # ── Also feed the external noise filter if provided ───────────
            if self._noise_filter is not None:
                ext_confirmed = self._noise_filter.update(
                    self.machine_id, sensor, is_anomalous=is_spike_raw
                )
                # Union: confirmed by either internal or external filter
                is_confirmed = is_confirmed or ext_confirmed

            # Always update the Welford baseline
            self._baseline.update(sensor, value)

            detail = SensorAnomaly(
                sensor=sensor,
                value=value,
                z_score=z,
                drift_ratio=dr,
                is_spike=is_spike_raw,
                is_confirmed=is_confirmed,
            )
            report.sensor_details[sensor] = detail

            if is_confirmed:
                report.confirmed_anomalies.append(sensor)

        return report

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _sensor_deviation(self, sensor: str, value: float) -> float:
        """
        Return the unsigned deviation of *value* from the nearest IQR boundary
        for *sensor*, normalised by the IQR range.

        If the IQR is zero or the bulk baseline has not been computed, falls
        back to the absolute z-score from the Welford tracker.

        A value of ``0.0`` means the reading is inside the fence.  A value of
        ``1.0`` means the reading is one full IQR-width beyond the fence.

        Parameters
        ----------
        sensor : str
            Sensor name, e.g. ``"temperature_C"``.
        value : float
            The most recent observed sensor value.

        Returns
        -------
        float
            Non-negative deviation magnitude.
        """
        b = self._baseline._bounds.get(sensor)
        if b is None or b.iqr < 1e-9:
            # Fallback: absolute z-score
            return abs(self._baseline.z_score(sensor, value))

        if value < b.lower_bound:
            return (b.lower_bound - value) / b.iqr
        if value > b.upper_bound:
            return (value - b.upper_bound) / b.iqr
        return 0.0  # inside the fence
