import time
import uuid
import random
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from pathlib import Path

router = APIRouter()

# Load model
MODEL_PATH = Path(__file__).parent.parent.parent / "ml" / "weights" / "best.pt"
if MODEL_PATH.exists():
    _model = YOLO(str(MODEL_PATH))
    print(f"✅ Custom ambulance model loaded")
else:
    _model = YOLO("yolov8n.pt")
    print("⚠️  Using yolov8n.pt — no ambulance class")

CONFIDENCE = 0.15

# COCO vehicle classes only
VEHICLE_IDS = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

# Emergency keywords
EMERGENCY_WORDS = ["ambulance", "fire", "police", "emergency", "rescue"]


def get_vehicle_type(name: str, cls_id: int):
    n = name.lower()
    for w in EMERGENCY_WORDS:
        if w in n:
            vtype = "ambulance" if "amb" in n or "emergency" in n or "rescue" in n else \
                    "police"    if "police" in n or "cop" in n else \
                    "fire_engine"
            return vtype, True
    return VEHICLE_IDS.get(cls_id, None), False


def process_frame(frame: np.ndarray):
    t0      = time.perf_counter()
    H, W    = frame.shape[:2]
    results = _model(frame, conf=CONFIDENCE, verbose=False)[0]

    vehicles           = []
    ambulance_detected = False
    ambulance_plate    = None

    for box in results.boxes:
        cls_id     = int(box.cls[0])
        conf       = float(box.conf[0])
        x1,y1,x2,y2 = map(int, box.xyxy[0])
        class_name = _model.names.get(cls_id, "unknown")

        vtype, is_emg = get_vehicle_type(class_name, cls_id)
        if vtype is None:
            continue  # skip non-vehicles

        if is_emg and "ambulance" in vtype:
            ambulance_detected = True
            ambulance_plate    = "KA-05-MK-4822"

        vehicles.append({
            "id":           str(uuid.uuid4())[:8],
            "type":         vtype,
            "confidence":   round(conf, 3),
            "bbox":         {"x": x1, "y": y1, "width": x2-x1, "height": y2-y1},
            "is_emergency": is_emg,
            "plate_number": ambulance_plate if is_emg else None,
        })

    # ── DEMO MODE ──────────────────────────────────────────
    # Randomly inject ambulance box so signals can be tested
    # Remove this block after training real ambulance model
    if random.random() < 0.07 and len(vehicles) > 1:
        aw = W // 4
        ah = H // 5
        ax = W // 2 - aw // 2
        ay = H // 2 - ah // 2
        vehicles.append({
            "id":           "demo-amb",
            "type":         "ambulance",
            "confidence":   0.94,
            "bbox":         {"x": ax, "y": ay, "width": aw, "height": ah},
            "is_emergency": True,
            "plate_number": "KA-05-MK-4822",
        })
        ambulance_detected = True
        ambulance_plate    = "KA-05-MK-4822"
    # ── END DEMO MODE ──────────────────────────────────────

    ms = round((time.perf_counter() - t0) * 1000, 1)
    return vehicles, ambulance_detected, ambulance_plate, ms


@router.post("/detect")
async def detect_vehicles(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(422, "Cannot decode image")

    vehicles, amb, plate, ms = process_frame(frame)
    return JSONResponse(content={
        "frame_id":           str(uuid.uuid4()),
        "timestamp":          time.time(),
        "vehicles":           vehicles,
        "vehicle_count":      len(vehicles),
        "ambulance_detected": amb,
        "ambulance_plate":    plate,
        "processing_time_ms": ms,
    })


@router.post("/detect/stream")
async def detect_stream(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return JSONResponse(content={"vehicle_count":0,"ambulance_detected":False,"vehicles":[],"processing_time_ms":0})
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse(content={"vehicle_count":0,"ambulance_detected":False,"vehicles":[],"processing_time_ms":0})

    vehicles, amb, plate, ms = process_frame(frame)
    return JSONResponse(content={
        "vehicle_count":      len(vehicles),
        "ambulance_detected": amb,
        "ambulance_plate":    plate,
        "vehicles":           vehicles,
        "processing_time_ms": ms,
    })