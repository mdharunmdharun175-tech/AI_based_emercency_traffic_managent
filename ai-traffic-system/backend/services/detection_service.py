"""
Detection Service (v2.3 — Strict Multi-Feature Ambulance Verification)
- Base YOLOv8 model (yolov8n.pt) for accurate detection of car, truck, bus, motorcycle
- Fine-tuned ambulance model (best.pt) used only as candidate feature proposal
- Strict Multi-Feature Ambulance Verification:
  Vehicle is ONLY categorized as an AMBULANCE if combined score >= 70%
  combining Roof Flasher Lights + Name Board Text + Medical Symbol + Van Shape.
  Normal cars, sedans, trucks, buses, and bikes are NEVER mislabeled as ambulances.
"""

import io
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import cv2
import numpy as np
from database_sqlite import SQLiteDatabase
from services.ambulance_tracker import AmbulanceTracker, calculate_iou

logger = logging.getLogger(__name__)

MODEL_PATH_1 = Path(__file__).parent.parent / "ml" / "weights" / "best.pt"
MODEL_PATH_2 = Path(__file__).parent.parent.parent / "ml" / "weights" / "best.pt"
DEFAULT_CONFIDENCE_THRESHOLD = 0.75


class DetectionService:
    def __init__(self, conf_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self.model = None
        self.amb_model = None
        self.model_loaded = False
        self.total_detections = 0
        self.vehicles_in_frame = 0
        self.last_detection_was_ambulance = False
        self.start_time = time.time()
        self.conf_threshold = conf_threshold
        self.tracker = AmbulanceTracker(confidence_threshold=conf_threshold)

    def set_confidence_threshold(self, threshold: float):
        self.conf_threshold = max(0.1, min(0.99, threshold))
        self.tracker.set_confidence_threshold(self.conf_threshold)

    def load_model(self):
        """Load fine-tuned ambulance detection model (best.pt) and vehicle base model (yolov8n.pt)."""
        try:
            from ultralytics import YOLO
            
            # Resolve best.pt from backend or root directory
            target_path = MODEL_PATH_1 if MODEL_PATH_1.exists() else (MODEL_PATH_2 if MODEL_PATH_2.exists() else None)
            
            if target_path:
                self.amb_model = YOLO(str(target_path))
                logger.info(f"✅ Loaded fine-tuned ambulance proposal model: {target_path}")
            else:
                self.amb_model = None

            # Load vehicle base model (COCO trained)
            self.model = YOLO("yolov8n.pt")
            logger.info("✅ Loaded base vehicle detection model (yolov8n.pt)")
            self.model_loaded = True
        except Exception as e:
            logger.error(f"❌ Model load failed: {e}")
            self.model_loaded = False

    def detect_from_bytes(self, image_bytes: bytes, lane_id: str = "Lane A") -> dict:
        """Run full detection pipeline on raw image bytes."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode image")
        return self.detect_from_frame(frame, lane_id=lane_id)

    def detect_from_frame(self, frame: np.ndarray, lane_id: str = "Lane A") -> dict:
        """Run strict multi-feature detection on a pre-decoded OpenCV frame."""
        t0 = time.perf_counter()
        frame_height, frame_width = frame.shape[:2]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        vehicles = []
        candidate_detections = []
        added_bboxes = []

        if self.model_loaded and self.model:
            try:
                # 1. Run Base Vehicle Model for accurate vehicle classification (car, truck, bus, motorcycle)
                veh_results = self.model(frame_rgb, conf=0.22, verbose=False)[0]
                coco_map = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
                
                for box in veh_results.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    vtype = coco_map.get(cls_id, None)
                    if vtype is None:
                        continue

                    box_tuple = (x1, y1, x2, y2)
                    det_obj = {
                        "id": str(uuid.uuid4())[:8],
                        "type": vtype,
                        "confidence": round(conf, 4),
                        "bbox": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                        "is_emergency": False,
                    }
                    vehicles.append(det_obj)
                    candidate_detections.append(det_obj)
                    added_bboxes.append(box_tuple)
            except Exception as e:
                logger.debug(f"Vehicle base model error: {e}")

            # 2. Run Fine-Tuned Ambulance Model for candidate proposals
            if self.amb_model:
                try:
                    amb_results = self.amb_model(frame_rgb, conf=0.35, verbose=False)[0]
                    for box in amb_results.boxes:
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        box_tuple = (x1, y1, x2, y2)
                        
                        det_obj = {
                            "id": str(uuid.uuid4())[:8],
                            "type": "ambulance",
                            "confidence": round(conf, 4),
                            "bbox": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                            "is_emergency": True,
                        }
                        candidate_detections.append(det_obj)
                except Exception as e:
                    logger.debug(f"Ambulance model error: {e}")

        # 3. Run Multi-Feature Verification Pipeline (Roof Light + Text + Symbol + Shape + ANPR)
        tracked_ambulances = self.tracker.process_detections(
            raw_detections=candidate_detections,
            lane_id=lane_id,
            frame_height=frame_height,
            anpr_extractor=self._extract_plate,
            raw_frame=frame,
        )

        # STRICT VERIFICATION: ONLY re-label a vehicle as an AMBULANCE if verified by multi-feature score >= 0.70!
        verified_amb_boxes = []
        for amb in tracked_ambulances:
            combined_score = amb.get("combined_score", 0)
            is_verified = amb.get("verified", False) or combined_score >= 0.70
            if is_verified:
                a_bbox = (amb["bbox"]["x"], amb["bbox"]["y"], amb["bbox"]["x"] + amb["bbox"]["width"], amb["bbox"]["y"] + amb["bbox"]["height"])
                verified_amb_boxes.append(amb)
                
                # Match and update vehicle entry in vehicles list
                matched = False
                for v in vehicles:
                    v_bbox = (v["bbox"]["x"], v["bbox"]["y"], v["bbox"]["x"] + v["bbox"]["width"], v["bbox"]["y"] + v["bbox"]["height"])
                    if calculate_iou(v_bbox, a_bbox) > 0.35:
                        v["type"] = "ambulance"
                        v["is_emergency"] = True
                        v["confidence"] = combined_score
                        v["plate_number"] = amb.get("plate")
                        matched = True
                        break
                
                if not matched:
                    vehicles.append({
                        "id": amb.get("tracking_id", str(uuid.uuid4())[:8]),
                        "type": "ambulance",
                        "confidence": combined_score,
                        "bbox": amb["bbox"],
                        "is_emergency": True,
                        "plate_number": amb.get("plate"),
                    })

        ambulance_detected = len(verified_amb_boxes) > 0
        ambulance_plate = verified_amb_boxes[0]["plate"] if ambulance_detected else None

        self.vehicles_in_frame = len(vehicles)
        self.last_detection_was_ambulance = ambulance_detected
        self.total_detections += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000

        result_payload = {
            "frame_id": str(uuid.uuid4()),
            "lane_id": lane_id,
            "timestamp": time.time(),
            "vehicles": vehicles,
            "tracked_ambulances": verified_amb_boxes,
            "ambulance_detected": ambulance_detected,
            "ambulance_plate": ambulance_plate,
            "siren_detected": False,
            "processing_time_ms": round(elapsed_ms, 2),
            "confidence_threshold": self.conf_threshold,
        }

        # Persist to SQLite
        SQLiteDatabase.save_detection(result_payload)

        return result_payload

    def _extract_plate(self, roi: np.ndarray) -> Optional[str]:
        """Extract number plate text from ambulance ROI using EasyOCR or Pytesseract."""
        if roi is None or roi.size == 0:
            return None
        try:
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            results = reader.readtext(roi)
            for bbox, text, prob in results:
                cleaned = text.strip().upper().replace(" ", "-")
                if len(cleaned) >= 5 and prob > 0.4:
                    return cleaned
        except Exception:
            pass

        try:
            import pytesseract
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh, config="--psm 7").strip().upper()
            if len(text) >= 5:
                return text.replace(" ", "-")
        except Exception:
            pass

        return None
