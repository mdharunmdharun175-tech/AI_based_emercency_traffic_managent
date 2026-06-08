"""Pydantic data models for request/response validation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SignalState(str, Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"


class VehicleType(str, Enum):
    CAR = "car"
    TRUCK = "truck"
    BUS = "bus"
    AMBULANCE = "ambulance"
    MOTORCYCLE = "motorcycle"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DetectedVehicle(BaseModel):
    id: str
    type: VehicleType
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBox
    plate_number: Optional[str] = None
    is_emergency: bool = False


class DetectionResult(BaseModel):
    frame_id: str
    timestamp: float
    vehicles: List[DetectedVehicle]
    ambulance_detected: bool
    ambulance_plate: Optional[str] = None
    siren_detected: bool = False
    processing_time_ms: float


class LaneSignal(BaseModel):
    lane_id: str
    name: str
    state: SignalState
    priority: bool = False
    queue_length: int = 0
    wait_time_seconds: int = 0


class SignalOverride(BaseModel):
    lane_id: str
    state: SignalState
    duration_seconds: int = 30
    reason: str = "manual_override"


class GPSPosition(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    heading: float = 0.0
    timestamp: float
    is_emergency: bool = False


class SystemStatus(BaseModel):
    ai_model_loaded: bool
    active_corridors: int
    total_detections: int
    uptime_seconds: int


class AlertEvent(BaseModel):
    id: str
    type: str  # emergency | info | success | warning
    message: str
    timestamp: float
    metadata: Dict[str, Any] = {}


class TrafficAnalytics(BaseModel):
    period: str
    avg_vehicles_per_minute: float
    peak_congestion_hour: int
    total_ambulances_detected: int
    avg_corridor_clear_time_seconds: float
    success_rate_percent: float
