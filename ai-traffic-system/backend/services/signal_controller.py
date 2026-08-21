"""
Finite State Machine (FSM) Traffic Signal Controller (v2.1 — Dynamic Stop-Line Emergency Preemption)
Supports:
- Normal circular 30-second rotation (Lane A -> Lane B -> Lane C -> Lane D)
- Live countdown calculation for all 4 lanes
- Multi-Feature Priority Queue management (Nearest Distance, ETA, Combined Confidence Score sorting)
- All-Red Safety State (2-second delay)
- Dynamic Emergency Preemption (holds GREEN until ambulance physically crosses virtual stop line)
- Automatic sequential serving of multiple ambulances in queue
- Emergency Pause & Saved Timer Resume
- Emergency Served Lane Skip Logic (single rotation skip)
- Persistent SQLite & System Event Logging
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from database_sqlite import SQLiteDatabase

logger = logging.getLogger(__name__)

LANES = ["Lane A", "Lane B", "Lane C", "Lane D"]
LANE_KEYS = ["A", "B", "C", "D"]
NORMAL_GREEN_DURATION = 30  # seconds
SAFETY_RED_DURATION = 2     # seconds

# Map normalized lane names
NORMALIZE_LANE = {
    "A": "Lane A", "B": "Lane B", "C": "Lane C", "D": "Lane D",
    "L1": "Lane A", "L2": "Lane B", "L3": "Lane C", "L4": "Lane D",
    "LANE A": "Lane A", "LANE B": "Lane B", "LANE C": "Lane C", "LANE D": "Lane D",
    "LANE 01": "Lane A", "LANE 02": "Lane B", "LANE 03": "Lane C", "LANE 04": "Lane D",
}


class ControllerState(str, Enum):
    NORMAL = "NORMAL"
    EMERGENCY_PAUSE = "EMERGENCY_PAUSE"
    ALL_RED_SAFETY = "ALL_RED_SAFETY"
    EMERGENCY_GREEN = "EMERGENCY_GREEN"
    RESUME = "RESUME"
    SKIP = "SKIP"


class SignalController:
    def __init__(self):
        # FSM State
        self.state: ControllerState = ControllerState.NORMAL
        
        # Normal rotation tracking: 0 -> Lane A, 1 -> Lane B, 2 -> Lane C, 3 -> Lane D
        self.current_lane_index: int = 0
        self.current_green_remaining: int = NORMAL_GREEN_DURATION
        
        # Paused state storage during emergency
        self.paused_lane: Optional[str] = None
        self.paused_remaining: int = 0
        
        # All-Red Safety timer
        self.safety_timer: int = 0
        
        # Emergency lane state
        self.active_emergency_lane: Optional[str] = None
        self.active_emergency_vehicle: Optional[Dict[str, Any]] = None
        
        # Priority Queue for multiple ambulances
        # Each item: {
        #   'tracking_id': str, 'lane_id': str, 'distance': float, 'eta': float, 'confidence': float,
        #   'combined_score': float, 'roof_lights_detected': bool, 'text_detected': bool,
        #   'symbol_detected': bool, 'symbol_name': str, 'shape_verified': bool, 'plate': str
        # }
        self.priority_queue: List[Dict[str, Any]] = []
        
        # Skip lanes tracking (lanes served in emergency to skip once in circular cycle)
        self.skip_lanes: Set[str] = set()
        
        # Rotation cycle counter & served tracker
        self.current_rotation_count: int = 1
        self.lanes_served_this_rotation: Set[str] = set()

        self._add_event_log("SYSTEM", "Signal Controller FSM Initialized", "Dynamic Stop-Line Preemption active")

    # ── Normalize lane helper ─────────────────────────────────
    def _norm_lane(self, lane_str: str) -> str:
        s = str(lane_str).upper().strip()
        return NORMALIZE_LANE.get(s, NORMALIZE_LANE.get(s[:1], "Lane A"))

    # ── Multi-Feature Priority Queue Management ────────────────
    def add_or_update_emergency_vehicle(
        self,
        tracking_id: str,
        lane_id: str,
        distance: float,
        eta: float,
        confidence: float,
        plate: str = "",
        roof_lights_detected: bool = False,
        text_detected: bool = False,
        symbol_detected: bool = False,
        symbol_name: str = "",
        shape_verified: bool = False,
        combined_score: Optional[float] = None,
    ):
        """
        Add or update an ambulance in the priority queue with multi-feature verification scores.
        Priority Queue is sorted by:
        1. Nearest Distance (ascending)
        2. ETA (ascending)
        3. Combined Confidence Score (descending)
        """
        norm_lane = self._norm_lane(lane_id)
        c_score = combined_score if combined_score is not None else confidence

        existing = next((v for v in self.priority_queue if v["tracking_id"] == tracking_id), None)
        if existing:
            existing["distance"] = round(distance, 1)
            existing["eta"] = round(eta, 1)
            existing["confidence"] = round(c_score, 3)
            existing["combined_score"] = round(c_score, 3)
            existing["lane_id"] = norm_lane
            if plate:
                existing["plate"] = plate
            if roof_lights_detected:
                existing["roof_lights_detected"] = True
            if text_detected:
                existing["text_detected"] = True
            if symbol_detected:
                existing["symbol_detected"] = True
                existing["symbol_name"] = symbol_name
            if shape_verified:
                existing["shape_verified"] = True
        else:
            vehicle = {
                "tracking_id": tracking_id,
                "lane_id": norm_lane,
                "distance": round(distance, 1),
                "eta": round(eta, 1),
                "confidence": round(c_score, 3),
                "combined_score": round(c_score, 3),
                "plate": plate or f"AMB-{tracking_id[-3:]}",
                "roof_lights_detected": roof_lights_detected,
                "text_detected": text_detected,
                "symbol_detected": symbol_detected,
                "symbol_name": symbol_name or ("Red Cross" if symbol_detected else "None"),
                "shape_verified": shape_verified,
                "detected_at": time.time(),
            }
            self.priority_queue.append(vehicle)
            self._add_event_log(
                "AMBULANCE_DETECTED",
                f"Ambulance {tracking_id} verified on {norm_lane}",
                f"Distance: {round(distance, 1)}m, ETA: {round(eta, 1)}s, Score: {round(c_score*100, 1)}%"
            )
            SQLiteDatabase.log_emergency_event(
                event_type="DETECTION",
                lane_id=norm_lane,
                tracking_id=tracking_id,
                plate_number=plate,
                distance_meters=distance,
                eta_seconds=eta,
                confidence=c_score,
                details=vehicle
            )

        # Priority Sorting: 1. Distance (nearest), 2. ETA, 3. -Combined Score
        self.priority_queue.sort(key=lambda x: (x["distance"], x["eta"], -x["combined_score"]))
        
        # Log Priority Queue state
        SQLiteDatabase.log_priority_queue(self.priority_queue, active_lane=self.active_emergency_lane or "")

        # Trigger emergency preemption if in NORMAL or RESUME state
        if self.state in (ControllerState.NORMAL, ControllerState.RESUME) and self.priority_queue:
            self._trigger_emergency_mode()
        elif self.state in (ControllerState.EMERGENCY_PAUSE, ControllerState.ALL_RED_SAFETY) and self.priority_queue:
            top_veh = self.priority_queue[0]
            self.active_emergency_lane = top_veh["lane_id"]
            self.active_emergency_vehicle = top_veh

    # ── Feature 4: Ambulance Stop Line Crossing Completed ─────
    def mark_ambulance_passed(self, tracking_id: str):
        """
        Invoked when a tracked ambulance physically crosses the virtual stop line.
        Ends the emergency phase for this vehicle and checks the queue for remaining ambulances.
        """
        vehicle = next((v for v in self.priority_queue if v["tracking_id"] == tracking_id), None)
        active_match = self.active_emergency_vehicle and self.active_emergency_vehicle.get("tracking_id") == tracking_id

        if vehicle or active_match:
            lane = vehicle["lane_id"] if vehicle else self.active_emergency_lane
            logger.info(f"🏁 Ambulance {tracking_id} passed stop line on {lane}")
            self._add_event_log(
                "AMBULANCE_PASSED",
                f"Ambulance {tracking_id} Crossed Stop Line",
                f"Emergency complete for {lane}"
            )
            SQLiteDatabase.log_emergency_event(
                event_type="PASSED",
                lane_id=lane or "",
                tracking_id=tracking_id
            )

            # Remove passed vehicle from Priority Queue
            self.priority_queue = [v for v in self.priority_queue if v["tracking_id"] != tracking_id]

            # Mark lane to skip once in the current circular rotation cycle
            if lane:
                self.skip_lanes.add(lane)
                self._add_event_log("SKIP_LANE_MARKED", f"{lane} added to Skip List", "Lane served during Emergency Mode will be skipped once")

            # Check if additional ambulances exist in Priority Queue
            if self.priority_queue:
                # Automatically transition to serve the next priority ambulance
                next_veh = self.priority_queue[0]
                self._add_event_log(
                    "NEXT_EMERGENCY",
                    f"Serving Next Ambulance {next_veh['tracking_id']}",
                    f"Target lane: {next_veh['lane_id']}"
                )
                self.state = ControllerState.ALL_RED_SAFETY
                self.safety_timer = SAFETY_RED_DURATION
                self.active_emergency_lane = next_veh["lane_id"]
                self.active_emergency_vehicle = next_veh
            else:
                # Queue empty: Clear emergency state & resume saved countdown
                self.active_emergency_lane = None
                self.active_emergency_vehicle = None
                self._resume_interrupted_signal()

    def _trigger_emergency_mode(self):
        """Pause current normal signal & start emergency preemption sequence."""
        if not self.priority_queue:
            return

        target_veh = self.priority_queue[0]
        current_lane = LANES[self.current_lane_index]

        # 1. Pause active signal state & save remaining timer
        self.paused_lane = current_lane
        self.paused_remaining = max(1, self.current_green_remaining)
        
        self.state = ControllerState.EMERGENCY_PAUSE
        self._add_event_log(
            "EMERGENCY_MODE_ACTIVATED",
            f"Emergency Mode Activated for {target_veh['lane_id']}",
            f"Interrupted {current_lane} with {self.paused_remaining}s saved"
        )
        SQLiteDatabase.log_signal_event(
            lane_id=current_lane,
            old_state="GREEN",
            new_state="RED_PAUSED",
            reason="Emergency Interrupt",
            duration_seconds=self.paused_remaining,
            controller_state="EMERGENCY_PAUSE"
        )

        # 2. Enter 2-second All-Red Safety State
        self.state = ControllerState.ALL_RED_SAFETY
        self.safety_timer = SAFETY_RED_DURATION
        self.active_emergency_lane = target_veh["lane_id"]
        self.active_emergency_vehicle = target_veh

    def _resume_interrupted_signal(self):
        """Resume exact countdown of interrupted signal."""
        if self.paused_lane and self.paused_remaining > 0:
            self.state = ControllerState.RESUME
            self.current_lane_index = LANES.index(self.paused_lane)
            self.current_green_remaining = self.paused_remaining
            self._add_event_log(
                "RESUME_SIGNAL",
                f"Resumed {self.paused_lane}",
                f"Restored saved countdown: {self.paused_remaining} sec remaining"
            )
            SQLiteDatabase.log_signal_event(
                lane_id=self.paused_lane,
                old_state="EMERGENCY_RED",
                new_state="GREEN_RESUMED",
                reason="Emergency Cleared",
                duration_seconds=self.paused_remaining,
                controller_state="RESUME"
            )
            self.paused_lane = None
            self.paused_remaining = 0
        else:
            self.state = ControllerState.NORMAL
            self.current_green_remaining = NORMAL_GREEN_DURATION

    # ── 1-Second FSM Tick ─────────────────────────────────────
    def tick(self):
        """Advance controller state by 1 second."""
        if self.state == ControllerState.ALL_RED_SAFETY:
            self.safety_timer -= 1
            if self.safety_timer <= 0:
                # Transition to EMERGENCY_GREEN
                self.state = ControllerState.EMERGENCY_GREEN
                self._add_event_log(
                    "EMERGENCY_GREEN",
                    f"{self.active_emergency_lane} GREEN (Dynamic Emergency)",
                    "Holding GREEN until ambulance crosses stop line. All remaining lanes RED."
                )

        elif self.state == ControllerState.EMERGENCY_GREEN:
            # Do NOT decrement any timer here!
            # The GREEN signal remains active until mark_ambulance_passed() is triggered by stop line crossing.
            # Timeout safeguard (90 seconds) in case tracking is completely lost:
            if self.active_emergency_vehicle:
                elapsed = time.time() - self.active_emergency_vehicle.get("detected_at", time.time())
                if elapsed > 90.0:
                    logger.warning("Emergency mode timeout safeguard triggered (>90s)")
                    tid = self.active_emergency_vehicle.get("tracking_id", "")
                    if tid:
                        self.mark_ambulance_passed(tid)

        elif self.state in (ControllerState.NORMAL, ControllerState.RESUME):
            self.current_green_remaining -= 1
            
            if self.current_green_remaining <= 0:
                # Active green lane finished! Move to next lane in circular rotation.
                self._advance_to_next_lane()

    def _advance_to_next_lane(self):
        """Advance circular rotation A -> B -> C -> D with Skip logic handling."""
        completed_lane = LANES[self.current_lane_index]
        self.lanes_served_this_rotation.add(completed_lane)

        # Move index to next lane
        next_index = (self.current_lane_index + 1) % 4
        next_lane = LANES[next_index]

        # Check Skip logic: if next lane is in skip_lanes, skip it ONCE!
        if next_lane in self.skip_lanes:
            self.skip_lanes.remove(next_lane)
            self._add_event_log(
                "SKIP_LANE_EXECUTED",
                f"Skip {next_lane}",
                f"{next_lane} already served during Emergency Mode"
            )
            SQLiteDatabase.log_signal_event(
                lane_id=next_lane,
                old_state="RED",
                new_state="SKIPPED",
                reason="Skip Mode Executed",
                controller_state="SKIP"
            )
            # Advance once more
            next_index = (next_index + 1) % 4
            next_lane = LANES[next_index]

        # Check if full rotation completed (all 4 lanes visited / processed)
        if len(self.lanes_served_this_rotation) >= 4 or next_index == 0:
            self.lanes_served_this_rotation.clear()
            self.current_rotation_count += 1
            if self.skip_lanes:
                self.skip_lanes.clear()
                self._add_event_log("NORMAL_CYCLE_RESTORED", "Normal Cycle Restored", "Rotation reset: A -> B -> C -> D")

        self.current_lane_index = next_index
        self.current_green_remaining = NORMAL_GREEN_DURATION
        self.state = ControllerState.NORMAL

        self._add_event_log(
            "SIGNAL_CHANGED",
            f"{next_lane} GREEN ({NORMAL_GREEN_DURATION}s)",
            f"Next step in circular rotation"
        )
        SQLiteDatabase.log_signal_event(
            lane_id=next_lane,
            old_state="RED",
            new_state="GREEN",
            reason="Normal Rotation",
            duration_seconds=NORMAL_GREEN_DURATION,
            controller_state="NORMAL"
        )

    # ── State queries for UI & WebSocket ──────────────────────
    def get_signal_states(self) -> Dict[str, Dict[str, Any]]:
        """Returns full signal state for all 4 lanes with accurate countdown timers."""
        states = {}
        curr_idx = self.current_lane_index
        rem = self.current_green_remaining

        if self.state == ControllerState.ALL_RED_SAFETY:
            for l in LANES:
                states[l] = {"color": "RED", "countdown": self.safety_timer, "is_active": False, "is_emergency": False}
            return states

        if self.state == ControllerState.EMERGENCY_GREEN and self.active_emergency_lane:
            emg_lane = self.active_emergency_lane
            for l in LANES:
                if l == emg_lane:
                    states[l] = {"color": "GREEN", "countdown": 0, "is_active": True, "is_emergency": True}
                else:
                    states[l] = {"color": "RED", "countdown": 0, "is_active": False, "is_emergency": False}
            return states

        # Normal or Resume mode
        for i, lane in enumerate(LANES):
            if i == curr_idx:
                states[lane] = {
                    "color": "GREEN",
                    "countdown": rem,
                    "is_active": True,
                    "is_emergency": False
                }
            else:
                steps_away = (i - curr_idx) % 4
                red_timer = rem + (steps_away - 1) * NORMAL_GREEN_DURATION
                states[lane] = {
                    "color": "RED",
                    "countdown": max(1, red_timer),
                    "is_active": False,
                    "is_emergency": False
                }
        return states

    def get_full_snapshot(self) -> Dict[str, Any]:
        """Returns full JSON state payload for WebSocket & REST API."""
        signals = self.get_signal_states()
        return {
            "controller_state": self.state.value,
            "active_green_lane": LANES[self.current_lane_index] if self.state not in (ControllerState.ALL_RED_SAFETY, ControllerState.EMERGENCY_GREEN) else self.active_emergency_lane,
            "current_green_remaining": self.current_green_remaining,
            "paused_lane": self.paused_lane,
            "paused_remaining": self.paused_remaining,
            "active_emergency_lane": self.active_emergency_lane,
            "priority_queue": self.priority_queue,
            "skip_lanes": list(self.skip_lanes),
            "signals": signals,
            "timestamp": time.time(),
        }

    def _add_event_log(self, event_type: str, title: str, details: str):
        msg = f"[{time.strftime('%H:%M:%S')}] {title} — {details}"
        logger.info(f"🚦 FSM LOG: {msg}")
        SQLiteDatabase.add_system_log(
            log_level="INFO",
            message=msg,
            category=event_type,
            metadata={"title": title, "details": details, "state": self.state.value}
        )

    def manual_override(self, lane_id: str, state: str = "GREEN"):
        """Manual operator override."""
        norm_lane = self._norm_lane(lane_id)
        if norm_lane in LANES:
            self.current_lane_index = LANES.index(norm_lane)
            self.current_green_remaining = NORMAL_GREEN_DURATION
            self.state = ControllerState.NORMAL
            self._add_event_log("MANUAL_OVERRIDE", f"Manual Override: {norm_lane} → {state}", "Operator manual control")

    def reset_fsm(self):
        """Reset signal controller to default Normal state."""
        self.state = ControllerState.NORMAL
        self.current_lane_index = 0
        self.current_green_remaining = NORMAL_GREEN_DURATION
        self.paused_lane = None
        self.paused_remaining = 0
        self.active_emergency_lane = None
        self.active_emergency_vehicle = None
        self.priority_queue.clear()
        self.skip_lanes.clear()
        self.lanes_served_this_rotation.clear()
        self._add_event_log("RESET", "Signals Reset", "Controller reset to normal circular rotation")
