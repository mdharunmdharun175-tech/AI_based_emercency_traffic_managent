"""
Dataset Preparation Script
Converts video footage to annotated frames for YOLOv8 training.

Usage:
    python prepare_dataset.py --video path/to/cctv.mp4 --output ./dataset --fps 5
"""

import argparse
import shutil
from pathlib import Path
import cv2


def extract_frames(video_path: str, output_dir: Path, fps: int = 5):
    """Extract frames from video at specified FPS."""
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(video_fps / fps))

    out_images = output_dir / "images" / "train"
    out_images.mkdir(parents=True, exist_ok=True)

    frame_num = 0
    saved = 0

    print(f"📹 Video: {video_path}")
    print(f"   Total frames: {total}, Source FPS: {video_fps:.1f}, Extracting at: {fps}fps")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_num % step == 0:
            fname = out_images / f"frame_{saved:06d}.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            saved += 1
        frame_num += 1

    cap.release()
    print(f"✅ Extracted {saved} frames to {out_images}")
    return saved


def split_dataset(images_dir: Path, train_ratio: float = 0.8, val_ratio: float = 0.15):
    """Split images into train/val/test sets."""
    import random
    frames = sorted(list(images_dir.glob("*.jpg")))
    random.shuffle(frames)

    n_train = int(len(frames) * train_ratio)
    n_val = int(len(frames) * val_ratio)

    splits = {
        "train": frames[:n_train],
        "val": frames[n_train:n_train + n_val],
        "test": frames[n_train + n_val:],
    }

    parent = images_dir.parent
    for split_name, files in splits.items():
        split_dir = parent / "images" / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        label_dir = parent / "labels" / split_name
        label_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.move(str(f), str(split_dir / f.name))

    print(f"✅ Dataset split: {len(splits['train'])} train / {len(splits['val'])} val / {len(splits['test'])} test")


def create_dataset_structure(base: Path):
    """Create YOLOv8-compatible directory structure."""
    for split in ("train", "val", "test"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)
    print(f"✅ Dataset structure created at {base}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", help="Path to input video file")
    parser.add_argument("--output", default="./dataset", help="Output directory")
    parser.add_argument("--fps", type=int, default=5, help="Frames per second to extract")
    parser.add_argument("--create-structure", action="store_true", help="Create empty dataset structure")
    args = parser.parse_args()

    out = Path(args.output)

    if args.create_structure:
        create_dataset_structure(out)
        print("\nNext steps:")
        print("  1. Place your video files in a folder")
        print("  2. Run: python prepare_dataset.py --video your_video.mp4 --output ./dataset --fps 5")
        print("  3. Annotate frames with LabelImg or upload to Roboflow")
        print("  4. Run: python train.py")
        return

    if not args.video:
        parser.error("--video is required (or use --create-structure)")

    extract_frames(args.video, out, fps=args.fps)
    split_dataset(out / "images" / "train")

    print("\n📌 Next: Annotate the extracted frames using:")
    print("   LabelImg: pip install labelImg && labelImg")
    print("   Roboflow: https://roboflow.com (recommended)")
    print("   Label classes: ambulance, car, truck, bus, motorcycle")


if __name__ == "__main__":
    main()
