# 🚑 AI-Powered Ambulance Detection & Smart Traffic Signal Control Software

A production-ready, modular, and scalable software system built with **Python**, **YOLOv8/v11**, **OpenCV**, **EasyOCR**, **FastAPI**, **SQLite**, and **React** for real-time ambulance detection, multi-vehicle tracking, and dynamic green corridor traffic signal control.

---

## 🎯 Architecture Diagram

```
                             ┌──────────────────────────────────────────────┐
                             │       Traffic Camera Video Feeds             │
                             │ (Webcam, CCTV, RTSP Streams, MP4 Files)      │
                             └──────────────────────┬───────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FASTAPI BACKEND SYSTEM                                        │
│                                                                                                 │
│  ┌───────────────────────┐   ┌────────────────────────────────┐   ┌──────────────────────────┐  │
│  │   Object Detection    │   │ Multi-Feature Verification     │   │   ByteTrack / IOU MOT    │  │
│  │ (YOLOv8/v11 Ensemble) ├──►│  Engine (Roof Siren + OCR      ├──►│     Vehicle Tracker      │  │
│  │                       │   │  Text + Cross + Van Shape)     │   │  (Unique IDs & Traj)     │  │
│  └───────────────────────┘   └────────────────────────────────┘   └────────────┬─────────────┘  │
│                                                                                │                │
│  ┌───────────────────────┐   ┌────────────────────────────────┐                │                │
│  │    SQLite Database    │   │ Traffic Signal FSM Controller  │◄──────────────┘                │
│  │ (Detections & Events) │◄──┤ (North → East → South → West)  │                                 │
│  └───────────────────────┘   └────────────────────────────────┘                                 │
└───────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                            │ WebSocket / REST API
                                            ▼
                             ┌──────────────────────────────────────────────┐
                             │           REACT DASHBOARD FRONTEND           │
                             │ (4-Channel Intersection Feeds, Signals, HUD) │
                             └──────────────────────────────────────────────┘
```

---

## 📂 Modular Folder Structure

```
ai-traffic-system/
├── backend/
│   ├── main.py                  # FastAPI entry point & lifespan manager
│   ├── database_sqlite.py       # SQLite database engine (6 tables & CSV export)
│   ├── config.py                # Environment configuration & threshold tokens
│   ├── requirements.txt         # Python dependencies
│   ├── routes/                  # REST API endpoints
│   │   ├── detect.py            # Image & video detection API
│   │   ├── signals.py           # Signal controller FSM API
│   │   ├── sim.py               # 4-channel intersection simulator & MJPEG streams
│   │   ├── analytics.py         # Dashboard analytics & CSV log exporter
│   │   ├── alerts.py            # Event alerts API
│   │   ├── siren.py             # Acoustic siren detection API
│   │   └── gps.py               # Live GPS updates API
│   ├── services/                # Core business logic services
│   │   ├── detection_service.py # YOLO ensemble detection pipeline
│   │   ├── ambulance_tracker.py # 6-feature verification engine & ByteTrack MOT
│   │   ├── signal_controller.py # Priority queue & dynamic preemption FSM
│   │   └── camera_simulator.py  # 4-channel intersection frame renderer
│   └── tests/                   # Automated pytest suite (19 test cases)
├── frontend/                    # React dashboard frontend
│   ├── src/
│   │   ├── pages/               # Dashboard, CameraFeeds, SignalControl, Logs pages
│   │   ├── components/          # Visual components & simulation controls
│   │   └── main.jsx             # React entry point
│   └── package.json             # NPM dependencies & scripts
├── ml/                          # Machine learning weights & training pipelines
│   ├── weights/                 # Fine-tuned model weights (best.pt)
│   └── train.py                 # Training script
└── docs/                        # Project architecture & API specifications
```

---

## ⚡ Key Features

1. **Multi-Feature Ambulance Detection Engine**:
   - High-preference verification combining **Roof Siren Flasher Lights** ($30\%$), **"AMBULANCE" / "ECNALUBMA" Name Board OCR** ($25\%$), **Van Shape Profile** ($15\%$), **YOLO Baseline** ($15\%$), **Medical Symbol** ($10\%$), and **ANPR Plate** ($5\%$).
   - Rejects false positives on ordinary cars, sedans, SUVs, and hatchbacks.

2. **Visual Bounding Box Distinction**:
   - **ONLY the verified Ambulance** is drawn in **BRIGHT RED (`#ff0000`)** with red crosshairs and a bold `🚨 AMBULANCE [SCORE%]` badge.
   - Standard traffic vehicles (**Car**, **Truck**, **Bus**, **Motorcycle**) use clean, subtle outlines.

3. **Dynamic Signal Preemption & Stop-Line Tracking**:
   - When an ambulance is detected on any lane, the signal controller instantly pauses circular rotation (North $\rightarrow$ East $\rightarrow$ South $\rightarrow$ West), enters **All-Red Safety (2s)**, and holds **GREEN** on the emergency lane indefinitely until the ambulance crosses the virtual stop line ($y = 85\%$).
   - Upon passage, the saved countdown resumes automatically.

4. **Concurrent 4-Lane Real-Time AI Detection**:
   - Processes all 4 junction feeds (**CAM-01**, **CAM-02**, **CAM-03**, **CAM-04**) concurrently in real-time.

5. **SQLite Persistence & CSV Log Exporter**:
   - Stores detection history, emergency events, signal transitions, distance tracking, and system logs.
   - One-click CSV log download via `/api/logs/export`.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Launch FastAPI Backend
```bash
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Launch React Frontend
```bash
cd frontend
npm install
npm run dev
```
- **Dashboard URL**: [http://localhost:3000](http://localhost:3000)

---

## 🔌 Core REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/detect` | Run detection on uploaded frame/image |
| `POST` | `/api/detect/stream` | Stream real-time frame detection |
| `GET` | `/api/signals/fsm_state` | Fetch full FSM signal state & priority queue |
| `POST` | `/api/signals/manual_override` | Manually switch signal to GREEN for specified lane |
| `POST` | `/api/sim/spawn` | Spawn simulated multi-feature ambulance |
| `POST` | `/api/sim/pass` | Trigger virtual stop line crossing event |
| `GET` | `/api/sim/feed/{lane_id}` | Live MJPEG stream for Lane A, B, C, or D |
| `GET` | `/api/analytics/summary` | Fetch dashboard performance stats |
| `GET` | `/api/logs/export` | Download event logs as CSV file |

---

## 🧪 Automated Testing

To run the complete test suite:
```bash
cd backend
.\venv\Scripts\pytest tests/test_multi_feature_verification.py tests/test_api.py
```
*(All 19 test cases pass 100% cleanly).*
