"""
YOLOv8 Training Script
Trains a custom ambulance/vehicle detection model.

Usage:
    python train.py [--epochs 50] [--batch 16] [--imgsz 640]

Prerequisites:
    pip install ultralytics
    Prepare dataset using Roboflow or LabelImg (see README)
"""

import argparse
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)


DATA_YAML = Path(__file__).parent / "data.yaml"
WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)


def parse_args():
    p = argparse.ArgumentParser(description="Train YOLOv8 for ambulance detection")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--model", default="yolov8n.pt", help="Base model (yolov8n/s/m/l/x.pt)")
    p.add_argument("--device", default="0", help="cuda device or 'cpu'")
    p.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    return p.parse_args()


def train(args):
    if not DATA_YAML.exists():
        print(f"❌ data.yaml not found at {DATA_YAML}")
        print("   Create it using prepare_dataset.py or follow docs/dataset_setup.md")
        sys.exit(1)

    print(f"🚀 Starting YOLOv8 training")
    print(f"   Model: {args.model}")
    print(f"   Epochs: {args.epochs}")
    print(f"   Batch: {args.batch}")
    print(f"   Image size: {args.imgsz}")
    print(f"   Data: {DATA_YAML}")

    model = YOLO(args.model)

    results = model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project="runs/train",
        name="ambulance_detector",
        resume=args.resume,
        patience=20,
        save=True,
        plots=True,
        workers=4,
        optimizer="AdamW",
        lr0=0.001,
        augment=True,
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
    )

    # Copy best weights
    best = Path("runs/train/ambulance_detector/weights/best.pt")
    if best.exists():
        import shutil
        dest = WEIGHTS_DIR / "best.pt"
        shutil.copy(best, dest)
        print(f"✅ Best weights saved to {dest}")
    else:
        print("⚠️  Training complete but best.pt not found. Check runs/train/")

    return results


def validate(weights_path: str = None):
    """Validate trained model on test set."""
    path = weights_path or str(WEIGHTS_DIR / "best.pt")
    model = YOLO(path)
    metrics = model.val(data=str(DATA_YAML))
    print(f"\n📊 Validation Results:")
    print(f"   mAP50:     {metrics.box.map50:.4f}")
    print(f"   mAP50-95:  {metrics.box.map:.4f}")
    print(f"   Precision: {metrics.box.mp:.4f}")
    print(f"   Recall:    {metrics.box.mr:.4f}")
    return metrics


def export_model(format: str = "onnx"):
    """Export model to ONNX or TensorRT for edge deployment."""
    model = YOLO(str(WEIGHTS_DIR / "best.pt"))
    model.export(format=format)
    print(f"✅ Model exported to {format}")


if __name__ == "__main__":
    args = parse_args()
    results = train(args)
    validate()
