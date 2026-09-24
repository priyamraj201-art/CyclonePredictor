"""Phase 2 Verification Tests: Cyclone Detection & Storm Centre Localisation Engine."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import pytest
import torch
import numpy as np

from src.core.constants import Basin, BASIN_BOUNDS
from src.data.mock_generator import SyntheticCycloneGenerator
from src.models.detection import (
    CycloneDetectionNetwork,
    CycloneDetector,
    CycloneDetectionDataset,
    YOLOv8Adapter,
    compute_circulation_energy_map,
    PRELIMINARY_STAGES,
)
from src.utils.geospatial import haversine_distance_km, pixel_to_latlon, latlon_to_pixel


def test_detection_network_forward():
    """Test 4-channel and 1-channel forward passes and output dimensions."""
    model = CycloneDetectionNetwork(in_channels=4, pretrained=False)
    model.eval()

    # 1. Standard 4-channel batch
    batch_4ch = torch.rand(3, 4, 256, 256)
    with torch.no_grad():
        out_4ch = model(batch_4ch)

    assert out_4ch["presence"].shape == (3, 1)
    assert out_4ch["centre"].shape == (3, 2)
    assert out_4ch["stage_logits"].shape == (3, 3)
    assert out_4ch["features"].shape == (3, 512)

    # Check bounds
    assert out_4ch["presence"].min() >= 0.0
    assert out_4ch["presence"].max() <= 1.0
    assert out_4ch["centre"].min() >= 0.0
    assert out_4ch["centre"].max() <= 1.0

    # 2. Single-channel IR fallback
    batch_1ch = torch.rand(2, 1, 256, 256)
    with torch.no_grad():
        out_1ch = model(batch_1ch)
    assert out_1ch["presence"].shape == (2, 1)
    assert out_1ch["centre"].shape == (2, 2)


def test_yolo_adapter():
    """Test YOLOv8 bounding box and center extraction interface."""
    adapter = YOLOv8Adapter(confidence_threshold=0.4)
    dummy_img = np.zeros((4, 256, 256), dtype=np.float32)

    boxes = adapter.predict_boxes(
        image_array=dummy_img,
        center_norm=(0.55, 0.45),
        confidence=0.88,
        stage_name="Severe Cyclonic Storm+",
    )

    assert len(boxes) == 1
    box = boxes[0]
    assert "bbox_xyxy" in box
    assert "center_pixel" in box
    assert box["confidence"] == 0.88
    assert box["class_name"] == "Severe Cyclonic Storm+"
    assert box["center_norm"] == [0.55, 0.45]


def test_circulation_energy_map():
    """Test circulation heatmap generation."""
    dummy_tensor = torch.rand(4, 256, 256)
    energy_map = compute_circulation_energy_map(
        tensor=dummy_tensor,
        predicted_center_norm=(0.5, 0.5),
        image_shape=(256, 256),
    )

    assert energy_map.shape == (256, 256)
    assert energy_map.min() >= 0.0
    assert energy_map.max() <= 1.0
    # Center region should have high energy
    center_energy = energy_map[128, 128]
    corner_energy = energy_map[10, 10]
    assert center_energy > corner_energy


def test_cyclone_detection_dataset():
    """Test dataset creation and sample loading."""
    generator = SyntheticCycloneGenerator(seed=42)
    sample1 = generator.generate_single_observation(intensity_kt=25.0)  # Depression
    sample2 = generator.generate_single_observation(intensity_kt=75.0)  # Severe+

    dataset = CycloneDetectionDataset([sample1, sample2])
    assert len(dataset) == 2

    item0 = dataset[0]
    assert item0["tensor"].shape == (4, 256, 256)
    assert item0["presence"].shape == (1,)
    assert item0["centre"].shape == (2,)
    assert item0["stage"].item() == 0  # Depression

    item1 = dataset[1]
    assert item1["stage"].item() == 2  # Severe+


def test_cyclone_detector_inference():
    """Test end-to-end CycloneDetector pipeline with geospatial projection."""
    generator = SyntheticCycloneGenerator(seed=777)
    obs, raw, mask = generator.generate_single_observation(
        basin=Basin.BAY_OF_BENGAL,
        intensity_kt=80.0,
    )

    # Normalize raw to tensor
    tensor = torch.from_numpy((raw - raw.min()) / (raw.max() - raw.min() + 1e-6)).float()

    detector = CycloneDetector()
    bbox = obs.satellite_meta.bounding_box
    ground_truth = (obs.best_track.lat, obs.best_track.lon)

    result = detector.detect(
        satellite_tensor=tensor,
        bounding_box=bbox,
        ground_truth_latlon=ground_truth,
    )

    assert "is_cyclone_detected" in result
    assert "presence_probability" in result
    assert "center_lat_lon" in result
    assert "preliminary_stage" in result
    assert "localisation_error_km" in result

    # Center must fall inside bounding box
    min_lat, max_lat, min_lon, max_lon = bbox
    pred_lat, pred_lon = result["center_lat_lon"]
    assert min_lat <= pred_lat <= max_lat
    assert min_lon <= pred_lon <= max_lon

    # Error in km must be non-negative
    assert result["localisation_error_km"] >= 0.0
    assert result["energy_heatmap"].shape == (256, 256)
