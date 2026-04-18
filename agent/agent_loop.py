import asyncio
import time
import logging
import aiohttp
from typing import Dict, Tuple

from config import SensorReading
from intelligence.anomaly_detector import AnomalyDetector, AnomalyResult
from intelligence.baseline import MachineBaseline
from agent.risk_scorer import compute_risk, RiskResult
from agent.explainer import Explainer
from actions.api_client import post_alert, schedule_maintenance
from dashboard.alert_store import push_alert as _push_alert

logger = logging.getLogger(__name__)

class PRISMAgent:
    def __init__(
        self,
        baselines: Dict[str, MachineBaseline],
        detectors: Dict[str, AnomalyDetector],
        data_queues: Dict[str, asyncio.Queue],
        dashboard_state: Dict[str, dict]
    ):
        self.baselines = baselines
        self.detectors = detectors
        self.data_queues = data_queues
        self.dashboard_state = dashboard_state
        
        # Uses asyncio.PriorityQueue keyed by (-risk_score, machine_id)
        self.queue: asyncio.PriorityQueue[Tuple[float, str, object]] = asyncio.PriorityQueue()
        self.explainer = Explainer()
        self.last_alert_time: Dict[str, float] = {}
        self._alert_counts: Dict[str, int] = {}

    async def feed_queues(self):
        """
        Reads from data_queues (filled by stream_consumer) and feeds priority queue.
        """
        async def _feed_machine(mid: str, q: asyncio.Queue):
            while True:
                try:
                    reading = await q.get()
                    risk_score = self.dashboard_state.get(mid, {}).get("risk_score", 0.0)
                    await self.queue.put((-risk_score, mid, reading))
                    q.task_done()
                except asyncio.CancelledError:
                    break
                    
        tasks = []
        for mid, q in self.data_queues.items():
            tasks.append(asyncio.create_task(_feed_machine(mid, q)))
            
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()

    def _coerce_reading(self, raw) -> SensorReading:
        """Convert any SensorReading variant (str or float timestamp) to config.SensorReading."""
        if isinstance(raw, SensorReading):
            return raw
        # stream_consumer.SensorReading has str timestamp — convert
        ts_raw = getattr(raw, 'timestamp', 0)
        try:
            ts = float(ts_raw)
        except (ValueError, TypeError):
            ts = time.time()
        return SensorReading(
            machine_id=str(getattr(raw, 'machine_id', '')),
            timestamp=ts,
            temperature_C=float(getattr(raw, 'temperature_C', 0.0)),
            vibration_mm_s=float(getattr(raw, 'vibration_mm_s', 0.0)),
            rpm=float(getattr(raw, 'rpm', 0.0)),
            current_A=float(getattr(raw, 'current_A', 0.0)),
            status=str(getattr(raw, 'status', 'OK')),
        )

    async def run(self):
        logger.info("PRISMAgent loop starting...")
        
        # Start feeding the priority queue
        feeder_task = asyncio.create_task(self.feed_queues())
        
        async with aiohttp.ClientSession() as session:
            try:
                while True:
                    # 1. Dequeue highest-risk machine reading from priority queue
                    neg_risk, machine_id, raw_reading = await self.queue.get()

                    # Coerce to config.SensorReading (handles str-timestamp variant)
                    reading = self._coerce_reading(raw_reading)
                    
                    # 2. Run anomaly detection — process() manages the sliding
                    #    window internally and returns AnomalyReport.
                    detector = self.detectors[machine_id]
                    report = detector.process(reading)

                    # 3. Build AnomalyResult from AnomalyReport for compute_risk()
                    anomaly = AnomalyResult(
                        spike_sensors=report.confirmed_anomalies,
                        drift_sensors=[
                            s for s in report.confirmed_anomalies
                            if report.sensor_details.get(s) and
                               abs(report.sensor_details[s].drift_ratio) > 0.1
                        ],
                        compound=len(report.confirmed_anomalies) >= 2,
                        compound_pairs=[
                            (report.confirmed_anomalies[i], report.confirmed_anomalies[j])
                            for i in range(len(report.confirmed_anomalies))
                            for j in range(i + 1, len(report.confirmed_anomalies))
                        ],
                        max_deviation=max(
                            (abs(d.z_score) for d in report.sensor_details.values()),
                            default=0.0
                        )
                    )
                    
                    # 4. Compute risk score
                    risk = compute_risk(anomaly, reading, self.baselines[machine_id])
                    
                    # 5. Generate LLM explanation
                    explanation = await self.explainer.explain(machine_id, risk, reading, anomaly)
                    
                    # Log every decision with timestamp
                    now = time.time()
                    last_time = self.last_alert_time.get(machine_id, 0.0)
                    
                    logger.info(f"[{now:.0f}] Decision for {machine_id}: Risk {risk.score:.1f} ({risk.level}). {explanation[:80]}")
                    
                    # 6. POST /alert if risk > 60 (with cooldown: skip if last alert < 60s ago)
                    if risk.score > 60 and (now - last_time >= 60.0):
                        r_dict = reading.to_dict() if hasattr(reading, 'to_dict') else {}
                        _push_alert(machine_id, risk.score, risk.level, explanation, r_dict)
                        await post_alert(machine_id, risk.score, explanation, reading, session)
                        self.last_alert_time[machine_id] = now
                        self._alert_counts[machine_id] = self._alert_counts.get(machine_id, 0) + 1
                            
                    # 7. POST /schedule-maintenance if risk > 80
                    if risk.score > 80 and (now - last_time >= 60.0):
                        await schedule_maintenance(machine_id, session)
                            
                    # 8. Update dashboard_state[machine_id] with latest result
                    self.dashboard_state[machine_id] = {
                        "machine_id": machine_id,
                        "risk_score": risk.score,
                        "risk_level": risk.level,
                        "explanation": explanation,
                        "timestamp": now,
                        "reading": reading,
                        "spike_sensors": anomaly.spike_sensors,
                        "drift_sensors": anomaly.drift_sensors,
                        "alerts_fired": self._alert_counts.get(machine_id, 0),
                    }
                    
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info("Graceful shutdown initiated: CancelledError")
                feeder_task.cancel()
            except KeyboardInterrupt:
                logger.info("Graceful shutdown initiated: KeyboardInterrupt")
                feeder_task.cancel()
