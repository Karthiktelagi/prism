import asyncio
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.console import Group

async def start_dashboard(state: dict) -> None:
    def generate_ui() -> Group:
        table = Table(title="PRISM Live Monitoring Dashboard", show_header=True, header_style="bold magenta")
        table.add_column("Machine", style="cyan")
        table.add_column("Temp°C", justify="right")
        table.add_column("Vibration", justify="right")
        table.add_column("RPM", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Risk Score", justify="right")
        table.add_column("Level", justify="center")
        table.add_column("Alerts", justify="center")
        table.add_column("Explanation")
        
        for machine_id, m_state in sorted(state.items()):
            if not isinstance(m_state, dict):
                continue
                
            reading = m_state.get("reading", {})
            if hasattr(reading, "temperature_C"):
                temp = f"{reading.temperature_C:.1f}"
                vib = f"{reading.vibration_mm_s:.2f}"
                rpm = f"{reading.rpm:.0f}"
                current = f"{reading.current_A:.1f}"
                status = reading.status
            elif isinstance(reading, dict):
                temp = f"{reading.get('temperature_C', 0.0):.1f}"
                vib = f"{reading.get('vibration_mm_s', 0.0):.2f}"
                rpm = f"{reading.get('rpm', 0.0):.0f}"
                current = f"{reading.get('current_A', 0.0):.1f}"
                status = reading.get("status", "UNKNOWN")
            else:
                temp = "N/A"
                vib = "N/A"
                rpm = "N/A"
                current = "N/A"
                status = "UNKNOWN"

            risk_score = m_state.get("risk_score", 0.0)
            risk_level = m_state.get("risk_level", "normal").lower()
            explanation = m_state.get("explanation", "")
            
            # Retrieve alerts count or default to 0
            alerts_count = str(m_state.get("alerts_fired", 0))
                
            risk_level_text = Text(risk_level.upper())
            if risk_level == "normal":
                risk_level_text.stylize("green")
            elif risk_level == "watch":
                risk_level_text.stylize("yellow")
            elif risk_level in ("alert", "high"):
                risk_level_text.stylize("red")
            elif risk_level == "critical":
                risk_level_text.stylize("bold red blink")
                
            table.add_row(
                machine_id, temp, vib, rpm, current, status,
                f"{risk_score:.1f}", risk_level_text, alerts_count, explanation
            )
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = Text(f"\nLast updated: {timestamp}", style="dim")
        
        return Group(table, footer)

    with Live(generate_ui(), refresh_per_second=1) as live:
        while True:
            await asyncio.sleep(1.0)
            live.update(generate_ui())
