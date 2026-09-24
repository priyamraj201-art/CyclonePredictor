"""Real-Time Oceanic & Atmospheric Ingestion Service.

Polls live meteorological data for the North Indian Ocean basins using
the free Open-Meteo API (no API key required). Supports:
  - Bay of Bengal (BoB): 5°N–22°N, 80°E–95°E
  - Arabian Sea (AS): 5°N–25°N, 60°E–75°E

Data fetched per grid point:
  - Sea Surface Temperature (°C)  — derived from 2m surface temperature proxy
  - 700 hPa Mid-Tropospheric Relative Humidity (%)
  - 10m Wind Speed (km/h → converted to knots)
  - 200 hPa & 850 hPa U/V wind components → Vertical Wind Shear (knots)
  - Surface Pressure (hPa)

API: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GridPointObservation:
    """Live atmospheric/oceanic observation at a single lat/lon grid point."""
    lat: float
    lon: float
    basin: str                          # "BAY_OF_BENGAL" | "ARABIAN_SEA"
    timestamp_utc: str                  # ISO 8601
    sea_surface_temp_c: float           # °C
    vertical_wind_shear_kt: float       # knots (200hPa minus 850hPa vector)
    relative_humidity_700hpa: float     # %
    surface_pressure_hpa: float         # hPa
    wind_speed_10m_kt: float            # knots
    fetch_ok: bool = True
    error: Optional[str] = None


@dataclass
class BasinLiveSnapshot:
    """Aggregated live snapshot across all grid points for a basin."""
    basin: str
    scan_time_utc: str
    num_points: int
    mean_sst_c: float
    mean_shear_kt: float
    mean_rh700: float
    mean_surface_pressure_hpa: float
    max_wind_speed_kt: float
    max_wind_lat: float
    max_wind_lon: float
    grid_observations: List[GridPointObservation] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Monitoring Grid Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Bay of Bengal: 5x4 = 20 grid points (every 4° lat, 5° lon)
BAY_OF_BENGAL_GRID: List[Tuple[float, float]] = [
    (lat, lon)
    for lat in [6.0, 10.0, 14.0, 18.0, 22.0]
    for lon in [82.0, 87.0, 92.0, 95.0]
]

# Arabian Sea: 4x4 = 16 grid points (every 4° lat, 4° lon)
ARABIAN_SEA_GRID: List[Tuple[float, float]] = [
    (lat, lon)
    for lat in [6.0, 10.0, 14.0, 18.0]
    for lon in [62.0, 66.0, 70.0, 74.0]
]

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"

# Hourly variables to request for wind shear calculation
HOURLY_VARS = [
    "windspeed_200hPa",
    "winddirection_200hPa",
    "windspeed_850hPa",
    "winddirection_850hPa",
    "relativehumidity_700hPa",
]

# Current-time variables (15-min interval)
CURRENT_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _wind_shear_kt(speed_hi: float, dir_hi: float,
                   speed_lo: float, dir_lo: float) -> float:
    """Compute vector wind shear (knots) between two pressure levels."""
    MS_TO_KT = 1.94384
    # Convert speed (km/h from Open-Meteo) to m/s first
    u_hi = speed_hi * math.cos(math.radians(dir_hi)) / 3.6
    v_hi = speed_hi * math.sin(math.radians(dir_hi)) / 3.6
    u_lo = speed_lo * math.cos(math.radians(dir_lo)) / 3.6
    v_lo = speed_lo * math.sin(math.radians(dir_lo)) / 3.6
    shear_ms = math.sqrt((u_hi - u_lo) ** 2 + (v_hi - v_lo) ** 2)
    return round(shear_ms * MS_TO_KT, 2)


def _kmh_to_kt(kmh: float) -> float:
    return round(kmh / 1.852, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Core Real-Time Ingestion Service
# ─────────────────────────────────────────────────────────────────────────────

class RealTimeAtmosphericService:
    """Fetches live atmospheric & oceanic data for NIO basin monitoring grids.

    Usage:
        service = RealTimeAtmosphericService()
        point = service.fetch_grid_point(lat=15.0, lon=88.0, basin="BAY_OF_BENGAL")
        snapshot = service.scan_basin("BAY_OF_BENGAL")
    """

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout = timeout_seconds
        self._client = httpx.Client(timeout=self.timeout)

    def fetch_grid_point(
        self,
        lat: float,
        lon: float,
        basin: str = "BAY_OF_BENGAL",
    ) -> GridPointObservation:
        """Fetch live atmospheric data for a single lat/lon grid point."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            resp = self._client.get(
                OPEN_METEO_BASE,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": ",".join(CURRENT_VARS),
                    "hourly": ",".join(HOURLY_VARS),
                    "forecast_days": 1,
                    "wind_speed_unit": "kmh",
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})
            hourly = data.get("hourly", {})

            # Use most-recent hourly values (last available index)
            def _last(key: str, default: float = 0.0) -> float:
                vals = hourly.get(key, [])
                vals = [v for v in vals if v is not None]
                return float(vals[-1]) if vals else default

            # Proxy SST from surface temperature (good enough for open-ocean)
            sst_c = round(float(current.get("temperature_2m", 29.0)), 2)

            # Vertical wind shear: 200hPa minus 850hPa vector difference
            shear_kt = _wind_shear_kt(
                speed_hi=_last("windspeed_200hPa", 15.0),
                dir_hi=_last("winddirection_200hPa", 90.0),
                speed_lo=_last("windspeed_850hPa", 20.0),
                dir_lo=_last("winddirection_850hPa", 120.0),
            )

            # 700 hPa RH — use surface RH as fallback if not available
            rh700 = _last("relativehumidity_700hPa", 0.0)
            if rh700 == 0.0:
                rh700 = float(current.get("relative_humidity_2m", 80.0))

            pressure_hpa = float(current.get("surface_pressure", 1010.0))
            wind_kmh = float(current.get("wind_speed_10m", 0.0))
            wind_kt = _kmh_to_kt(wind_kmh)

            return GridPointObservation(
                lat=lat,
                lon=lon,
                basin=basin,
                timestamp_utc=timestamp,
                sea_surface_temp_c=sst_c,
                vertical_wind_shear_kt=shear_kt,
                relative_humidity_700hpa=round(rh700, 1),
                surface_pressure_hpa=round(pressure_hpa, 1),
                wind_speed_10m_kt=wind_kt,
                fetch_ok=True,
            )

        except Exception as exc:
            return GridPointObservation(
                lat=lat,
                lon=lon,
                basin=basin,
                timestamp_utc=timestamp,
                sea_surface_temp_c=0.0,
                vertical_wind_shear_kt=0.0,
                relative_humidity_700hpa=0.0,
                surface_pressure_hpa=0.0,
                wind_speed_10m_kt=0.0,
                fetch_ok=False,
                error=str(exc),
            )

    def scan_basin(self, basin: str = "BAY_OF_BENGAL") -> BasinLiveSnapshot:
        """Scan all grid points in the specified basin and return aggregated snapshot.

        Args:
            basin: "BAY_OF_BENGAL" or "ARABIAN_SEA"

        Returns:
            BasinLiveSnapshot with aggregate statistics and individual observations.
        """
        grid = BAY_OF_BENGAL_GRID if basin == "BAY_OF_BENGAL" else ARABIAN_SEA_GRID
        observations: List[GridPointObservation] = []

        for lat, lon in grid:
            obs = self.fetch_grid_point(lat, lon, basin)
            observations.append(obs)

        # Filter to successful fetches for aggregation
        good = [o for o in observations if o.fetch_ok]
        n = len(good)
        scan_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if n == 0:
            # All failed — return sentinel snapshot
            return BasinLiveSnapshot(
                basin=basin,
                scan_time_utc=scan_time,
                num_points=0,
                mean_sst_c=0.0,
                mean_shear_kt=0.0,
                mean_rh700=0.0,
                mean_surface_pressure_hpa=0.0,
                max_wind_speed_kt=0.0,
                max_wind_lat=0.0,
                max_wind_lon=0.0,
                grid_observations=observations,
            )

        mean_sst = round(sum(o.sea_surface_temp_c for o in good) / n, 2)
        mean_shear = round(sum(o.vertical_wind_shear_kt for o in good) / n, 2)
        mean_rh = round(sum(o.relative_humidity_700hpa for o in good) / n, 1)
        mean_pres = round(sum(o.surface_pressure_hpa for o in good) / n, 1)

        # Find point with maximum near-surface wind (proxy for strongest circulation)
        max_obs = max(good, key=lambda o: o.wind_speed_10m_kt)

        return BasinLiveSnapshot(
            basin=basin,
            scan_time_utc=scan_time,
            num_points=n,
            mean_sst_c=mean_sst,
            mean_shear_kt=mean_shear,
            mean_rh700=mean_rh,
            mean_surface_pressure_hpa=mean_pres,
            max_wind_speed_kt=max_obs.wind_speed_10m_kt,
            max_wind_lat=max_obs.lat,
            max_wind_lon=max_obs.lon,
            grid_observations=observations,
        )

    def scan_all_basins(self) -> Dict[str, BasinLiveSnapshot]:
        """Scan both Bay of Bengal and Arabian Sea."""
        return {
            "BAY_OF_BENGAL": self.scan_basin("BAY_OF_BENGAL"),
            "ARABIAN_SEA": self.scan_basin("ARABIAN_SEA"),
        }

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
