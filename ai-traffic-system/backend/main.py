"""
AI Traffic System - FastAPI Backend  (v1.0 — full build)
Entry point: uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes.detect    import router as detect_router
from routes.signals   import router as signals_router
from routes.gps       import router as gps_router
from routes.analytics import router as analytics_router
from routes.alerts    import router as alerts_router
from routes.siren     import router as siren_router
from services.connection_manager import ConnectionManager
from services.detection_service  import DetectionService
from services.signal_service     import SignalService
from services.density_service    import TrafficDensityService
from services.accident_service   import AccidentDetectionService
from models.database  import Database
from models.schemas   import SystemStatus

manager       = ConnectionManager()
detection_svc = DetectionService()
signal_svc    = SignalService()
density_svc   = TrafficDensityService()

async def on_incident(incident: dict):
    await manager.broadcast_json({"type": "incident_alert", **incident})

accident_svc = AccidentDetectionService(alert_callback=on_incident)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AI Traffic System starting…")
    await Database.connect()
    detection_svc.load_model()
    asyncio.create_task(broadcast_loop())
    yield
    await Database.disconnect()
    print("🛑 Shutdown complete")


app = FastAPI(
    title="AI Emergency Traffic Control System",
    description="Real-time ambulance detection, ANPR, siren classification and smart signal control.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect_router,    prefix="/api", tags=["Detection"])
app.include_router(signals_router,   prefix="/api", tags=["Signals"])
app.include_router(gps_router,       prefix="/api", tags=["GPS"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(alerts_router,    prefix="/api", tags=["Alerts"])
app.include_router(siren_router,     prefix="/api", tags=["Siren"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "AI Emergency Traffic Control System",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "ws":   "/ws",
    }


@app.get("/api/status", response_model=SystemStatus, tags=["Root"])
async def system_status():
    return SystemStatus(
        ai_model_loaded=detection_svc.model_loaded,
        active_corridors=signal_svc.active_corridors(),
        total_detections=detection_svc.total_detections,
        uptime_seconds=int(time.time() - detection_svc.start_time),
    )


@app.get("/api/density", tags=["Analytics"])
async def traffic_density():
    return {
        "lane_stats": density_svc.get_lane_stats(),
        "forecast":   density_svc.get_congestion_forecast(),
        "overall":    density_svc.get_density_level(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": time.time()}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_loop():
    """Push system status to all connected dashboard clients every second."""
    while True:
        await asyncio.sleep(1)
        if not manager.active_connections:
            continue
        payload = {
            "type":               "status_update",
            "timestamp":          time.time(),
            "ambulance_detected": detection_svc.last_detection_was_ambulance,
            "active_corridors":   signal_svc.active_corridors(),
            "signal_states":      signal_svc.get_all_states(),
            "total_vehicles":     detection_svc.vehicles_in_frame,
            "density":            density_svc.get_density_level(),
            "incidents_today":    accident_svc.incidents_today,
            "total_detections":   detection_svc.total_detections,
        }
        await manager.broadcast(json.dumps(payload))
