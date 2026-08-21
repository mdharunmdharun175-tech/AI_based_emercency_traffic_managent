"""
4-Lane Junction Camera Simulation Engine (v2.2 — Background Traffic & Multi-Feature Pipeline Renders)
- Generates synthetic live video streams for 4 junction lanes (Lane A, Lane B, Lane C, Lane D)
- Simulates moving ambulances, background cars, trucks, buses, motorcycles, virtual stop line, and lane signals
"""

import time
import math
import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Any
from services.signal_controller import SignalController

logger = logging.getLogger(__name__)

LANES = ["Lane A", "Lane B", "Lane C", "Lane D"]

STATIC_BG_VEHICLES = {
    "Lane A": [
        {"type": "car", "x": 0.25, "y": 0.35, "w": 45, "h": 35, "conf": 0.92, "color": (255, 170, 0)},
        {"type": "truck", "x": 0.70, "y": 0.50, "w": 65, "h": 50, "conf": 0.88, "color": (0, 170, 255)},
        {"type": "car", "x": 0.35, "y": 0.65, "w": 55, "h": 40, "conf": 0.94, "color": (255, 170, 0)},
        {"type": "bus", "x": 0.60, "y": 0.30, "w": 60, "h": 45, "conf": 0.96, "color": (255, 68, 170)},
    ],
    "Lane B": [
        {"type": "car", "x": 0.30, "y": 0.40, "w": 50, "h": 38, "conf": 0.91, "color": (255, 170, 0)},
        {"type": "motorcycle", "x": 0.65, "y": 0.45, "w": 30, "h": 25, "conf": 0.85, "color": (136, 255, 0)},
        {"type": "car", "x": 0.40, "y": 0.70, "w": 55, "h": 42, "conf": 0.93, "color": (255, 170, 0)},
    ],
    "Lane C": [
        {"type": "truck", "x": 0.25, "y": 0.45, "w": 60, "h": 48, "conf": 0.89, "color": (0, 170, 255)},
        {"type": "car", "x": 0.72, "y": 0.55, "w": 50, "h": 38, "conf": 0.95, "color": (255, 170, 0)},
        {"type": "bus", "x": 0.45, "y": 0.30, "w": 65, "h": 50, "conf": 0.92, "color": (255, 68, 170)},
    ],
    "Lane D": [
        {"type": "car", "x": 0.35, "y": 0.38, "w": 48, "h": 36, "conf": 0.90, "color": (255, 170, 0)},
        {"type": "motorcycle", "x": 0.55, "y": 0.60, "w": 28, "h": 24, "conf": 0.87, "color": (136, 255, 0)},
        {"type": "car", "x": 0.68, "y": 0.48, "w": 52, "h": 40, "conf": 0.94, "color": (255, 170, 0)},
    ],
}


class CameraSimulator:
    def __init__(self, signal_controller: SignalController):
        self.signal_controller = signal_controller
        self.active_vehicles: Dict[str, List[Dict[str, Any]]] = {lane: [] for lane in LANES}
        self.next_sim_id: int = 101

    def spawn_ambulance(
        self,
        lane_id: str,
        initial_distance: float = 150.0,
        confidence: float = 0.88,
        plate: str = "",
        roof_lights: bool = True,
        text_detected: bool = True,
        symbol_detected: bool = True,
        symbol_name: str = "Red Cross",
        shape_verified: bool = True,
    ):
        """Spawn a simulated ambulance with multi-feature visual attributes."""
        norm_lane = self.signal_controller._norm_lane(lane_id)
        tid = f"AMB-{self.next_sim_id}"
        self.next_sim_id += 1
        
        plate_str = plate if plate else f"KA-05-EM-{self.next_sim_id + 100}"
        combined_score = float(confidence)
        
        sim_amb = {
            "tracking_id": tid,
            "lane_id": norm_lane,
            "distance": float(initial_distance),
            "speed_mps": 14.0,  # ~50 km/h approach speed
            "confidence": combined_score,
            "combined_score": combined_score,
            "yolo_score": min(0.99, combined_score + 0.05),
            "roof_lights_detected": roof_lights,
            "roof_light_score": 0.90 if roof_lights else 0.0,
            "text_detected": text_detected,
            "text_score": 0.95 if text_detected else 0.0,
            "symbol_detected": symbol_detected,
            "symbol_score": 0.90 if symbol_detected else 0.0,
            "symbol_name": symbol_name if symbol_detected else "None",
            "shape_verified": shape_verified,
            "shape_score": 0.90 if shape_verified else 0.20,
            "ocr_score": 0.90,
            "plate": plate_str,
            "created_at": time.time(),
        }
        
        self.active_vehicles[norm_lane].append(sim_amb)
        logger.info(f"🚨 Simulated Multi-Feature Ambulance {tid} spawned on {norm_lane} at {initial_distance}m (Score: {combined_score*100:.0f}%)")
        
        # Instantly register with FSM Priority Queue & Tracker
        eta = initial_distance / sim_amb["speed_mps"]
        self.signal_controller.add_or_update_emergency_vehicle(
            tracking_id=tid,
            lane_id=norm_lane,
            distance=initial_distance,
            eta=eta,
            confidence=combined_score,
            plate=plate_str,
            roof_lights_detected=roof_lights,
            text_detected=text_detected,
            symbol_detected=symbol_detected,
            symbol_name=symbol_name,
            shape_verified=shape_verified,
            combined_score=combined_score,
        )

    def update_simulation_tick(self, delta_seconds: float = 1.0):
        """Update simulation physics every tick (move vehicles closer to virtual stop line)."""
        signal_snapshot = self.signal_controller.get_signal_states()

        for lane_id in LANES:
            lane_signal = signal_snapshot.get(lane_id, {}).get("color", "RED")
            is_green = lane_signal == "GREEN"

            updated_vehicles = []
            for veh in self.active_vehicles[lane_id]:
                if is_green or veh["distance"] > 15.0:
                    veh["distance"] -= veh["speed_mps"] * delta_seconds

                if veh["distance"] <= 0.0:
                    logger.info(f"🏁 Vehicle {veh['tracking_id']} crossed virtual stop line on {lane_id}")
                    self.signal_controller.mark_ambulance_passed(veh["tracking_id"])
                else:
                    eta = veh["distance"] / max(1.0, veh["speed_mps"])
                    self.signal_controller.add_or_update_emergency_vehicle(
                        tracking_id=veh["tracking_id"],
                        lane_id=lane_id,
                        distance=veh["distance"],
                        eta=eta,
                        confidence=veh["confidence"],
                        plate=veh["plate"],
                        roof_lights_detected=veh["roof_lights_detected"],
                        text_detected=veh["text_detected"],
                        symbol_detected=veh["symbol_detected"],
                        symbol_name=veh.get("symbol_name", ""),
                        shape_verified=veh["shape_verified"],
                        combined_score=veh["combined_score"],
                    )
                    updated_vehicles.append(veh)

            self.active_vehicles[lane_id] = updated_vehicles

    def generate_frame(self, lane_id: str, width: int = 640, height: int = 360) -> np.ndarray:
        """Generate OpenCV BGR frame image representing camera feed for a lane."""
        norm_lane = self.signal_controller._norm_lane(lane_id)
        
        # Create dark road background canvas
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (15, 22, 32)

        # Draw road perspective guidelines
        cv2.line(frame, (int(width * 0.2), height), (int(width * 0.4), 0), (45, 55, 70), 2)
        cv2.line(frame, (int(width * 0.8), height), (int(width * 0.6), 0), (45, 55, 70), 2)
        cv2.line(frame, (int(width * 0.5), height), (int(width * 0.5), 0), (60, 75, 90), 1)

        # Draw Virtual Stop Line
        stop_y = int(height * 0.85)
        cv2.line(frame, (int(width * 0.15), stop_y), (int(width * 0.85), stop_y), (0, 0, 255), 3)
        cv2.putText(frame, "VIRTUAL STOP LINE (0m)", (int(width * 0.2), stop_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)

        # Draw Traffic Signal Status overlay
        signals = self.signal_controller.get_signal_states()
        sig_info = signals.get(norm_lane, {"color": "RED", "countdown": 0})
        sig_color_bgr = (0, 255, 0) if sig_info["color"] == "GREEN" else (0, 0, 255)
        
        # Draw light box
        cv2.rectangle(frame, (width - 140, 15), (width - 15, 65), (10, 15, 20), -1)
        cv2.rectangle(frame, (width - 140, 15), (width - 15, 65), sig_color_bgr, 2)
        cv2.circle(frame, (width - 118, 40), 12, sig_color_bgr, -1)
        
        sig_text = f"{sig_info['color']} ({sig_info['countdown']}s)"
        cv2.putText(frame, sig_text, (width - 98, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw Lane Label Header
        cv2.rectangle(frame, (15, 15), (200, 50), (10, 15, 20), -1)
        cv2.rectangle(frame, (15, 15), (200, 50), (0, 229, 255), 1)
        cv2.putText(frame, f"CAM: {norm_lane}", (25, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 229, 255), 2, cv2.LINE_AA)

        # Draw Background Vehicles (Cars, Trucks, Buses, Motorcycles)
        bg_vehs = STATIC_BG_VEHICLES.get(norm_lane, [])
        for bg in bg_vehs:
            bx = int(width * bg["x"])
            by = int(height * bg["y"])
            bw, bh = bg["w"], bg["h"]
            col = bg["color"]
            
            # Vehicle bounding box
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), col, 2)
            # Vehicle type tag
            lbl = f"{bg['type'].upper()} {int(bg['conf']*100)}%"
            cv2.rectangle(frame, (bx, max(0, by - 16)), (bx + len(lbl) * 8, by), col, -1)
            cv2.putText(frame, lbl, (bx + 2, max(12, by - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)

        # Draw Simulated Multi-Feature Ambulances
        vehicles = self.active_vehicles.get(norm_lane, [])
        for veh in vehicles:
            dist = veh["distance"]
            ratio = max(0.0, min(1.0, 1.0 - (dist / 200.0)))
            box_y2 = int(height * 0.15 + ratio * (height * 0.70))
            
            box_h = int(45 + ratio * 65)
            box_w = int(55 + ratio * 85)
            box_x1 = int(width * 0.5 - box_w / 2)
            box_y1 = max(0, box_y2 - box_h)
            box_x2 = box_x1 + box_w

            # Draw Bounding Box in Bright Red
            cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 255), 2)
            
            # Feature 1: Roof Flasher Light Bar Animation
            if veh.get("roof_lights_detected", True):
                cv2.rectangle(frame, (box_x1 + 8, box_y1 - 12), (box_x2 - 8, box_y1), (255, 255, 255), -1)
                flicker = int(time.time() * 5) % 2 == 0
                color_left = (0, 0, 255) if flicker else (255, 0, 0)
                color_right = (255, 0, 0) if flicker else (0, 0, 255)
                cv2.circle(frame, (box_x1 + 16, box_y1 - 6), 5, color_left, -1)
                cv2.circle(frame, (box_x2 - 16, box_y1 - 6), 5, color_right, -1)

            # Feature 3: Medical Symbol Badge (Red Cross)
            if veh.get("symbol_detected", True):
                cx, cy = box_x1 + 14, box_y1 + 14
                cv2.rectangle(frame, (cx - 2, cy - 8), (cx + 2, cy + 8), (0, 0, 255), -1)
                cv2.rectangle(frame, (cx - 8, cy - 2), (cx + 8, cy + 2), (0, 0, 255), -1)

            # Feature 2: AMBULANCE Text Badge
            if veh.get("text_detected", True):
                cv2.putText(frame, "AMBULANCE", (box_x1 + 25, box_y1 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            # Overlay Multi-Feature Combined Score & Tracking HUD
            score_pct = int(veh.get("combined_score", 0.88) * 100)
            tag_text = f"🚨 {veh['tracking_id']} | CONF: {score_pct}% | {dist:.1f}m"
            cv2.rectangle(frame, (box_x1 - 10, max(0, box_y1 - 36)), (box_x2 + 35, box_y1 - 12), (10, 10, 15), -1)
            cv2.putText(frame, tag_text, (box_x1 - 5, box_y1 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 229, 255), 1, cv2.LINE_AA)
            
            plate_text = f"PLATE: {veh['plate']} | ROOF: {'OK' if veh.get('roof_lights_detected') else 'NO'}"
            cv2.putText(frame, plate_text, (box_x1 - 5, box_y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 136), 1, cv2.LINE_AA)

        return frame

    def get_jpeg_bytes(self, lane_id: str) -> bytes:
        """Encode simulated frame to JPEG bytes for MJPEG streaming."""
        frame = self.generate_frame(lane_id)
        _, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes()
