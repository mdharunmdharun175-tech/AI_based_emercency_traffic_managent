"""
AI Traffic System - FastAPI Backend  (v2.0 — FSM & Simulation Enhanced)
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
from routes.signals   import router as signals_router, signal_controller
from routes.sim       import router as sim_router, camera_simulator
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
from database_sqlite  import SQLiteDatabase

manager       = ConnectionManager()
detection_svc = DetectionService(conf_threshold=0.75)
signal_svc    = SignalService()
density_svc   = TrafficDensityService()

async def on_incident(incident: dict):
    await manager.broadcast_json({"type": "incident_alert", **incident})

accident_svc = AccidentDetectionService(alert_callback=on_incident)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AI Traffic System starting (FSM & 4-Lane Simulation active)…")
    await Database.connect()
    detection_svc.load_model()
    asyncio.create_task(broadcast_loop())
    yield
    await Database.disconnect()
    print("🛑 Shutdown complete")


app = FastAPI(
    title="AI Emergency Traffic Control System",
    description="Real-time ambulance detection, ANPR, FSM signal controller, and 4-lane junction simulation.",
    version="2.0.0",
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
app.include_router(sim_router,       prefix="/api", tags=["Simulation"])
app.include_router(gps_router,       prefix="/api", tags=["GPS"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(alerts_router,    prefix="/api", tags=["Alerts"])
app.include_router(siren_router,     prefix="/api", tags=["Siren"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "AI Emergency Traffic Control System",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "ws":   "/ws",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Return comprehensive system health and hardware interface status."""
    import torch
    device_name = "CUDA GPU" if torch.cuda.is_available() else "CPU"
    return {
        "status": "healthy",
        "ai_model_loaded": detection_svc.model_loaded,
        "execution_device": device_name,
        "active_corridors": 1 if signal_controller.state.value in ("EMERGENCY_GREEN", "ALL_RED_SAFETY") else 0,
        "total_detections": detection_svc.total_detections,
        "uptime_seconds": int(time.time() - detection_svc.start_time),
        "hardware_interface": "software_simulation_mode",
    }


@app.get("/api/status", response_model=SystemStatus, tags=["Root"])
async def system_status():
    return SystemStatus(
        ai_model_loaded=detection_svc.model_loaded,
        active_corridors=1 if signal_controller.state.value in ("EMERGENCY_GREEN", "ALL_RED_SAFETY") else 0,
        total_detections=detection_svc.total_detections,
        uptime_seconds=int(time.time() - detection_svc.start_time),
    )


@app.post("/api/detection/start", tags=["Detection"])
async def start_detection():
    """Enable active camera feed detection pipeline."""
    return {"success": True, "message": "Detection pipeline active", "timestamp": time.time()}


@app.post("/api/detection/stop", tags=["Detection"])
async def stop_detection():
    """Pause camera feed detection pipeline."""
    return {"success": True, "message": "Detection pipeline paused", "timestamp": time.time()}


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
    """Push system status & FSM state to all connected dashboard clients every second."""
    while True:
        await asyncio.sleep(1)
        
        # 1-second FSM tick & camera simulation update
        signal_controller.tick()
        camera_simulator.update_simulation_tick(delta_seconds=1.0)
        
        if not manager.active_connections:
            continue

        fsm_snapshot = signal_controller.get_full_snapshot()
        recent_logs = SQLiteDatabase.get_system_logs(limit=25)

        payload = {
            "type":               "status_update",
            "timestamp":          time.time(),
            "controller_state":   fsm_snapshot["controller_state"],
            "active_green_lane":  fsm_snapshot["active_green_lane"],
            "current_green_remaining": fsm_snapshot["current_green_remaining"],
            "paused_lane":        fsm_snapshot["paused_lane"],
            "paused_remaining":   fsm_snapshot["paused_remaining"],
            "active_emergency_lane": fsm_snapshot["active_emergency_lane"],
            "priority_queue":     fsm_snapshot["priority_queue"],
            "skip_lanes":         fsm_snapshot["skip_lanes"],
            "signals":            fsm_snapshot["signals"],
            "ambulance_detected": len(fsm_snapshot["priority_queue"]) > 0,
            "total_vehicles":     detection_svc.vehicles_in_frame,
            "density":            density_svc.get_density_level(),
            "incidents_today":    accident_svc.incidents_today,
            "total_detections":   detection_svc.total_detections,
            "logs":               recent_logs,
        }
        await manager.broadcast(json.dumps(payload))
