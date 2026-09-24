"""FastAPI Production Inference Backend for the SIH 2026 Cyclone AI System.

Provides all REST endpoints for detection, intensity, RI, track forecasting,
coastal risk, bulletin generation, simulation playback, and forecaster audit.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import asyncio
import hashlib
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import MODELS_DIR
from src.core.audit import AuditTrailManager
from src.core.constants import Basin, CycloneStage
from src.core.schemas import BestTrackPoint, EnvironmentalFeatures
from src.data.mock_generator import SyntheticCycloneGenerator
from src.models.detection import CycloneDetector
from src.models.intensity import IntensityEstimator
from src.models.rapid_intensification import RapidIntensificationClassifier
from src.models.track import TrackForecastPipeline
from src.models.fusion import MultimodalFusionPipeline
from src.utils.uncertainty_cone import UncertaintyConeGenerator
from src.utils.landfall import LandfallPredictor
from src.risk.risk_assessment import CoastalRiskAssessmentEngine
from src.risk.bulletin_generator import IMDBulletinGenerator
from src.data.ingestion_real import OFFICIAL_NIO_STORMS, RealDataIngestionManager
from src.risk.cap_generator import generate_cap_xml, generate_wmo_tca


app = FastAPI(
    title="Cyclone AI Prediction System — SIH 2026 PS 26070",
    description=(
        "Operational-grade AI/ML system for tropical cyclone identification, intensity estimation, "
        "rapid intensification prediction, track forecasting, coastal vulnerability scoring, and "
        "automated IMD warning bulletin generation.\n\n"
        "**Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)**"
    ),
    version="1.0.0",
    contact={"name": "SIH 2026 Team", "email": "cyclone-ai@moes.gov.in"},
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Lazy-loaded global model instances (initialized on first request)
# ──────────────────────────────────────────────────────────────────────────────
_models: Dict[str, Any] = {}
_audit = AuditTrailManager()
_generator = SyntheticCycloneGenerator(seed=42)
_bulletin_counter = {"n": 1}


def get_models() -> Dict[str, Any]:
    """Initialize all inference pipelines once."""
    global _models
    if not _models:
        _models = {
            "detector": CycloneDetector(),
            "intensity": IntensityEstimator(),
            "ri": RapidIntensificationClassifier(),
            "track": TrackForecastPipeline(),
            "fusion": MultimodalFusionPipeline(),
            "cone": UncertaintyConeGenerator(),
            "landfall": LandfallPredictor(),
            "risk": CoastalRiskAssessmentEngine(),
        }
    return _models


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────────────────────────────────────
class DetectRequest(BaseModel):
    frame_id: str = "DEMO_FRAME_001"
    basin: str = "BAY_OF_BENGAL"
    intensity_hint_kt: Optional[float] = None


class IntensityRequest(BaseModel):
    frame_id: str = "DEMO_FRAME_001"
    basin: str = "BAY_OF_BENGAL"
    intensity_hint_kt: Optional[float] = None


class RIRequest(BaseModel):
    sea_surface_temp_c: float = 30.5
    vertical_wind_shear_kt: float = 11.0
    relative_humidity_700hpa: float = 82.0
    ocean_heat_content_kj_cm2: float = 95.0
    vorticity_850hpa: float = 20.0
    coriolis_parameter: float = 0.45
    current_wind_kt: float = 65.0


class TrackRequest(BaseModel):
    initial_lat: float = 12.5
    initial_lon: float = 88.5
    initial_wind_kt: float = 55.0
    num_history_steps: int = 3


class RiskRequest(BaseModel):
    storm_lat: float = 19.4
    storm_lon: float = 87.2
    wind_kt: float = 90.0
    central_pressure_hpa: float = 945.0
    has_landfall: bool = True
    landfall_lat: Optional[float] = 20.25
    landfall_lon: Optional[float] = 86.65
    landfall_district: str = "Jagatsinghpur"
    landfall_state: str = "Odisha"
    intensity_at_landfall_kt: float = 85.0


class ForecasterReviewRequest(BaseModel):
    frame_id: str
    forecaster_id: str
    status: str  # "APPROVED" or "MODIFIED"
    override_wind_kt: Optional[float] = None
    override_center_lat: Optional[float] = None
    override_center_lon: Optional[float] = None
    forecaster_notes: str = "Reviewed and approved."


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """System health check: model load status and compute device."""
    models = get_models()
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models_loaded": list(models.keys()),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
    }


@app.post("/api/v1/detect", tags=["Detection"])
async def detect_cyclone(req: DetectRequest):
    """Run cyclone detection and storm centre localisation on a synthetic frame."""
    basin = Basin.ARABIAN_SEA if "ARABIAN" in req.basin.upper() else Basin.BAY_OF_BENGAL
    obs, raw, mask = _generator.generate_single_observation(
        basin=basin, intensity_kt=req.intensity_hint_kt
    )
    tensor = torch.from_numpy((raw - raw.min()) / (raw.max() - raw.min() + 1e-6)).float()
    models = get_models()
    result = models["detector"].detect(
        satellite_tensor=tensor,
        bounding_box=obs.satellite_meta.bounding_box,
        ground_truth_latlon=(obs.best_track.lat, obs.best_track.lon),
    )
    result["energy_heatmap"] = result["energy_heatmap"].tolist()
    result["latent_features"] = result["latent_features"].tolist()
    result["frame_id"] = obs.frame_id
    result["ground_truth"] = {
        "lat": obs.best_track.lat,
        "lon": obs.best_track.lon,
        "imd_category": obs.best_track.imd_category.value if obs.best_track.imd_category else None,
        "wind_kt": obs.best_track.max_sustained_wind_kt,
    }
    return result


@app.post("/api/v1/intensity", tags=["Intensity"])
async def estimate_intensity(req: IntensityRequest):
    """Estimate maximum sustained wind speed, IMD category, and Grad-CAM saliency."""
    basin = Basin.ARABIAN_SEA if "ARABIAN" in req.basin.upper() else Basin.BAY_OF_BENGAL
    obs, raw, mask = _generator.generate_single_observation(
        basin=basin, intensity_kt=req.intensity_hint_kt
    )
    tensor = torch.from_numpy((raw - raw.min()) / (raw.max() - raw.min() + 1e-6)).float()
    models = get_models()
    result = models["intensity"].estimate(tensor)
    result["visual_embedding"] = result["visual_embedding"].tolist()
    result["frame_id"] = obs.frame_id
    result["ground_truth_kt"] = obs.best_track.max_sustained_wind_kt
    return result


@app.post("/api/v1/ri", tags=["Rapid Intensification"])
async def predict_rapid_intensification(req: RIRequest):
    """Predict 24-hour Rapid Intensification probability with thermodynamic diagnostics."""
    env = EnvironmentalFeatures(
        sea_surface_temp_c=req.sea_surface_temp_c,
        vertical_wind_shear_kt=req.vertical_wind_shear_kt,
        relative_humidity_700hpa=req.relative_humidity_700hpa,
        ocean_heat_content_kj_cm2=req.ocean_heat_content_kj_cm2,
        vorticity_850hpa=req.vorticity_850hpa,
        coriolis_parameter=req.coriolis_parameter,
    )
    models = get_models()
    return models["ri"].predict(env, req.current_wind_kt)


@app.post("/api/v1/track", tags=["Track Forecasting"])
async def forecast_track(req: TrackRequest):
    """Forecast +6h to +48h track positions, uncertainty cone GeoJSON, and landfall ETA."""
    t0 = datetime.now(timezone.utc)
    history = []
    lat = req.initial_lat
    lon = req.initial_lon
    for i in range(req.num_history_steps):
        history.append(BestTrackPoint(
            timestamp=t0 - timedelta(hours=6 * (req.num_history_steps - i)),
            lat=lat - (req.num_history_steps - i) * 0.9,
            lon=lon + (req.num_history_steps - i) * 0.6,
            max_sustained_wind_kt=req.initial_wind_kt - (req.num_history_steps - i) * 5,
        ))
    history.append(BestTrackPoint(timestamp=t0, lat=req.initial_lat, lon=req.initial_lon,
                                  max_sustained_wind_kt=req.initial_wind_kt))
    models = get_models()
    track = models["track"].forecast(history)
    cone_geojson = models["cone"].generate_geojson(
        track["forecast_points"], initial_point=history[-1], storm_name="CYCLONE"
    )
    landfall = models["landfall"].predict_landfall(track["forecast_points"], initial_point=history[-1])
    return {
        "forecast_points": [
            {
                "timestamp": pt.timestamp.isoformat(),
                "lat": pt.lat, "lon": pt.lon,
                "wind_kt": pt.max_sustained_wind_kt,
                "imd_category": pt.imd_category.value if pt.imd_category else None,
                "pressure_hpa": pt.central_pressure_hpa,
            }
            for pt in track["forecast_points"]
        ],
        "uncertainty_cone_geojson": cone_geojson,
        "landfall": landfall,
        "track_embedding_dim": len(track["track_embedding"]),
    }


@app.post("/api/v1/risk", tags=["Coastal Risk"])
async def assess_risk(req: RiskRequest):
    """Evaluate coastal district risk scores, storm surge, wind hazard, and bulletin."""
    storm = BestTrackPoint(
        timestamp=datetime.now(timezone.utc),
        lat=req.storm_lat, lon=req.storm_lon,
        max_sustained_wind_kt=req.wind_kt,
        central_pressure_hpa=req.central_pressure_hpa,
    )
    landfall_info: Dict[str, Any] = {"has_landfall": req.has_landfall}
    if req.has_landfall:
        landfall_info.update({
            "landfall_lat": req.landfall_lat,
            "landfall_lon": req.landfall_lon,
            "district": req.landfall_district,
            "state_or_country": req.landfall_state,
            "intensity_at_landfall_kt": req.intensity_at_landfall_kt,
            "intensity_at_landfall_kmh": round(req.intensity_at_landfall_kt * 1.852, 1),
            "stage_at_landfall": storm.imd_category.value if storm.imd_category else "Cyclonic Storm",
            "eta_ist": (datetime.now(timezone.utc) + timedelta(hours=24) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %H:%M IST"),
            "uncertainty_window_hours": 4.5,
        })
    models = get_models()
    evaluations = models["risk"].evaluate_risk_swath(storm, landfall_point=landfall_info)
    bulletin_gen = IMDBulletinGenerator(bulletin_sequence=_bulletin_counter["n"])
    _bulletin_counter["n"] += 1
    bulletin = bulletin_gen.generate_bulletin(
        storm_name="CYCLONE",
        current_observation=storm,
        forecast_points=[],
        landfall_info=landfall_info,
        high_risk_districts=evaluations,
    )
    return {
        "district_risk_assessments": evaluations[:8],
        "bulletin": {k: v for k, v in bulletin.items() if k != "html"},
        "bulletin_html": bulletin["html"],
    }


@app.post("/api/v1/pipeline/full-run", tags=["Pipeline"])
async def full_pipeline_run():
    """Execute the complete end-to-end inference pipeline on a synthetic storm."""
    t_start = time.time()
    obs, raw, mask = _generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL, intensity_kt=85.0, add_mask=True
    )
    tensor = torch.from_numpy((raw - raw.min()) / (raw.max() - raw.min() + 1e-6)).float()
    models = get_models()

    # Detection
    detect_res = models["detector"].detect(tensor, bounding_box=obs.satellite_meta.bounding_box)

    # Intensity
    int_res = models["intensity"].estimate(tensor)

    # RI
    ri_res = models["ri"].predict(obs.env_features, obs.best_track.max_sustained_wind_kt)

    # Track — build a synthetic 3-step history (TrackPipeline requires ≥2 points)
    t0 = obs.best_track.timestamp
    history = [
        BestTrackPoint(
            timestamp=t0 - timedelta(hours=12),
            lat=obs.best_track.lat - 1.8,
            lon=obs.best_track.lon + 1.2,
            max_sustained_wind_kt=obs.best_track.max_sustained_wind_kt - 10,
        ),
        BestTrackPoint(
            timestamp=t0 - timedelta(hours=6),
            lat=obs.best_track.lat - 0.9,
            lon=obs.best_track.lon + 0.6,
            max_sustained_wind_kt=obs.best_track.max_sustained_wind_kt - 5,
        ),
        obs.best_track,
    ]
    track = models["track"].forecast(history)
    cone = models["cone"].generate_geojson(track["forecast_points"], initial_point=obs.best_track)
    landfall = models["landfall"].predict_landfall(track["forecast_points"], initial_point=obs.best_track)

    # Risk
    evaluations = models["risk"].evaluate_risk_swath(obs.best_track, landfall_point=landfall)

    # Bulletin
    bulletin_gen = IMDBulletinGenerator(bulletin_sequence=_bulletin_counter["n"])
    _bulletin_counter["n"] += 1
    bulletin = bulletin_gen.generate_bulletin(
        storm_name="SYNTHETIC_STORM",
        current_observation=obs.best_track,
        forecast_points=track["forecast_points"],
        landfall_info=landfall,
        high_risk_districts=evaluations,
        ri_info=ri_res,
    )

    # Audit
    audit_record = _audit.log_prediction(
        frame_id=obs.frame_id,
        model_version="1.0.0",
        predictions={
            "wind_kt": int_res["wind_speed_kt"],
            "imd_category": int_res["imd_category"],
            "ri_probability": ri_res["ri_probability"],
            "landfall_detected": landfall["has_landfall"],
        },
    )

    return {
        "frame_id": obs.frame_id,
        "detection": {k: v for k, v in detect_res.items() if k not in ("energy_heatmap", "latent_features")},
        "intensity": {k: v for k, v in int_res.items() if k != "visual_embedding"},
        "rapid_intensification": ri_res,
        "track_forecast": [{"lat": pt.lat, "lon": pt.lon, "wind_kt": pt.max_sustained_wind_kt} for pt in track["forecast_points"]],
        "landfall": landfall,
        "top_risk_districts": evaluations[:3],
        "bulletin_summary": {k: v for k, v in bulletin.items() if k not in ("plain_text", "html")},
        "audit_hash": audit_record["record_hash"][:16] + "...",
        "elapsed_ms": round((time.time() - t_start) * 1000, 1),
    }


@app.get("/api/v1/alerts/cap-xml", tags=["Alerts"])
async def get_cap_xml_alert(storm: str = "FANI"):
    """Generate OASIS Common Alerting Protocol (CAP v1.2 XML) broadcast for NDMA/Sachet."""
    storm_upper = storm.upper()
    if storm_upper in OFFICIAL_NIO_STORMS:
        info = OFFICIAL_NIO_STORMS[storm_upper]
        track_point = info["track"][-1]
        obs = BestTrackPoint(
            timestamp=datetime.now(timezone.utc),
            lat=track_point["lat"],
            lon=track_point["lon"],
            max_sustained_wind_kt=track_point["wind_kt"],
            central_pressure_hpa=track_point.get("pressure_hpa", 960.0),
        )
        landfall = info.get("landfall", {})
        landfall_dto = {
            "has_landfall": True,
            "district": landfall.get("district", "Puri"),
            "state_or_country": landfall.get("state", "Odisha"),
            "eta_ist": landfall.get("date", "03-May-2019 08:00 IST"),
        }
    else:
        obs = BestTrackPoint(
            timestamp=datetime.now(timezone.utc),
            lat=19.4,
            lon=86.5,
            max_sustained_wind_kt=85.0,
            central_pressure_hpa=965.0,
        )
        landfall_dto = {"has_landfall": True, "district": "Puri", "state_or_country": "Odisha", "eta_ist": "Tomorrow 06:00 IST"}

    xml_content = generate_cap_xml(storm_name=storm_upper, current_obs=obs, landfall_info=landfall_dto)
    from fastapi.responses import Response
    return Response(content=xml_content, media_type="application/xml")


@app.get("/api/v1/simulation/official-storms", tags=["Simulation"])
async def get_official_storms():
    """List cataloged North Indian Ocean historic storms with official IMD/IBTrACS best-track."""
    return {
        "count": len(OFFICIAL_NIO_STORMS),
        "storms": list(OFFICIAL_NIO_STORMS.keys()),
        "catalog": OFFICIAL_NIO_STORMS,
    }


@app.get("/api/v1/simulation/playback", tags=["Simulation"])
async def simulation_playback(storm: str = "FANI", step: int = 0):
    """Stream a historic storm simulation timestep (Cyclone Fani, Amphan, Biparjoy)."""
    STORM_TRACKS = {
        "FANI": [
            {"lat": 8.3, "lon": 86.5, "wind_kt": 35, "label": "Depression (02 May)"},
            {"lat": 10.5, "lon": 86.8, "wind_kt": 55, "label": "Cyclonic Storm (03 May)"},
            {"lat": 12.8, "lon": 86.4, "wind_kt": 75, "label": "Very Severe (04 May)"},
            {"lat": 15.5, "lon": 85.5, "wind_kt": 100, "label": "Extremely Severe (05 May)"},
            {"lat": 17.8, "lon": 85.1, "wind_kt": 115, "label": "Extremely Severe Peak (01 May)"},
            {"lat": 19.5, "lon": 85.7, "wind_kt": 105, "label": "Landfall Puri (03 May)"},
        ],
        "AMPHAN": [
            {"lat": 8.0, "lon": 87.0, "wind_kt": 30, "label": "Depression (16 May)"},
            {"lat": 10.5, "lon": 87.2, "wind_kt": 60, "label": "Cyclonic Storm (17 May)"},
            {"lat": 13.2, "lon": 87.0, "wind_kt": 90, "label": "Extremely Severe (18 May)"},
            {"lat": 16.0, "lon": 86.7, "wind_kt": 120, "label": "Super Cyclonic Storm (19 May)"},
            {"lat": 19.0, "lon": 87.0, "wind_kt": 100, "label": "Very Severe (20 May)"},
            {"lat": 21.7, "lon": 88.0, "wind_kt": 85, "label": "Landfall Sunderbans (20 May)"},
        ],
        "BIPARJOY": [
            {"lat": 13.5, "lon": 65.2, "wind_kt": 35, "label": "Depression (06 Jun)"},
            {"lat": 15.5, "lon": 65.0, "wind_kt": 65, "label": "Very Severe (09 Jun)"},
            {"lat": 17.2, "lon": 65.5, "wind_kt": 85, "label": "Extremely Severe (11 Jun)"},
            {"lat": 19.5, "lon": 66.8, "wind_kt": 75, "label": "Very Severe (14 Jun)"},
            {"lat": 22.5, "lon": 68.2, "wind_kt": 55, "label": "Landfall Kachchh (15 Jun)"},
        ],
    }
    storm_upper = storm.upper()
    if storm_upper not in STORM_TRACKS:
        raise HTTPException(status_code=404, detail=f"Storm '{storm}' not found. Use FANI, AMPHAN, or BIPARJOY.")
    track = STORM_TRACKS[storm_upper]
    current_step = step % len(track)
    point = track[current_step]
    return {
        "storm": storm_upper,
        "step": current_step,
        "total_steps": len(track),
        "label": point["label"],
        "lat": point["lat"],
        "lon": point["lon"],
        "wind_kt": point["wind_kt"],
        "imd_category": __import__("src.utils.conversions", fromlist=["knots_to_stage"]).knots_to_stage(point["wind_kt"]).value,
        "next_step": (current_step + 1) % len(track),
    }


@app.post("/api/v1/forecaster/review", tags=["Forecaster"])
async def forecaster_review(req: ForecasterReviewRequest):
    """Submit human-in-the-loop forecaster review, approval, or parameter override."""
    corrections = {}
    if req.override_wind_kt is not None:
        corrections["wind_kt_override"] = req.override_wind_kt
    if req.override_center_lat is not None:
        corrections["center_lat_override"] = req.override_center_lat
    if req.override_center_lon is not None:
        corrections["center_lon_override"] = req.override_center_lon

    audit_record = _audit.log_prediction(
        frame_id=req.frame_id,
        model_version="1.0.0",
        predictions={},
        forecaster_id=req.forecaster_id,
        forecaster_corrections=corrections,
        forecaster_notes=req.forecaster_notes,
        status=req.status,
    )
    return {
        "status": "RECORDED",
        "frame_id": req.frame_id,
        "forecaster_id": req.forecaster_id,
        "review_status": req.status,
        "corrections_applied": corrections,
        "audit_hash": audit_record["record_hash"],
        "message": f"Forecaster action '{req.status}' has been cryptographically sealed into the audit chain.",
    }


@app.get("/api/v1/forecaster/audit/verify", tags=["Forecaster"])
async def verify_audit_chain():
    """Verify tamper integrity of the entire SHA-256 prediction audit chain."""
    result = _audit.verify_chain()
    return result


@app.get("/api/v1/forecaster/audit/log", tags=["Forecaster"])
async def get_audit_log(limit: int = 20):
    """Retrieve the most recent prediction and forecaster review records."""
    records = _audit.get_audit_log(limit=limit)
    return {"total_records": len(records), "records": records}
