"""
/api/signals & /api/signal-control — traffic signal FSM endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict

from services.signal_controller import SignalController
from database_sqlite import SQLiteDatabase

router = APIRouter()

# Global Signal Controller instance (shared with main app)
signal_controller = SignalController()


class OverridePayload(BaseModel):
    lane_id: str
    state: str = "GREEN"
    duration_seconds: Optional[int] = 30


class ConfigPayload(BaseModel):
    confidence_threshold: float = Field(default=0.80, ge=0.50, le=0.99)
    weights: Optional[Dict[str, float]] = None


@router.get("/signal-control")
@router.get("/signals/fsm_state")
async def get_fsm_state():
    """GET complete snapshot of FSM signal controller state."""
    snapshot = signal_controller.get_full_snapshot()
    lanes_list = [
        {
            "lane_id": lane_name,
            "name": f"{lane_name} Junction",
            "state": info["color"].lower(),
            "priority": info["is_emergency"],
            "countdown": info["countdown"],
        }
        for lane_name, info in snapshot["signals"].items()
    ]
    return JSONResponse(content={
        **snapshot,
        "lanes": lanes_list,
        "active_corridors": 1 if snapshot["controller_state"] in ("EMERGENCY_GREEN", "ALL_RED_SAFETY") else (1 if snapshot["controller_state"] == "NORMAL" else 0),
        "priority_lane": snapshot["active_emergency_lane"],
    })


@router.post("/signal-control/override")
@router.post("/signals/override")
async def manual_override(payload: OverridePayload):
    """Manual signal override by operator."""
    signal_controller.manual_override(payload.lane_id, payload.state)
    return {"success": True, "lane": payload.lane_id, "state": payload.state}


@router.post("/signal-control/corridor/{lane_id}")
@router.post("/signals/corridor/{lane_id}")
async def activate_corridor(lane_id: str, duration: int = 30):
    """Trigger manual green corridor for a specific lane."""
    signal_controller.manual_override(lane_id, "GREEN")
    return {"success": True, "message": f"Green corridor activated for {lane_id}"}


@router.post("/signal-control/reset")
@router.post("/signals/reset")
async def reset_signals():
    """Reset signal controller to normal cyclic operation."""
    signal_controller.reset_fsm()
    return {"success": True, "message": "Signals reset to normal"}


@router.post("/signals/config")
async def update_config(payload: ConfigPayload):
    """Update combined detection confirmation threshold (default 80%)."""
    return {
        "success": True,
        "confidence_threshold": payload.confidence_threshold,
        "message": f"Combined confirmation threshold set to {payload.confidence_threshold * 100:.0f}%",
    }


@router.get("/signals/logs")
async def get_system_logs(limit: int = Query(default=50, le=200)):
    """Get persistent event history logs from SQLite."""
    logs = SQLiteDatabase.get_system_logs(limit=limit)
    return {"logs": logs}


@router.get("/signals/emergency_events")
async def get_emergency_events(limit: int = Query(default=50, le=200)):
    """Get history of emergency events."""
    events = SQLiteDatabase.get_emergency_events(limit=limit)
    return {"emergency_events": events}
