"""Phase 1 Verification Tests: Schemas, Synthetic Ingestion, and Autoencoder Inpainting."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import torch

from src.core.constants import CycloneStage, Basin, CHANNEL_NORMALIZATION_RANGES
from src.core.schemas import (
    CycloneObservation,
    EnvironmentalFeatures,
    BestTrackPoint,
    SatelliteFrameMeta,
)
from src.data.mock_generator import SyntheticCycloneGenerator
from src.data.autoencoder import SatelliteInpaintingAutoencoder, InpaintingPipeline
from src.data.preprocessing import (
    SatellitePreprocessor,
    normalize_channels,
    denormalize_channels,
)
from src.data.ingestion import load_single_archive, SatelliteObservationDataset
from src.utils.conversions import knots_to_kmh, kmh_to_knots, knots_to_stage, estimate_central_pressure
from src.utils.geospatial import haversine_distance_km, pixel_to_latlon, latlon_to_pixel, identify_basin


def test_imd_wind_conversions():
    """Test IMD intensity classification logic across all stages."""
    assert knots_to_stage(12.0) == CycloneStage.LPA
    assert knots_to_stage(20.0) == CycloneStage.D
    assert knots_to_stage(30.0) == CycloneStage.DD
    assert knots_to_stage(40.0) == CycloneStage.CS
    assert knots_to_stage(55.0) == CycloneStage.SCS
    assert knots_to_stage(75.0) == CycloneStage.VSCS
    assert knots_to_stage(105.0) == CycloneStage.ESCS
    assert knots_to_stage(130.0) == CycloneStage.SuCS

    # Boundary tests
    assert knots_to_stage(17.0) == CycloneStage.D
    assert knots_to_stage(34.0) == CycloneStage.CS
    assert knots_to_stage(64.0) == CycloneStage.VSCS
    assert knots_to_stage(120.0) == CycloneStage.SuCS

    # Speed conversions
    assert knots_to_kmh(100.0) == 185.2
    assert kmh_to_knots(185.2) == 100.0

    # Empirical central pressure should decrease as wind speed increases
    p_lpa = estimate_central_pressure(15.0)
    p_cs = estimate_central_pressure(40.0)
    p_vscs = estimate_central_pressure(75.0)
    p_sucs = estimate_central_pressure(130.0)
    assert p_lpa > p_cs > p_vscs > p_sucs
    assert p_sucs >= 880.0


def test_geospatial_utilities():
    """Test Haversine distance and coordinate transformations."""
    # Distance between Chennai (13.0827, 80.2707) and Kolkata (22.5726, 88.3639) is ~1360 km
    dist = haversine_distance_km(13.0827, 80.2707, 22.5726, 88.3639)
    assert 1300.0 < dist < 1420.0

    # Distance to self is 0
    assert haversine_distance_km(15.0, 85.0, 15.0, 85.0) == 0.0

    # Pixel coordinate roundtrip
    bbox = (5.0, 25.0, 80.0, 100.0)
    shape = (256, 256)
    px, py = latlon_to_pixel(15.0, 90.0, shape, bbox)
    lat, lon = pixel_to_latlon(px, py, shape, bbox)
    assert abs(lat - 15.0) < 0.2
    assert abs(lon - 90.0) < 0.2

    # Basin identification
    assert identify_basin(14.0, 85.0) == Basin.BAY_OF_BENGAL
    assert identify_basin(17.0, 68.0) == Basin.ARABIAN_SEA


def test_pydantic_schemas():
    """Test domain model validation and automatic computation."""
    now = datetime(2026, 5, 12, 12, 0)
    meta = SatelliteFrameMeta(
        frame_id="TEST_001",
        timestamp=now,
        bounding_box=(5.0, 25.0, 80.0, 100.0),
    )
    assert meta.channels == ["IR", "WV", "VIS", "PMW"]

    env = EnvironmentalFeatures(
        sea_surface_temp_c=30.2,
        vertical_wind_shear_kt=11.5,
        relative_humidity_700hpa=82.0,
        ocean_heat_content_kj_cm2=88.0,
    )
    assert env.sea_surface_temp_c == 30.2

    track = BestTrackPoint(
        timestamp=now,
        lat=15.2,
        lon=88.4,
        max_sustained_wind_kt=70.0,
    )
    # Autocomputed properties
    assert track.imd_category == CycloneStage.VSCS
    assert track.max_sustained_wind_kmh is not None
    assert track.basin == Basin.BAY_OF_BENGAL

    obs = CycloneObservation(
        frame_id=meta.frame_id,
        satellite_meta=meta,
        env_features=env,
        best_track=track,
    )
    assert obs.best_track.imd_category == CycloneStage.VSCS


def test_synthetic_cyclone_generator():
    """Test Holland-vortex synthetic multi-channel satellite generation."""
    generator = SyntheticCycloneGenerator(seed=123)
    obs, raw_channels, mask = generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL,
        intensity_kt=65.0,
        add_mask=True,
    )

    # Check shapes
    assert raw_channels.shape == (4, 256, 256)
    assert mask.shape == (4, 256, 256)

    # Check physical value bounds
    ir_min, ir_max = CHANNEL_NORMALIZATION_RANGES["IR"]
    wv_min, wv_max = CHANNEL_NORMALIZATION_RANGES["WV"]
    vis_min, vis_max = CHANNEL_NORMALIZATION_RANGES["VIS"]
    pmw_min, pmw_max = CHANNEL_NORMALIZATION_RANGES["PMW"]

    # Filter unmasked areas for physical range verification
    assert raw_channels[0][mask[0] == 1].min() >= ir_min - 1.0
    assert raw_channels[0][mask[0] == 1].max() <= ir_max + 1.0
    assert raw_channels[1][mask[1] == 1].min() >= wv_min - 1.0
    assert raw_channels[1][mask[1] == 1].max() <= wv_max + 1.0
    assert raw_channels[2][mask[2] == 1].min() >= vis_min - 0.05
    assert raw_channels[2][mask[2] == 1].max() <= vis_max + 0.05
    assert raw_channels[3][mask[3] == 1].min() >= pmw_min - 1.0
    assert raw_channels[3][mask[3] == 1].max() <= pmw_max + 1.0

    # Test trajectory generation
    traj = generator.generate_synthetic_trajectory(num_steps=5)
    assert len(traj) == 5
    for step_obs, step_raw, step_mask in traj:
        assert step_raw.shape == (4, 256, 256)
        assert 5.0 <= step_obs.best_track.lat <= 25.0


def test_autoencoder_inpainting_forward():
    """Test PyTorch Convolutional Autoencoder architecture and inpainting blend."""
    model = SatelliteInpaintingAutoencoder(in_channels=4, out_channels=4)
    model.eval()

    # Batch of 2 frames with random missing patches
    x = torch.rand(2, 4, 256, 256)
    mask = torch.ones(2, 4, 256, 256)
    mask[:, :, 50:100, 50:100] = 0.0  # Missing patch
    x = x * mask  # Corrupted input

    with torch.no_grad():
        out = model(x, mask=mask)

    assert out.shape == (2, 4, 256, 256)
    assert out.min() >= 0.0
    assert out.max() <= 1.0

    # Verify that valid unmasked pixels are preserved exactly
    valid_region_diff = torch.abs((out - x) * mask).max().item()
    assert valid_region_diff < 1e-5


def test_preprocessing_and_ingestion_pipeline():
    """Test end-to-end preprocessing, QA screening, and dataset loading."""
    generator = SyntheticCycloneGenerator(seed=999)
    obs, raw, mask = generator.generate_single_observation(add_mask=True)

    preprocessor = SatellitePreprocessor()

    # Successful processing with inpainting
    tensor, report = preprocessor.process(raw, mask=mask, inpaint_if_needed=True)
    assert tensor.shape == (4, 256, 256)
    assert report["is_valid"] is True
    assert report["was_inpainted"] is True

    # Test rejection of corrupt input (contains NaNs)
    corrupt_raw = raw.copy()
    corrupt_raw[0, 10, 10] = np.nan
    with pytest.raises(ValueError):
        preprocessor.process(corrupt_raw)

    # Test disk save & load
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        saved_file = generator.save_observation_npz(obs, raw, mask, tmp_path)
        assert saved_file.exists()

        loaded_tensor, loaded_obs = load_single_archive(saved_file)
        assert loaded_tensor.shape == (4, 256, 256)
        assert loaded_obs.frame_id == obs.frame_id
        assert loaded_obs.best_track.imd_category == obs.best_track.imd_category
