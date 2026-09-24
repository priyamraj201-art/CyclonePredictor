"""Landfall Prediction & Coastal Intersection Engine.

Determines if and where a forecast cyclone track crosses North Indian Ocean coastlines,
identifying the impacted district, state/country, ETA (UTC & IST), and intensity at landfall.
"""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.core.schemas import BestTrackPoint
from src.utils.conversions import knots_to_stage, knots_to_kmh
from src.utils.geospatial import haversine_distance_km

# Representative coastal anchor points for Indian and neighboring NIO coasts:
# [(lat, lon, district, state_or_country)]
COASTAL_ANCHORS: List[Tuple[float, float, str, str]] = [
    # West Bengal
    (21.60, 88.20, "South 24 Parganas (Sunderbans)", "West Bengal"),
    (21.65, 87.55, "Digha / East Medinipur", "West Bengal"),
    # Odisha
    (21.50, 87.05, "Balasore", "Odisha"),
    (20.90, 86.90, "Bhadrak / Dhamra", "Odisha"),
    (20.50, 86.75, "Kendrapara", "Odisha"),
    (20.25, 86.65, "Jagatsinghpur / Paradip", "Odisha"),
    (19.80, 85.80, "Puri", "Odisha"),
    (19.30, 85.05, "Ganjam / Gopalpur", "Odisha"),
    # Andhra Pradesh
    (18.30, 83.90, "Srikakulam", "Andhra Pradesh"),
    (17.70, 83.30, "Visakhapatnam", "Andhra Pradesh"),
    (16.95, 82.25, "Kakinada / East Godavari", "Andhra Pradesh"),
    (16.15, 81.15, "Machilipatnam / Krishna", "Andhra Pradesh"),
    (15.50, 80.05, "Ongole / Prakasam", "Andhra Pradesh"),
    (14.45, 80.00, "Nellore", "Andhra Pradesh"),
    # Tamil Nadu
    (13.10, 80.30, "Chennai", "Tamil Nadu"),
    (11.75, 79.75, "Cuddalore", "Tamil Nadu"),
    (10.75, 79.85, "Nagapattinam", "Tamil Nadu"),
    # Gujarat
    (23.25, 68.60, "Kachchh (Mandvi/Koteshwar)", "Gujarat"),
    (22.25, 68.95, "Devbhumi Dwarka", "Gujarat"),
    (21.60, 69.60, "Porbandar", "Gujarat"),
    (20.90, 70.40, "Veraval / Gir Somnath", "Gujarat"),
    (21.15, 72.80, "Surat", "Gujarat"),
    # Maharashtra
    (19.70, 72.75, "Palghar", "Maharashtra"),
    (18.95, 72.80, "Mumbai", "Maharashtra"),
    (18.30, 72.95, "Raigad (Alibaug)", "Maharashtra"),
    (16.98, 73.30, "Ratnagiri", "Maharashtra"),
    # Bangladesh
    (22.20, 89.60, "Khulna / Mongla", "Bangladesh"),
    (22.30, 91.80, "Chittagong", "Bangladesh"),
    # Myanmar
    (20.15, 92.90, "Sittwe / Rakhine", "Myanmar"),
]


def line_segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> Optional[Tuple[float, float, float]]:
    """Determine if line segment p1-p2 intersects segment p3-p4.
    
    Coordinates are (lon, lat).
    Returns (intersection_lon, intersection_lat, t_fraction) if intersecting, else None.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-9:
        return None  # Parallel

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

    if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
        ix = x1 + ua * (x2 - x1)
        iy = y1 + ua * (y2 - y1)
        return ix, iy, ua
    return None


class LandfallPredictor:
    """Detects track intersection with coastal boundaries and calculates Landfall ETA & Impact."""

    def __init__(self, coastal_anchors: Optional[List[Tuple[float, float, str, str]]] = None):
        self.anchors = coastal_anchors or COASTAL_ANCHORS

    def find_nearest_coastal_district(self, lat: float, lon: float) -> Tuple[str, str, float]:
        """Find closest coastal station/district to a geographic point."""
        best_dist = float("inf")
        best_district = "Coastal North Indian Ocean"
        best_state = "India"

        for c_lat, c_lon, district, state in self.anchors:
            d = haversine_distance_km(lat, lon, c_lat, c_lon)
            if d < best_dist:
                best_dist = d
                best_district = district
                best_state = state

        return best_district, best_state, best_dist

    def predict_landfall(
        self,
        forecast_track: List[BestTrackPoint],
        initial_point: Optional[BestTrackPoint] = None,
        landfall_proximity_threshold_km: float = 35.0,
    ) -> Dict[str, Any]:
        """Check for coastal intersection along forecast trajectory.
        
        Args:
            forecast_track: List of forward BestTrackPoints (+6h, +12h, +24h, +48h)
            initial_point: Current observation point (+0h)
            landfall_proximity_threshold_km: Buffer threshold for coastal crossing
        Returns:
            Structured Landfall Diagnostic Dictionary
        """
        all_pts = ([initial_point] if initial_point else []) + forecast_track
        if len(all_pts) < 2:
            return {"has_landfall": False, "reason": "Insufficient forecast points."}

        # Check line segment intersections with segments formed by adjacent coastal anchors
        detected_intersections = []

        for i in range(len(all_pts) - 1):
            pt_a = all_pts[i]
            pt_b = all_pts[i + 1]

            track_p1 = (pt_a.lon, pt_a.lat)
            track_p2 = (pt_b.lon, pt_b.lat)

            # Check against coastal line segments
            for c_idx in range(len(self.anchors) - 1):
                c_lat1, c_lon1, dist1, state1 = self.anchors[c_idx]
                c_lat2, c_lon2, dist2, state2 = self.anchors[c_idx + 1]

                # Only test adjacent anchors within reasonable distance (< 250 km)
                if haversine_distance_km(c_lat1, c_lon1, c_lat2, c_lon2) > 250.0:
                    continue

                coast_p1 = (c_lon1, c_lat1)
                coast_p2 = (c_lon2, c_lat2)

                res = line_segments_intersect(track_p1, track_p2, coast_p1, coast_p2)
                if res is not None:
                    ix_lon, ix_lat, t_frac = res
                    # Interpolate time and intensity
                    delta_seconds = (pt_b.timestamp - pt_a.timestamp).total_seconds()
                    eta_utc = pt_a.timestamp + timedelta(seconds=delta_seconds * t_frac)
                    eta_ist = eta_utc + timedelta(hours=5, minutes=30)

                    wind_interp = pt_a.max_sustained_wind_kt + t_frac * (
                        pt_b.max_sustained_wind_kt - pt_a.max_sustained_wind_kt
                    )
                    wind_interp = round(float(wind_interp), 1)

                    nearest_dist, nearest_state, dist_km = self.find_nearest_coastal_district(ix_lat, ix_lon)

                    detected_intersections.append({
                        "landfall_lat": round(ix_lat, 4),
                        "landfall_lon": round(ix_lon, 4),
                        "eta_utc": eta_utc.strftime("%Y-%m-%d %H:%M UTC"),
                        "eta_ist": eta_ist.strftime("%Y-%m-%d %H:%M IST"),
                        "district": nearest_dist,
                        "state_or_country": nearest_state,
                        "intensity_at_landfall_kt": wind_interp,
                        "intensity_at_landfall_kmh": round(wind_interp * 1.852, 1),
                        "stage_at_landfall": knots_to_stage(wind_interp).value,
                        "uncertainty_window_hours": 4.5,
                    })

        if detected_intersections:
            first_landfall = detected_intersections[0]
            first_landfall["has_landfall"] = True
            first_landfall["status"] = "LANDFALL_PREDICTED"
            return first_landfall

        # Fallback: Check if any waypoint passes within proximity threshold of coast
        for pt in all_pts:
            district, state, dist_km = self.find_nearest_coastal_district(pt.lat, pt.lon)
            if dist_km <= landfall_proximity_threshold_km:
                eta_ist = pt.timestamp + timedelta(hours=5, minutes=30)
                return {
                    "has_landfall": True,
                    "status": "COASTAL_CROSSING_PROXIMITY",
                    "landfall_lat": pt.lat,
                    "landfall_lon": pt.lon,
                    "eta_utc": pt.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                    "eta_ist": eta_ist.strftime("%Y-%m-%d %H:%M IST"),
                    "district": district,
                    "state_or_country": state,
                    "intensity_at_landfall_kt": pt.max_sustained_wind_kt,
                    "intensity_at_landfall_kmh": round(pt.max_sustained_wind_kt * 1.852, 1),
                    "stage_at_landfall": pt.imd_category.value if pt.imd_category else knots_to_stage(pt.max_sustained_wind_kt).value,
                    "uncertainty_window_hours": 6.0,
                }

        # No landfall predicted
        closest_dist, closest_state, min_dist = self.find_nearest_coastal_district(
            all_pts[-1].lat, all_pts[-1].lon
        )
        return {
            "has_landfall": False,
            "status": "NO_LANDFALL_DETECTED",
            "closest_coastal_point": f"{closest_dist}, {closest_state}",
            "closest_distance_km": round(min_dist, 1),
            "reason": "Forecast trajectory remains over open ocean waters throughout the 48-hour forecast window.",
        }
