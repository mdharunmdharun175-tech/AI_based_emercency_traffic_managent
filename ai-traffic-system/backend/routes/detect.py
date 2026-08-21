"""
/api/detect — Image & Video Frame Detection Endpoint using Multi-Feature Pipeline
"""

import time
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.detection_service import DetectionService

router = APIRouter()

# Global DetectionService instance
detection_svc = DetectionService(conf_threshold=0.75)
detection_svc.load_model()


@router.post("/detect")
async def detect_vehicles(file: UploadFile = File(...)):
    """Run multi-feature ambulance detection on uploaded image file."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(422, "Cannot decode image")

    result = detection_svc.detect_from_frame(frame, lane_id="Lane A")
    return JSONResponse(content=result)


@router.post("/detect/stream")
async def detect_stream(file: UploadFile = File(...)):
    """Run real-time multi-feature detection on video frame stream."""
    data = await file.read()
    if not data:
        return JSONResponse(content={"vehicle_count": 0, "ambulance_detected": False, "vehicles": [], "processing_time_ms": 0})
    
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse(content={"vehicle_count": 0, "ambulance_detected": False, "vehicles": [], "processing_time_ms": 0})

    result = detection_svc.detect_from_frame(frame, lane_id="Lane A")
    return JSONResponse(content=result)