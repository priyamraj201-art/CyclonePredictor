"""IMD Domain Constants and Physical Parameters.

Smart India Hackathon 2026 | Problem Statement ID: 26070
MoES / India Meteorological Department (IMD)
"""

from enum import Enum
from typing import Dict, Tuple

# Speed conversion constant
KNOTS_TO_KMH: float = 1.852

class CycloneStage(str, Enum):
    """Official IMD Tropical Cyclone Intensity Categories."""
    LPA = "Low Pressure Area"
    D = "Depression"
    DD = "Deep Depression"
    CS = "Cyclonic Storm"
    SCS = "Severe Cyclonic Storm"
    VSCS = "Very Severe Cyclonic Storm"
    ESCS = "Extremely Severe Cyclonic Storm"
    SuCS = "Super Cyclonic Storm"


class Basin(str, Enum):
    """North Indian Ocean Marine Basins."""
    BAY_OF_BENGAL = "Bay of Bengal"
    ARABIAN_SEA = "Arabian Sea"
    EQUATORIAL_IO = "Equatorial Indian Ocean"


# IMD Wind Speed Thresholds in Knots: (min_wind_kt, max_wind_kt)
# Note: max_wind_kt is inclusive for upper bound except SuCS which has no upper bound.
IMD_WIND_THRESHOLDS_KT: Dict[CycloneStage, Tuple[float, float]] = {
    CycloneStage.LPA: (0.0, 16.9),
    CycloneStage.D: (17.0, 27.9),
    CycloneStage.DD: (28.0, 33.9),
    CycloneStage.CS: (34.0, 47.9),
    CycloneStage.SCS: (48.0, 63.9),
    CycloneStage.VSCS: (64.0, 89.9),
    CycloneStage.ESCS: (90.0, 119.9),
    CycloneStage.SuCS: (120.0, 250.0),
}

# Rapid Intensification Threshold: >= 30 kt increase in 24 hours
RAPID_INTENSIFICATION_THRESHOLD_KT_24H: float = 30.0

# Geographic bounding boxes: (min_lat, max_lat, min_lon, max_lon)
BASIN_BOUNDS: Dict[Basin, Tuple[float, float, float, float]] = {
    Basin.BAY_OF_BENGAL: (5.0, 25.0, 80.0, 100.0),
    Basin.ARABIAN_SEA: (5.0, 25.0, 50.0, 77.5),
    Basin.EQUATORIAL_IO: (0.0, 10.0, 60.0, 95.0),
}

# Standard 4 Satellite Channels for INSAT-3D/3DR payloads
SATELLITE_CHANNELS = ["IR", "WV", "VIS", "PMW"]

CHANNEL_NORMALIZATION_RANGES: Dict[str, Tuple[float, float]] = {
    "IR": (180.0, 310.0),   # Brightness Temp in Kelvin (10.8 µm)
    "WV": (200.0, 270.0),   # Water Vapor Brightness Temp in Kelvin (6.7 µm)
    "VIS": (0.0, 1.0),      # Visible Albedo [0, 1] (0.65 µm)
    "PMW": (150.0, 300.0),  # Passive Microwave brightness temp proxy (89 GHz)
}

# Default Image Spatial Resolution
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (256, 256)
NUM_CHANNELS: int = 4

# Operational IMD Uncertainty Cone Radii (km)
UNCERTAINTY_CONE_RADII_KM: Dict[int, float] = {
    6: 30.0,
    12: 55.0,
    24: 100.0,
    48: 180.0,
    72: 270.0,
}
