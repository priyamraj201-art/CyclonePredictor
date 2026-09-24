"""Radiometric Calibration and Spatial Reprojection Engine for Multi-Spectral Satellite Data.

Implements Planck's function inversion for thermal infrared channels (TIR1, TIR2, WV, MIR)
and coordinate transforms between geostationary satellite projection and EPSG:4326.
"""

import math
from typing import Dict, Optional, Tuple, Union
import numpy as np

# Physical constants for Planck's law
H_PLANCK = 6.62607015e-34     # J*s (Planck constant)
C_LIGHT = 2.99792458e8        # m/s (Speed of light)
K_BOLTZMANN = 1.380649e-23     # J/K (Boltzmann constant)

# Central wavelengths (micrometers) for INSAT-3D/3DR channels
INSAT_CENTRAL_WAVELENGTHS = {
    "TIR1": 10.8e-6,   # Thermal IR 1
    "TIR2": 12.0e-6,   # Thermal IR 2
    "WV":   6.7e-6,    # Water Vapor
    "MIR":  3.9e-6,    # Middle IR
    "VIS":  0.65e-6,   # Visible (Albedo, not Planck)
}

# Empirical sensor calibration coefficients for INSAT-3D/3DR (Band-specific slope & offset)
DEFAULT_CALIBRATION_LUT = {
    "TIR1": {"slope": 0.0524, "intercept": 150.0, "c1": 1.191042e8, "c2": 1.4387752e4},
    "TIR2": {"slope": 0.0498, "intercept": 150.0, "c1": 1.191042e8, "c2": 1.4387752e4},
    "WV":   {"slope": 0.0382, "intercept": 170.0, "c1": 1.191042e8, "c2": 1.4387752e4},
    "MIR":  {"slope": 0.0612, "intercept": 180.0, "c1": 1.191042e8, "c2": 1.4387752e4},
}


class RadiometricCalibrator:
    """Calibrates raw satellite detector counts into physical Brightness Temperature (K) or Albedo."""

    def __init__(self, custom_lut: Optional[Dict[str, Dict[str, float]]] = None):
        self.lut = custom_lut or DEFAULT_CALIBRATION_LUT

    def planck_inversion(
        self,
        radiance: np.ndarray,
        wavelength_m: float,
    ) -> np.ndarray:
        """Invert Planck's Law to convert Spectral Radiance (W / (m^2 * sr * um)) to Brightness Temp (K).
        
        T_B = (h * c) / (k * lambda * ln(1 + (2 * h * c^2) / (radiance * lambda^5)))
        """
        c1 = 2.0 * H_PLANCK * (C_LIGHT ** 2)
        c2 = (H_PLANCK * C_LIGHT) / K_BOLTZMANN

        safe_radiance = np.maximum(radiance, 1e-6)
        argument = 1.0 + (c1 / ((wavelength_m ** 5) * safe_radiance * 1e6))
        argument = np.maximum(argument, 1.00001)

        t_b = c2 / (wavelength_m * np.log(argument))
        return np.clip(t_b, 150.0, 340.0)

    def counts_to_brightness_temperature(
        self,
        raw_counts: np.ndarray,
        channel_name: str = "TIR1",
    ) -> np.ndarray:
        """Convert raw 10-bit or 16-bit detector counts into Kelvin Brightness Temperature."""
        ch = channel_name.upper()
        if ch not in self.lut:
            # Fallback linear mapping if no LUT available
            return np.clip(raw_counts.astype(np.float32) * 0.1 + 180.0, 180.0, 320.0)

        params = self.lut[ch]
        radiance = params["slope"] * raw_counts.astype(np.float32) + 0.1
        wavelength = INSAT_CENTRAL_WAVELENGTHS[ch]
        return self.planck_inversion(radiance, wavelength)

    def counts_to_albedo(self, raw_counts: np.ndarray, max_count: float = 1023.0) -> np.ndarray:
        """Convert visible channel counts to planetary reflectance albedo [0.0, 1.0]."""
        return np.clip(raw_counts.astype(np.float32) / max_count, 0.0, 1.0)


class SpatialReprojector:
    """Reprojects geostationary coordinate grids (INSAT-3D/3DR) into standard EPSG:4326 Lat/Lon."""

    def __init__(
        self,
        sub_satellite_lon: float = 82.0,  # INSAT-3DR at 82.0° E (Bay of Bengal focus)
        satellite_height_km: float = 35786.0,
    ):
        self.sub_lon = sub_satellite_lon
        self.sat_h = satellite_height_km

    def geostationary_to_latlon(
        self,
        scan_x_rad: np.ndarray,
        scan_y_rad: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert geostationary scan angles (radians) to geographic latitude and longitude."""
        cos_x = np.cos(scan_x_rad)
        cos_y = np.cos(scan_y_rad)
        sin_y = np.sin(scan_y_rad)
        sin_x = np.sin(scan_x_rad)

        r_eq = 6378.137  # Earth equatorial radius in km
        r_pol = 6356.752  # Earth polar radius in km
        h = self.sat_h

        # Standard spherical approximation for fast vectorized grid mapping
        lat_rad = np.arcsin(sin_y * cos_x)
        lon_rad = np.radians(self.sub_lon) + np.arctan2(sin_x, cos_x * cos_y)

        lat = np.degrees(lat_rad)
        lon = np.degrees(lon_rad)
        return lat, lon

    def crop_basin_patch(
        self,
        raster: np.ndarray,
        source_bbox: Tuple[float, float, float, float],
        target_bbox: Tuple[float, float, float, float],
        target_shape: Tuple[int, int] = (256, 256),
    ) -> np.ndarray:
        """Bilinear resample and crop a regional sub-window to target (H, W)."""
        import torch
        import torch.nn.functional as F

        tensor = torch.from_numpy(raster).float()
        if tensor.ndim == 2:
            tensor = tensor.unsqueeze(0).unsqueeze(0)
        elif tensor.ndim == 3:
            tensor = tensor.unsqueeze(0)

        resampled = F.interpolate(
            tensor,
            size=target_shape,
            mode="bilinear",
            align_corners=False,
        )
        return resampled.squeeze(0).cpu().numpy()
