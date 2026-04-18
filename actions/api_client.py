import logging
import asyncio
import aiohttp
from config import SensorReading

logger = logging.getLogger(__name__)

async def post_alert(machine_id: str, risk_score: float, explanation: str, reading: SensorReading, session: aiohttp.ClientSession) -> bool:
    url = "http://localhost:3000/alert"
    
    # Safely format the reading to a dictionary
    if hasattr(reading, "to_dict"):
        reading_dict = reading.to_dict()
    elif hasattr(reading, "__dict__"):
        reading_dict = reading.__dict__
    elif isinstance(reading, dict):
        reading_dict = reading
    else:
        reading_dict = {}

    payload = {
        "machine_id": machine_id,
        "reason": explanation,
        "reading": reading_dict
    }
    
    for attempt in range(1, 4):
        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                try:
                    data = await response.json()
                except Exception:
                    data = {}
                    
            alert_id = data.get("alert_id") or data.get("id") or "UNKNOWN_ID"
            logger.info(f"Successfully posted alert for {machine_id} on attempt {attempt}. Alert ID: {alert_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to post alert for {machine_id} on attempt {attempt}: {e}")
            if attempt < 3:
                await asyncio.sleep(2.0)
                
    logger.error(f"Failed to post alert for {machine_id} after 3 attempts")
    return False

async def schedule_maintenance(machine_id: str, session: aiohttp.ClientSession) -> bool:
    url = "http://localhost:3000/schedule-maintenance"
    
    payload = {
        "machine_id": machine_id
    }
    
    for attempt in range(1, 4):
        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                try:
                    data = await response.json()
                except Exception:
                    data = {}
                    
            booking_id = data.get("booking_id") or data.get("id") or "UNKNOWN_ID"
            logger.info(f"Successfully scheduled maintenance for {machine_id} on attempt {attempt}. Booking ID: {booking_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to schedule maintenance for {machine_id} on attempt {attempt}: {e}")
            if attempt < 3:
                await asyncio.sleep(2.0)
                
    logger.error(f"Failed to schedule maintenance for {machine_id} after 3 attempts")
    return False
