from dataclasses import dataclass

from config import SensorReading
from intelligence.anomaly_detector import AnomalyResult
from intelligence.baseline import MachineBaseline

@dataclass
class RiskResult:
    score: float
    level: str
    spike_score: float
    drift_score: float
    compound_bonus: float
    status_bonus: float

def compute_risk(anomaly: AnomalyResult, reading: SensorReading, baseline: MachineBaseline) -> RiskResult:
    # spike_score = min(40, anomaly.max_deviation * 8)
    spike_score = min(40.0, anomaly.max_deviation * 8.0)
    
    # drift_score = sum(baseline.get_drift(s) * 5 for s in anomaly.drift_sensors)
    drift_score = sum(abs(baseline.get_drift(s)) * 5.0 for s in anomaly.drift_sensors)
    
    # compound_bonus = 20 if anomaly.compound else 0
    compound_bonus = 20.0 if anomaly.compound else 0.0
    
    # status_bonus = 30 if reading.status == "fault" else (15 if reading.status == "warning" else 0)
    status_lower = str(reading.status).lower()
    if status_lower == "fault":
        status_bonus = 30.0
    elif status_lower == "warning":
        status_bonus = 15.0
    else:
        status_bonus = 0.0
        
    # total = min(100, spike_score + drift_score + compound_bonus + status_bonus)
    total = min(100.0, spike_score + drift_score + compound_bonus + status_bonus)
    
    # level ("normal"/"watch"/"alert"/"critical")
    if total >= 80:
        level = "critical"
    elif total >= 60:
        level = "alert"
    elif total >= 40:
        level = "watch"
    else:
        level = "normal"
        
    return RiskResult(
        score=total,
        level=level,
        spike_score=spike_score,
        drift_score=drift_score,
        compound_bonus=compound_bonus,
        status_bonus=status_bonus
    )
