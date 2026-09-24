"""Geospatial utilities for coordinate transformations and distance metrics.

Supports North Indian Ocean satellite projection, Haversine formula, and basin identification.
"""

import math
from typing import Tuple, Optional
from src.core.constants import Basin, BASIN_BOUNDS

EARTH_RADIUS_KM = 6371.0

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic points in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(EARTH_RADIUS_KM * c, 2)

def pixel_to_latlon(
    pixel_x: float,
    pixel_y: float,
    image_shape: Tuple[int, int],
    bbox: Tuple[float, float, float, float]
) -> Tuple[float, float]:
    """Convert image pixel coordinates (x, y) to geographic (latitude, longitude).
    
    Args:
        pixel_x: Column index [0, width)
        pixel_y: Row index [0, height)
        image_shape: (height, width)
        bbox: (min_lat, max_lat, min_lon, max_lon)
    Returns:
        (latitude, longitude)
    """
    height, width = image_shape
    min_lat, max_lat, min_lon, max_lon = bbox

    # Normalized coordinates [0, 1]
    norm_x = pixel_x / max(1.0, float(width - 1))
    norm_y = pixel_y / max(1.0, float(height - 1))

    # In satellite imagery, top row (y=0) corresponds to max_lat (North), bottom to min_lat (South)
    lat = max_lat - norm_y * (max_lat - min_lat)
    lon = min_lon + norm_x * (max_lon - min_lon)

    return round(lat, 4), round(lon, 4)

def latlon_to_pixel(
    lat: float,
    lon: float,
    image_shape: Tuple[int, int],
    bbox: Tuple[float, float, float, float]
) -> Tuple[float, float]:
    """Convert geographic (latitude, longitude) to normalized and discrete pixel coordinates.
    
    Returns:
        (pixel_x, pixel_y)
    """
    height, width = image_shape
    min_lat, max_lat, min_lon, max_lon = bbox

    norm_x = (lon - min_lon) / (max_lon - min_lon)
    norm_y = (max_lat - lat) / (max_lat - min_lat)

    pixel_x = norm_x * (width - 1)
    pixel_y = norm_y * (height - 1)

    return round(pixel_x, 2), round(pixel_y, 2)

def identify_basin(lat: float, lon: float) -> Basin:
    """Identify which ocean basin a coordinate belongs to."""
    if 50.0 <= lon <= 77.5 and 0.0 <= lat <= 30.0:
        return Basin.ARABIAN_SEA
    elif 77.5 < lon <= 100.0 and 0.0 <= lat <= 30.0:
        return Basin.BAY_OF_BENGAL
    return Basin.EQUATORIAL_IO
