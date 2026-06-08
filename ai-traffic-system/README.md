# 🚑 AI-Based Smart Emergency Vehicle Detection & Traffic Signal Control System

A full-stack intelligent traffic management system that detects ambulances using YOLOv8, controls traffic signals in real-time, and provides a live monitoring dashboard.

## 📁 Project Structure

```
ai-traffic-system/
├── frontend/          # React.js dashboard (Vite)
├── backend/           # FastAPI server + AI integration
├── ml/                # YOLOv8 training scripts
├── mobile/            # React Native ambulance driver app
├── scripts/           # Setup & utility scripts
└── docs/              # Architecture & API docs
```

## 🚀 Quick Start

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. ML Model Training
```bash
cd ml
pip install ultralytics
python train.py
```

## 🛠️ Tech Stack
- **AI/ML**: YOLOv8, OpenCV, TensorFlow, Librosa
- **Backend**: FastAPI, WebSockets, Python 3.10+
- **Frontend**: React.js, Tailwind CSS, Chart.js
- **Database**: MongoDB
- **Hardware**: Arduino/Raspberry Pi for signal control
- **Maps**: Google Maps API

## 🔌 API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/detect` | Upload frame for vehicle detection |
| GET | `/signal-control` | Get current signal states |
| POST | `/signal-control` | Override signal manually |
| GET | `/gps-data` | Get live GPS positions |
| WS | `/ws` | WebSocket for real-time updates |

## 📡 Hardware Setup
See `docs/hardware_setup.md` for Arduino/Raspberry Pi wiring diagrams.


how to run ?

first backend....

cd d:\Projects\ai-traffic-system\ai-traffic-system\backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000


next video stream  ......

cd D:\Projects\ai-traffic-system\ai-traffic-system\scripts

python rpi_camera_stream.py --api http://localhost:8000 --camera "C:\Users\Dharun kumar\Downloads\3800731-hd_1920_1080_25fps.mp4" --fps 10


next front ennd ....

cd d:\Projects\ai-traffic-system\ai-traffic-system\frontend
npm run dev
