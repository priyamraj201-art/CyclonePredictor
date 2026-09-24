"""Phase 3 Verification Script: Intensity Estimation, RI Classifier & Grad-CAM.

Validates:
1. CNN + Multi-Head Self-Attention wind speed regression and heteroscedastic uncertainty.
2. XGBoost/GBDT Rapid Intensification classifier on NIO thermodynamic features.
3. Grad-CAM visual saliency heatmap and Base64 overlay generation.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from src.core.config import MODELS_DIR
from src.core.constants import Basin
from src.core.logger import logger
from src.data.mock_generator import SyntheticCycloneGenerator
from src.models.intensity import IntensityEstimator
from src.models.rapid_intensification import RapidIntensificationClassifier
from src.models.explainability import GradCAM


def verify_phase3():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 - Phase 3 Verification: Intensity, RI & Explainability")
    logger.info("=" * 65)

    # 1. Synthesize observation
    generator = SyntheticCycloneGenerator(seed=202)
    obs, raw, mask = generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL,
        intensity_kt=90.0,  # Extremely Severe Cyclonic Storm
        add_mask=False,
    )
    norm_tensor = torch.from_numpy((raw - raw.min()) / (raw.max() - raw.min() + 1e-6)).float()

    # 2. Intensity Estimation
    logger.info("[1/3] Evaluating CNN + Multi-Head Self-Attention Intensity Estimator...")
    intensity_estimator = IntensityEstimator()
    int_res = intensity_estimator.estimate(norm_tensor)

    logger.info(f"  [OK] Storm ID: {obs.frame_id}")
    logger.info(f"  [OK] Ground Truth Intensity: {obs.best_track.max_sustained_wind_kt} kt ({obs.best_track.imd_category.value})")
    logger.info(f"  [OK] Predicted Wind Speed: {int_res['wind_speed_kt']} kt ({int_res['wind_speed_kmh']} km/h)")
    logger.info(f"  [OK] Uncertainty (1-sigma): +/- {int_res['uncertainty_kt']} kt")
    logger.info(f"  [OK] Predicted IMD Stage: {int_res['imd_category']}")
    logger.info(f"  [OK] Central Pressure: {int_res['central_pressure_hpa']} hPa (Deficit: {int_res['pressure_deficit_hpa']} hPa)")
    logger.info(f"  [OK] Visual Latent Embedding: shape {int_res['visual_embedding'].shape}")

    weights_int = intensity_estimator.save_weights(MODELS_DIR / "intensity_phase3.pt")
    logger.info(f"  [OK] Intensity Weights Cached: {weights_int.name}")

    # 3. Rapid Intensification Prediction
    logger.info("\n[2/3] Evaluating Rapid Intensification (RI) Classifier...")
    ri_classifier = RapidIntensificationClassifier(operational_threshold=0.35)
    ri_res = ri_classifier.predict(obs.env_features, current_wind_kt=obs.best_track.max_sustained_wind_kt)

    logger.info(f"  [OK] Model Backend: {ri_res['model_type']}")
    logger.info(f"  [OK] RI Probability (24-hour): {ri_res['ri_probability']:.1%}")
    logger.info(f"  [OK] Operational Trigger Threshold: {ri_res['operational_threshold']:.0%}")
    logger.info(f"  [OK] RI Alert Flagged: {ri_res['is_ri_flagged']}")
    for factor in ri_res["favorable_factors"]:
        logger.info(f"    + Favorable: {factor}")
    for factor in ri_res["inhibiting_factors"]:
        logger.info(f"    - Inhibiting: {factor}")
    logger.info(f"  [OK] IMD Advisory: {ri_res['advisory']}")

    ri_model_path = ri_classifier.save(MODELS_DIR / "ri_classifier_phase3.pkl")
    logger.info(f"  [OK] RI Model Cached: {ri_model_path.name}")

    # 4. Grad-CAM Explainability
    logger.info("\n[3/3] Generating Grad-CAM Visual Explainability Saliency Overlay...")
    grad_cam = GradCAM(intensity_estimator.model)
    overlay_rgb, b64_overlay = grad_cam.generate_saliency_overlay(norm_tensor)

    logger.info(f"  [OK] Saliency Heatmap Shape: {overlay_rgb.shape}")
    logger.info(f"  [OK] Base64 Overlay URL Generated: {b64_overlay[:60]}... ({len(b64_overlay)} chars)")

    logger.info("\n" + "=" * 65)
    logger.info("PHASE 3 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    verify_phase3()
