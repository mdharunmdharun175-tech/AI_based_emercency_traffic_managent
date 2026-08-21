"""
/api/sim — Camera Simulation & Multi-Feature Ambulance Spawner Endpoints
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from routes.signals import signal_controller
from services.camera_simulator import CameraSimulator

router = APIRouter()

# Global Camera Simulator instance
camera_simulator = CameraSimulator(signal_controller=signal_controller)


class SpawnAmbulancePayload(BaseModel):
    lane_id: str = "Lane B"
    distance: float = Field(default=150.0, ge=10.0, le=300.0)
    confidence: float = Field(default=0.88, ge=0.5, le=1.0)
    plate: Optional[str] = ""
    roof_lights: bool = True
    text_detected: bool = True
    symbol_detected: bool = True
    symbol_name: str = "Red Cross"
    shape_verified: bool = True


class PassAmbulancePayload(BaseModel):
    tracking_id: str


@router.post("/sim/spawn")
async def spawn_ambulance(payload: SpawnAmbulancePayload):
    """Spawn a simulated ambulance on a specified lane with multi-feature visual attributes."""
    camera_simulator.spawn_ambulance(
        lane_id=payload.lane_id,
        initial_distance=payload.distance,
        confidence=payload.confidence,
        plate=payload.plate or "",
        roof_lights=payload.roof_lights,
        text_detected=payload.text_detected,
        symbol_detected=payload.symbol_detected,
        symbol_name=payload.symbol_name,
        shape_verified=payload.shape_verified,
    )
    return {
        "success": True,
        "lane": payload.lane_id,
        "distance": payload.distance,
        "confidence": payload.confidence,
        "combined_score": payload.confidence,
        "roof_lights": payload.roof_lights,
        "text_detected": payload.text_detected,
        "symbol_detected": payload.symbol_detected,
        "symbol_name": payload.symbol_name,
        "message": f"Multi-Feature Ambulance spawned on {payload.lane_id} at {payload.distance}m (Score: {payload.confidence*100:.0f}%)",
    }


@router.post("/sim/pass")
async def pass_ambulance(payload: PassAmbulancePayload):
    """Manually trigger stop-line crossing for an ambulance tracking ID."""
    signal_controller.mark_ambulance_passed(payload.tracking_id)
    return {"success": True, "message": f"Ambulance {payload.tracking_id} marked as passed virtual stop line"}


async def mjpeg_frame_generator(lane_id: str):
    """Generates MJPEG video stream frames for a specific lane."""
    while True:
        try:
            jpg_bytes = camera_simulator.get_jpeg_bytes(lane_id)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n")
            await asyncio.sleep(0.1)  # ~10 FPS for video stream
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.2)


@router.get("/sim/feed/{lane_id}")
async def lane_feed(lane_id: str):
    """Return live MJPEG video stream for Lane A, Lane B, Lane C, or Lane D."""
    norm_lane = signal_controller._norm_lane(lane_id)
    return StreamingResponse(
        mjpeg_frame_generator(norm_lane),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
