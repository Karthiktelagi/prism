"""
main.py — PRISM entry point
"""
import argparse
import asyncio

from config import MACHINE_IDS
from agent.agent_loop import PRISMAgent
from dashboard.terminal_ui import start_dashboard
from dashboard.web_server import start_web_server
from intelligence.anomaly_detector import AnomalyDetector
from intelligence.baseline import MachineBaseline
from utils.logger import get_logger  # ensures root logger configured once

async def _main(args: argparse.Namespace) -> None:
    # Logging is configured by utils/logger.py on first import above
    logger = get_logger("prism.main")
    logger.info("=" * 60)
    logger.info("  PRISM — Predictive Risk Intelligence & Sensor Monitor")
    logger.info("  Team ByteForge | Hack Malenadu '26")
    logger.info("=" * 60)

    # Initialize shared components for the new PRISMAgent architecture
    baselines = {mid: MachineBaseline(mid) for mid in MACHINE_IDS}
    detectors = {mid: AnomalyDetector(baselines[mid]) for mid in MACHINE_IDS}
    data_queues = {mid: asyncio.Queue() for mid in MACHINE_IDS}
    dashboard_state = {}

    # Setup the main agent loop
    agent = PRISMAgent(
        baselines=baselines,
        detectors=detectors,
        data_queues=data_queues,
        dashboard_state=dashboard_state
    )

    import aiohttp
    from ingestion.history_loader import fetch_history
    from ingestion.stream_consumer import consume_stream

    # Warm up baselines with history before starting streams
    async def _warmup_baselines():
        logger.info("Fetching historical data to warm up baselines...")
        async with aiohttp.ClientSession() as session:
            for mid in MACHINE_IDS:
                readings = await fetch_history(mid, session)
                if readings:
                    # Bulk-init IQR bounds and correlation matrix
                    baselines[mid].compute(readings)
                    # Also warm up the CUSUM rolling window
                    for r in readings:
                        baselines[mid].update_rolling(r)
                    logger.info("Baseline ready for %s (%d readings)", mid, len(readings))
                else:
                    logger.warning("No history for %s — baseline starts cold", mid)

    coros = [_warmup_baselines(), agent.run()]

    # Connect to live SSE streams
    for mid in MACHINE_IDS:
        coros.append(consume_stream(mid, data_queues[mid]))

    if not args.no_web:
        coros.append(start_web_server(dashboard_state))

    if not args.no_ui:
        coros.append(start_dashboard(dashboard_state))

    try:
        await asyncio.gather(*coros)
    except KeyboardInterrupt:
        logger.info("PRISM shutdown requested via KeyboardInterrupt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PRISM — Predictive Risk Intelligence & Sensor Monitor"
    )
    parser.add_argument("--demo", action="store_true", help="Use synthetic sensor data")
    parser.add_argument("--no-web", action="store_true", help="Disable the web dashboard")
    parser.add_argument("--no-ui", action="store_true", help="Disable the terminal UI")
    parser.add_argument("--history", type=str, default=None, help="Path or URL to historical data")
    args = parser.parse_args()

    try:
        asyncio.run(_main(args))
    except KeyboardInterrupt:
        print("\n[PRISM] Shutdown complete.")


if __name__ == "__main__":
    main()
