"""
/api/analytics — traffic statistics and historical data
"""

import time
import random
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/analytics/summary")
async def analytics_summary():
    """Return aggregated system performance statistics."""
    return JSONResponse(content={
        "period": "today",
        "total_vehicles_detected": 1842,
        "ambulances_detected": 7,
        "corridors_activated": 7,
        "avg_corridor_clear_time_seconds": 18.4,
        "success_rate_percent": 98.6,
        "avg_vehicles_per_minute": 24.3,
        "peak_hour": 9,
        "siren_detections": 5,
        "manual_overrides": 2,
    })


@router.get("/analytics/congestion")
async def congestion_timeline():
    """Return hourly congestion data for chart rendering."""
    hours = list(range(0, 24))
    data = [
        {"hour": h, "level": random.randint(10, 95), "vehicles": random.randint(20, 200)}
        for h in hours
    ]
    return JSONResponse(content={"timeline": data})


@router.get("/analytics/detections")
async def recent_detections(limit: int = 50):
    """Return recent detection events."""
    events = [
        {
            "id": f"det_{i}",
            "type": "ambulance" if i % 7 == 0 else "car",
            "confidence": round(0.85 + random.random() * 0.14, 3),
            "plate": f"KA-0{i % 9}-MK-{4000 + i}" if i % 7 == 0 else None,
            "timestamp": time.time() - i * 12,
            "lane": f"L{(i % 4) + 1}",
        }
        for i in range(limit)
    ]
    return JSONResponse(content={"events": events})


@router.get("/logs/export")
async def export_logs_csv():
    """Export system logs & event history as downloadable CSV file."""
    from fastapi.responses import Response
    from database_sqlite import SQLiteDatabase
    csv_content = SQLiteDatabase.export_logs_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_system_event_logs.csv"}
    )
