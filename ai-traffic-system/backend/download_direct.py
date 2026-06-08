import requests, zipfile, os, io, shutil

print("Downloading ambulance dataset...")

# Direct download from public GitHub dataset
urls = [
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip",
]

# Download Indian ambulance images dataset
url = "https://github.com/user-attachments/files/ambulance-yolov8.zip"

# Use this working public dataset instead
import subprocess
result = subprocess.run([
    "python", "-c",
    """
from ultralytics import YOLO
import os, shutil
os.makedirs('../ml/weights', exist_ok=True)

# Download and use a vehicle detection model
# that includes ambulance-like classes
model = YOLO('yolov8n.pt')

# Export model info
print('Model classes:', model.names)
print('Model ready for fine-tuning')
"""
], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
```

---

## Step 2 — Use Google Colab to train (FREE GPU — fastest method)

Open your browser and go to:
```
https://colab.research.google.com