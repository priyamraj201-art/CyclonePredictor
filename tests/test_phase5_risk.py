"""Phase 5 Verification Tests: Multimodal Fusion & Dynamic Coastal Risk Assessment."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from datetime import datetime
import pytest
import torch
import numpy as np

from src.core.schemas import BestTrackPoint
from src.core.constants import CycloneStage
from src.models.fusion import CrossModalAttentionFusion, MultimodalFusionPipeline
from src.risk.risk_assessment import CoastalRiskAssessmentEngine
from src.risk.bulletin_generator import IMDBulletinGenerator


def test_cross_modal_attention_fusion_forward():
    """Test multimodal attention fusion forward pass and dimensions."""
    model = CrossModalAttentionFusion(visual_dim=256, track_dim=64, env_dim=7, fusion_dim=128)
    model.eval()

    v = torch.rand(2, 256)
    t = torch.rand(2, 64)
    e = torch.rand(2, 7)

    with torch.no_grad():
        fused, hazard = model(v, t, e)

    assert fused.shape == (2, 128)
    assert hazard.shape == (2, 1)
    assert 0.0 <= hazard.min().item() <= 1.0
    assert 0.0 <= hazard.max().item() <= 1.0


def test_multimodal_fusion_pipeline():
    """Test wrapper pipeline."""
    pipeline = MultimodalFusionPipeline()
    v = np.random.randn(256).astype(np.float32)
    t = np.random.randn(64).astype(np.float32)
    e = np.array([30.0, 10.0, 80.0, 90.0, 18.0, 0.45, 75.0], dtype=np.float32)

    res = pipeline.fuse(v, t, e)
    assert res["fused_embedding"].shape == (128,)
    assert 0.0 <= res["composite_hazard_index"] <= 1.0
    assert res["fused_dimension"] == 128


def test_coastal_risk_assessment():
    """Test coastal district impact and composite risk scoring."""
    engine = CoastalRiskAssessmentEngine()
    now = datetime(2026, 5, 20, 12, 0)

    # Mature storm right off Odisha coast (19.8°N, 86.5°E) with 95 kt winds
    storm = BestTrackPoint(
        timestamp=now,
        lat=19.8,
        lon=86.5,
        max_sustained_wind_kt=95.0,
        central_pressure_hpa=945.0,
        imd_category=CycloneStage.ESCS,
    )

    landfall_mock = {
        "has_landfall": True,
        "landfall_lat": 20.25,
        "landfall_lon": 86.65,
        "district": "Jagatsinghpur",
        "state_or_country": "Odisha",
        "intensity_at_landfall_kt": 90.0,
    }

    evaluations = engine.evaluate_risk_swath(storm, landfall_point=landfall_mock)

    assert len(evaluations) > 0
    top_district = evaluations[0]

    # Top district should have substantial risk
    assert top_district["composite_risk"] >= 60.0
    assert top_district["risk_category"] in ["HIGH", "CRITICAL"]
    assert top_district["surge_height_m"] > 1.5
    assert "critical_infrastructure" in top_district
    assert top_district["color_code"].startswith("#")


def test_imd_bulletin_generator():
    """Test standard IMD meteorological warning bulletin assembly."""
    generator = IMDBulletinGenerator(bulletin_sequence=3)
    now = datetime(2026, 5, 20, 12, 0)

    storm = BestTrackPoint(
        timestamp=now,
        lat=19.5,
        lon=87.0,
        max_sustained_wind_kt=85.0,
        central_pressure_hpa=955.0,
        imd_category=CycloneStage.VSCS,
    )

    landfall = {
        "has_landfall": True,
        "district": "Puri",
        "state_or_country": "Odisha",
        "eta_ist": "21-May-2026 14:30 IST",
        "intensity_at_landfall_kt": 80.0,
        "intensity_at_landfall_kmh": 148.2,
        "stage_at_landfall": "Very Severe Cyclonic Storm",
        "uncertainty_window_hours": 4.0,
    }

    high_risk_districts = [
        {"district": "Puri", "state": "Odisha", "composite_risk": 82.5, "risk_category": "CRITICAL", "surge_height_m": 3.2, "rainfall_alert": "RED"},
        {"district": "Jagatsinghpur", "state": "Odisha", "composite_risk": 78.0, "risk_category": "CRITICAL", "surge_height_m": 2.8, "rainfall_alert": "RED"},
    ]

    bulletin = generator.generate_bulletin(
        storm_name="FANI-TEST",
        current_observation=storm,
        forecast_points=[],
        landfall_info=landfall,
        high_risk_districts=high_risk_districts,
    )

    assert bulletin["bulletin_number"] == 3
    assert "STAGE" in bulletin["stage_tier"]
    assert len(bulletin["damages"]) >= 3
    assert len(bulletin["actions"]) >= 3
    assert "INDIA METEOROLOGICAL DEPARTMENT" in bulletin["plain_text"]
    assert "FANI-TEST" in bulletin["plain_text"]
    assert "<div class=" in bulletin["html"]
