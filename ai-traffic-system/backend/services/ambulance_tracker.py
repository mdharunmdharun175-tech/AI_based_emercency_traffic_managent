"""
Ambulance Tracking, ANPR Verification, Multi-Feature Pipeline & Distance Engine
- Multi-Object Tracking (ByteTrack / IOU-based MOT tracker)
- Multi-Feature Ambulance Verification Pipeline:
  1. YOLO Ambulance Detection (40%)
  2. Emergency Roof Light Flasher Detection (20%)
  3. AMBULANCE Text Detection (15%)
  4. Medical Symbol Detection (Red Cross / Star of Life) (10%)
  5. Ambulance Shape Profile Verification (5%)
  6. License Plate Recognition / OCR Verification (10%)
- Combined Confidence Score calculation (default threshold 80% / 0.80)
- Multi-frame stability tracking (consecutive frames requirement)
- Virtual Stop Line crossing detection
- Distance & ETA estimation
"""

import time
import math
import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from database_sqlite import SQLiteDatabase

logger = logging.getLogger(__name__)

# Virtual Stop Line definition in normalized frame space (0.0 to 1.0)
STOP_LINE_Y_RATIO = 0.85  # y = 85% from top of frame is 0 meters (junction entry)
FAR_LINE_Y_RATIO = 0.15   # y = 15% from top is 200 meters away
MAX_DISTANCE_METERS = 200.0
MIN_STABILITY_FRAMES = 2   # Require at least 2 consecutive frames for multi-frame verification

# Feature weights giving maximum preference to Roof Flasher Light (30%), Name Board Text (25%), and Vehicle Shape (15%)
DEFAULT_FEATURE_WEIGHTS = {
    "roof_light": 0.30,  # Top preference for siren red/blue flashing light bar
    "text": 0.25,        # High preference for "AMBULANCE" / "ECNALUBMA" name board
    "shape": 0.15,       # High preference for van / box ambulance profile
    "yolo": 0.15,        # YOLO vehicle detection baseline
    "symbol": 0.10,      # Medical symbol (Red Cross / Star of Life)
    "ocr": 0.05,         # ANPR license plate OCR
}

DEFAULT_CONFIRMATION_THRESHOLD = 0.80  # 80% combined confidence required to confirm


def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union (IOU) between two bounding boxes (x1, y1, x2, y2)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return iou


# ── Feature 1: Emergency Roof Light Detection ─────────────────
def detect_roof_flasher_lights(roi: np.ndarray) -> Tuple[bool, float]:
    """
    Detect presence of roof-mounted emergency siren/flasher light bar (red & blue LEDs).
    High preference for top siren light bar verification.
    Returns (has_roof_lights: bool, score: float [0.0 - 1.0]).
    """
    if roi is None or roi.size == 0 or roi.shape[0] < 15 or roi.shape[1] < 15:
        return False, 0.0

    try:
        # Crop upper 40% of vehicle bounding box (roof area where siren light bar is mounted)
        roof_h = max(10, int(roi.shape[0] * 0.40))
        roof_roi = roi[0:roof_h, :]

        # Convert to HSV color space for vibrant flasher color segmentation
        hsv = cv2.cvtColor(roof_roi, cv2.COLOR_BGR2HSV)

        # Red flasher mask (hue 0-12 & 155-180, saturation > 60, brightness > 60)
        lower_red1 = np.array([0, 60, 60])
        upper_red1 = np.array([12, 255, 255])
        lower_red2 = np.array([155, 60, 60])
        upper_red2 = np.array([180, 255, 255])
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        # Blue flasher mask (hue 95-135, saturation > 60, brightness > 60)
        lower_blue = np.array([95, 60, 60])
        upper_blue = np.array([135, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

        # Combined emergency roof light mask
        mask_emergency = cv2.bitwise_or(mask_red, mask_blue)
        emergency_pixel_count = cv2.countNonZero(mask_emergency)
        total_roof_pixels = float(roof_roi.shape[0] * roof_roi.shape[1] + 1e-5)
        
        ratio = emergency_pixel_count / total_roof_pixels
        has_lights = ratio > 0.005
        # High preference scoring: >0.5% flasher pixels gives maximum 1.0 score
        score = round(min(1.0, ratio * 50.0), 3) if has_lights else round(ratio * 20.0, 3)

        return has_lights, max(0.0, min(1.0, score))
    except Exception as e:
        logger.debug(f"Roof light detection error: {e}")
        return False, 0.0


# ── Feature 2: AMBULANCE Name Board Text Detection ───────────
def detect_ambulance_text(roi: np.ndarray, ocr_text: Optional[str] = None) -> Tuple[bool, float, str]:
    """
    Detect the word "AMBULANCE" or mirror-printed "ECNALUBMA" from front, rear, or side name board.
    Tolerates partial visibility ("AMB", "BULANCE"), mirrored front text, different fonts, angles.
    Returns (text_detected: bool, score: float [0.0 - 1.0], matched_text: str).
    """
    keywords = ["AMBULANCE", "ECNALUBMA", "AMBULANCIA", "AMBU", "BULANCE", "SAMU", "EMERGENCY", "RESCUE", "PARAMEDIC"]
    
    # Check if pre-extracted OCR text matches any keyword
    if ocr_text:
        cleaned = ocr_text.upper().strip()
        for kw in keywords:
            if kw in cleaned:
                score = 1.0 if ("AMBULANCE" in cleaned or "ECNALUBMA" in cleaned) else 0.90
                return True, score, kw

    if roi is None or roi.size == 0 or roi.shape[0] < 20 or roi.shape[1] < 20:
        return False, 0.0, ""

    try:
        import pytesseract
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        text = pytesseract.image_to_string(gray, config="--psm 11").strip().upper()
        
        for kw in keywords:
            if kw in text:
                score = 1.0 if ("AMBULANCE" in text or "ECNALUBMA" in text) else 0.90
                return True, score, kw
    except Exception:
        pass

    return False, 0.0, ""


# ── Feature 3: Medical Symbols Detection ──────────────────────
def detect_medical_symbols(roi: np.ndarray) -> Tuple[bool, float, str]:
    """
    Detect medical symbols such as Red Cross or Blue Star of Life / Emergency graphics.
    Returns (symbol_detected: bool, score: float [0.0 - 1.0], symbol_name: str).
    """
    if roi is None or roi.size == 0 or roi.shape[0] < 20 or roi.shape[1] < 20:
        return False, 0.0, ""

    try:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 1. Red Cross Detection (Red color mask + cross-shaped contours)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        mask_red = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), cv2.inRange(hsv, lower_red2, upper_red2))
        
        contours, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 40:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w) / float(h)
                # Red cross usually has aspect ratio ~1.0 (between 0.7 and 1.3)
                if 0.7 <= aspect_ratio <= 1.3:
                    extent = area / float(w * h)
                    # Cross contour extent is typically around 0.45 to 0.75
                    if 0.40 <= extent <= 0.80:
                        return True, 0.90, "Red Cross"

        # 2. Blue Star of Life Detection (Cyan/Blue color mask)
        lower_cyan = np.array([85, 90, 90])
        upper_cyan = np.array([125, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_cyan, upper_cyan)
        blue_pixel_count = cv2.countNonZero(mask_blue)
        if blue_pixel_count > 50:
            return True, 0.85, "Star of Life"

    except Exception as e:
        logger.debug(f"Medical symbol check error: {e}")

    return False, 0.0, ""


# ── Feature 4: Ambulance Vehicle Shape Verification ───────────
def verify_vehicle_shape(bbox: Tuple[int, int, int, int]) -> Tuple[bool, float]:
    """
    Verify vehicle shape profile to distinguish boxy van ambulances from sedans or low cars.
    Ambulances typically have height-to-width ratio between 0.60 and 1.30.
    Returns (is_ambulance_shape: bool, score: float [0.0 - 1.0]).
    """
    x1, y1, x2, y2 = bbox
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    aspect_ratio = float(h) / float(w)

    # Van / Box ambulance aspect ratio ranges
    if 0.60 <= aspect_ratio <= 1.35:
        # Score scales higher when aspect ratio is close to ~0.85 (typical van profile)
        dist_from_ideal = abs(aspect_ratio - 0.85)
        score = max(0.5, 1.0 - dist_from_ideal * 1.2)
        return True, round(score, 3)
    else:
        return False, 0.20


# ── Feature 2: Ambulance Combined Confidence Score Engine ─────
def calculate_combined_confidence_score(
    yolo_score: float,
    roof_light_score: float,
    text_score: float,
    symbol_score: float,
    shape_score: float,
    ocr_score: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate combined multi-feature confidence score using weighted aggregation.
    Default Weights:
    - YOLO Ambulance Detection: 40%
    - Emergency Roof Light:      20%
    - AMBULANCE Text Detection:  15%
    - Medical Symbol Detection:  10%
    - Vehicle Shape Profile:      5%
    - License Plate ANPR / OCR:  10%
    """
    w = weights or DEFAULT_FEATURE_WEIGHTS
    
    score = (
        (w.get("yolo", 0.40) * yolo_score) +
        (w.get("roof_light", 0.20) * roof_light_score) +
        (w.get("text", 0.15) * text_score) +
        (w.get("symbol", 0.10) * symbol_score) +
        (w.get("shape", 0.05) * shape_score) +
        (w.get("ocr", 0.10) * ocr_score)
    )
    
    return round(max(0.0, min(1.0, score)), 4)


class AmbulanceTracker:
    def __init__(
        self,
        confidence_threshold: float = 0.75,
        confirmation_threshold: float = DEFAULT_CONFIRMATION_THRESHOLD,
    ):
        self.confidence_threshold: float = confidence_threshold
        self.confirmation_threshold: float = confirmation_threshold
        self.feature_weights: Dict[str, float] = dict(DEFAULT_FEATURE_WEIGHTS)
        
        # Tracked objects store: tracking_id -> dict
        self.tracks: Dict[str, Dict[str, Any]] = {}
        self.next_id: int = 101

    def set_confidence_threshold(self, threshold: float):
        self.confidence_threshold = max(0.1, min(0.99, threshold))
        logger.info(f"⚙️ Detection confidence threshold updated to {self.confidence_threshold * 100:.0f}%")

    def set_confirmation_threshold(self, threshold: float):
        self.confirmation_threshold = max(0.50, min(0.99, threshold))
        logger.info(f"⚙️ Combined confirmation threshold updated to {self.confirmation_threshold * 100:.0f}%")

    def estimate_distance_and_eta(
        self, bbox: Tuple[int, int, int, int], frame_height: int
    ) -> Tuple[float, float, float]:
        """
        Estimate distance to virtual stop line in meters, speed in m/s, and ETA in seconds.
        """
        _, y1, _, y2 = bbox
        box_bottom_y = float(y2)
        
        stop_line_y = float(frame_height * STOP_LINE_Y_RATIO)
        far_line_y = float(frame_height * FAR_LINE_Y_RATIO)
        
        if stop_line_y <= far_line_y:
            ratio = 0.0
        else:
            ratio = (stop_line_y - box_bottom_y) / (stop_line_y - far_line_y)
        
        distance = max(0.0, min(MAX_DISTANCE_METERS, ratio * MAX_DISTANCE_METERS))
        speed_mps = 12.5  # ~45 km/h approach speed
        eta = distance / max(1.0, speed_mps)
        
        return round(distance, 1), round(speed_mps, 1), round(eta, 1)

    def process_detections(
        self,
        raw_detections: List[Dict[str, Any]],
        lane_id: str,
        frame_height: int = 360,
        anpr_extractor=None,
        raw_frame=None,
    ) -> List[Dict[str, Any]]:
        """
        Multi-feature ambulance tracking & verification pipeline.
        Combines 6 features, multi-frame stability tracking, distance estimation, and stop line crossing.
        """
        now = time.time()
        current_frame_ambulances = []

        # Filter candidate detections
        candidate_dets = []
        for det in raw_detections:
            conf = det.get("confidence", 0.0)
            is_amb = det.get("is_emergency", False) or det.get("type", "").lower() == "ambulance"
            if conf >= 0.15 and (is_amb or det.get("type") in ("car", "bus", "truck", "van", "unknown")):
                candidate_dets.append(det)

        matched_track_ids = set()

        for det in candidate_dets:
            bbox_dict = det.get("bbox", {})
            x1 = bbox_dict.get("x", 0)
            y1 = bbox_dict.get("y", 0)
            w = bbox_dict.get("width", 50)
            h = bbox_dict.get("height", 50)
            x2, y2 = x1 + w, y1 + h
            bbox_tuple = (x1, y1, x2, y2)
            
            yolo_score = det.get("confidence", 0.75) if (det.get("is_emergency") or det.get("type") == "ambulance") else 0.40

            # Match detections with existing active tracks using IOU
            best_iou = 0.0
            best_track_id = None

            for tid, tr in self.tracks.items():
                if tr["lane_id"] == lane_id and (now - tr["last_seen"]) < 2.0:
                    iou = calculate_iou(bbox_tuple, tr["bbox"])
                    if iou > 0.3 and iou > best_iou:
                        best_iou = iou
                        best_track_id = tid

            if best_track_id:
                tr = self.tracks[best_track_id]
                tr["bbox"] = bbox_tuple
                tr["yolo_score"] = max(tr["yolo_score"], yolo_score)
                tr["last_seen"] = now
                tr["frame_count"] += 1
                matched_track_ids.add(best_track_id)
                track_id = best_track_id
            else:
                track_id = f"AMB-{self.next_id}"
                self.next_id += 1
                tr = {
                    "tracking_id": track_id,
                    "lane_id": lane_id,
                    "bbox": bbox_tuple,
                    "yolo_score": yolo_score,
                    "roof_light_score": det.get("roof_light_score", 0.0),
                    "text_score": det.get("text_score", 0.0),
                    "symbol_score": det.get("symbol_score", 0.0),
                    "shape_score": 0.0,
                    "ocr_score": 0.0,
                    "combined_score": 0.0,
                    "plate": det.get("plate_number", "") or "",
                    "frame_count": 1,
                    "roof_lights_detected": det.get("roof_lights_detected", False),
                    "text_detected": det.get("text_detected", False),
                    "symbol_detected": det.get("symbol_detected", False),
                    "symbol_name": det.get("symbol_name", ""),
                    "shape_verified": False,
                    "verified": False,
                    "last_seen": now,
                    "created_at": now,
                    "crossed_stop_line": False,
                }
                self.tracks[track_id] = tr
                matched_track_ids.add(track_id)

            # Crop vehicle ROI if raw OpenCV frame is present
            roi = None
            if raw_frame is not None and raw_frame.size > 0:
                try:
                    roi = raw_frame[max(0, y1):min(frame_height, y2), max(0, x1):min(raw_frame.shape[1], x2)]
                except Exception:
                    roi = None

            # Feature 1: Roof Flasher Light Detection
            if not tr["roof_lights_detected"]:
                if det.get("roof_lights_detected"):
                    tr["roof_lights_detected"] = True
                    tr["roof_light_score"] = det.get("roof_light_score", 0.90)
                elif roi is not None and roi.size > 0:
                    has_roof, r_score = detect_roof_flasher_lights(roi)
                    if has_roof:
                        tr["roof_lights_detected"] = True
                        tr["roof_light_score"] = max(tr["roof_light_score"], r_score)

            # Feature 2: AMBULANCE Text Detection
            if not tr["text_detected"]:
                if det.get("text_detected"):
                    tr["text_detected"] = True
                    tr["text_score"] = det.get("text_score", 0.95)
                elif roi is not None and roi.size > 0:
                    has_txt, t_score, matched_txt = detect_ambulance_text(roi, ocr_text=tr.get("plate"))
                    if has_txt:
                        tr["text_detected"] = True
                        tr["text_score"] = max(tr["text_score"], t_score)

            # Feature 3: Medical Symbols Detection
            if not tr["symbol_detected"]:
                if det.get("symbol_detected"):
                    tr["symbol_detected"] = True
                    tr["symbol_score"] = det.get("symbol_score", 0.90)
                    tr["symbol_name"] = det.get("symbol_name", "Red Cross")
                elif roi is not None and roi.size > 0:
                    has_sym, s_score, sym_name = detect_medical_symbols(roi)
                    if has_sym:
                        tr["symbol_detected"] = True
                        tr["symbol_score"] = max(tr["symbol_score"], s_score)
                        tr["symbol_name"] = sym_name

            # Feature 4: Ambulance Shape Verification
            is_shape, shape_score = verify_vehicle_shape(bbox_tuple)
            tr["shape_verified"] = is_shape
            tr["shape_score"] = shape_score

            # Feature 6: ANPR Plate Extraction / OCR Score
            if not tr["plate"] and anpr_extractor and roi is not None and roi.size > 0:
                try:
                    plate_text = anpr_extractor(roi)
                    if plate_text:
                        tr["plate"] = plate_text
                except Exception:
                    pass

            if tr["plate"]:
                tr["ocr_score"] = 0.90
            elif det.get("plate_number"):
                tr["plate"] = det.get("plate_number")
                tr["ocr_score"] = 0.90

            # Calculate Combined Confidence Score
            tr["combined_score"] = calculate_combined_confidence_score(
                yolo_score=tr["yolo_score"],
                roof_light_score=tr["roof_light_score"],
                text_score=tr["text_score"],
                symbol_score=tr["symbol_score"],
                shape_score=tr["shape_score"],
                ocr_score=tr["ocr_score"],
                weights=self.feature_weights,
            )

            # Multi-Frame Verification Check:
            # Requires at least MIN_STABILITY_FRAMES (>=2) AND combined_score >= confirmation_threshold (>= 0.80)
            if (tr["frame_count"] >= MIN_STABILITY_FRAMES and tr["combined_score"] >= self.confirmation_threshold) and not tr["verified"]:
                tr["verified"] = True
                logger.info(
                    f"✅ Multi-Feature Verified Ambulance {track_id} on {lane_id} "
                    f"(Combined Score: {tr['combined_score']*100:.1f}%, Plate: {tr['plate'] or 'AMB-EMG'}, "
                    f"Roof Lights: {tr['roof_lights_detected']}, Text: {tr['text_detected']}, Symbol: {tr['symbol_name'] or 'None'})"
                )

            # Calculate Distance & ETA to Stop Line
            dist, speed, eta = self.estimate_distance_and_eta(bbox_tuple, frame_height)
            tr["distance"] = dist
            tr["speed_mps"] = speed
            tr["eta"] = eta

            # Virtual Stop Line Crossing Check (y2 >= stop_line_y or distance <= 0)
            stop_line_y = frame_height * STOP_LINE_Y_RATIO
            if y2 >= stop_line_y or dist <= 0.0:
                tr["crossed_stop_line"] = True

            # Log distance history to database
            SQLiteDatabase.log_distance(
                tracking_id=track_id,
                lane_id=lane_id,
                distance_meters=dist,
                speed_mps=speed,
                eta_seconds=eta,
                confidence=tr["combined_score"]
            )

            # Only include in verified list if combined_score >= 0.50 or verified
            if tr["verified"] or tr["combined_score"] >= 0.50:
                current_frame_ambulances.append({
                    "tracking_id": track_id,
                    "lane_id": lane_id,
                    "bbox": {"x": x1, "y": y1, "width": w, "height": h},
                    "confidence": round(tr["combined_score"], 3),
                    "combined_score": round(tr["combined_score"], 3),
                    "yolo_score": round(tr["yolo_score"], 3),
                    "roof_light_score": round(tr["roof_light_score"], 3),
                    "text_score": round(tr["text_score"], 3),
                    "symbol_score": round(tr["symbol_score"], 3),
                    "shape_score": round(tr["shape_score"], 3),
                    "ocr_score": round(tr["ocr_score"], 3),
                    "plate": tr["plate"] or f"AMB-{track_id[-3:]}",
                    "roof_lights_detected": tr["roof_lights_detected"],
                    "text_detected": tr["text_detected"],
                    "symbol_detected": tr["symbol_detected"],
                    "symbol_name": tr["symbol_name"],
                    "shape_verified": tr["shape_verified"],
                    "frame_count": tr["frame_count"],
                    "verified": tr["verified"],
                    "distance": dist,
                    "eta": eta,
                    "crossed_stop_line": tr["crossed_stop_line"],
                })

        # Stale track cleanup (> 3s missing)
        stale_ids = [tid for tid, tr in self.tracks.items() if (now - tr["last_seen"]) > 3.0]
        for tid in stale_ids:
            del self.tracks[tid]

        return current_frame_ambulances
