"""Phase 6 Verification: FastAPI Serving Layer and Audit Trail."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.logger import logger
from src.api.main import app
from src.core.audit import AuditTrailManager

client = TestClient(app)
audit = AuditTrailManager()

PASS = "[OK]"
FAIL = "[FAIL]"


def check(label: str, condition: bool, detail: str = ""):
    symbol = PASS if condition else FAIL
    msg = f"  {symbol} {label}"
    if detail:
        msg += f": {detail}"
    logger.info(msg)
    if not condition:
        raise AssertionError(f"FAILED: {label}")


def run_verification():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 — Phase 6: FastAPI Serving Layer Verification")
    logger.info("=" * 65)

    # ── 1. Health ────────────────────────────────────────────────────────
    logger.info("\n[1/5] API Health & Model Initialisation...")
    r = client.get("/api/v1/health")
    check("HTTP 200 OK from /health", r.status_code == 200)
    d = r.json()
    check("Status is HEALTHY", d["status"] == "HEALTHY")
    check("All 8 model pipelines loaded", len(d["models_loaded"]) == 8,
          f"loaded={d['models_loaded']}")
    logger.info("")

    # ── 2. Individual Inference Endpoints ────────────────────────────────
    logger.info("[2/5] Testing Individual AI Inference Endpoints...")

    r = client.post("/api/v1/detect", json={"frame_id": "VER_FRAME"})
    check("POST /detect — is_cyclone_detected key present", "is_cyclone_detected" in r.json())

    r = client.post("/api/v1/intensity", json={"intensity_hint_kt": 80.0})
    check("POST /intensity — wind_speed_kt returned", "wind_speed_kt" in r.json())
    check("POST /intensity — imd_category returned", "imd_category" in r.json())

    ri_payload = {
        "sea_surface_temp_c": 30.0, "vertical_wind_shear_kt": 10.0,
        "relative_humidity_700hpa": 80.0, "ocean_heat_content_kj_cm2": 90.0,
        "vorticity_850hpa": 18.0, "coriolis_parameter": 0.42, "current_wind_kt": 70.0,
    }
    r = client.post("/api/v1/ri", json=ri_payload)
    ri = r.json()
    check("POST /ri — ri_probability in [0,1]", 0.0 <= ri["ri_probability"] <= 1.0,
          f"p={ri['ri_probability']:.3f}")

    r = client.post("/api/v1/track", json={"initial_lat": 13.0, "initial_lon": 88.0, "initial_wind_kt": 60.0})
    track = r.json()
    check("POST /track — forecast_points > 0", len(track["forecast_points"]) > 0,
          f"n={len(track['forecast_points'])}")
    check("POST /track — uncertainty cone GeoJSON present",
          isinstance(track["uncertainty_cone_geojson"], dict))
    logger.info("")

    # ── 3. Risk + Bulletin ───────────────────────────────────────────────
    logger.info("[3/5] Testing Coastal Risk and IMD Bulletin Endpoint...")
    risk_payload = {
        "storm_lat": 18.5, "storm_lon": 87.0, "wind_kt": 95.0,
        "central_pressure_hpa": 940.0, "has_landfall": True,
        "landfall_lat": 20.25, "landfall_lon": 86.65,
        "landfall_district": "Jagatsinghpur", "landfall_state": "Odisha",
        "intensity_at_landfall_kt": 90.0,
    }
    r = client.post("/api/v1/risk", json=risk_payload)
    risk = r.json()
    check("POST /risk — district_risk_assessments list", len(risk["district_risk_assessments"]) > 0)
    check("POST /risk — bulletin HTML generated", len(risk["bulletin_html"]) > 100)
    logger.info("")

    # ── 4. Full Pipeline ─────────────────────────────────────────────────
    logger.info("[4/5] Testing Full End-to-End Pipeline...")
    r = client.post("/api/v1/pipeline/full-run")
    pipeline = r.json()
    check("POST /pipeline/full-run — frame_id returned", "frame_id" in pipeline)
    check("POST /pipeline/full-run — audit_hash present", "audit_hash" in pipeline)
    check("POST /pipeline/full-run — elapsed < 10s", pipeline["elapsed_ms"] < 10000,
          f"elapsed={pipeline['elapsed_ms']:.0f}ms")
    logger.info("")

    # ── 5. Simulation + Forecaster Audit ────────────────────────────────
    logger.info("[5/5] Testing Simulation Playback and Forecaster Audit Trail...")
    r = client.get("/api/v1/simulation/playback?storm=AMPHAN&step=3")
    sim = r.json()
    check("GET /simulation/playback — lat returned", "lat" in sim)
    check("GET /simulation/playback — step label", "label" in sim)

    r = client.post("/api/v1/forecaster/review", json={
        "frame_id": "VER_REVIEW_001",
        "forecaster_id": "FOR-IMD-001",
        "status": "APPROVED",
        "forecaster_notes": "Verified against NWP analysis.",
    })
    check("POST /forecaster/review — RECORDED", r.json()["status"] == "RECORDED")

    r = client.get("/api/v1/forecaster/audit/verify")
    chain = r.json()
    check("GET /audit/verify — chain valid", chain["valid"],
          chain.get("details", ""))
    check("GET /audit/verify — records > 0", chain["records_checked"] > 0,
          f"n={chain['records_checked']}")

    logger.info("")
    logger.info("=" * 65)
    logger.info("PHASE 6 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    run_verification()
