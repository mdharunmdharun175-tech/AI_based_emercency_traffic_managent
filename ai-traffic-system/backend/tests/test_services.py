"""
Unit tests for AI Traffic System backend.
Run: pytest tests/ -v
"""

import time
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# ── Signal Service Tests ────────────────────────────────────────────────────

class TestSignalService:
    def setup_method(self):
        # Patch serial to avoid hardware dependency
        with patch("services.signal_service.serial", create=True):
            from services.signal_service import SignalService
            self.svc = SignalService()

    def test_initial_all_red(self):
        states = self.svc.get_all_states()
        for lane in states:
            assert lane["state"] == "red", f"{lane['lane_id']} should start RED"

    def test_activate_corridor_sets_green(self):
        self.svc._states = {"L1": "red", "L2": "red", "L3": "red", "L4": "red"}
        self.svc._arduino = None  # no hardware
        # Patch asyncio task creation
        with patch("asyncio.create_task"):
            self.svc.activate_corridor("L2")
        assert self.svc._states["L2"] == "green"
        assert self.svc._states["L1"] == "red"
        assert self.svc._states["L3"] == "red"

    def test_activate_corridor_sets_priority(self):
        self.svc._arduino = None
        with patch("asyncio.create_task"):
            self.svc.activate_corridor("L3")
        assert self.svc._priority_lane == "L3"

    def test_active_corridors_count(self):
        self.svc._states = {"L1": "red", "L2": "green", "L3": "red", "L4": "green"}
        assert self.svc.active_corridors() == 2

    def test_manual_override(self):
        self.svc._arduino = None
        self.svc.manual_override("L1", "green", 30)
        assert self.svc._states["L1"] == "green"

    def test_invalid_lane_raises(self):
        with pytest.raises(ValueError):
            self.svc.activate_corridor("L99")

    def test_invalid_state_raises(self):
        with pytest.raises(ValueError):
            self.svc.manual_override("L1", "purple")

    def test_detect_lane_from_y_position(self):
        assert self.svc.detect_lane_from_position(90, 720) == "L1"
        assert self.svc.detect_lane_from_position(200, 720) == "L2"
        assert self.svc.detect_lane_from_position(400, 720) == "L3"
        assert self.svc.detect_lane_from_position(600, 720) == "L4"

    def test_reset_to_normal(self):
        self.svc._priority_lane = "L3"
        self.svc.reset_to_normal()
        assert self.svc._priority_lane is None


# ── Density Service Tests ───────────────────────────────────────────────────

class TestDensityService:
    def setup_method(self):
        from services.density_service import TrafficDensityService
        self.svc = TrafficDensityService()

    def _make_detections(self, count: int, lane_y_center: float = 200):
        return [
            {"id": str(i), "bbox": {"x": i * 50, "y": lane_y_center - 20, "width": 60, "height": 40}}
            for i in range(count)
        ]

    def test_initial_density_low(self):
        assert self.svc.get_density_level() == "low"

    def test_low_density_after_few_vehicles(self):
        self.svc.update(self._make_detections(3), 720)
        assert self.svc.get_density_level() in ("low", "medium")

    def test_high_density_many_vehicles(self):
        for _ in range(15):
            self.svc.update(self._make_detections(30, 600), 720)
        assert self.svc.get_density_level() == "high"

    def test_optimal_green_time_in_range(self):
        self.svc.update(self._make_detections(10), 720)
        t = self.svc.get_optimal_green_time("L1")
        assert 15 <= t <= 60

    def test_forecast_returns_5_points(self):
        forecast = self.svc.get_congestion_forecast()
        assert len(forecast) == 5
        for f in forecast:
            assert "minutes" in f
            assert 0 <= f["pct"] <= 100

    def test_lane_stats_all_4_lanes(self):
        stats = self.svc.get_lane_stats()
        ids = [s["lane_id"] for s in stats]
        assert "L1" in ids and "L4" in ids
        assert len(stats) == 4


# ── Accident Service Tests ──────────────────────────────────────────────────

class TestAccidentService:
    def setup_method(self):
        from services.accident_service import AccidentDetectionService
        self.svc = AccidentDetectionService()

    def _bbox(self, x, y):
        return {"id": f"v_{x}_{y}", "bbox": {"x": x, "y": y, "width": 60, "height": 40}}

    def test_no_incident_normal_traffic(self):
        dets = [self._bbox(i * 200, 300) for i in range(4)]
        incidents = self.svc.update(dets)
        assert incidents == []

    def test_cluster_detected_overlapping(self):
        # 5 vehicles all at same spot
        dets = [self._bbox(100 + i * 5, 300) for i in range(5)]
        incidents = self.svc.update(dets)
        cluster = [i for i in incidents if i["type"] == "vehicle_cluster"]
        assert len(cluster) > 0

    def test_stationary_vehicle_flagged(self):
        det = [self._bbox(300, 300)]
        # Simulate 20 frames without movement
        for _ in range(25):
            incidents = self.svc.update(det)
        stationary = [i for i in incidents if i["type"] == "stopped_vehicle"]
        assert len(stationary) > 0


# ── Schemas Tests ───────────────────────────────────────────────────────────

class TestSchemas:
    def test_detection_result_valid(self):
        from models.schemas import DetectionResult, DetectedVehicle, BoundingBox, VehicleType
        v = DetectedVehicle(
            id="abc123",
            type=VehicleType.AMBULANCE,
            confidence=0.98,
            bbox=BoundingBox(x=100, y=200, width=80, height=50),
            plate_number="KA-05-MK-4822",
            is_emergency=True,
        )
        r = DetectionResult(
            frame_id="frame_001",
            timestamp=time.time(),
            vehicles=[v],
            ambulance_detected=True,
            ambulance_plate="KA-05-MK-4822",
            processing_time_ms=45.2,
        )
        assert r.ambulance_detected is True
        assert r.vehicles[0].confidence == 0.98

    def test_confidence_out_of_range(self):
        from models.schemas import DetectedVehicle, BoundingBox, VehicleType
        with pytest.raises(Exception):
            DetectedVehicle(
                id="x", type=VehicleType.CAR, confidence=1.5,
                bbox=BoundingBox(x=0, y=0, width=10, height=10),
            )
