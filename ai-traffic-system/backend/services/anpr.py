"""
ANPR — Automatic Number Plate Recognition
Standalone module; can also be used as a CLI tool.

Pipeline:
  1. Detect plate region using Haar cascade or YOLOv8 plate model
  2. Pre-process ROI: resize, denoise, threshold
  3. OCR with Tesseract
  4. Post-process: regex clean, format validation

Usage (CLI):
    python anpr.py --image /path/to/frame.jpg
    python anpr.py --video /path/to/clip.mp4
"""

import argparse
import re
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Haar cascade for licence plates (ships with OpenCV)
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
_plate_cascade = cv2.CascadeClassifier(_CASCADE_PATH)

# Indian plate regex patterns
_PLATE_PATTERNS = [
    re.compile(r"[A-Z]{2}[-\s]?\d{2}[-\s]?[A-Z]{1,2}[-\s]?\d{4}"),  # KA-05-MK-4822
    re.compile(r"[A-Z]{2}\d{2}[A-Z]{2}\d{4}"),                        # KA05MK4822 (no sep)
]


# ── Pre-processing helpers ──────────────────────────────────────

def _upscale(img: np.ndarray, factor: int = 3) -> np.ndarray:
    return cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def _grayscale(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img


def _denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(gray, (3, 3), 0)


def _threshold(gray: np.ndarray) -> np.ndarray:
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _deskew(img: np.ndarray) -> np.ndarray:
    """Correct small rotation using Hough lines."""
    edges = cv2.Canny(img, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=50, maxLineGap=10)
    if lines is None:
        return img
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 != 0:
            angles.append(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
    if not angles:
        return img
    median_angle = np.median(angles)
    if abs(median_angle) > 15:   # too skewed — skip
        return img
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def preprocess_plate_roi(roi: np.ndarray) -> np.ndarray:
    """Full preprocessing pipeline for a plate ROI."""
    gray  = _grayscale(roi)
    large = _upscale(gray, factor=3)
    noisy = _denoise(large)
    skew  = _deskew(noisy)
    return _threshold(skew)


# ── Plate detection ─────────────────────────────────────────────

def detect_plate_regions(frame: np.ndarray) -> List[Tuple[int,int,int,int]]:
    """
    Find candidate plate bounding boxes in a full frame.
    Returns list of (x, y, w, h) tuples.
    """
    gray = _grayscale(frame)
    plates = _plate_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(60, 20),
        maxSize=(400, 120),
    )
    return list(plates) if len(plates) > 0 else []


# ── OCR ─────────────────────────────────────────────────────────

def ocr_plate(roi_processed: np.ndarray) -> str:
    """Run Tesseract OCR on a pre-processed plate image."""
    try:
        import pytesseract
        # PSM 8: single word; PSM 7: single line
        configs = [
            "--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
            "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
            "--psm 6 --oem 3",
        ]
        best = ""
        for cfg in configs:
            text = pytesseract.image_to_string(roi_processed, config=cfg).strip()
            text = re.sub(r"[^A-Z0-9\-]", "", text.upper())
            if len(text) > len(best):
                best = text
        return best
    except ImportError:
        logger.error("pytesseract not installed: pip install pytesseract")
        return ""
    except Exception as e:
        logger.debug(f"OCR error: {e}")
        return ""


# ── Post-processing ─────────────────────────────────────────────

def validate_indian_plate(text: str) -> Optional[str]:
    """
    Validate and normalise an Indian number plate string.
    Returns formatted plate (e.g. "KA-05-MK-4822") or None if invalid.
    """
    cleaned = re.sub(r"[\s\-_]", "", text.upper())
    for pat in _PLATE_PATTERNS:
        m = pat.search(cleaned)
        if m:
            raw = re.sub(r"[^A-Z0-9]", "", m.group())
            # Format: SS-NN-LL-NNNN
            if len(raw) >= 8:
                return f"{raw[:2]}-{raw[2:4]}-{raw[4:6]}-{raw[6:]}"
    return None


# ── Main detection entry point ──────────────────────────────────

def extract_plate_from_frame(frame: np.ndarray) -> Optional[str]:
    """
    Full ANPR pipeline on a BGR frame.
    Returns validated plate string or None.
    """
    regions = detect_plate_regions(frame)

    candidates = []

    # Try detected regions first
    for (x, y, w, h) in regions:
        roi = frame[y:y+h, x:x+w]
        processed = preprocess_plate_roi(roi)
        text = ocr_plate(processed)
        plate = validate_indian_plate(text)
        if plate:
            candidates.append(plate)

    if candidates:
        return candidates[0]

    # Fallback: OCR on full (small) frame
    processed = preprocess_plate_roi(frame)
    text = ocr_plate(processed)
    return validate_indian_plate(text)


def extract_plate_from_ambulance_bbox(frame: np.ndarray, bbox: dict) -> Optional[str]:
    """
    Crop ambulance bounding box from frame and run ANPR on it.
    bbox = {"x": int, "y": int, "width": int, "height": int}
    """
    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
    # Add small padding
    pad = 10
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(frame.shape[1], x + w + pad)
    y2 = min(frame.shape[0], y + h + pad)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return extract_plate_from_frame(roi)


# ── Visualisation helper ────────────────────────────────────────

def draw_anpr_result(frame: np.ndarray, plate: Optional[str], regions: List) -> np.ndarray:
    """Annotate frame with detected plate boxes and text."""
    out = frame.copy()
    for (x, y, w, h) in regions:
        cv2.rectangle(out, (x, y), (x+w, y+h), (0, 229, 255), 2)
    if plate:
        cv2.putText(out, plate, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 229, 255), 2)
    return out


# ── CLI ─────────────────────────────────────────────────────────

def _run_on_image(path: str):
    frame = cv2.imread(path)
    if frame is None:
        print(f"Cannot read image: {path}")
        return
    plate = extract_plate_from_frame(frame)
    print(f"Detected plate: {plate or 'None'}")
    out = draw_anpr_result(frame, plate, detect_plate_regions(frame))
    cv2.imshow("ANPR Result", out)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def _run_on_video(path: str):
    cap = cv2.VideoCapture(path)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        plate = extract_plate_from_frame(frame)
        out = draw_anpr_result(frame, plate, detect_plate_regions(frame))
        cv2.imshow("ANPR", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Standalone ANPR tool")
    p.add_argument("--image", help="Path to image file")
    p.add_argument("--video", help="Path to video file")
    args = p.parse_args()
    if args.image:
        _run_on_image(args.image)
    elif args.video:
        _run_on_video(args.video)
    else:
        p.print_help()
