# Hardware Setup Guide

## Arduino Signal Controller Wiring

```
Arduino UNO
│
├── Pin 2  → L1 RED    signal light
├── Pin 3  → L1 GREEN  signal light
├── Pin 4  → L2 RED
├── Pin 5  → L2 GREEN
├── Pin 6  → L3 RED
├── Pin 7  → L3 GREEN
├── Pin 8  → L4 RED
├── Pin 9  → L4 GREEN
├── Pin 10 → Buzzer (optional)
├── GND    → Common ground for all LEDs
└── USB-B  → Raspberry Pi USB-A
```

Each LED/relay output → 220Ω resistor → LED → GND

## Raspberry Pi Setup

```bash
# Install OS: Raspberry Pi OS Lite (64-bit)
# Enable SSH, Camera, Serial in raspi-config

# Install dependencies
sudo apt update && sudo apt install -y python3-pip python3-venv git tesseract-ocr

# Clone project
git clone <your-repo> ai-traffic-system
cd ai-traffic-system

# Setup
chmod +x scripts/setup.sh && ./scripts/setup.sh

# Run backend
cd backend && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Run camera stream (separate terminal)
cd scripts
python rpi_camera_stream.py --api http://localhost:8000 --fps 10
```

## Camera RTSP Stream (IP Camera)

For IP cameras, replace `--camera 0` with the RTSP URL:
```bash
python rpi_camera_stream.py --api http://localhost:8000 --camera "rtsp://admin:password@192.168.1.100:554/stream"
```

## Arduino Firmware

1. Open `scripts/arduino_signal_controller.ino` in Arduino IDE
2. Select: Board = Arduino UNO, Port = /dev/ttyUSB0
3. Upload

## Serial Port Permissions (Linux)

```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```
