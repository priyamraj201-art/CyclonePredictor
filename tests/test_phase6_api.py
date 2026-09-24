"""Phase 6 Unit Tests: FastAPI Endpoints and Audit Trail."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "HEALTHY"
    assert "models_loaded" in data


def test_detect_endpoint():
    r = client.post("/api/v1/detect", json={"frame_id": "TEST_DETECT", "basin": "BAY_OF_BENGAL"})
    assert r.status_code == 200
    data = r.json()
    assert "is_cyclone_detected" in data
    assert "frame_id" in data


def test_intensity_endpoint():
    r = client.post("/api/v1/intensity", json={"frame_id": "TEST_INTENSITY", "basin": "BAY_OF_BENGAL", "intensity_hint_kt": 70.0})
    assert r.status_code == 200
    data = r.json()
    assert "wind_speed_kt" in data
    assert "imd_category" in data


def test_ri_endpoint():
    payload = {
        "sea_surface_temp_c": 30.5,
        "vertical_wind_shear_kt": 11.0,
        "relative_humidity_700hpa": 82.0,
        "ocean_heat_content_kj_cm2": 95.0,
        "vorticity_850hpa": 20.0,
        "coriolis_parameter": 0.45,
        "current_wind_kt": 65.0,
    }
    r = client.post("/api/v1/ri", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "ri_probability" in data
    assert 0.0 <= data["ri_probability"] <= 1.0


def test_track_endpoint():
    r = client.post("/api/v1/track", json={"initial_lat": 12.5, "initial_lon": 88.5, "initial_wind_kt": 55.0})
    assert r.status_code == 200
    data = r.json()
    assert len(data["forecast_points"]) > 0
    assert "uncertainty_cone_geojson" in data


def test_risk_endpoint():
    payload = {
        "storm_lat": 19.4, "storm_lon": 87.2, "wind_kt": 90.0,
        "central_pressure_hpa": 945.0, "has_landfall": True,
        "landfall_lat": 20.25, "landfall_lon": 86.65,
        "landfall_district": "Jagatsinghpur", "landfall_state": "Odisha",
        "intensity_at_landfall_kt": 85.0,
    }
    r = client.post("/api/v1/risk", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "district_risk_assessments" in data
    assert "bulletin" in data


def test_full_pipeline_endpoint():
    r = client.post("/api/v1/pipeline/full-run")
    assert r.status_code == 200
    data = r.json()
    assert "frame_id" in data
    assert "audit_hash" in data
    assert "elapsed_ms" in data
    assert data["elapsed_ms"] < 10000


def test_simulation_playback():
    r = client.get("/api/v1/simulation/playback?storm=FANI&step=0")
    assert r.status_code == 200
    data = r.json()
    assert data["storm"] == "FANI"
    assert "lat" in data
    assert "wind_kt" in data


def test_forecaster_review():
    r = client.post("/api/v1/forecaster/review", json={
        "frame_id": "TEST_REVIEW_001",
        "forecaster_id": "FOR-IMD-042",
        "status": "APPROVED",
        "forecaster_notes": "AI prediction aligns with synoptic analysis.",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "RECORDED"
    assert "audit_hash" in data


def test_audit_verify():
    r = client.get("/api/v1/forecaster/audit/verify")
    assert r.status_code == 200
    data = r.json()
    assert "valid" in data


def test_audit_log():
    r = client.get("/api/v1/forecaster/audit/log?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "records" in data
