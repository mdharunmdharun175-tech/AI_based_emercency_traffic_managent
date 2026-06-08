"""
Model Inference Benchmark
Measures YOLOv8 detection speed and accuracy on a test video or image folder.

Usage:
    python benchmark.py --source ./dataset/images/test --runs 100
"""

import argparse
import time
import statistics
from pathlib import Path
import cv2
import numpy as np


def benchmark_model(source: str, runs: int, model_path: str, conf: float = 0.55):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ ultralytics not installed")
        return

    model = YOLO(model_path)
    source_path = Path(source)

    # Collect image paths
    if source_path.is_dir():
        images = list(source_path.glob("*.jpg")) + list(source_path.glob("*.png"))
        if not images:
            print("❌ No images found in source directory")
            return
    elif source_path.is_file():
        images = [source_path]
    else:
        # Generate synthetic frames for speed test
        print("⚠️  Source not found — using synthetic frames for speed test")
        images = None

    times = []
    ambulance_count = 0
    total_vehicles = 0

    print(f"🏁 Benchmarking: {model_path}")
    print(f"   Runs: {runs} | Confidence: {conf}")
    print("-" * 50)

    for i in range(runs):
        if images:
            img_path = str(images[i % len(images)])
            frame = cv2.imread(img_path)
        else:
            frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        t0 = time.perf_counter()
        results = model(frame, conf=conf, verbose=False)[0]
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)

        for box in results.boxes:
            cls_id = int(box.cls[0])
            total_vehicles += 1
            if cls_id == 0:  # ambulance
                ambulance_count += 1

        if (i + 1) % 10 == 0:
            print(f"  Run {i+1:3d}/{runs} | Avg: {statistics.mean(times[-10:]):.1f}ms | Last: {elapsed:.1f}ms")

    print("\n" + "=" * 50)
    print("📊 BENCHMARK RESULTS")
    print(f"   Total runs:        {runs}")
    print(f"   Mean latency:      {statistics.mean(times):.2f} ms")
    print(f"   Median latency:    {statistics.median(times):.2f} ms")
    print(f"   Min latency:       {min(times):.2f} ms")
    print(f"   Max latency:       {max(times):.2f} ms")
    print(f"   Std deviation:     {statistics.stdev(times):.2f} ms")
    print(f"   Effective FPS:     {1000/statistics.mean(times):.1f}")
    print(f"   Total detections:  {total_vehicles}")
    print(f"   Ambulances:        {ambulance_count}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="./dataset/images/test")
    parser.add_argument("--model",  default="./weights/best.pt")
    parser.add_argument("--runs",   type=int, default=100)
    parser.add_argument("--conf",   type=float, default=0.55)
    args = parser.parse_args()
    benchmark_model(args.source, args.runs, args.model, args.conf)
