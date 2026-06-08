"""
/api/signal-control — traffic signal management endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services.signal_service import SignalService
from models.schemas import SignalOverride

router = APIRouter()
_signal_svc = SignalService()


@router.get("/signal-control")
async def get_signal_states():
    """GET current state of all lane signals."""
    return JSONResponse(content={
        "lanes": _signal_svc.get_all_states(),
        "active_corridors": _signal_svc.active_corridors(),
        "priority_lane": _signal_svc._priority_lane,
    })


@router.post("/signal-control/corridor/{lane_id}")
async def activate_corridor(lane_id: str, duration: int = 30):
    """Activate green corridor for a specific lane."""
    try:
        _signal_svc.activate_corridor(lane_id, duration)
        return {"success": True, "message": f"Green corridor activated for {lane_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signal-control/override")
async def manual_override(payload: SignalOverride):
    """Manual signal override by dashboard operator."""
    try:
        _signal_svc.manual_override(payload.lane_id, payload.state.value, payload.duration_seconds)
        return {"success": True, "lane": payload.lane_id, "state": payload.state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signal-control/reset")
async def reset_signals():
    """Reset all signals to normal cyclic operation."""
    _signal_svc.reset_to_normal()
    return {"success": True, "message": "Signals reset to normal"}
