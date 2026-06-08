"""
/api/gps-data — GPS tracking endpoints
Receives position updates from ambulance mobile app and stores them.
"""

import time
import uuid
from typing import List
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models.schemas import GPSPosition

router = APIRouter()

# In-memory store (replace with MongoDB in production)
_positions: dict = {}


@router.get("/gps-data")
async def get_all_positions():
    """Return latest GPS position of all tracked vehicles."""
    return JSONResponse(content={"vehicles": list(_positions.values())})


@router.get("/gps-data/{vehicle_id}")
async def get_vehicle_position(vehicle_id: str):
    if vehicle_id not in _positions:
        return JSONResponse(content={"error": "Vehicle not found"}, status_code=404)
    return JSONResponse(content=_positions[vehicle_id])


@router.post("/gps-data")
async def update_position(position: GPSPosition):
    """Ambulance app posts its GPS position here every second."""
    _positions[position.vehicle_id] = {
        **position.dict(),
        "last_updated": time.time(),
    }
    return {"success": True}


@router.delete("/gps-data/{vehicle_id}")
async def remove_vehicle(vehicle_id: str):
    _positions.pop(vehicle_id, None)
    return {"success": True}
