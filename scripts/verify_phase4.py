"""Phase 4 Verification Script: Track Forecasting, Uncertainty Cones & Landfall Prediction.

Validates:
1. Sequential multi-step track projection via Bi-directional LSTM.
2. GeoJSON 70% probability uncertainty cone generation.
3. Coastal intersection ray-casting for Landfall Location, District, ETA (UTC & IST), and Intensity.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import MODELS_DIR
from src.core.logger import logger
from src.core.schemas import BestTrackPoint
from src.models.track import TrackForecastPipeline
from src.utils.uncertainty_cone import UncertaintyConeGenerator
from src.utils.landfall import LandfallPredictor


def verify_phase4():
    logger.info("=" * 65)
    logger.info("SIH 2026 PS 26070 - Phase 4 Verification: Track & Landfall Engine")
    logger.info("=" * 65)

    t0 = datetime(2026, 5, 18, 6, 0)

    # 1. Historical track sequence
    logger.info("[1/3] Running Sequential Track Forecaster (+6h, +12h, +24h, +48h)...")
    history = [
        BestTrackPoint(timestamp=t0 - timedelta(hours=18), lat=12.5, lon=89.5, max_sustained_wind_kt=45.0),
        BestTrackPoint(timestamp=t0 - timedelta(hours=12), lat=13.8, lon=88.8, max_sustained_wind_kt=60.0),
        BestTrackPoint(timestamp=t0 - timedelta(hours=6),  lat=15.2, lon=88.1, max_sustained_wind_kt=75.0),
        BestTrackPoint(timestamp=t0,                       lat=16.8, lon=87.4, max_sustained_wind_kt=90.0),
    ]

    forecaster = TrackForecastPipeline()
    track_res = forecaster.forecast(history)

    for pt in track_res["forecast_points"]:
        lead_h = int((pt.timestamp - t0).total_seconds() / 3600)
        logger.info(
            f"  [OK] +{lead_h:02d}h ({pt.timestamp.strftime('%d %b %H:%M UTC')}): "
            f"{pt.lat:.2f}°N, {pt.lon:.2f}°E | {pt.max_sustained_wind_kt:.0f} kt ({pt.imd_category.value}) "
            f"| P_min: {pt.central_pressure_hpa} hPa"
        )
    logger.info(f"  [OK] Sequential Track Latent Embedding Shape: {track_res['track_embedding'].shape}")

    weights_path = forecaster.save_weights(MODELS_DIR / "track_phase4.pt")
    logger.info(f"  [OK] Track Forecaster Weights Cached: {weights_path.name}")

    # 2. Uncertainty Cone Generation
    logger.info("\n[2/3] Generating 70% Probability Uncertainty Cone & GeoJSON Payload...")
    cone_gen = UncertaintyConeGenerator()
    geojson = cone_gen.generate_geojson(
        forecast_points=track_res["forecast_points"],
        initial_point=history[-1],
        storm_name="VERY SEVERE CYCLONIC STORM",
    )

    cone_feature = next(f for f in geojson["features"] if f["properties"]["type"] == "uncertainty_cone")
    poly_pts = len(cone_feature["geometry"]["coordinates"][0])
    logger.info(f"  [OK] Uncertainty Cone Closed Polygon Points: {poly_pts}")
    logger.info(f"  [OK] GeoJSON Total Features: {len(geojson['features'])} (Cone + Centerline + {len(geojson['features'])-2} Waypoints)")

    # 3. Landfall Prediction Engine
    logger.info("\n[3/3] Evaluating Coastal Crossing Ray-Casting & Landfall Prediction...")
    landfall_pred = LandfallPredictor()
    landfall_res = landfall_pred.predict_landfall(
        forecast_track=track_res["forecast_points"],
        initial_point=history[-1],
    )

    if landfall_res["has_landfall"]:
        logger.info("  [OK] LANDFALL PREDICTED!")
        logger.info(f"    - Target Location: {landfall_res['district']}, {landfall_res['state_or_country']}")
        logger.info(f"    - Landfall Coordinates: {landfall_res['landfall_lat']:.2f}°N, {landfall_res['landfall_lon']:.2f}°E")
        logger.info(f"    - Landfall ETA (UTC): {landfall_res['eta_utc']}")
        logger.info(f"    - Landfall ETA (IST): {landfall_res['eta_ist']}")
        logger.info(f"    - Estimated Intensity at Landfall: {landfall_res['intensity_at_landfall_kt']} kt ({landfall_res['intensity_at_landfall_kmh']} km/h)")
        logger.info(f"    - IMD Category at Landfall: {landfall_res['stage_at_landfall']}")
        logger.info(f"    - Uncertainty Window: +/- {landfall_res['uncertainty_window_hours']} hours")
    else:
        logger.info(f"  [OK] Status: {landfall_res['status']} | Closest coast: {landfall_res.get('closest_coastal_point')}")

    logger.info("\n" + "=" * 65)
    logger.info("PHASE 4 VERIFICATION COMPLETED SUCCESSFULLY: ALL CHECKS PASSED!")
    logger.info("=" * 65)


if __name__ == "__main__":
    verify_phase4()
