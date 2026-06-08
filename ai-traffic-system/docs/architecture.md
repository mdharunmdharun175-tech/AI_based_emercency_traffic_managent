# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FIELD HARDWARE                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  IP Camera   │  │  Microphone  │  │  GPS (Ambulance) │  │
│  │  (RTSP/USB)  │  │  (Siren det) │  │  Mobile App      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼────────────────┼───────────────────┼─────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│              RASPBERRY PI / EDGE SERVER                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              FastAPI Backend (Python)               │   │
│  │                                                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │  YOLOv8  │  │  Siren   │  │  ANPR (OpenCV    │  │   │
│  │  │ Detection│  │   CNN    │  │  + Tesseract)    │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │         Signal Control Service               │   │   │
│  │  │   Detects lane → Activates green corridor    │   │   │
│  │  └────────────────────┬─────────────────────────┘   │   │
│  └───────────────────────┼─────────────────────────────┘   │
│                          │ Serial (USB)                     │
│  ┌───────────────────────▼──────────────────────────────┐  │
│  │             Arduino UNO                              │  │
│  │   Drives RED/GREEN LEDs for 4 signal lanes           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │ WebSocket / REST API
          ▼
┌─────────────────────────────────────────────────────────────┐
│               WEB DASHBOARD (React.js)                      │
│  Live Camera  │  Signal Status  │  GPS Map  │  Analytics    │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│          MOBILE APP (Flutter / React Native)                │
│   Ambulance driver: route guidance + signal ahead status    │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. Camera → FastAPI `/api/detect`
2. YOLOv8 detects ambulance → confidence ≥ 0.55
3. ANPR extracts plate number
4. Signal service selects lane → sends serial command to Arduino
5. Arduino turns L3 GREEN, others RED
6. WebSocket broadcasts status to dashboard
7. Dashboard updates in real time (<1s latency)

## Hardware Bill of Materials

| Component               | Qty | Notes                         |
|------------------------|-----|-------------------------------|
| Raspberry Pi 4 (4GB)   | 1   | Edge server + camera host     |
| Arduino UNO            | 1   | Signal relay driver           |
| IP Camera (1080p)      | 4   | One per junction              |
| USB Microphone         | 1   | Siren detection               |
| 5V Relay Module (8ch)  | 1   | Drives signal lights          |
| Traffic Signal LEDs    | 16  | Red + Green × 4 lanes         |
| USB-A to USB-B cable   | 1   | Pi → Arduino serial           |
| MicroSD 64GB           | 1   | Pi OS + model weights         |
| Power Supply 5V/3A     | 1   | Pi power                      |

## API Rate Limits (recommended)

| Endpoint            | Rate       |
|--------------------|------------|
| /api/detect        | 10 req/s   |
| /api/detect/stream | 30 req/s   |
| /api/signal-*      | 5 req/s    |
| /api/gps-data      | 10 req/s   |
| /ws                | persistent |
