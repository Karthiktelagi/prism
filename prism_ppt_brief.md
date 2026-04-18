# PRISM — PPT Brief Explanation

---

## Slide 1: Title
**PRISM**
**Predictive Risk Intelligence & Sensor Monitor**
> Real-time AI-powered monitoring for industrial CNC machines
*Team ByteForge | Hack Malenadu '26*

---

## Slide 2: The Problem
- Industrial machines (CNC, Pumps, Conveyors) fail **without warning**
- Failures cause **costly downtime**, safety risks, and production loss
- Manual monitoring is **slow, error-prone, and not real-time**
- Operators often miss early warning signs buried in sensor data

---

## Slide 3: Our Solution — PRISM
PRISM is an **AI-powered real-time monitoring system** that:
- 📡 Reads **live sensor data** from machines every second
- 🧠 Detects **anomalies** automatically using statistics
- ⚠️ Scores **risk from 0–100** for each machine
- 🤖 Generates **AI explanations** in plain English (powered by Claude)
- 🔔 **Alerts operators** and schedules maintenance automatically

---

## Slide 4: How It Works (Simple Flow)
```
SENSOR DATA → DETECT ANOMALY → SCORE RISK → AI EXPLAINS → ALERT
```
1. **Sensor Streams** — 4 sensors per machine (Temp, Vibration, RPM, Current)
2. **Anomaly Detection** — Spots sudden spikes and slow drifts
3. **Risk Score** — 0 (safe) to 100 (critical failure imminent)
4. **Claude AI** — Tells you what's wrong and what to do
5. **Auto Action** — Sends alerts, schedules maintenance

---

## Slide 5: Key Features
| Feature | What It Does |
|---|---|
| 🔴 Real-Time Monitoring | Live sensor data every second |
| 📊 Statistical Baselines | Learns normal behavior per machine |
| 🚨 Smart Alerting | Alerts only when risk > 60, with 60s cooldown |
| 🤖 AI Diagnosis | Plain-English explanation of every fault |
| 🌐 Web Dashboard | Browser-based UI for operators & managers |
| 💾 Persistent Logs | 7-day alert history in SQLite |
| 🔐 Role-Based Access | Separate operator and manager logins |

---

## Slide 6: Risk Levels
| Score | Level | Action |
|---|---|---|
| 0–39 | 🟢 NORMAL | Monitor |
| 40–59 | 🟡 WATCH | Keep an eye |
| 60–79 | 🟠 ALERT | Alert sent |
| 80–100 | 🔴 CRITICAL | Alert + Maintenance scheduled |

---

## Slide 7: Dashboards
**Two interfaces:**

**Terminal Dashboard** — Live table in the terminal showing all 4 machines with current sensor values, risk score, level, and AI explanation

**Web Dashboard** — Browser-based at `localhost:7860`
- **Operator View** — Real-time sensor graphs and machine status
- **Manager View** — Alert history, acknowledge alerts, export CSV, schedule maintenance

---

## Slide 8: Tech Stack
| Layer | Technology |
|---|---|
| Language | Python (async/await) |
| Sensor Streaming | SSE (Server-Sent Events) + aiohttp |
| Anomaly Detection | NumPy + Pandas (IQR, z-score, drift) |
| AI Explanations | Claude Haiku (Anthropic API) |
| Web Server | FastAPI + Uvicorn |
| Terminal UI | Rich library |
| Database | SQLite (alerts + sessions) |
| Backend API | Hack Malenadu REST API |

---

## Slide 9: Machines Monitored
- **CNC_01** — CNC Milling Machine
- **CNC_02** — CNC Milling Machine
- **PUMP_03** — Industrial Pump
- **CONVEYOR_04** — Conveyor Belt

**4 Sensors per Machine:** Temperature (°C), Vibration (mm/s), RPM, Current (A)

---

## Slide 10: Impact
- ✅ **Prevents unplanned downtime** by catching faults early
- ✅ **Reduces human error** with automated anomaly detection
- ✅ **Saves time** — AI explains the fault so engineers don't have to guess
- ✅ **Scalable** — works for any number of machines
- ✅ **Production-ready** — handles reconnects, noisy data, and server restarts
