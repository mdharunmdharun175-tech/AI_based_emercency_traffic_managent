"""
Offline Video Analysis Utility
Runs the full detection pipeline on a saved video file and writes an
annotated output video + JSON report. Useful for demos and evaluation.

Usage:
    python video_replay.py --input highway.mp4 --output annotated.mp4 --fps 15
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np


def parse_args():
    p = argparse.ArgumentParser(description="Offline video analysis with ANPR + YOLOv8")
    p.add_argument("--input",  required=True,          help="Input video path")
    p.add_argument("--output", default="annotated.mp4", help="Output annotated video")
    p.add_argument("--report", default="report.json",   help="JSON detection report")
    p.add_argument("--fps",    type=int, default=10,    help="Process every Nth frame equivalent")
    p.add_argument("--conf",   type=float, default=0.55, help="YOLOv8 confidence threshold")
    p.add_argument("--show",   action="store_true",     help="Show live preview window")
    return p.parse_args()


def draw_detection(frame: np.ndarray, vehicles: list, plate: str = None) -> np.ndarray:
    """Draw bounding boxes, labels, and ANPR overlay on frame."""
    out = frame.copy()

    for v in vehicles:
        bb  = v["bbox"]
        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
        is_emg = v.get("is_emergency", False)
        color  = (0, 229, 255) if is_emg else (68, 136, 255)
        lw     = 2 if is_emg else 1

        cv2.rectangle(out, (x, y), (x+w, y+h), color, lw)

        label = f"{v['type']} {v['confidence']:.2f}"
        (lw2, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(out, (x, y - lh - 6), (x + lw2, y), color, -1)
        cv2.putText(out, label, (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        if is_emg:
            # Pulsing glow ring
            cv2.circle(out, (x + w//2, y + h//2), max(w, h)//2 + 10, color, 1)

    # ANPR overlay
    if plate:
        overlay = out.copy()
        cv2.rectangle(overlay, (8, 8), (280, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, out, 0.4, 0, out)
        cv2.putText(out, "PLATE:", (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1)
        cv2.putText(out, plate, (70, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 229, 255), 2)

    return out


def process_video(args):
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {args.input}")

    src_fps   = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, int(src_fps / args.fps))

    # Writer
    out_path = Path(args.output)
    writer = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        min(args.fps, src_fps),
        (w, h),
    )

    # Load model (lazy import so module is still importable without torch)
    try:
        from ultralytics import YOLO
        weights = Path(__file__).parent.parent / "ml" / "weights" / "best.pt"
        model = YOLO(str(weights) if weights.exists() else "yolov8n.pt")
        print(f"✅ Model loaded: {weights if weights.exists() else 'yolov8n.pt (pretrained)'}")
    except ImportError:
        model = None
        print("⚠️  ultralytics not installed — skipping AI detection, writing raw frames")

    try:
        from services.anpr import extract_plate_from_frame
        anpr_available = True
    except ImportError:
        anpr_available = False

    report = {
        "input": args.input,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_frames": total_frames,
        "detections": [],
        "summary": {"total_vehicles": 0, "ambulances": 0, "unique_plates": []},
    }

    CLASS_NAMES = {0: "ambulance", 1: "car", 2: "truck", 3: "bus", 4: "motorcycle"}
    frame_num = 0
    processed = 0

    print(f"📹 Processing {total_frames} frames ({w}×{h}) at ~{args.fps}fps…")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        if frame_num % step != 0:
            continue

        t0 = time.perf_counter()
        vehicles = []
        plate = None
        ambulance_detected = False

        if model:
            results = model(frame, conf=args.conf, verbose=False)[0]
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vtype  = CLASS_NAMES.get(cls_id, "unknown")
                is_emg = vtype == "ambulance"
                if is_emg:
                    ambulance_detected = True
                vehicles.append({
                    "type": vtype, "confidence": round(conf, 3),
                    "bbox": {"x": x1, "y": y1, "width": x2-x1, "height": y2-y1},
                    "is_emergency": is_emg,
                })
            report["summary"]["total_vehicles"] += len(vehicles)
            if ambulance_detected:
                report["summary"]["ambulances"] += 1

        if ambulance_detected and anpr_available:
            plate = extract_plate_from_frame(frame)
            if plate and plate not in report["summary"]["unique_plates"]:
                report["summary"]["unique_plates"].append(plate)

        ms = round((time.perf_counter() - t0) * 1000, 1)
        annotated = draw_detection(frame, vehicles, plate)

        # Frame counter HUD
        cv2.putText(annotated, f"Frame {frame_num}/{total_frames}  {ms}ms",
                    (w - 240, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 60, 90), 1)

        writer.write(annotated)
        processed += 1

        if ambulance_detected:
            report["detections"].append({
                "frame": frame_num,
                "vehicles": vehicles,
                "plate": plate,
                "processing_ms": ms,
            })

        if args.show:
            cv2.imshow("Replay", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if processed % 50 == 0:
            pct = frame_num / total_frames * 100
            print(f"  {pct:.0f}%  frame {frame_num}/{total_frames}  ambulances so far: {report['summary']['ambulances']}")

    cap.release()
    writer.release()
    if args.show:
        cv2.destroyAllWindows()

    # Write report
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Done!")
    print(f"   Annotated video → {args.output}")
    print(f"   Report          → {args.report}")
    print(f"   Vehicles:  {report['summary']['total_vehicles']}")
    print(f"   Ambulances: {report['summary']['ambulances']}")
    print(f"   Plates:    {', '.join(report['summary']['unique_plates']) or 'None'}")
    return report


if __name__ == "__main__":
    args = parse_args()
    process_video(args)
