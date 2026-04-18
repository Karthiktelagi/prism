import time
import httpx
from typing import Dict, Tuple

from config import ANTHROPIC_API_KEY, SensorReading
from intelligence.anomaly_detector import AnomalyResult
from agent.risk_scorer import RiskResult

class Explainer:
    def __init__(self):
        self._cache: Dict[str, Tuple[float, str]] = {}

    async def explain(self, machine_id: str, risk: RiskResult, reading: SensorReading, anomaly: AnomalyResult) -> str:
        now = time.time()
        
        # Cache explanation per machine: don't call LLM more than once per 30 seconds per machine
        if machine_id in self._cache:
            last_time, last_explanation = self._cache[machine_id]
            if now - last_time < 30.0:
                return last_explanation

        system_prompt = "You are an industrial maintenance AI. Generate a 2-sentence plain-English diagnosis."
        user_prompt = (
            f"Machine: {machine_id}\n"
            f"Risk: {risk.score}/100 ({risk.level})\n"
            f"Sensors: temp={reading.temperature_C}°C, vib={reading.vibration_mm_s}mm/s, rpm={reading.rpm}, current={reading.current_A}A\n"
            f"Anomalies: spikes in {anomaly.spike_sensors}, drift in {anomaly.drift_sensors}\n"
            f"Compound: {anomaly.compound_pairs}\n"
            f"Status: {reading.status}\n"
            f"Provide: cause, urgency, recommended action."
        )

        # FALLBACK if LLM fails
        explanation = self._fallback_explain(machine_id, risk, reading, anomaly)
        
        # PRIMARY: Call Anthropic API
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your-key-here":
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": ANTHROPIC_API_KEY,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": "claude-haiku-4-5-20251001",
                            "max_tokens": 256,
                            "system": system_prompt,
                            "messages": [
                                {"role": "user", "content": user_prompt}
                            ]
                        }
                    )
                    response.raise_for_status()
                    explanation = response.json()["content"][0]["text"]
            except Exception:
                pass # Use fallback explanation

        self._cache[machine_id] = (now, explanation)
        return explanation

    def _fallback_explain(self, machine_id: str, risk: RiskResult, reading: SensorReading, anomaly: AnomalyResult) -> str:
        action = "Schedule maintenance immediately" if risk.level in ["critical", "alert"] else "Monitor closely"
        spike_str = ", ".join(anomaly.spike_sensors) if anomaly.spike_sensors else "no"
        drift_str = ", ".join(anomaly.drift_sensors) if anomaly.drift_sensors else "no"
        
        return f"Machine {machine_id} shows {spike_str} spikes and {drift_str} drift. Risk {risk.score}/100 ({risk.level}) — {action}."
