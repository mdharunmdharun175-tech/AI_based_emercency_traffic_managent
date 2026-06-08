Place your trained YOLOv8 weights here:
  best.pt       — YOLOv8 ambulance/vehicle detection model
  siren_cnn.h5  — Siren sound classification CNN

To train:
  cd ml && python train.py          # vehicle detection
  cd ml && python train_siren.py    # siren audio classifier
