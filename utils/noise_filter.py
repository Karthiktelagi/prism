"""
utils/noise_filter.py — Sliding-window noise filter
=====================================================
Rule 8: raise an anomaly only if at least K of the last N readings
for a given (machine_id, sensor) pair are individually flagged anomalous.

This prevents transient glitches from triggering false positives.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Tuple

from config import ANOMALY_CONFIRM_K, ANOMALY_CONFIRM_N


class NoiseFilter:
    """
    Per-(machine, sensor) sliding-window confirmation filter.

    Usage
    -----
    filter = NoiseFilter()
    confirmed = filter.update("CNC_01", "temperature_C", is_anomalous=True)
    """

    def __init__(
        self,
        n: int = ANOMALY_CONFIRM_N,
        k: int = ANOMALY_CONFIRM_K,
    ) -> None:
        """
        Parameters
        ----------
        n : int
            Window size (last N readings examined).
        k : int
            Minimum number of anomalous readings in the window to confirm.
        """
        if k > n:
            raise ValueError(f"k ({k}) must be ≤ n ({n})")
        self._n = n
        self._k = k
        # key: (machine_id, sensor_name) → deque of booleans (True=anomalous)
        self._windows: Dict[Tuple[str, str], Deque[bool]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        machine_id: str,
        sensor: str,
        *,
        is_anomalous: bool,
    ) -> bool:
        """
        Record the latest reading verdict and return whether the anomaly
        is *confirmed* (i.e. ≥ k of last n readings were anomalous).

        Parameters
        ----------
        machine_id : str
            Machine identifier, e.g. ``"CNC_01"``.
        sensor : str
            Sensor name, e.g. ``"temperature_C"``.
        is_anomalous : bool
            Whether the current reading is individually anomalous.

        Returns
        -------
        bool
            ``True`` iff the anomaly is confirmed by the noise filter.
        """
        key = (machine_id, sensor)
        if key not in self._windows:
            self._windows[key] = deque(maxlen=self._n)

        window = self._windows[key]
        window.append(is_anomalous)
        return sum(window) >= self._k

    def reset(self, machine_id: str, sensor: str | None = None) -> None:
        """
        Clear the window for a machine (all sensors or a specific one).

        Useful when a machine comes back online after a fault.
        """
        if sensor is not None:
            self._windows.pop((machine_id, sensor), None)
        else:
            keys_to_delete = [k for k in self._windows if k[0] == machine_id]
            for k in keys_to_delete:
                del self._windows[k]

    def state_snapshot(self) -> Dict[Tuple[str, str], list]:
        """Return a read-only copy of all windows (for diagnostics)."""
        return {k: list(v) for k, v in self._windows.items()}
