"""Probability Uncertainty Cone & GeoJSON Generator.

Generates smooth expanding uncertainty cones matching official IMD/WMO 70% probability radii
(30 km at 6h, 55 km at 12h, 100 km at 24h, 180 km at 48h) for Leaflet / GIS rendering.
"""

from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.core.constants import UNCERTAINTY_CONE_RADII_KM
from src.core.schemas import BestTrackPoint

# Approximate 1 degree latitude = 111.0 km
KM_PER_DEG_LAT = 111.0


def km_to_deg(radius_km: float, lat: float) -> Tuple[float, float]:
    """Convert distance in km to degree increments (d_lat, d_lon)."""
    d_lat = radius_km / KM_PER_DEG_LAT
    # Longitude degrees shrink with cos(lat)
    cos_lat = max(0.2, math.cos(math.radians(lat)))
    d_lon = radius_km / (KM_PER_DEG_LAT * cos_lat)
    return d_lat, d_lon


class UncertaintyConeGenerator:
    """Calculates expanding probability cones and outputs standard GeoJSON."""

    def __init__(self, radii_km: Optional[Dict[int, float]] = None):
        self.radii_km = radii_km or UNCERTAINTY_CONE_RADII_KM

    def generate_cone_polygon(
        self,
        forecast_points: List[BestTrackPoint],
        initial_point: Optional[BestTrackPoint] = None,
        num_arc_points: int = 16,
    ) -> List[Tuple[float, float]]:
        """Generate a closed polygon boundary coordinates [(lon, lat), ...] wrapping the forecast track.
        
        GeoJSON standard requires (longitude, latitude) order and closed ring (first == last).
        """
        all_points = []
        if initial_point is not None:
            all_points.append((initial_point, 0.0))

        lead_hours = [6, 12, 24, 48]
        for i, pt in enumerate(forecast_points):
            h = lead_hours[i] if i < len(lead_hours) else 48
            radius = self.radii_km.get(h, 100.0)
            all_points.append((pt, radius))

        if len(all_points) < 2:
            raise ValueError("Need at least 2 track points to generate an uncertainty cone.")

        left_boundary = []
        right_boundary = []

        # Traverse track segments to compute normal vectors
        for i in range(len(all_points)):
            pt, r_km = all_points[i]
            lat, lon = pt.lat, pt.lon

            # Compute track direction heading angle
            if i < len(all_points) - 1:
                next_pt, _ = all_points[i + 1]
                dx = (next_pt.lon - lon) * math.cos(math.radians(lat))
                dy = next_pt.lat - lat
            else:
                prev_pt, _ = all_points[i - 1]
                dx = (lon - prev_pt.lon) * math.cos(math.radians(lat))
                dy = lat - prev_pt.lat

            heading = math.atan2(dy, dx)
            # Normal perpendicular angles: heading + pi/2 (left), heading - pi/2 (right)
            d_lat, d_lon = km_to_deg(r_km, lat)

            left_lat = lat + d_lat * math.sin(heading + math.pi / 2)
            left_lon = lon + d_lon * math.cos(heading + math.pi / 2)

            right_lat = lat + d_lat * math.sin(heading - math.pi / 2)
            right_lon = lon + d_lon * math.cos(heading - math.pi / 2)

            left_boundary.append((round(left_lon, 4), round(left_lat, 4)))
            right_boundary.append((round(right_lon, 4), round(right_lat, 4)))

        # Build rounded semicircular arc around final point
        last_pt, last_r = all_points[-1]
        last_dlat, last_dlon = km_to_deg(last_r, last_pt.lat)
        prev_pt, _ = all_points[-2]
        dx = (last_pt.lon - prev_pt.lon) * math.cos(math.radians(last_pt.lat))
        dy = last_pt.lat - prev_pt.lat
        final_heading = math.atan2(dy, dx)

        terminal_arc = []
        # Arc from heading + pi/2 to heading - pi/2
        angles = np.linspace(final_heading + math.pi / 2, final_heading - math.pi / 2, num_arc_points)
        for angle in angles:
            arc_lat = last_pt.lat + last_dlat * math.sin(angle)
            arc_lon = last_pt.lon + last_dlon * math.cos(angle)
            terminal_arc.append((round(arc_lon, 4), round(arc_lat, 4)))

        # Assemble full closed ring: Left boundary (forward) + terminal arc + Right boundary (backward) + close
        polygon_ring = left_boundary + terminal_arc + right_boundary[::-1]
        if polygon_ring[0] != polygon_ring[-1]:
            polygon_ring.append(polygon_ring[0])

        return polygon_ring

    def generate_geojson(
        self,
        forecast_points: List[BestTrackPoint],
        initial_point: Optional[BestTrackPoint] = None,
        storm_name: str = "TROPICAL CYCLONE",
    ) -> Dict[str, Any]:
        """Produce full GeoJSON FeatureCollection with uncertainty polygon, centerline, and waypoints."""
        polygon_coords = self.generate_cone_polygon(forecast_points, initial_point)

        # 1. Uncertainty Cone Polygon Feature
        cone_feature = {
            "type": "Feature",
            "properties": {
                "name": f"{storm_name} - 70% Probability Uncertainty Cone",
                "type": "uncertainty_cone",
                "stroke": "#d9381e",
                "stroke-width": 2,
                "fill": "#ff453a",
                "fill-opacity": 0.25,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords],
            },
        }

        # 2. Track Polyline Feature (LineString)
        all_pts = ([initial_point] if initial_point else []) + forecast_points
        line_coords = [[round(p.lon, 4), round(p.lat, 4)] for p in all_pts]

        track_feature = {
            "type": "Feature",
            "properties": {
                "name": f"{storm_name} - Forecast Track",
                "type": "forecast_track",
                "stroke": "#0a84ff",
                "stroke-width": 3.5,
                "stroke-opacity": 0.9,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": line_coords,
            },
        }

        # 3. Waypoint Points Features
        waypoint_features = []
        lead_hours = [0] + [6, 12, 24, 48] if initial_point else [6, 12, 24, 48]
        for i, pt in enumerate(all_pts):
            lead = lead_hours[i] if i < len(lead_hours) else 48
            wp = {
                "type": "Feature",
                "properties": {
                    "type": "track_waypoint",
                    "lead_hours": lead,
                    "lead_time_label": f"+{lead}h" if lead > 0 else "CURRENT",
                    "timestamp": pt.timestamp.isoformat(),
                    "lat": pt.lat,
                    "lon": pt.lon,
                    "wind_kt": pt.max_sustained_wind_kt,
                    "wind_kmh": pt.max_sustained_wind_kmh,
                    "imd_category": pt.imd_category.value if pt.imd_category else None,
                    "central_pressure_hpa": pt.central_pressure_hpa,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(pt.lon, 4), round(pt.lat, 4)],
                },
            }
            waypoint_features.append(wp)

        feature_collection = {
            "type": "FeatureCollection",
            "properties": {
                "storm_name": storm_name,
                "model": "Antigravity Bi-LSTM Track & Uncertainty Cone Engine",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "features": [cone_feature, track_feature] + waypoint_features,
        }

        return feature_collection
