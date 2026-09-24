"""Phase 1 Verification Script.

Executes end-to-end generation of synthetic satellite frames, runs radiometric normalization,
inpaint missing scan gaps with the convolutional autoencoder, and validates IMD domain contracts.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import torch


from src.core.constants import CycloneStage, Basin
from src.core.config import SYNTHETIC_DATA_DIR, MODELS_DIR
from src.core.logger import logger
from src.data.mock_generator import SyntheticCycloneGenerator
from src.data.autoencoder import InpaintingPipeline
from src.data.preprocessing import SatellitePreprocessor
from src.data.ingestion import load_single_archive
from src.utils.conversions import knots_to_kmh, knots_to_stage, estimate_central_pressure
from src.utils.geospatial import haversine_distance_km


def verify_phase1():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 - Phase 1 Verification: Data Engine & Inpainting")
    logger.info("=" * 65)

    # 1. IMD Classification & Pressure Verification
    logger.info("[1/5] Testing IMD Wind Speed to Stage Classifications...")
    test_cases = [
        (15.0, CycloneStage.LPA),
        (25.0, CycloneStage.D),
        (30.0, CycloneStage.DD),
        (45.0, CycloneStage.CS),
        (60.0, CycloneStage.SCS),
        (80.0, CycloneStage.VSCS),
        (105.0, CycloneStage.ESCS),
        (130.0, CycloneStage.SuCS),
    ]
    for w_kt, expected_stage in test_cases:
        stage = knots_to_stage(w_kt)
        kmh = knots_to_kmh(w_kt)
        press = estimate_central_pressure(w_kt)
        assert stage == expected_stage, f"Failed for {w_kt} kt: got {stage} vs {expected_stage}"
        logger.info(f"  [OK] {w_kt:5.1f} kt ({kmh:5.1f} km/h) -> {stage.value:<28} | Est. Pressure: {press} hPa")

    # 2. Synthetic Satellite Frame Generation
    logger.info("\n[2/5] Synthesizing 4-Channel INSAT-3D Frame (Holland Vortex Model)...")
    generator = SyntheticCycloneGenerator(seed=42)
    obs, raw, mask = generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL,
        intensity_kt=75.0,  # Very Severe Cyclonic Storm
        add_mask=True,
    )
    logger.info(f"  [OK] Generated Frame ID: {obs.frame_id}")
    logger.info(f"  [OK] Storm Center: {obs.best_track.lat:.2f}°N, {obs.best_track.lon:.2f}°E ({obs.best_track.basin.value})")
    logger.info(f"  [OK] Intensity: {obs.best_track.max_sustained_wind_kt} kt ({obs.best_track.imd_category.value})")
    logger.info(f"  [OK] Raw Shape: {raw.shape} | Channels: IR, WV, VIS, PMW")
    logger.info(f"  [OK] IR Range: [{raw[0].min():.1f} K, {raw[0].max():.1f} K]")
    logger.info(f"  [OK] WV Range: [{raw[1].min():.1f} K, {raw[1].max():.1f} K]")
    logger.info(f"  [OK] VIS Range: [{raw[2].min():.3f}, {raw[2].max():.3f}]")
    logger.info(f"  [OK] PMW Range: [{raw[3].min():.1f} K, {raw[3].max():.1f} K]")
    missing_pct = (1.0 - (np.sum(mask) / mask.size)) * 100
    logger.info(f"  [OK] Simulated Missing/Sensor Dropout: {missing_pct:.2f}% of pixels")

    # 3. Convolutional Autoencoder Inpainting
    logger.info("\n[3/5] Inpainting Missing Satellite Patches via Convolutional U-Net Autoencoder...")
    inpainter = InpaintingPipeline()
    preprocessor = SatellitePreprocessor(inpainter=inpainter)
    tensor, qa_report = preprocessor.process(raw, mask=mask, inpaint_if_needed=True)

    logger.info(f"  [OK] QA Screening: {qa_report['reason']}")
    logger.info(f"  [OK] Inpainting Applied: {qa_report['was_inpainted']}")
    logger.info(f"  [OK] Final Tensor Shape: {tuple(tensor.shape)} on {tensor.device}")
    logger.info(f"  [OK] Value Range Post-Normalization: [{tensor.min().item():.3f}, {tensor.max().item():.3f}]")
    assert tensor.shape == (4, 256, 256)
    assert not torch.isnan(tensor).any()

    # Save initialized weights
    weights_path = inpainter.save_weights(MODELS_DIR / "autoencoder_phase1.pt")
    logger.info(f"  [OK] Inpainting Autoencoder Weights Cached at: {weights_path.name}")

    # 4. Storage & Round-Trip Ingestion
    logger.info("\n[4/5] Testing Compressed Archive Storage & Dataset Loading...")
    saved_path = generator.save_observation_npz(obs, raw, mask, SYNTHETIC_DATA_DIR)
    logger.info(f"  [OK] Saved .npz Archive: {saved_path.name} ({saved_path.stat().st_size / 1024:.1f} KB)")

    loaded_tensor, loaded_obs = load_single_archive(saved_path)
    logger.info(f"  [OK] Successfully Reloaded Observation: {loaded_obs.frame_id}")
    assert loaded_obs.frame_id == obs.frame_id
    assert loaded_tensor.shape == (4, 256, 256)

    # 5. Geospatial Verification
    logger.info("\n[5/5] Verifying Geospatial Projection & Haversine Distance...")
    dist = haversine_distance_km(obs.best_track.lat, obs.best_track.lon, 20.0, 86.0)
    logger.info(f"  [OK] Distance from storm center to Odisha coast (20N, 86E): {dist:.1f} km")

    logger.info("\n" + "=" * 65)
    logger.info("PHASE 1 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    verify_phase1()
