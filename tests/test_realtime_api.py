"""Automated pytest tests for Step 4 Real-Time FastAPI Endpoints.

Tests:
  test_basin_scan_bob         — GET /api/v1/realtime/basin-scan (BoB)
  test_basin_scan_arabian_sea — GET /api/v1/realtime/basin-scan (AS)
  test_basin_scan_invalid     — GET /api/v1/realtime/basin-scan (400 on bad basin)
  test_live_storm_bob         — GET /api/v1/realtime/live-storm (BoB)
  test_live_storm_schema      — Validate complete response schema
  test_trigger_scan_ack       — POST /api/v1/realtime/trigger-scan (immediate ACK)
  test_trigger_scan_invalid   — POST /api/v1/realtime/trigger-scan (400 on bad basin)
  test_existing_health        — Existing /api/v1/health still returns 200 (no regression)
  test_existing_simulation    — Existing /api/v1/simulation/playback still works
"""

import sys
import pytest

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app, raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# No-Regression: Existing endpoints must still work
# ─────────────────────────────────────────────────────────────────────────────

def test_existing_health():
    """Existing health endpoint returns HTTP 200 — no regression."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "HEALTHY"
    assert "models_loaded" in body


def test_existing_simulation_playback():
    """Existing simulation/playback endpoint still responds — no regression."""
    r = client.get("/api/v1/simulation/playback?storm=FANI&step=0")
    assert r.status_code == 200
    body = r.json()
    assert body["storm"] == "FANI"
    assert "lat" in body and "lon" in body


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Basin Scan
# ─────────────────────────────────────────────────────────────────────────────

def test_basin_scan_bob():
    """GET /api/v1/realtime/basin-scan returns HTTP 200 for Bay of Bengal."""
    r = client.get("/api/v1/realtime/basin-scan?basin=BAY_OF_BENGAL")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["basin"] == "BAY_OF_BENGAL"
    assert "primary_vortex" in body
    assert "sectors" in body
    assert body["total_sectors"] >= 10


def test_basin_scan_bob_schema():
    """Basin-scan response schema is complete and all fields are valid."""
    r = client.get("/api/v1/realtime/basin-scan?basin=BAY_OF_BENGAL")
    assert r.status_code == 200
    body = r.json()

    # Top-level fields
    for key in ("basin", "scan_timestamp_utc", "total_sectors",
                "primary_vortex", "basin_mean_gpi", "basin_max_gpi", "sectors"):
        assert key in body, f"Missing key: {key}"

    # Primary vortex schema
    vortex = body["primary_vortex"]
    assert 5.0 <= vortex["lat"] <= 23.0
    assert 79.0 <= vortex["lon"] <= 96.0
    assert vortex["max_gpi"] >= 0.0
    assert 0.0 <= vortex["genesis_probability"] <= 1.0
    assert vortex["threat_level"] in ("NONE", "LOW", "MODERATE", "HIGH", "EXTREME")

    # Sector fields
    for s in body["sectors"]:
        assert "gpi_score" in s
        assert s["gpi_score"] >= 0.0
        assert 0.0 <= s["genesis_probability"] <= 1.0


def test_basin_scan_arabian_sea():
    """GET /api/v1/realtime/basin-scan returns HTTP 200 for Arabian Sea."""
    r = client.get("/api/v1/realtime/basin-scan?basin=ARABIAN_SEA")
    assert r.status_code == 200
    body = r.json()
    assert body["basin"] == "ARABIAN_SEA"
    assert body["total_sectors"] >= 8


def test_basin_scan_invalid():
    """GET /api/v1/realtime/basin-scan returns HTTP 400 for invalid basin."""
    r = client.get("/api/v1/realtime/basin-scan?basin=PACIFIC_OCEAN")
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Live Storm
# ─────────────────────────────────────────────────────────────────────────────

def test_live_storm_bob():
    """GET /api/v1/realtime/live-storm returns HTTP 200 for Bay of Bengal."""
    r = client.get("/api/v1/realtime/live-storm?basin=BAY_OF_BENGAL")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["basin"] == "BAY_OF_BENGAL"
    assert "intensity" in body
    assert "rapid_intensification" in body
    assert "track_waypoints" in body
    assert "uncertainty_cone_geojson" in body
    assert "coastal_risk_top5" in body


def test_live_storm_schema():
    """Live-storm response schema is fully populated and physically valid."""
    r = client.get("/api/v1/realtime/live-storm?basin=BAY_OF_BENGAL")
    assert r.status_code == 200
    body = r.json()

    # Genesis fields
    assert 5.0 <= body["genesis_lat"] <= 23.0
    assert 79.0 <= body["genesis_lon"] <= 96.0
    assert body["genesis_gpi"] >= 0.0
    assert 0.0 <= body["genesis_probability"] <= 1.0
    assert body["genesis_threat_level"] in ("NONE","LOW","MODERATE","HIGH","EXTREME")

    # Intensity
    inten = body["intensity"]
    assert 20.0 <= inten["wind_speed_kt"] <= 180.0
    assert 850.0 <= inten["central_pressure_hpa"] <= 1010.0
    assert inten["pressure_deficit_hpa"] > 0
    assert bool(inten["imd_category"])

    # RI
    ri = body["rapid_intensification"]
    assert 0.0 <= ri["ri_probability"] <= 1.0
    assert isinstance(ri["is_ri_flagged"], bool)
    assert bool(ri["advisory"])

    # Track
    waypoints = body["track_waypoints"]
    assert len(waypoints) == 4
    lead_hours = [w["lead_hours"] for w in waypoints]
    assert lead_hours == [12, 24, 36, 48]
    for w in waypoints:
        assert 3.0 <= w["lat"] <= 35.0
        assert 45.0 <= w["lon"] <= 115.0
        assert w["wind_speed_kt"] > 0

    # Cone GeoJSON
    cone = body["uncertainty_cone_geojson"]
    assert cone["type"] == "FeatureCollection"
    assert len(cone["features"]) >= 2

    # Risk
    risk = body["coastal_risk_top5"]
    assert isinstance(risk, list)
    for d in risk:
        assert 0.0 <= d["composite_risk"] <= 100.0


def test_live_storm_invalid():
    """GET /api/v1/realtime/live-storm returns HTTP 400 for invalid basin."""
    r = client.get("/api/v1/realtime/live-storm?basin=MEDITERRANEAN")
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Trigger Scan
# ─────────────────────────────────────────────────────────────────────────────

def test_trigger_scan_ack():
    """POST /api/v1/realtime/trigger-scan returns immediate HTTP 200 acknowledgement."""
    r = client.post("/api/v1/realtime/trigger-scan?basin=BAY_OF_BENGAL")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "SCAN_TRIGGERED"
    assert body["basin"] == "BAY_OF_BENGAL"
    assert "triggered_at" in body
    assert "poll_endpoint" in body
    assert body["estimated_completion_seconds"] > 0


def test_trigger_scan_arabian_sea():
    """POST /api/v1/realtime/trigger-scan works for Arabian Sea."""
    r = client.post("/api/v1/realtime/trigger-scan?basin=ARABIAN_SEA")
    assert r.status_code == 200
    body = r.json()
    assert body["basin"] == "ARABIAN_SEA"
    assert body["status"] == "SCAN_TRIGGERED"


def test_trigger_scan_invalid():
    """POST /api/v1/realtime/trigger-scan returns HTTP 400 for invalid basin."""
    r = client.post("/api/v1/realtime/trigger-scan?basin=NORTH_ATLANTIC")
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Swagger / OpenAPI doc tag verification
# ─────────────────────────────────────────────────────────────────────────────

def test_swagger_docs_real_time_tag():
    """Swagger OpenAPI spec includes 'Real-Time' tag for the new endpoints."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec.get("paths", {})
    rt_paths = [p for p in paths if "/realtime/" in p]
    assert len(rt_paths) == 3, f"Expected 3 real-time paths, got: {rt_paths}"
    # Verify Real-Time tag is present in at least one endpoint
    for path, ops in paths.items():
        if "/realtime/" in path:
            for method, op in ops.items():
                assert "Real-Time" in op.get("tags", []), \
                    f"'Real-Time' tag missing from {method.upper()} {path}"
