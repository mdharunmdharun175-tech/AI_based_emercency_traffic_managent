# Dataset Setup Guide

## Step 1 — Collect Video Footage

Collect CCTV / dashcam videos from:
- Indian highway junction cameras
- Hospital approach roads
- City intersections

Recommended: at least 20 minutes of footage per scene, various lighting conditions.

## Step 2 — Extract Frames

```bash
cd ml
python prepare_dataset.py --video /path/to/cctv.mp4 --output ./dataset --fps 5
```

This extracts one frame every 5 FPS and splits into train/val/test sets.

## Step 3 — Annotate with LabelImg

```bash
pip install labelImg
labelImg ./dataset/images/train ./dataset/labels/train
```

Label these classes (must match data.yaml):
- `ambulance`  (class 0)
- `car`        (class 1)
- `truck`      (class 2)
- `bus`        (class 3)
- `motorcycle` (class 4)

Save format: **YOLO** (not Pascal VOC or COCO)

## Alternative — Roboflow (Recommended)

1. Create account at https://roboflow.com
2. Upload frames
3. Annotate online with team collaboration
4. Export → YOLOv8 format
5. Replace `ml/dataset/` with exported folder

## Step 4 — Train

```bash
cd ml
source venv/bin/activate
python train.py --epochs 50 --batch 16 --imgsz 640
```

Expected mAP50 after 50 epochs on a balanced dataset: **0.85+**

## Step 5 — Verify

```bash
python train.py validate  # prints mAP, precision, recall
```

Trained weights land at: `ml/weights/best.pt`
