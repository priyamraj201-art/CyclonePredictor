"""Phase 3 Verification Tests: Intensity Estimation, RI Prediction, and Grad-CAM."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import pytest
import torch
import numpy as np

from src.core.schemas import EnvironmentalFeatures
from src.core.constants import CycloneStage
from src.models.intensity import IntensityEstimationNetwork, IntensityEstimator
from src.models.rapid_intensification import RapidIntensificationClassifier
from src.models.explainability import GradCAM


def test_intensity_estimation_network_forward():
    """Test CNN + Self-Attention hybrid forward pass and output shapes."""
    model = IntensityEstimationNetwork(in_channels=4, embed_dim=256)
    model.eval()

    # Batch of 2 frames
    x = torch.rand(2, 4, 256, 256)
    with torch.no_grad():
        wind_speed, uncertainty, embedding = model(x)

    assert wind_speed.shape == (2,)
    assert uncertainty.shape == (2,)
    assert embedding.shape == (2, 256)

    assert wind_speed.min().item() >= 0.0
    assert uncertainty.min().item() > 0.0

    # Single-channel fallback
    x_single = torch.rand(1, 1, 256, 256)
    with torch.no_grad():
        w_single, _, _ = model(x_single)
    assert w_single.shape == (1,)


def test_intensity_estimator_wrapper():
    """Test production IntensityEstimator pipeline."""
    estimator = IntensityEstimator()
    tensor = torch.rand(4, 256, 256)

    res = estimator.estimate(tensor, calibration_bias_kt=5.0)

    assert "wind_speed_kt" in res
    assert "wind_speed_kmh" in res
    assert "uncertainty_kt" in res
    assert "imd_category" in res
    assert "central_pressure_hpa" in res
    assert res["visual_embedding"].shape == (256,)

    # Physical validity
    assert 10.0 <= res["wind_speed_kt"] <= 180.0
    assert 880.0 <= res["central_pressure_hpa"] <= 1010.0


def test_rapid_intensification_classifier():
    """Test GBDT RI prediction on favorable vs hostile thermodynamic profiles."""
    classifier = RapidIntensificationClassifier(operational_threshold=0.35)

    # 1. Highly favorable environment for RI
    env_favorable = EnvironmentalFeatures(
        sea_surface_temp_c=31.0,
        vertical_wind_shear_kt=7.0,
        relative_humidity_700hpa=88.0,
        ocean_heat_content_kj_cm2=110.0,
        vorticity_850hpa=25.0,
        coriolis_parameter=0.45,
    )
    res_fav = classifier.predict(env_favorable, current_wind_kt=55.0)

    assert "ri_probability" in res_fav
    assert "is_ri_flagged" in res_fav
    assert 0.0 <= res_fav["ri_probability"] <= 1.0
    assert len(res_fav["favorable_factors"]) >= 3

    # 2. Hostile environment (cold ocean, high shear, dry air)
    env_hostile = EnvironmentalFeatures(
        sea_surface_temp_c=26.5,
        vertical_wind_shear_kt=32.0,
        relative_humidity_700hpa=48.0,
        ocean_heat_content_kj_cm2=25.0,
        vorticity_850hpa=8.0,
        coriolis_parameter=0.30,
    )
    res_hostile = classifier.predict(env_hostile, current_wind_kt=30.0)

    # Hostile RI probability should be substantially lower than favorable
    assert res_hostile["ri_probability"] < res_fav["ri_probability"]
    assert res_hostile["is_ri_flagged"] is False
    assert len(res_hostile["inhibiting_factors"]) >= 3


def test_grad_cam_explainability():
    """Test Grad-CAM saliency extraction and Base64 overlay export."""
    model = IntensityEstimationNetwork(in_channels=4, embed_dim=256)
    grad_cam = GradCAM(model)

    test_tensor = torch.rand(4, 256, 256)

    # 1. 2D Heatmap
    heatmap = grad_cam.generate_heatmap(test_tensor)
    assert heatmap.shape == (256, 256)
    assert heatmap.min() >= 0.0
    assert heatmap.max() <= 1.0

    # 2. RGB Overlay and Base64 export
    overlay_rgb, b64_str = grad_cam.generate_saliency_overlay(test_tensor)
    assert overlay_rgb.shape == (256, 256, 3)
    assert overlay_rgb.dtype == np.uint8
    assert b64_str.startswith("data:image/png;base64,")
    assert len(b64_str) > 500
