import cv2
import requests

cap = cv2.VideoCapture(r"C:\Users\Dharun kumar\Downloads\3800731-hd_1920_1080_25fps.mp4")
ret, frame = cap.read()
cap.release()

_, buf = cv2.imencode(".jpg", frame)
res = requests.post(
    "http://localhost:8000/api/detect",
    files={"file": ("f.jpg", buf.tobytes(), "image/jpeg")}
)
data = res.json()
print("Vehicles found:", data["vehicle_count"])
for v in data["vehicles"]:
    print(f"  {v['type']}  conf={v['confidence']}  x={v['bbox']['x']}  y={v['bbox']['y']}")