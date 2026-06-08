"""
MongoDB Database Layer (async via Motor)
Stores detection events, signal logs, GPS history, and analytics.
"""

import os
import time
import logging
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ai_traffic")


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect(cls):
        try:
            cls.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            cls.db = cls.client["ai_traffic"]
            await cls.client.admin.command("ping")
            logger.info(f"✅ MongoDB connected: {MONGO_URI}")
            await cls._create_indexes()
        except Exception as e:
            logger.warning(f"⚠️  MongoDB unavailable ({e}). Running in memory-only mode.")
            cls.client = None
            cls.db = None

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    async def _create_indexes(cls):
        """Create indexes for fast queries."""
        if not cls.db:
            return
        await cls.db.detections.create_index([("timestamp", DESCENDING)])
        await cls.db.detections.create_index([("ambulance_detected", 1)])
        await cls.db.gps_positions.create_index([("vehicle_id", 1), ("timestamp", DESCENDING)])
        await cls.db.signal_logs.create_index([("timestamp", DESCENDING)])
        await cls.db.alerts.create_index([("timestamp", DESCENDING)])


# ── Detection Events ──────────────────────────────────────────────────────────

async def save_detection(result: dict):
    if not Database.db:
        return
    try:
        await Database.db.detections.insert_one({**result, "saved_at": time.time()})
    except Exception as e:
        logger.error(f"DB save_detection failed: {e}")


async def get_recent_detections(limit: int = 50) -> List[dict]:
    if not Database.db:
        return []
    cursor = Database.db.detections.find(
        {}, {"_id": 0}
    ).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


async def get_ambulance_detections(limit: int = 20) -> List[dict]:
    if not Database.db:
        return []
    cursor = Database.db.detections.find(
        {"ambulance_detected": True}, {"_id": 0}
    ).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ── Signal Logs ───────────────────────────────────────────────────────────────

async def log_signal_event(lane_id: str, state: str, reason: str, duration: int = 0):
    if not Database.db:
        return
    try:
        await Database.db.signal_logs.insert_one({
            "lane_id": lane_id,
            "state": state,
            "reason": reason,
            "duration_seconds": duration,
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.error(f"DB log_signal_event failed: {e}")


async def get_signal_logs(limit: int = 100) -> List[dict]:
    if not Database.db:
        return []
    cursor = Database.db.signal_logs.find(
        {}, {"_id": 0}
    ).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ── GPS History ───────────────────────────────────────────────────────────────

async def save_gps_position(position: dict):
    if not Database.db:
        return
    try:
        await Database.db.gps_positions.insert_one({**position, "recorded_at": time.time()})
    except Exception as e:
        logger.error(f"DB save_gps failed: {e}")


async def get_vehicle_track(vehicle_id: str, limit: int = 200) -> List[dict]:
    """Return last N GPS points for a vehicle (for route replay)."""
    if not Database.db:
        return []
    cursor = Database.db.gps_positions.find(
        {"vehicle_id": vehicle_id}, {"_id": 0}
    ).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ── Alerts ────────────────────────────────────────────────────────────────────

async def save_alert(alert_type: str, message: str, metadata: dict = {}):
    if not Database.db:
        return
    try:
        await Database.db.alerts.insert_one({
            "type": alert_type,
            "message": message,
            "metadata": metadata,
            "timestamp": time.time(),
            "acknowledged": False,
        })
    except Exception as e:
        logger.error(f"DB save_alert failed: {e}")


async def get_alerts(limit: int = 50, unread_only: bool = False) -> List[dict]:
    if not Database.db:
        return []
    query = {"acknowledged": False} if unread_only else {}
    cursor = Database.db.alerts.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ── Analytics Aggregation ────────────────────────────────────────────────────

async def get_daily_summary() -> dict:
    """Aggregate today's stats from MongoDB."""
    if not Database.db:
        return {}
    day_start = time.time() - 86400
    pipeline = [
        {"$match": {"timestamp": {"$gte": day_start}}},
        {"$group": {
            "_id": None,
            "total_detections": {"$sum": 1},
            "ambulances": {"$sum": {"$cond": ["$ambulance_detected", 1, 0]}},
            "avg_processing_ms": {"$avg": "$processing_time_ms"},
        }},
    ]
    try:
        result = await Database.db.detections.aggregate(pipeline).to_list(length=1)
        return result[0] if result else {}
    except Exception as e:
        logger.error(f"DB aggregation failed: {e}")
        return {}
