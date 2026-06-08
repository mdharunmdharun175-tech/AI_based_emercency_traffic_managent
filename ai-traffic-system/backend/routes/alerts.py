"""
/api/alerts — system alert management
"""

import time
import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models.database import get_alerts, save_alert

router = APIRouter()

# In-memory fallback
_alerts = []


@router.get("/alerts")
async def list_alerts(limit: int = 50, unread_only: bool = False):
    db_alerts = await get_alerts(limit=limit, unread_only=unread_only)
    if db_alerts:
        return JSONResponse(content={"alerts": db_alerts})
    # Fallback to in-memory
    alerts = _alerts if not unread_only else [a for a in _alerts if not a.get("acknowledged")]
    return JSONResponse(content={"alerts": alerts[-limit:]})


@router.post("/alerts")
async def create_alert(alert_type: str, message: str):
    entry = {
        "id": str(uuid.uuid4()),
        "type": alert_type,
        "message": message,
        "timestamp": time.time(),
        "acknowledged": False,
    }
    _alerts.append(entry)
    await save_alert(alert_type, message)
    return JSONResponse(content=entry)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    for a in _alerts:
        if a.get("id") == alert_id:
            a["acknowledged"] = True
            return {"success": True}
    return JSONResponse(content={"error": "Alert not found"}, status_code=404)


@router.delete("/alerts")
async def clear_alerts():
    _alerts.clear()
    return {"success": True, "message": "All alerts cleared"}
