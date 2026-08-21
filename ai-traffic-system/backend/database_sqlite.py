"""
SQLite Database Engine — Zero-dependency local persistence for AI Traffic Control System.
Manages 6 required tables:
1. detection_history
2. emergency_events
3. signal_events
4. distance_history
5. priority_queue_history
6. system_logs
"""

import sqlite3
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "ai_traffic.db"


class SQLiteDatabase:
    _db_path = DB_PATH

    @classmethod
    def get_connection(cls):
        conn = sqlite3.connect(str(cls._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        """Initialize all 6 database tables if they do not exist."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Detection History
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS detection_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        frame_id TEXT,
                        lane_id TEXT,
                        timestamp REAL,
                        vehicle_count INTEGER,
                        ambulance_detected INTEGER,
                        ambulance_plate TEXT,
                        vehicles_json TEXT,
                        processing_time_ms REAL,
                        created_at REAL
                    )
                """)

                # 2. Emergency Events
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS emergency_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT,
                        lane_id TEXT,
                        tracking_id TEXT,
                        plate_number TEXT,
                        distance_meters REAL,
                        eta_seconds REAL,
                        confidence REAL,
                        timestamp REAL,
                        details_json TEXT
                    )
                """)

                # 3. Signal Events
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signal_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lane_id TEXT,
                        old_state TEXT,
                        new_state TEXT,
                        reason TEXT,
                        duration_seconds INTEGER,
                        controller_state TEXT,
                        timestamp REAL
                    )
                """)

                # 4. Distance History
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS distance_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tracking_id TEXT,
                        lane_id TEXT,
                        distance_meters REAL,
                        speed_mps REAL,
                        eta_seconds REAL,
                        confidence REAL,
                        timestamp REAL
                    )
                """)

                # 5. Priority Queue History
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS priority_queue_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        queue_snapshot_json TEXT,
                        active_lane TEXT,
                        queue_length INTEGER,
                        timestamp REAL
                    )
                """)

                # 6. System Logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        log_level TEXT,
                        message TEXT,
                        category TEXT,
                        metadata_json TEXT,
                        timestamp REAL
                    )
                """)

                conn.commit()
                logger.info(f"✅ SQLite Database initialized at {cls._db_path}")
        except Exception as e:
            logger.error(f"❌ SQLite init failed: {e}")

    # ── 1. Detection History CRUD ─────────────────────────────
    @classmethod
    def save_detection(cls, data: Dict[str, Any]):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO detection_history (
                        frame_id, lane_id, timestamp, vehicle_count,
                        ambulance_detected, ambulance_plate, vehicles_json,
                        processing_time_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.get("frame_id", ""),
                        data.get("lane_id", "A"),
                        data.get("timestamp", time.time()),
                        len(data.get("vehicles", [])),
                        1 if data.get("ambulance_detected") else 0,
                        data.get("ambulance_plate", "") or "",
                        json.dumps(data.get("vehicles", [])),
                        data.get("processing_time_ms", 0.0),
                        time.time(),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite save_detection error: {e}")

    @classmethod
    def get_recent_detections(cls, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM detection_history ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                result = []
                for r in rows:
                    item = dict(r)
                    item["vehicles"] = json.loads(item.get("vehicles_json") or "[]")
                    item["ambulance_detected"] = bool(item["ambulance_detected"])
                    result.append(item)
                return result
        except Exception as e:
            logger.error(f"SQLite get_recent_detections error: {e}")
            return []

    # ── 2. Emergency Events CRUD ─────────────────────────────
    @classmethod
    def log_emergency_event(
        cls,
        event_type: str,
        lane_id: str,
        tracking_id: str = "",
        plate_number: str = "",
        distance_meters: float = 0.0,
        eta_seconds: float = 0.0,
        confidence: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO emergency_events (
                        event_type, lane_id, tracking_id, plate_number,
                        distance_meters, eta_seconds, confidence, timestamp, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        lane_id,
                        tracking_id,
                        plate_number,
                        distance_meters,
                        eta_seconds,
                        confidence,
                        time.time(),
                        json.dumps(details or {}),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite log_emergency_event error: {e}")

    @classmethod
    def get_emergency_events(cls, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM emergency_events ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_emergency_events error: {e}")
            return []

    # ── 3. Signal Events CRUD ─────────────────────────────────
    @classmethod
    def log_signal_event(
        cls,
        lane_id: str,
        old_state: str,
        new_state: str,
        reason: str,
        duration_seconds: int = 0,
        controller_state: str = "NORMAL",
    ):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO signal_events (
                        lane_id, old_state, new_state, reason,
                        duration_seconds, controller_state, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lane_id,
                        old_state,
                        new_state,
                        reason,
                        duration_seconds,
                        controller_state,
                        time.time(),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite log_signal_event error: {e}")

    @classmethod
    def get_signal_events(cls, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM signal_events ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_signal_events error: {e}")
            return []

    # ── 4. Distance History CRUD ──────────────────────────────
    @classmethod
    def log_distance(
        cls,
        tracking_id: str,
        lane_id: str,
        distance_meters: float,
        speed_mps: float = 0.0,
        eta_seconds: float = 0.0,
        confidence: float = 0.0,
    ):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO distance_history (
                        tracking_id, lane_id, distance_meters, speed_mps,
                        eta_seconds, confidence, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tracking_id,
                        lane_id,
                        distance_meters,
                        speed_mps,
                        eta_seconds,
                        confidence,
                        time.time(),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite log_distance error: {e}")

    # ── 5. Priority Queue History CRUD ────────────────────────
    @classmethod
    def log_priority_queue(cls, queue_items: List[Dict[str, Any]], active_lane: str = ""):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO priority_queue_history (
                        queue_snapshot_json, active_lane, queue_length, timestamp
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        json.dumps(queue_items),
                        active_lane,
                        len(queue_items),
                        time.time(),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite log_priority_queue error: {e}")

    # ── 6. System Logs CRUD ───────────────────────────────────
    @classmethod
    def add_system_log(
        cls, log_level: str, message: str, category: str = "GENERAL", metadata: Optional[Dict[str, Any]] = None
    ):
        try:
            with cls.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO system_logs (
                        log_level, message, category, metadata_json, timestamp
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        log_level.upper(),
                        message,
                        category.upper(),
                        json.dumps(metadata or {}),
                        time.time(),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite add_system_log error: {e}")

    @classmethod
    def get_system_logs(cls, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_system_logs error: {e}")
            return []

    @classmethod
    def export_logs_csv(cls) -> str:
        """Export system logs & emergency events as CSV string."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Category", "Level", "Message", "Metadata"])
        
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, timestamp, category, log_level, message, metadata_json FROM system_logs ORDER BY timestamp DESC")
                for row in cursor.fetchall():
                    writer.writerow([row["id"], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["timestamp"])), row["category"], row["log_level"], row["message"], row["metadata_json"]])
        except Exception as e:
            logger.error(f"SQLite export_logs_csv error: {e}")
            
        return output.getvalue()


# Initialize tables on import
SQLiteDatabase.init_db()
