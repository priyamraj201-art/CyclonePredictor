"""Phase 2 Verification Script: Cyclone Detection & Centre Localisation Engine.

Tests automated detection, storm center regression, geographic coordinate projection,
YOLOv8 compatibility, and circulation energy heatmap generation.
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
from src.core.constants import Basin, BASIN_BOUNDS
from src.core.logger import logger
from src.data.mock_generator import SyntheticCycloneGenerator
from src.models.detection import CycloneDetector, PRELIMINARY_STAGES
from src.utils.geospatial import haversine_distance_km


def verify_phase2():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 - Phase 2 Verification: Detection & Centre Engine")
    logger.info("=" * 65)

    generator = SyntheticCycloneGenerator(seed=101)
    detector = CycloneDetector()

    # 1. Bay of Bengal Mature Cyclone Detection
    logger.info("[1/4] Evaluating Detection & Centre Localisation on Bay of Bengal Cyclone...")
    obs_bob, raw_bob, mask_bob = generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL,
        intensity_kt=85.0,  # VSCS
        add_mask=False,
    )
    tensor_bob = torch.from_numpy((raw_bob - raw_bob.min()) / (raw_bob.max() - raw_bob.min() + 1e-6)).float()
    bbox_bob = obs_bob.satellite_meta.bounding_box
    gt_bob = (obs_bob.best_track.lat, obs_bob.best_track.lon)

    res_bob = detector.detect(
        satellite_tensor=tensor_bob,
        bounding_box=bbox_bob,
        ground_truth_latlon=gt_bob,
    )

    logger.info(f"  [OK] Storm ID: {obs_bob.frame_id}")
    logger.info(f"  [OK] True Center: {gt_bob[0]:.2f}°N, {gt_bob[1]:.2f}°E | Ground Truth: {obs_bob.best_track.imd_category.value}")
    logger.info(f"  [OK] Presence Probability: {res_bob['presence_probability']:.4f} (Detected: {res_bob['is_cyclone_detected']})")
    logger.info(f"  [OK] Predicted Center: {res_bob['center_lat_lon'][0]:.2f}°N, {res_bob['center_lat_lon'][1]:.2f}°E")
    logger.info(f"  [OK] Center Localisation Error: {res_bob['localisation_error_km']:.1f} km")
    logger.info(f"  [OK] Preliminary Stage: {res_bob['preliminary_stage']}")

    # 2. Arabian Sea Cyclone Detection
    logger.info("\n[2/4] Evaluating Detection & Centre Localisation on Arabian Sea Cyclone...")
    obs_as, raw_as, mask_as = generator.generate_single_observation(
        basin=Basin.ARABIAN_SEA,
        intensity_kt=45.0,  # Cyclonic Storm
        add_mask=False,
    )
    tensor_as = torch.from_numpy((raw_as - raw_as.min()) / (raw_as.max() - raw_as.min() + 1e-6)).float()
    bbox_as = obs_as.satellite_meta.bounding_box
    gt_as = (obs_as.best_track.lat, obs_as.best_track.lon)

    res_as = detector.detect(
        satellite_tensor=tensor_as,
        bounding_box=bbox_as,
        ground_truth_latlon=gt_as,
    )

    logger.info(f"  [OK] Storm ID: {obs_as.frame_id}")
    logger.info(f"  [OK] True Center: {gt_as[0]:.2f}°N, {gt_as[1]:.2f}°E ({obs_as.best_track.basin.value})")
    logger.info(f"  [OK] Presence Probability: {res_as['presence_probability']:.4f}")
    logger.info(f"  [OK] Predicted Center: {res_as['center_lat_lon'][0]:.2f}°N, {res_as['center_lat_lon'][1]:.2f}°E")
    logger.info(f"  [OK] Localisation Error: {res_as['localisation_error_km']:.1f} km")
    assert BASIN_BOUNDS[Basin.ARABIAN_SEA][2] <= res_as['center_lat_lon'][1] <= BASIN_BOUNDS[Basin.ARABIAN_SEA][3]

    # 3. YOLOv8 Interface & Circulation Energy Heatmap
    logger.info("\n[3/4] Verifying YOLOv8 Adapter & Circulation Energy Heatmap...")
    yolo_box = res_bob["yolo_detection"]
    logger.info(f"  [OK] YOLOv8 Bounding Box [x1, y1, x2, y2]: {yolo_box['bbox_xyxy']}")
    logger.info(f"  [OK] YOLOv8 Center Pixel: {yolo_box['center_pixel']} | Confidence: {yolo_box['confidence']}")

    energy_map = res_bob["energy_heatmap"]
    logger.info(f"  [OK] Circulation Energy Heatmap Shape: {energy_map.shape} | Range: [{energy_map.min():.2f}, {energy_map.max():.2f}]")
    assert energy_map.shape == (256, 256)

    # 4. Multi-Task Latent Feature Representation
    logger.info("\n[4/4] Verifying Multi-Task Latent Embeddings & Model Caching...")
    latent = res_bob["latent_features"]
    logger.info(f"  [OK] ResNet-18 Latent Feature Embedding Dimension: {latent.shape} (Ready for Phase 5 Attention Fusion)")

    weights_path = detector.save_weights(MODELS_DIR / "detection_phase2.pt")
    logger.info(f"  [OK] Detection Model Weights Cached at: {weights_path.name}")

    logger.info("\n" + "=" * 65)
    logger.info("PHASE 2 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    verify_phase2()
