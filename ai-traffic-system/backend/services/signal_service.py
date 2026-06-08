"""
Traffic Signal Service
- Manages lane signal states (RED / GREEN / YELLOW)
- Creates green corridors for ambulances
- Interfaces with Arduino via serial port
- Supports manual override
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LANES = ["L1", "L2", "L3", "L4"]
DEFAULT_GREEN_DURATION = 30  # seconds
ARDUINO_PORT = "/dev/ttyUSB0"
ARDUINO_BAUD = 9600


class SignalService:
    def __init__(self):
        self._states: Dict[str, str] = {lane: "red" for lane in LANES}
        self._priority_lane: Optional[str] = None
        self._override_until: Dict[str, float] = {}
        self._arduino = None
        self._lane_names = {
            "L1": "Lane 01 Junction",
            "L2": "Lane 02 Junction",
            "L3": "Lane 03 Junction",
            "L4": "Lane 04 Junction",
        }
        self._try_connect_arduino()

    def _try_connect_arduino(self):
        """Attempt to connect to Arduino for physical signal control."""
        try:
            import serial
            self._arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
            logger.info(f"✅ Arduino connected on {ARDUINO_PORT}")
        except Exception as e:
            logger.warning(f"⚠️  Arduino not available ({e}). Simulating signal control.")
            self._arduino = None

    def get_all_states(self) -> List[dict]:
        return [
            {
                "lane_id": lane,
                "name": self._lane_names[lane],
                "state": self._states[lane],
                "priority": lane == self._priority_lane,
            }
            for lane in LANES
        ]

    def active_corridors(self) -> int:
        return sum(1 for s in self._states.values() if s == "green")

    def activate_corridor(self, lane_id: str, duration: int = DEFAULT_GREEN_DURATION):
        """
        Create green corridor: set target lane GREEN, all others RED.
        Called automatically when ambulance detected on a lane.
        """
        if lane_id not in LANES:
            raise ValueError(f"Unknown lane: {lane_id}")

        self._priority_lane = lane_id
        for lane in LANES:
            self._states[lane] = "green" if lane == lane_id else "red"

        self._send_to_arduino(lane_id)
        logger.info(f"🟢 Green corridor activated: {lane_id} for {duration}s")

        # Schedule auto-reset
        asyncio.create_task(self._reset_after(duration))

    async def _reset_after(self, seconds: int):
        await asyncio.sleep(seconds)
        self.reset_to_normal()

    def reset_to_normal(self):
        """Return to normal timed signal cycling."""
        self._priority_lane = None
        self._states = {"L1": "green", "L2": "red", "L3": "red", "L4": "red"}
        logger.info("🔄 Signals reset to normal cycling")

    def manual_override(self, lane_id: str, state: str, duration: int = 30):
        """Manual override from dashboard operator."""
        if lane_id not in LANES:
            raise ValueError(f"Unknown lane: {lane_id}")
        if state not in ("red", "green", "yellow"):
            raise ValueError(f"Invalid state: {state}")

        self._states[lane_id] = state
        self._override_until[lane_id] = time.time() + duration
        self._send_to_arduino(lane_id)
        logger.info(f"🛠️  Manual override: {lane_id} → {state} for {duration}s")

    def _send_to_arduino(self, green_lane: str):
        """
        Send signal command to Arduino.
        Protocol: "<LANE_ID>:<STATE>;" e.g. "L3:G;L1:R;L2:R;L4:R;"
        """
        if not self._arduino:
            return
        try:
            cmd = ""
            for lane in LANES:
                state_char = "G" if self._states[lane] == "green" else "R"
                cmd += f"{lane}:{state_char};"
            self._arduino.write(cmd.encode())
        except Exception as e:
            logger.error(f"Arduino write failed: {e}")

    def detect_lane_from_position(self, bbox_y: float, frame_height: float) -> str:
        """Heuristic: map bounding box y-position to a lane ID."""
        ratio = bbox_y / frame_height
        if ratio < 0.25:
            return "L1"
        elif ratio < 0.5:
            return "L2"
        elif ratio < 0.75:
            return "L3"
        else:
            return "L4"
