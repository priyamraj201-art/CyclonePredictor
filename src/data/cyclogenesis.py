"""Real-Time Cyclogenesis Potential Index (GPI) & Low-Pressure Scanner.

Module: src/data/cyclogenesis.py

Computes the Emanuel-Nolan (2004) Genesis Potential Index (GPI) for the
North Indian Ocean basins using live atmospheric data from Open-Meteo.

GPI formula (Emanuel & Nolan, 2004):
    GPI = |10^5 * eta|^(3/2)  *  (H/50)^3  *  (Vpot/70)^3  *  (1 + 0.1*Vshear)^(-2)

Where:
    eta    = 850 hPa absolute vorticity (s^-1)
    H      = 700 hPa relative humidity (%)
    Vpot   = Maximum Potential Intensity (knots)  -- DeMaria & Kaplan 1994
    Vshear = 200-850 hPa vertical wind shear magnitude (knots)

Thermodynamic genesis thresholds (IMD/WMO operational):
    SST    >= 26.5 deg C
    Shear  <=  15 kt   -- low shear favors cyclogenesis
    RH700  >= 75 %     -- moist mid-troposphere

Threat levels:   GPI  0-0.05  -> NONE
                      0.05-0.5 -> LOW
                      0.5-2.0  -> MODERATE
                      2.0-5.0  -> HIGH
                      > 5.0    -> EXTREME
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from src.data.realtime_service import (
    BAY_OF_BENGAL_GRID,
    ARABIAN_SEA_GRID,
    OPEN_METEO_BASE,
    RealTimeAtmosphericService,
    GridPointObservation,
)


# ─────────────────────────────────────────────────────────────────────────────
# Physical / Operational Constants
# ─────────────────────────────────────────────────────────────────────────────

SST_THRESHOLD_C: float = 26.5      # Minimum SST for genesis (deg C)
SHEAR_THRESHOLD_KT: float = 15.0   # Max shear for favorable conditions (kt)
RH700_THRESHOLD_PCT: float = 75.0  # Min RH at 700 hPa for genesis (%)

OMEGA: float = 7.2921e-5           # Earth rotation rate (rad/s)
DEG_LAT_M: float = 111_320.0       # Metres per degree latitude
MS_TO_KT: float = 1.94384          # m/s -> knots conversion

# Empirical GPI->probability scale calibrated to NIO basin
GPI_PROB_SCALE: float = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GridPointGPI:
    """GPI analysis result at a single lat/lon grid point."""
    lat: float
    lon: float
    basin: str
    # Atmospheric state
    sst_c: float
    shear_kt: float
    rh700_pct: float
    pressure_hpa: float
    wind_speed_10m_kt: float
    # Vorticity components
    u850_ms: float
    v850_ms: float
    relative_vorticity_s1: float
    absolute_vorticity_s1: float
    # GPI components
    mpi_kt: float
    gpi_score: float
    genesis_probability: float
    # Threshold flags
    meets_sst_threshold: bool
    meets_shear_threshold: bool
    meets_rh_threshold: bool

    @property
    def cyclogenesis_favorable(self) -> bool:
        """True when all three thermodynamic thresholds are simultaneously met."""
        return (
            self.meets_sst_threshold
            and self.meets_shear_threshold
            and self.meets_rh_threshold
        )


@dataclass
class CyclogenesisThreat:
    """Primary cyclogenesis threat / candidate low-pressure vortex."""
    basin: str
    detected: bool                  # True if GPI > NONE threshold
    center_lat: float               # Latitude of max-GPI cell
    center_lon: float               # Longitude of max-GPI cell
    max_gpi: float
    genesis_probability: float      # [0.0, 1.0]
    threat_level: str               # NONE|LOW|MODERATE|HIGH|EXTREME
    favorable_point_count: int      # Grid points meeting all 3 thresholds
    timestamp_utc: str


@dataclass
class BasinCyclogenesisReport:
    """Full cyclogenesis analysis report for an ocean basin."""
    basin: str
    timestamp_utc: str
    grid_gpi_points: List[GridPointGPI] = field(default_factory=list)
    primary_threat: Optional[CyclogenesisThreat] = None
    basin_mean_gpi: float = 0.0
    basin_max_gpi: float = 0.0
    favorable_point_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Function Physics Helpers
# ─────────────────────────────────────────────────────────────────────────────

def coriolis_parameter(lat_deg: float) -> float:
    """Absolute Coriolis parameter  f = 2*Omega*sin(phi)  (s^-1)."""
    return 2.0 * OMEGA * math.sin(math.radians(lat_deg))


def mpi_knots(sst_c: float) -> float:
    """Maximum Potential Intensity (kt) via DeMaria & Kaplan (1994).

    MPI(m/s) = A + B * exp(C * (SST - T0)),  NIO-calibrated coefficients.
    Returns 0.0 when SST < 26.0 degC (below genesis warm-pool threshold).
    """
    if sst_c < 26.0:
        return 0.0
    A, B, C, T0 = 28.2, 55.8, 0.1813, 30.0
    mpi_ms = A + B * math.exp(C * (sst_c - T0))
    return round(max(0.0, mpi_ms) * MS_TO_KT, 3)


def genesis_potential_index(
    eta_abs: float,
    rh700: float,
    mpi_kt: float,
    shear_kt: float,
) -> float:
    """Compute Emanuel-Nolan (2004) Genesis Potential Index.

    GPI = |10^5 * eta|^(3/2)  *  (H/50)^3  *  (Vpot/70)^3  *  (1 + 0.1*Vshear)^(-2)
    """
    eta_term = abs(1e5 * eta_abs) ** 1.5
    rh_term = max(0.0, rh700 / 50.0) ** 3
    mpi_term = max(0.0, mpi_kt / 70.0) ** 3
    shear_term = (1.0 + 0.1 * max(0.0, shear_kt)) ** (-2)
    return round(eta_term * rh_term * mpi_term * shear_term, 8)


def genesis_probability(gpi: float) -> float:
    """Map GPI to genesis probability in [0.0, 1.0].

    P = 1 - exp(-scale * GPI),  scale calibrated for NIO basin.
    """
    return round(min(1.0, max(0.0, 1.0 - math.exp(-GPI_PROB_SCALE * gpi))), 4)


def threat_level(gpi: float) -> str:
    """Classify cyclogenesis threat level from GPI magnitude."""
    if gpi <= 0.05:
        return "NONE"
    elif gpi <= 0.5:
        return "LOW"
    elif gpi <= 2.0:
        return "MODERATE"
    elif gpi <= 5.0:
        return "HIGH"
    else:
        return "EXTREME"


def wind_to_uv(speed_kmh: float, direction_deg: float) -> Tuple[float, float]:
    """Convert meteorological wind (speed km/h, FROM direction) to u,v (m/s).

    u > 0 = eastward (westerly wind),  v > 0 = northward (southerly wind).
    """
    speed_ms = speed_kmh / 3.6
    rad = math.radians(direction_deg)
    u = -speed_ms * math.sin(rad)
    v = -speed_ms * math.cos(rad)
    return u, v


# ─────────────────────────────────────────────────────────────────────────────
# Core Cyclogenesis Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class CyclogenesisAnalyzer:
    """Real-Time Cyclogenesis Potential Index scanner for the NIO.

    Combines live atmospheric observations (from RealTimeAtmosphericService)
    with additional 850 hPa wind vector fetches to compute relative vorticity
    via finite differences, then evaluates the full Emanuel-Nolan GPI at every
    basin grid point.

    Usage:
        service  = RealTimeAtmosphericService()
        analyzer = CyclogenesisAnalyzer(service)
        report   = analyzer.analyze_basin("BAY_OF_BENGAL")
        print(report.primary_threat.threat_level)
        analyzer.close()
        service.close()
    """

    def __init__(
        self,
        service: RealTimeAtmosphericService,
        timeout: float = 15.0,
    ) -> None:
        self._service = service
        # Dedicated HTTP client, lifecycle independent of the service's client.
        self._client = httpx.Client(timeout=timeout)

    # ── Internal: 850 hPa u/v fetch ─────────────────────────────────────────

    def _fetch_850hpa_uv(self, lat: float, lon: float) -> Tuple[float, float]:
        """Fetch 850 hPa u,v wind components (m/s) for vorticity calculation.

        Gracefully returns (0.0, 0.0) on any network/parse failure so GPI
        degrades to Coriolis-only absolute vorticity.
        """
        try:
            resp = self._client.get(
                OPEN_METEO_BASE,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "windspeed_850hPa,winddirection_850hPa",
                    "forecast_days": 1,
                    "wind_speed_unit": "kmh",
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})

            def _last(key: str) -> Optional[float]:
                vals = [v for v in hourly.get(key, []) if v is not None]
                return float(vals[-1]) if vals else None

            speed = _last("windspeed_850hPa")
            dirn = _last("winddirection_850hPa")
            if speed is None or dirn is None:
                return 0.0, 0.0
            return wind_to_uv(speed, dirn)
        except Exception:
            return 0.0, 0.0

    # ── Internal: Finite-difference vorticity ───────────────────────────────

    @staticmethod
    def _relative_vorticity(
        grid: List[Tuple[float, float]],
        uv_map: Dict[Tuple[float, float], Tuple[float, float]],
    ) -> Dict[Tuple[float, float], float]:
        """Compute 850 hPa relative vorticity  zeta = dv/dx - du/dy  (s^-1).

        Uses second-order central differences for interior grid points and
        first-order one-sided differences at grid edges.
        """
        lats = sorted(set(p[0] for p in grid))
        lons = sorted(set(p[1] for p in grid))
        lat_idx = {v: i for i, v in enumerate(lats)}
        lon_idx = {v: j for j, v in enumerate(lons)}

        vort: Dict[Tuple[float, float], float] = {}

        for lat, lon in grid:
            i = lat_idx[lat]
            j = lon_idx[lon]

            # dv/dx -- east-west
            if len(lons) >= 2:
                if j == 0:
                    la, lb, c = lons[0], lons[1], 1.0
                elif j == len(lons) - 1:
                    la, lb, c = lons[-2], lons[-1], 1.0
                else:
                    la, lb, c = lons[j - 1], lons[j + 1], 0.5
                v_a = uv_map.get((lat, la), (0.0, 0.0))[1]
                v_b = uv_map.get((lat, lb), (0.0, 0.0))[1]
                dx = (lb - la) * DEG_LAT_M * math.cos(math.radians(lat))
                dv_dx = c * (v_b - v_a) / dx if dx != 0.0 else 0.0
            else:
                dv_dx = 0.0

            # du/dy -- north-south
            if len(lats) >= 2:
                if i == 0:
                    la, lb, c = lats[0], lats[1], 1.0
                elif i == len(lats) - 1:
                    la, lb, c = lats[-2], lats[-1], 1.0
                else:
                    la, lb, c = lats[i - 1], lats[i + 1], 0.5
                u_a = uv_map.get((la, lon), (0.0, 0.0))[0]
                u_b = uv_map.get((lb, lon), (0.0, 0.0))[0]
                dy = (lb - la) * DEG_LAT_M
                du_dy = c * (u_b - u_a) / dy if dy != 0.0 else 0.0
            else:
                du_dy = 0.0

            vort[(lat, lon)] = dv_dx - du_dy

        return vort

    # ── Public: Basin Analysis ───────────────────────────────────────────────

    def analyze_basin(self, basin: str = "BAY_OF_BENGAL") -> BasinCyclogenesisReport:
        """Run full cyclogenesis GPI analysis for the given basin.

        Workflow:
            1. Live atmospheric fetch (SST, Shear, RH700, Pressure, Wind)
            2. 850 hPa u,v fetch for numerical vorticity computation
            3. Relative vorticity via finite differences on basin grid
            4. GPI at every grid point (Emanuel-Nolan 2004)
            5. Primary threat identification (max-GPI cell = vortex candidate)

        Args:
            basin: "BAY_OF_BENGAL" or "ARABIAN_SEA"

        Returns:
            BasinCyclogenesisReport with per-point GPI and primary threat.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        grid = BAY_OF_BENGAL_GRID if basin == "BAY_OF_BENGAL" else ARABIAN_SEA_GRID

        # Step 1: Live atmospheric state
        snapshot = self._service.scan_basin(basin)
        obs_map: Dict[Tuple[float, float], GridPointObservation] = {
            (o.lat, o.lon): o for o in snapshot.grid_observations
        }

        # Step 2: 850 hPa u/v wind vectors for vorticity
        uv_map: Dict[Tuple[float, float], Tuple[float, float]] = {}
        for lat, lon in grid:
            uv_map[(lat, lon)] = self._fetch_850hpa_uv(lat, lon)

        # Step 3: Relative vorticity (finite differences)
        rel_vort_map = self._relative_vorticity(grid, uv_map)

        # Step 4: GPI at each grid point
        gpi_points: List[GridPointGPI] = []

        for lat, lon in grid:
            obs = obs_map.get((lat, lon))
            if obs is None or not obs.fetch_ok:
                continue

            u850, v850 = uv_map.get((lat, lon), (0.0, 0.0))
            rel_vort = rel_vort_map.get((lat, lon), 0.0)
            f = coriolis_parameter(lat)
            abs_vort = abs(f + rel_vort)

            mpi = mpi_knots(obs.sea_surface_temp_c)
            gpi = genesis_potential_index(
                eta_abs=abs_vort,
                rh700=obs.relative_humidity_700hpa,
                mpi_kt=mpi,
                shear_kt=obs.vertical_wind_shear_kt,
            )
            prob = genesis_probability(gpi)

            pt = GridPointGPI(
                lat=lat,
                lon=lon,
                basin=basin,
                sst_c=obs.sea_surface_temp_c,
                shear_kt=obs.vertical_wind_shear_kt,
                rh700_pct=obs.relative_humidity_700hpa,
                pressure_hpa=obs.surface_pressure_hpa,
                wind_speed_10m_kt=obs.wind_speed_10m_kt,
                u850_ms=round(u850, 4),
                v850_ms=round(v850, 4),
                relative_vorticity_s1=round(rel_vort, 9),
                absolute_vorticity_s1=round(abs_vort, 9),
                mpi_kt=mpi,
                gpi_score=gpi,
                genesis_probability=prob,
                meets_sst_threshold=obs.sea_surface_temp_c >= SST_THRESHOLD_C,
                meets_shear_threshold=obs.vertical_wind_shear_kt <= SHEAR_THRESHOLD_KT,
                meets_rh_threshold=obs.relative_humidity_700hpa >= RH700_THRESHOLD_PCT,
            )
            gpi_points.append(pt)

        # Step 5: Primary threat identification
        if not gpi_points:
            null_threat = CyclogenesisThreat(
                basin=basin, detected=False,
                center_lat=0.0, center_lon=0.0,
                max_gpi=0.0, genesis_probability=0.0,
                threat_level="NONE", favorable_point_count=0,
                timestamp_utc=timestamp,
            )
            return BasinCyclogenesisReport(
                basin=basin, timestamp_utc=timestamp,
                grid_gpi_points=[], primary_threat=null_threat,
            )

        best = max(gpi_points, key=lambda p: p.gpi_score)
        favorable = [p for p in gpi_points if p.cyclogenesis_favorable]
        mean_gpi = round(
            sum(p.gpi_score for p in gpi_points) / len(gpi_points), 8
        )

        primary = CyclogenesisThreat(
            basin=basin,
            detected=best.gpi_score > 0.05,
            center_lat=best.lat,
            center_lon=best.lon,
            max_gpi=best.gpi_score,
            genesis_probability=best.genesis_probability,
            threat_level=threat_level(best.gpi_score),
            favorable_point_count=len(favorable),
            timestamp_utc=timestamp,
        )

        return BasinCyclogenesisReport(
            basin=basin,
            timestamp_utc=timestamp,
            grid_gpi_points=gpi_points,
            primary_threat=primary,
            basin_mean_gpi=mean_gpi,
            basin_max_gpi=best.gpi_score,
            favorable_point_count=len(favorable),
        )

    def analyze_all_basins(self) -> Dict[str, BasinCyclogenesisReport]:
        """Analyze both Bay of Bengal and Arabian Sea."""
        return {
            "BAY_OF_BENGAL": self.analyze_basin("BAY_OF_BENGAL"),
            "ARABIAN_SEA":   self.analyze_basin("ARABIAN_SEA"),
        }

    def close(self) -> None:
        """Release the internal HTTP client."""
        self._client.close()

    def __enter__(self) -> "CyclogenesisAnalyzer":
        return self

    def __exit__(self, *_) -> None:
        self.close()
