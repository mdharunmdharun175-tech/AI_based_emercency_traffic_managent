"""
Database Layer — MongoDB via Motor (async)
All collections and CRUD helpers live here.

Collections:
  detections  — every YOLOv8 detection event
  alerts      — system alert log
  gps_history — historical GPS tracks
  signal_log  — every signal state change
"""

import time
import logging
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from bson import ObjectId

from config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[settings.MONGODB_DB_NAME]


# ── Detection collection ──────────────────────────────────────

async def insert_detection(result: dict) -> str:
    """Insert a detection result and return its inserted id."""
    db = get_db()
    try:
        res = await db.detections.insert_one({**result, "created_at": time.time()})
        return str(res.inserted_id)
    except Exception as e:
        logger.error(f"DB insert_detection failed: {e}")
        return ""


async def get_recent_detections(limit: int = 50) -> List[dict]:
    db = get_db()
    try:
        cursor = db.detections.find(
            {},
            {"_id": 1, "timestamp": 1, "ambulance_detected": 1, "ambulance_plate": 1,
             "processing_time_ms": 1, "vehicles": 1}
        ).sort("timestamp", DESCENDING).limit(limit)
        docs = await cursor.to_list(length=limit)
        for d in docs:
            d["id"] = str(d.pop("_id"))
        return docs
    except Exception as e:
        logger.error(f"DB get_recent_detections failed: {e}")
        return []


async def get_ambulance_detections_today() -> int:
    db = get_db()
    today_start = time.time() - (time.time() % 86400)
    try:
        return await db.detections.count_documents(
            {"ambulance_detected": True, "timestamp": {"$gte": today_start}}
        )
    except Exception:
        return 0


# ── Alert collection ──────────────────────────────────────────

async def insert_alert(alert_type: str, message: str, metadata: dict = None) -> str:
    db = get_db()
    try:
        res = await db.alerts.insert_one({
            "type": alert_type,
            "message": message,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })
        return str(res.inserted_id)
    except Exception as e:
        logger.error(f"DB insert_alert failed: {e}")
        return ""


async def get_recent_alerts(limit: int = 30) -> List[dict]:
    db = get_db()
    try:
        cursor = db.alerts.find({}).sort("timestamp", DESCENDING).limit(limit)
        docs = await cursor.to_list(length=limit)
        for d in docs:
            d["id"] = str(d.pop("_id"))
        return docs
    except Exception as e:
        logger.error(f"DB get_recent_alerts failed: {e}")
        return []


# ── GPS history ───────────────────────────────────────────────

async def insert_gps_point(vehicle_id: str, lat: float, lng: float, speed: float, is_emergency: bool):
    db = get_db()
    try:
        await db.gps_history.insert_one({
            "vehicle_id": vehicle_id,
            "lat": lat,
            "lng": lng,
            "speed_kmh": speed,
            "is_emergency": is_emergency,
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.debug(f"GPS history insert failed: {e}")


async def get_vehicle_track(vehicle_id: str, last_n: int = 100) -> List[dict]:
    db = get_db()
    try:
        cursor = db.gps_history.find(
            {"vehicle_id": vehicle_id},
            {"_id": 0, "lat": 1, "lng": 1, "speed_kmh": 1, "timestamp": 1}
        ).sort("timestamp", DESCENDING).limit(last_n)
        return await cursor.to_list(length=last_n)
    except Exception:
        return []


# ── Signal log ────────────────────────────────────────────────

async def log_signal_change(lane_id: str, old_state: str, new_state: str, reason: str):
    db = get_db()
    try:
        await db.signal_log.insert_one({
            "lane_id": lane_id,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.debug(f"Signal log insert failed: {e}")


# ── Analytics aggregations ────────────────────────────────────

async def get_hourly_stats() -> List[dict]:
    """Aggregate vehicle detections per hour for the last 24h."""
    db = get_db()
    since = time.time() - 86400
    try:
        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {
                "_id": {"$floor": {"$divide": [{"$subtract": ["$timestamp", since]}, 3600]}},
                "total_vehicles": {"$sum": {"$size": "$vehicles"}},
                "ambulances": {"$sum": {"$cond": ["$ambulance_detected", 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]
        cursor = db.detections.aggregate(pipeline)
        return await cursor.to_list(length=24)
    except Exception as e:
        logger.error(f"Hourly stats aggregation failed: {e}")
        return []


async def close_db():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")
