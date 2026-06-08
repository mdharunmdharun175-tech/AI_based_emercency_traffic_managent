"""
Traffic Density Analysis Service
Computes real-time density, predicts congestion, optimizes signal timing.
"""

import time
import logging
from collections import deque
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Density thresholds (vehicles per frame)
LOW_DENSITY    = 5
MEDIUM_DENSITY = 15
HIGH_DENSITY   = 25

# Green time ranges (seconds)
GREEN_MIN = 15
GREEN_MAX = 60
GREEN_DEFAULT = 30


class TrafficDensityService:
    def __init__(self, history_window: int = 60):
        # Rolling window of per-lane vehicle counts (last N seconds)
        self._lane_counts: Dict[str, deque] = {
            f"L{i}": deque(maxlen=history_window) for i in range(1, 5)
        }
        self._timestamps: deque = deque(maxlen=history_window)
        self._total_counts: deque = deque(maxlen=history_window)

    def update(self, detections: List[dict], frame_height: int = 720):
        """
        Update density estimate from latest YOLO detections.
        Heuristically assigns vehicles to lanes by bbox Y position.
        """
        now = time.time()
        per_lane = {"L1": 0, "L2": 0, "L3": 0, "L4": 0}

        for det in detections:
            bbox = det.get("bbox", {})
            cy = bbox.get("y", 0) + bbox.get("height", 0) / 2
            lane = self._y_to_lane(cy, frame_height)
            per_lane[lane] = per_lane.get(lane, 0) + 1

        for lane, count in per_lane.items():
            self._lane_counts[lane].append(count)

        total = sum(per_lane.values())
        self._total_counts.append(total)
        self._timestamps.append(now)

        return per_lane

    def get_density_level(self, lane_id: str = None) -> str:
        """Returns 'low' | 'medium' | 'high' for a lane or overall."""
        if lane_id and lane_id in self._lane_counts:
            hist = list(self._lane_counts[lane_id])
        else:
            hist = list(self._total_counts)

        if not hist:
            return "low"

        avg = np.mean(hist[-10:]) if len(hist) >= 10 else np.mean(hist)
        if avg >= HIGH_DENSITY:
            return "high"
        if avg >= MEDIUM_DENSITY:
            return "medium"
        return "low"

    def get_optimal_green_time(self, lane_id: str) -> int:
        """
        Proportional green time based on lane density relative to others.
        Ensures each lane gets a fair share but denser lanes get more time.
        """
        counts = {}
        for lid, hist in self._lane_counts.items():
            counts[lid] = np.mean(list(hist)[-5:]) if hist else 0

        total = sum(counts.values()) or 1
        lane_ratio = counts.get(lane_id, 0) / total
        # Map ratio [0, 1] → [GREEN_MIN, GREEN_MAX]
        green_time = int(GREEN_MIN + lane_ratio * (GREEN_MAX - GREEN_MIN))
        return max(GREEN_MIN, min(GREEN_MAX, green_time))

    def get_congestion_forecast(self) -> List[dict]:
        """
        Simple linear extrapolation of current density trend.
        Returns predicted congestion % for next 20 minutes (5-min intervals).
        """
        hist = list(self._total_counts)
        if len(hist) < 5:
            return [{"minutes": i * 5, "pct": 50} for i in range(5)]

        recent = np.array(hist[-30:], dtype=float)
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]

        forecasts = []
        max_vehicles = HIGH_DENSITY * 4  # 4 lanes
        current_avg = float(np.mean(recent[-5:]))

        for step in range(5):
            minutes = (step + 1) * 5
            predicted = current_avg + slope * (minutes * 2)  # ~2 samples/min
            pct = int(min(100, max(0, (predicted / max_vehicles) * 100)))
            forecasts.append({"minutes": minutes, "pct": pct, "raw": round(predicted, 1)})

        return forecasts

    def get_lane_stats(self) -> List[dict]:
        """Return per-lane stats for the dashboard."""
        stats = []
        for lane_id, hist in self._lane_counts.items():
            hist_list = list(hist)
            avg = float(np.mean(hist_list)) if hist_list else 0
            peak = float(max(hist_list)) if hist_list else 0
            stats.append({
                "lane_id": lane_id,
                "avg_vehicles": round(avg, 1),
                "peak_vehicles": round(peak, 1),
                "density_level": self.get_density_level(lane_id),
                "optimal_green_s": self.get_optimal_green_time(lane_id),
            })
        return stats

    @staticmethod
    def _y_to_lane(cy: float, frame_height: int) -> str:
        """Map vertical bbox center to lane ID."""
        ratio = cy / frame_height
        if ratio < 0.25:   return "L1"
        elif ratio < 0.5:  return "L2"
        elif ratio < 0.75: return "L3"
        else:              return "L4"
