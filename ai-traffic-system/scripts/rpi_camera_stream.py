import argparse
import time
import logging
import requests
import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--api",    default="http://localhost:8000")
    p.add_argument("--camera", default="0")
    p.add_argument("--fps",    type=int, default=5)
    p.add_argument("--width",  type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    return p.parse_args()

def stream(args):
    # Support both webcam index and video file path
    source = int(args.camera) if args.camera.isdigit() else args.camera
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error(f"Cannot open camera/video: {source}")
        return

    logger.info(f"✅ Opened: {source}")
    interval = 1.0 / args.fps
    endpoint = f"{args.api}/api/detect/stream"

    while True:
        t0 = time.time()
        ret, frame = cap.read()
        if not ret:
            logger.info("Video ended or no frame.")
            break

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        try:
            resp = requests.post(
                endpoint,
                files={"file": ("frame.jpg", buf.tobytes(), "image/jpeg")},
                timeout=3,
            )
            if resp.ok:
                data = resp.json()
                if data.get("ambulance_detected"):
                    logger.warning(f"🚨 AMBULANCE! Plate: {data.get('ambulance_plate')} | {data.get('processing_time_ms')}ms")
                else:
                    logger.info(f"Vehicles: {data.get('vehicle_count', 0)} | {data.get('processing_time_ms', 0)}ms")
            else:
                logger.error(f"API error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            time.sleep(2)

        elapsed = time.time() - t0
        time.sleep(max(0, interval - elapsed))

    cap.release()

if __name__ == "__main__":
    args = parse_args()
    stream(args)