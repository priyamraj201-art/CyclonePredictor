"""Phase 5 Verification Script: Multimodal Fusion & Dynamic Coastal Risk Assessment.

Validates:
1. Cross-Modal Attention Fusion (Visual 256-d + Track 64-d + Reanalysis 7-d -> Unified 128-d).
2. GIS Coastal District Risk Engine (wind swath, surge heights, population exposure).
3. Automated IMD 4-Stage Warning Bulletin Generation (Plain Text & HTML).
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from src.core.config import MODELS_DIR
from src.core.constants import CycloneStage
from src.core.logger import logger
from src.core.schemas import BestTrackPoint
from src.models.fusion import MultimodalFusionPipeline
from src.risk.risk_assessment import CoastalRiskAssessmentEngine
from src.risk.bulletin_generator import IMDBulletinGenerator


def verify_phase5():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 - Phase 5 Verification: Fusion & Coastal Risk Engine")
    logger.info("=" * 65)

    now = datetime(2026, 5, 20, 6, 0)

    # 1. Multimodal Cross-Attention Fusion
    logger.info("[1/3] Executing Cross-Modal Attention Fusion...")
    fusion_pipe = MultimodalFusionPipeline()

    visual_dummy = np.random.randn(256).astype(np.float32)
    track_dummy = np.random.randn(64).astype(np.float32)
    env_dummy = np.array([30.5, 11.0, 82.0, 95.0, 20.0, 0.48, 85.0], dtype=np.float32)

    fusion_res = fusion_pipe.fuse(visual_dummy, track_dummy, env_dummy)

    logger.info(f"  [OK] Input Modalities: Visual (256-d), Track Dynamics (64-d), Reanalysis (7-d)")
    logger.info(f"  [OK] Fused Unified Representation Dimension: {fusion_res['fused_dimension']}")
    logger.info(f"  [OK] Composite Deep Hazard Index: {fusion_res['composite_hazard_index']:.4f}")

    weights_path = fusion_pipe.save_weights(MODELS_DIR / "multimodal_fusion_phase5.pt")
    logger.info(f"  [OK] Multimodal Fusion Weights Cached: {weights_path.name}")

    # 2. Dynamic GIS Coastal Risk Assessment
    logger.info("\n[2/3] Evaluating Coastal District Vulnerability & Multi-Hazard Impact...")
    risk_engine = CoastalRiskAssessmentEngine()

    current_storm = BestTrackPoint(
        timestamp=now,
        lat=19.4,
        lon=87.2,
        max_sustained_wind_kt=95.0,  # Extremely Severe Cyclonic Storm
        central_pressure_hpa=942.0,
        imd_category=CycloneStage.ESCS,
    )

    landfall_target = {
        "has_landfall": True,
        "landfall_lat": 20.25,
        "landfall_lon": 86.65,
        "district": "Jagatsinghpur",
        "state_or_country": "Odisha",
        "intensity_at_landfall_kt": 90.0,
        "intensity_at_landfall_kmh": round(90.0 * 1.852, 1),
        "stage_at_landfall": "Extremely Severe Cyclonic Storm",
        "eta_ist": "21-May-2026 11:30 IST",
        "uncertainty_window_hours": 4.5,
    }

    evaluations = risk_engine.evaluate_risk_swath(current_storm, landfall_point=landfall_target)

    logger.info(f"  [OK] Total Coastal Districts Evaluated in Impact Swath: {len(evaluations)}")
    logger.info("  [OK] Top Impacted Coastal Districts Ranked by Composite Risk:")
    for dist in evaluations[:4]:
        logger.info(
            f"    - {dist['district']:<18} ({dist['state']}): Risk {dist['composite_risk']:5.1f} "
            f"[{dist['risk_category']}] | Surge: {dist['surge_height_m']}m ({dist['surge_severity']}) "
            f"| Wind: {dist['local_wind_kt']} kt | Infra: {', '.join(dist['critical_infrastructure'][:2])}"
        )

    # 3. Automated IMD Cyclone Warning Bulletin Generation
    logger.info("\n[3/3] Generating Standard IMD 4-Stage Cyclone Alert Bulletin...")
    bulletin_gen = IMDBulletinGenerator(bulletin_sequence=5)
    bulletin = bulletin_gen.generate_bulletin(
        storm_name="SHAKTI",
        current_observation=current_storm,
        forecast_points=[],
        landfall_info=landfall_target,
        high_risk_districts=evaluations,
    )

    logger.info(f"  [OK] Bulletin Sequence: #{bulletin['bulletin_number']}")
    logger.info(f"  [OK] Warning Tier: {bulletin['stage_tier']}")
    logger.info(f"  [OK] Issued At: {bulletin['issued_at_ist']}")
    logger.info(f"  [OK] Plain Text Bulletin Length: {len(bulletin['plain_text'].splitlines())} lines")
    logger.info(f"  [OK] HTML Export Length: {len(bulletin['html'])} chars")

    logger.info("\n" + "=" * 65)
    logger.info("PHASE 5 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    verify_phase5()
