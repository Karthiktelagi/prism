# 🚀 PRISM — Predictive Risk Intelligence & Sensor Monitor

PRISM is a production-grade, asynchronous Python-based predictive maintenance platform for **real-time CNC machine monitoring, anomaly detection, and risk intelligence**.

It simulates an industrial monitoring environment by collecting machine sensor data, detecting abnormal behavior, and providing actionable operational insights through an interactive dashboard.

---

## ✨ Features

- 📡 Real-time sensor monitoring  
- ⚠️ Anomaly detection using statistical methods (IQR / CUSUM)  
- 🧠 Predictive risk intelligence engine  
- 📊 Interactive monitoring dashboard  
- 🔄 Asynchronous Python architecture  
- 🏭 Multi-machine CNC monitoring simulation  
- 📈 Live operational insights and alerts

---

## 🏗️ System Architecture

```text
Sensors/Data Sources
       ↓
Data Ingestion Layer
       ↓
Anomaly Detection Engine
       ↓
Risk Intelligence Engine
       ↓
Dashboard + Alerts
```

---

## 📂 Project Structure

```text
prism/
│
├── main.py                # Application entry point
├── requirements.txt       # Dependencies
├── dashboard/             # Monitoring dashboard
├── data/                  # Sensor datasets
├── models/                # Detection logic / analytics
├── utils/                 # Helper modules
└── README.md
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/Karthiktelagi/prism.git
cd prism
```

---

### 2. Create Virtual Environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac
```bash
python -m venv venv
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables (Optional)

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your-api-key"
```

---

## ▶️ Run the Application

```bash
python main.py
```

---

## 🌐 Access Dashboard

After starting:

```text
http://localhost:8000/dashboard
```
## 📸 Dashboard Preview

PRISM provides a real-time predictive maintenance dashboard for monitoring CNC machines, sensor health, anomaly detection, and risk intelligence.

### Features Shown
- Live machine monitoring  
- Risk score visualization  
- Temperature, Vibration, Speed and Current metrics  
- Normal / Watch / Alert / Critical states  
- Real-time operational alerts  
- Machine-level health summaries  

![PRISM Dashboard](https://raw.githubusercontent.com/Karthiktelagi/prism/main/dashboard.png)
---

## 📊 Use Cases

- Predictive Maintenance  
- Industrial IoT Monitoring  
- CNC Machine Health Analysis  
- Sensor-Based Risk Detection  
- Smart Manufacturing Research

---

## 🛠 Tech Stack

- Python  
- Asyncio  
- Streamlit / Dashboard  
- Statistical Anomaly Detection  
- Machine Monitoring Simulation

---

## 🚀 Deployment

Can be deployed using:

- Streamlit Cloud  
- Render  
- Railway  
- Hugging Face Spaces

---

## 👨‍💻 Author

**Karthik TS, Dhanushree G , Greeshma**  
Cybersecurity & AI Enthusiast 
GitHub: https://github.com/Karthiktelagi

---

## 📜 License

MIT License
