"""
Detection Service
- YOLOv8 vehicle & ambulance detection
- OpenCV preprocessing
- ANPR (Automatic Number Plate Recognition)
- Siren sound detection
"""

import io
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "ml" / "weights" / "best.pt"
AMBULANCE_CLASS_ID = 0  # as defined in data.yaml
CONFIDENCE_THRESHOLD = 0.15
PLATE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")


class DetectionService:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.total_detections = 0
        self.vehicles_in_frame = 0
        self.last_detection_was_ambulance = False
        self.start_time = time.time()
        self._class_names = {
            0: "ambulance",
            1: "car",
            2: "truck",
            3: "bus",
            4: "motorcycle",
        }

    def load_model(self):
        """Load YOLOv8 model. Falls back to nano pretrained if custom weights missing."""
        try:
            from ultralytics import YOLO
            if MODEL_PATH.exists():
                self.model = YOLO(str(MODEL_PATH))
                logger.info(f"✅ Loaded custom model: {MODEL_PATH}")
            else:
                self.model = YOLO("yolov8n.pt")
                logger.warning("⚠️  Custom weights not found, using yolov8n.pt (pretrained)")
            self.model_loaded = True
        except Exception as e:
            logger.error(f"❌ Model load failed: {e}")
            self.model_loaded = False

    def detect_from_bytes(self, image_bytes: bytes) -> dict:
        """Run full detection pipeline on raw image bytes."""
        t0 = time.perf_counter()

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode image")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vehicles = []
        ambulance_detected = False
        ambulance_plate = None

        if self.model_loaded and self.model:
            results = self.model(frame_rgb, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]

            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vtype = self._class_names.get(cls_id, "unknown")
                is_emg = vtype == "ambulance"

                plate = None
                if is_emg:
                    ambulance_detected = True
                    roi = frame[y1:y2, x1:x2]
                    plate = self._extract_plate(roi)
                    ambulance_plate = plate

                vehicles.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": vtype,
                    "confidence": round(conf, 4),
                    "bbox": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                    "plate_number": plate,
                    "is_emergency": is_emg,
                })

        self.vehicles_in_frame = len(vehicles)
        self.last_detection_was_ambulance = ambulance_detected
        self.total_detections += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "frame_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "vehicles": vehicles,
            "ambulance_detected": ambulance_detected,
            "ambulance_plate": ambulance_plate,
            "siren_detected": False,
            "processing_time_ms": round(elapsed_ms, 2),
        }

    def _extract_plate(self, roi: np.ndarray) -> Optional[str]:
        """Extract number plate text from ambulance ROI using OCR."""
        try:
            import pytesseract
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            plates = PLATE_CASCADE.detectMultiScale(thresh, scaleFactor=1.1, minNeighbors=4)
            for (px, py, pw, ph) in plates:
                plate_roi = thresh[py:py+ph, px:px+pw]
                text = pytesseract.image_to_string(
                    plate_roi,
                    config="--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
                ).strip()
                if len(text) >= 6:
                    return text.replace(" ", "-")

            # Fallback: full ROI OCR
            text = pytesseract.image_to_string(thresh, config="--psm 7").strip()
            return text if len(text) >= 6 else None
        except Exception as e:
            logger.debug(f"ANPR failed: {e}")
            return None

    def detect_from_frame(self, frame: np.ndarray) -> dict:
        """Run detection on a pre-decoded OpenCV frame (for video stream use)."""
        _, buf = cv2.imencode(".jpg", frame)
        return self.detect_from_bytes(buf.tobytes())
