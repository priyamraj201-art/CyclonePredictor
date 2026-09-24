"""Phase 4 Verification Tests: Track Forecasting, Uncertainty Cones, and Landfall Prediction."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from datetime import datetime, timedelta
import pytest
import torch

from src.core.schemas import BestTrackPoint
from src.models.track import BiLSTMTrackForecaster, TrackForecastPipeline
from src.utils.uncertainty_cone import UncertaintyConeGenerator
from src.utils.landfall import LandfallPredictor


def test_bilstm_track_network_forward():
    """Test Bi-directional LSTM forward pass and output shapes."""
    model = BiLSTMTrackForecaster(input_dim=6, hidden_dim=128)
    model.eval()

    # Batch of 2 historical trajectories, each of length 4 steps
    x = torch.rand(2, 4, 6)
    with torch.no_grad():
        deltas, intensities, embedding = model(x)

    assert deltas.shape == (2, 4, 2)
    assert intensities.shape == (2, 4)
    assert embedding.shape == (2, 64)


def test_track_forecast_pipeline():
    """Test multi-step trajectory projection."""
    pipeline = TrackForecastPipeline()
    t0 = datetime(2026, 5, 15, 0, 0)

    # 3 historical points (12 hours of tracking)
    history = [
        BestTrackPoint(timestamp=t0 - timedelta(hours=12), lat=12.0, lon=89.0, max_sustained_wind_kt=40.0),
        BestTrackPoint(timestamp=t0 - timedelta(hours=6),  lat=13.0, lon=88.5, max_sustained_wind_kt=50.0),
        BestTrackPoint(timestamp=t0,                       lat=14.2, lon=88.0, max_sustained_wind_kt=65.0),
    ]

    res = pipeline.forecast(history)

    assert "forecast_points" in res
    assert len(res["forecast_points"]) == 4
    assert res["track_embedding"].shape == (64,)

    # Check timestamps: +6h, +12h, +24h, +48h
    leads = [6, 12, 24, 48]
    for i, pt in enumerate(res["forecast_points"]):
        expected_time = t0 + timedelta(hours=leads[i])
        assert pt.timestamp == expected_time
        assert 0.0 <= pt.lat <= 35.0
        assert 45.0 <= pt.lon <= 105.0
        assert pt.max_sustained_wind_kt > 0


def test_uncertainty_cone_geojson():
    """Test GeoJSON 70% probability envelope generation."""
    generator = UncertaintyConeGenerator()
    t0 = datetime(2026, 5, 15, 0, 0)

    cur_pt = BestTrackPoint(timestamp=t0, lat=15.0, lon=88.0, max_sustained_wind_kt=60.0)
    forecast_pts = [
        BestTrackPoint(timestamp=t0 + timedelta(hours=6),  lat=15.8, lon=87.5, max_sustained_wind_kt=70.0),
        BestTrackPoint(timestamp=t0 + timedelta(hours=12), lat=16.6, lon=87.0, max_sustained_wind_kt=80.0),
        BestTrackPoint(timestamp=t0 + timedelta(hours=24), lat=18.2, lon=86.3, max_sustained_wind_kt=90.0),
        BestTrackPoint(timestamp=t0 + timedelta(hours=48), lat=20.5, lon=85.8, max_sustained_wind_kt=75.0),
    ]

    geojson = generator.generate_geojson(forecast_pts, initial_point=cur_pt, storm_name="TEST CYCLONE")

    assert geojson["type"] == "FeatureCollection"
    features = geojson["features"]
    assert len(features) >= 3  # Cone polygon + Track line + Waypoints

    # Cone Polygon check
    cone_feat = next(f for f in features if f["properties"]["type"] == "uncertainty_cone")
    coords = cone_feat["geometry"]["coordinates"][0]
    assert len(coords) > 10
    # Must be closed polygon
    assert coords[0] == coords[-1]


def test_landfall_prediction():
    """Test landfall detection on a track crossing the Odisha coast."""
    predictor = LandfallPredictor()
    t0 = datetime(2026, 5, 15, 0, 0)

    cur_pt = BestTrackPoint(timestamp=t0, lat=17.5, lon=87.5, max_sustained_wind_kt=75.0)
    # Track heading directly into Odisha coast near Puri (lat ~ 19.8N, lon ~ 85.8E)
    forecast_pts = [
        BestTrackPoint(timestamp=t0 + timedelta(hours=6),  lat=18.2, lon=87.0, max_sustained_wind_kt=80.0),
        BestTrackPoint(timestamp=t0 + timedelta(hours=12), lat=19.0, lon=86.5, max_sustained_wind_kt=85.0),
        BestTrackPoint(timestamp=t0 + timedelta(hours=24), lat=20.2, lon=85.8, max_sustained_wind_kt=70.0),  # Inland
        BestTrackPoint(timestamp=t0 + timedelta(hours=48), lat=22.0, lon=85.2, max_sustained_wind_kt=40.0),  # Dissipating inland
    ]

    res = predictor.predict_landfall(forecast_pts, initial_point=cur_pt)

    assert res["has_landfall"] is True
    assert "Puri" in res["district"] or "Odisha" in res["state_or_country"] or "Kendrapara" in res["district"] or "Jagatsinghpur" in res["district"]
    assert "eta_utc" in res
    assert "eta_ist" in res
    assert res["intensity_at_landfall_kt"] > 50.0
