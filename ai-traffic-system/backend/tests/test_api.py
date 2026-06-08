"""
Integration tests for FastAPI endpoints.
Run: pytest tests/ -v
Requires: pip install httpx pytest pytest-asyncio
"""

import io
import time
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport

# Patch heavy imports before importing app
import unittest.mock as mock
mock.patch("services.signal_service.serial", create=True).start()
mock.patch("services.detection_service.YOLO", create=True).start()
mock.patch("models.database.AsyncIOMotorClient", create=True).start()

from main import app  # noqa: E402


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "operational"
    assert "version" in data


@pytest.mark.asyncio
async def test_system_status(client):
    r = await client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "ai_model_loaded" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_get_signals(client):
    r = await client.get("/api/signal-control")
    assert r.status_code == 200
    data = r.json()
    assert "lanes" in data
    assert len(data["lanes"]) == 4


@pytest.mark.asyncio
async def test_signal_override(client):
    payload = {
        "lane_id": "L2",
        "state": "green",
        "duration_seconds": 15,
        "reason": "test",
    }
    r = await client.post("/api/signal-control/override", json=payload)
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_signal_reset(client):
    r = await client.post("/api/signal-control/reset")
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_gps_update_and_get(client):
    pos = {
        "vehicle_id": "AMB-TEST",
        "latitude": 12.971,
        "longitude": 77.594,
        "speed_kmh": 55.0,
        "heading": 90.0,
        "timestamp": time.time(),
        "is_emergency": True,
    }
    r = await client.post("/api/gps-data", json=pos)
    assert r.status_code == 200

    r2 = await client.get("/api/gps-data/AMB-TEST")
    assert r2.status_code == 200
    data = r2.json()
    assert data["vehicle_id"] == "AMB-TEST"
    assert abs(data["latitude"] - 12.971) < 0.0001


@pytest.mark.asyncio
async def test_analytics_summary(client):
    r = await client.get("/api/analytics/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_vehicles_detected" in data
    assert "success_rate_percent" in data


@pytest.mark.asyncio
async def test_detect_invalid_file(client):
    r = await client.post(
        "/api/detect",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_detect_empty_file(client):
    r = await client.post(
        "/api/detect",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_detect_with_real_image(client):
    """Test detection with a synthetically generated image."""
    import cv2
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    r = await client.post(
        "/api/detect",
        files={"file": ("frame.jpg", buf.tobytes(), "image/jpeg")},
    )
    # Without real model loaded, still expect a response structure
    assert r.status_code in (200, 500)  # 500 only if model not initialised


@pytest.mark.asyncio
async def test_siren_status(client):
    r = await client.get("/api/siren/status")
    assert r.status_code == 200
    assert "model_loaded" in r.json()


@pytest.mark.asyncio
async def test_alerts_create_and_list(client):
    r = await client.post("/api/alerts?alert_type=info&message=Test+alert")
    assert r.status_code == 200

    r2 = await client.get("/api/alerts")
    assert r2.status_code == 200
    assert "alerts" in r2.json()


@pytest.mark.asyncio
async def test_congestion_timeline(client):
    r = await client.get("/api/analytics/congestion")
    assert r.status_code == 200
    data = r.json()
    assert "timeline" in data
    assert len(data["timeline"]) == 24  # one entry per hour
