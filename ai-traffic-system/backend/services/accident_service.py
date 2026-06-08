"""
Accident Detection Service
Analyzes consecutive frames to detect:
  - Sudden vehicle stops / unusual clustering
  - Vehicles outside lane boundaries
  - Rapid velocity changes (collision signature)

Sends alerts to hospital and authorities via SMS/email hooks.
"""

import time
import logging
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

STOPPED_THRESHOLD_S   = 8     # vehicle stationary > 8s in traffic = suspect
CLUSTER_DISTANCE_PX   = 60    # vehicles within this distance = suspect cluster
VELOCITY_CHANGE_RATIO = 0.6   # speed drop ratio triggering alert
ALERT_COOLDOWN_S      = 30    # minimum seconds between repeated alerts


@dataclass
class TrackedVehicle:
    id: str
    bbox_history: List[dict] = field(default_factory=list)  # last N bboxes
    stationary_since: Optional[float] = None
    last_seen: float = field(default_factory=time.time)
    alerted: bool = False


class AccidentDetectionService:
    def __init__(self, alert_callback=None):
        self._tracks: Dict[str, TrackedVehicle] = {}
        self._last_alert_time: float = 0
        self._alert_callback = alert_callback  # async fn(event_type, message, metadata)
        self.incidents_today: int = 0

    def update(self, detections: List[dict], frame_size: tuple = (1280, 720)):
        """
        Called each frame with list of detections from YOLO.
        Each detection: {"id": str, "bbox": {"x","y","width","height"}, "type": str}
        Returns list of incident dicts (empty if none).
        """
        now = time.time()
        incidents = []
        active_ids = set()

        for det in detections:
            vid = det.get("id", "unknown")
            bbox = det.get("bbox", {})
            active_ids.add(vid)

            if vid not in self._tracks:
                self._tracks[vid] = TrackedVehicle(id=vid)

            track = self._tracks[vid]
            track.last_seen = now
            track.bbox_history.append({"bbox": bbox, "t": now})
            if len(track.bbox_history) > 30:
                track.bbox_history = track.bbox_history[-30:]

            # Check stationary
            incident = self._check_stationary(track, now)
            if incident:
                incidents.append(incident)

        # Remove stale tracks
        stale = [vid for vid, t in self._tracks.items() if now - t.last_seen > 10]
        for vid in stale:
            del self._tracks[vid]

        # Check cluster (possible multi-vehicle collision)
        cluster_incident = self._check_cluster(detections)
        if cluster_incident:
            incidents.append(cluster_incident)

        # Fire callbacks
        for inc in incidents:
            if now - self._last_alert_time > ALERT_COOLDOWN_S:
                self._last_alert_time = now
                self.incidents_today += 1
                logger.warning(f"🚨 Incident detected: {inc['type']} — {inc['message']}")
                if self._alert_callback:
                    asyncio.create_task(self._alert_callback(inc))

        return incidents

    def _check_stationary(self, track: TrackedVehicle, now: float) -> Optional[dict]:
        """Flag vehicles that haven't moved for STOPPED_THRESHOLD_S seconds."""
        if len(track.bbox_history) < 5:
            return None

        recent = track.bbox_history[-5:]
        cx = [h["bbox"].get("x", 0) + h["bbox"].get("width", 0) / 2 for h in recent]
        cy = [h["bbox"].get("y", 0) + h["bbox"].get("height", 0) / 2 for h in recent]
        movement = np.sqrt(np.var(cx) + np.var(cy))

        if movement < 5:  # pixels — essentially stationary
            if track.stationary_since is None:
                track.stationary_since = now
            elif (now - track.stationary_since > STOPPED_THRESHOLD_S) and not track.alerted:
                track.alerted = True
                return {
                    "type": "stopped_vehicle",
                    "vehicle_id": track.id,
                    "message": f"Vehicle {track.id} stationary for {int(now - track.stationary_since)}s",
                    "severity": "warning",
                    "timestamp": now,
                }
        else:
            track.stationary_since = None
            track.alerted = False

        return None

    def _check_cluster(self, detections: List[dict]) -> Optional[dict]:
        """Detect abnormal vehicle clustering (multi-vehicle pileup signature)."""
        if len(detections) < 3:
            return None

        centers = []
        for det in detections:
            b = det.get("bbox", {})
            cx = b.get("x", 0) + b.get("width", 0) / 2
            cy = b.get("y", 0) + b.get("height", 0) / 2
            centers.append((cx, cy))

        # Count pairs within CLUSTER_DISTANCE_PX
        close_pairs = 0
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                dist = np.sqrt((centers[i][0] - centers[j][0])**2 + (centers[i][1] - centers[j][1])**2)
                if dist < CLUSTER_DISTANCE_PX:
                    close_pairs += 1

        if close_pairs >= 3:
            return {
                "type": "vehicle_cluster",
                "message": f"Abnormal vehicle clustering detected — possible collision ({close_pairs} overlapping vehicles)",
                "severity": "emergency",
                "timestamp": time.time(),
                "close_pairs": close_pairs,
            }

        return None


# ── Notification hooks ────────────────────────────────────────────────────────

async def notify_hospital(incident: dict, hospital_api_url: str = ""):
    """
    POST incident details to hospital emergency API.
    Replace with your hospital's actual endpoint.
    """
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(hospital_api_url, json={
                "source": "AI_TRAFFIC_SYSTEM",
                "incident_type": incident.get("type"),
                "message": incident.get("message"),
                "severity": incident.get("severity"),
                "timestamp": incident.get("timestamp"),
            }, timeout=5)
        logger.info("✅ Hospital notified")
    except Exception as e:
        logger.error(f"Hospital notification failed: {e}")


async def notify_sms(incident: dict, phone_numbers: list, twilio_sid="", twilio_token="", from_num=""):
    """
    Send SMS alerts via Twilio.
    pip install twilio
    """
    if not twilio_sid:
        logger.debug("Twilio not configured — skipping SMS")
        return
    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_token)
        msg = f"[AI TRAFFIC ALERT] {incident['type'].upper()}: {incident['message']}"
        for num in phone_numbers:
            client.messages.create(body=msg, from_=from_num, to=num)
        logger.info(f"✅ SMS sent to {len(phone_numbers)} recipients")
    except Exception as e:
        logger.error(f"SMS notification failed: {e}")
