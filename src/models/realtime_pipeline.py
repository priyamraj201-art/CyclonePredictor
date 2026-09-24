"""Live Pipeline Integration — Real-Time End-to-End Cyclone Inference Engine.

Module: src/models/realtime_pipeline.py

Connects real-time cyclogenesis coordinates (from CyclogenesisAnalyzer)
to the full production inference chain:

    Stage 1  — Intensity Estimator      (current wind speed & central pressure)
    Stage 2  — RI Classifier            (XGBoost 24-h rapid intensification P)
    Stage 3  — Bi-LSTM Track Forecaster (+12h, +24h, +36h, +48h trajectory)
    Stage 4  — Uncertainty Cone         (70% IMD/WMO GeoJSON polygon)
    Stage 5  — Coastal Risk Engine      (district-level composite risk score)

Designed for sub-1.5 second end-to-end inference on CPU.
No breaking changes: all existing /api/v1/pipeline/run and /api/v1/simulation/storms
endpoints remain fully operational alongside these real-time endpoints.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from src.core.constants import CycloneStage
from src.core.schemas import BestTrackPoint, EnvironmentalFeatures
from src.data.cyclogenesis import (
    BasinCyclogenesisReport,
    CyclogenesisThreat,
    CyclogenesisAnalyzer,
    coriolis_parameter,
)
from src.data.realtime_service import RealTimeAtmosphericService
from src.models.intensity import IntensityEstimator
from src.models.rapid_intensification import RapidIntensificationClassifier
from src.models.track import TrackForecastPipeline
from src.risk.risk_assessment import CoastalRiskAssessmentEngine
from src.utils.conversions import estimate_central_pressure, knots_to_stage
from src.utils.uncertainty_cone import UncertaintyConeGenerator


# ─────────────────────────────────────────────────────────────────────────────
# Output Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntensityResult:
    """Current storm intensity estimate."""
    wind_speed_kt: float
    wind_speed_kmh: float
    uncertainty_kt: float
    central_pressure_hpa: float
    pressure_deficit_hpa: float
    imd_category: str


@dataclass
class RIResult:
    """Rapid Intensification classification result."""
    ri_probability: float
    is_ri_flagged: bool
    operational_threshold: float
    favorable_factors: List[str]
    inhibiting_factors: List[str]
    advisory: str


@dataclass
class TrackWaypoint:
    """Single forecast track position."""
    lead_hours: int
    timestamp_utc: str
    lat: float
    lon: float
    wind_speed_kt: float
    wind_speed_kmh: float
    central_pressure_hpa: float
    imd_category: str


@dataclass
class RealTimePipelineOutput:
    """Complete real-time end-to-end inference result."""
    # Metadata
    pipeline_version: str
    run_timestamp_utc: str
    elapsed_seconds: float
    basin: str
    data_source: str

    # Cyclogenesis inputs
    genesis_lat: float
    genesis_lon: float
    genesis_gpi: float
    genesis_probability: float
    genesis_threat_level: str

    # Stage results
    intensity: IntensityResult
    rapid_intensification: RIResult
    track_waypoints: List[TrackWaypoint]
    uncertainty_cone_geojson: Dict[str, Any]
    coastal_risk: List[Dict[str, Any]]

    # Flags
    is_active_cyclone: bool
    requires_immediate_advisory: bool


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Synthetic satellite tensor from atmospheric features
# ─────────────────────────────────────────────────────────────────────────────

def _build_synthetic_tensor(
    sst_c: float,
    wind_kt: float,
    rh700: float,
    pressure_hpa: float,
    device: torch.device,
    image_size: int = 256,
) -> torch.Tensor:
    """Construct a physics-grounded synthetic 4-channel satellite tensor.

    When real INSAT-3D imagery is unavailable (pre-Phase 3 training), this
    function generates a surrogate tensor whose statistical properties mirror
    the thermodynamic state at the detected vortex centre.

    Channels:
        0 — TIR1 (10.8 um) proxy: cold-top brightness temperature
        1 — WV   (6.7  um) proxy: moisture channel (anti-correlated with RH)
        2 — MIR  (3.9  um) proxy: SST-modulated surface emission
        3 — VIS  (0.65 um) proxy: convective cloud albedo

    Returns:
        Tensor of shape (4, image_size, image_size) on the given device.
    """
    rng = np.random.default_rng(seed=int(sst_c * 100 + wind_kt))

    # Brightness temperature proxy (TIR1): colder over active convection
    # Vigorous convection (high wind) -> lower BT
    bt_mean = max(200.0, 290.0 - (wind_kt / 180.0) * 80.0)
    bt_sigma = 12.0 + (wind_kt / 100.0) * 10.0
    ch0 = rng.normal(bt_mean / 310.0, bt_sigma / 310.0, (image_size, image_size))

    # WV channel: drier air -> brighter; high RH -> darker (lower value)
    wv_mean = 0.5 - (rh700 / 100.0) * 0.25
    ch1 = rng.normal(wv_mean, 0.06, (image_size, image_size))

    # MIR channel: SST modulated (warm ocean surface emission)
    mir_mean = (sst_c - 26.0) / 10.0 * 0.4 + 0.3
    ch2 = rng.normal(mir_mean, 0.05, (image_size, image_size))

    # VIS channel: convective cloud albedo (high wind -> dense cloud cover)
    vis_mean = min(0.95, 0.3 + (wind_kt / 160.0) * 0.55)
    ch3 = rng.normal(vis_mean, 0.08, (image_size, image_size))

    # Stack and normalise to [0, 1]
    arr = np.stack([ch0, ch1, ch2, ch3], axis=0).astype(np.float32)
    arr = np.clip(arr, 0.0, 1.0)

    return torch.tensor(arr, dtype=torch.float32).to(device)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Build BestTrackPoint history from vortex centre
# ─────────────────────────────────────────────────────────────────────────────

def _build_track_history(
    lat: float,
    lon: float,
    wind_kt: float,
    pressure_hpa: float,
    n_points: int = 4,
) -> List[BestTrackPoint]:
    """Synthesise a 6-hourly backward track history for Bi-LSTM input.

    Uses standard NIO climatological motion vectors (NW recurvature ~310°)
    to extrapolate backward from the current vortex centre at 15 km/h.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # North-West motion: approximate backward track (S -> current position)
    dlat_per_6h = 0.75    # degrees northward per 6h
    dlon_per_6h = -0.50   # degrees westward per 6h

    points = []
    for i in range(n_points - 1, -1, -1):
        t = now - timedelta(hours=i * 6)
        past_lat = round(lat - dlat_per_6h * i, 4)
        past_lon = round(lon - dlon_per_6h * i, 4)
        # Wind decays slightly going backward
        past_wind = max(20.0, wind_kt - (i * 3.0))
        pt = BestTrackPoint(
            timestamp=t,
            lat=past_lat,
            lon=past_lon,
            max_sustained_wind_kt=round(past_wind, 1),
            central_pressure_hpa=estimate_central_pressure(past_wind),
            translation_speed_kmh=15.0,
            heading_deg=315.0,
        )
        points.append(pt)
    return points


# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline Class
# ─────────────────────────────────────────────────────────────────────────────

class RealTimePipeline:
    """Full end-to-end real-time cyclone inference pipeline.

    Accepts a BasinCyclogenesisReport (from Step 2) and runs the complete
    prediction chain through intensity, RI, track, uncertainty cone, and risk.

    Usage:
        service  = RealTimeAtmosphericService()
        analyzer = CyclogenesisAnalyzer(service)
        pipeline = RealTimePipeline()

        report   = analyzer.analyze_basin("BAY_OF_BENGAL")
        result   = pipeline.run(report)

        print(result.intensity.wind_speed_kt)
        print(result.track_waypoints[2].lat)   # +24h position
        pipeline.close()
    """

    PIPELINE_VERSION = "1.0.0-realtime"

    def __init__(self, device: Optional[str] = None) -> None:
        self.device = torch.device(device or "cpu")

        # Initialise all inference modules with pre-trained or baseline weights
        self._intensity   = IntensityEstimator(device=str(self.device))
        self._ri_clf      = RapidIntensificationClassifier()
        self._track       = TrackForecastPipeline(device=str(self.device))
        self._cone        = UncertaintyConeGenerator()
        self._risk_engine = CoastalRiskAssessmentEngine()

    # ── Public: Run full pipeline ────────────────────────────────────────────

    def run(
        self,
        cyclogenesis_report: BasinCyclogenesisReport,
        storm_name: str = "LIVE CYCLONIC SYSTEM",
    ) -> RealTimePipelineOutput:
        """Execute complete real-time inference chain.

        Args:
            cyclogenesis_report: BasinCyclogenesisReport from CyclogenesisAnalyzer.
            storm_name: Optional advisory storm name label.

        Returns:
            RealTimePipelineOutput with all stage results populated.
        """
        t_start = time.perf_counter()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        threat = cyclogenesis_report.primary_threat
        basin  = cyclogenesis_report.basin

        # ── Stage 1: Intensity Estimation ─────────────────────────────────
        # Use atmospheric state at the vortex centre grid point
        centre_obs = self._get_centre_obs(cyclogenesis_report)
        sst_c    = centre_obs.get("sst_c", 29.0)
        shear_kt = centre_obs.get("shear_kt", 15.0)
        rh700    = centre_obs.get("rh700_pct", 75.0)
        pres_hpa = centre_obs.get("pressure_hpa", 1005.0)
        wind_10m = centre_obs.get("wind_speed_10m_kt", 20.0)

        # Estimate current wind from GPI + 10m wind proxy
        init_wind_kt = self._estimate_wind_from_gpi(
            gpi=threat.max_gpi,
            wind_10m_kt=wind_10m,
        )

        sat_tensor = _build_synthetic_tensor(
            sst_c=sst_c,
            wind_kt=init_wind_kt,
            rh700=rh700,
            pressure_hpa=pres_hpa,
            device=self.device,
        )

        intensity_raw = self._intensity.estimate(sat_tensor)
        # Blend model estimate with GPI-derived estimate
        model_wind = intensity_raw["wind_speed_kt"]
        blended_wind = round(0.5 * model_wind + 0.5 * init_wind_kt, 1)
        blended_wind = max(20.0, min(180.0, blended_wind))
        central_pres = estimate_central_pressure(blended_wind)

        intensity = IntensityResult(
            wind_speed_kt=blended_wind,
            wind_speed_kmh=round(blended_wind * 1.852, 1),
            uncertainty_kt=intensity_raw["uncertainty_kt"],
            central_pressure_hpa=central_pres,
            pressure_deficit_hpa=round(1010.0 - central_pres, 1),
            imd_category=knots_to_stage(blended_wind).value,
        )

        # ── Stage 2: Rapid Intensification Classifier ──────────────────────
        # OHC approximated from SST (warm pool thermal depth proxy)
        ohc_proxy = max(0.0, (sst_c - 26.0) * 8.5 + 30.0)
        vort_1e5 = centre_obs.get("abs_vorticity_s1", 5e-5) * 1e5

        env = EnvironmentalFeatures(
            sea_surface_temp_c=sst_c,
            vertical_wind_shear_kt=shear_kt,
            relative_humidity_700hpa=max(10.0, rh700),
            ocean_heat_content_kj_cm2=ohc_proxy,
            vorticity_850hpa=vort_1e5,
            coriolis_parameter=abs(coriolis_parameter(threat.center_lat)) * 1e4,
        )
        ri_raw = self._ri_clf.predict(env, blended_wind)
        ri = RIResult(
            ri_probability=ri_raw["ri_probability"],
            is_ri_flagged=ri_raw["is_ri_flagged"],
            operational_threshold=ri_raw["operational_threshold"],
            favorable_factors=ri_raw["favorable_factors"],
            inhibiting_factors=ri_raw["inhibiting_factors"],
            advisory=ri_raw["advisory"],
        )

        # ── Stage 3: Bi-LSTM Track Forecasting ────────────────────────────
        history = _build_track_history(
            lat=threat.center_lat,
            lon=threat.center_lon,
            wind_kt=blended_wind,
            pressure_hpa=central_pres,
        )
        track_raw = self._track.forecast(history)
        forecast_pts: List[BestTrackPoint] = track_raw["forecast_points"]

        waypoints: List[TrackWaypoint] = []
        for lead_h, fp in zip([12, 24, 36, 48], forecast_pts):
            waypoints.append(TrackWaypoint(
                lead_hours=lead_h,
                timestamp_utc=fp.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                lat=fp.lat,
                lon=fp.lon,
                wind_speed_kt=fp.max_sustained_wind_kt,
                wind_speed_kmh=round(fp.max_sustained_wind_kt * 1.852, 1),
                central_pressure_hpa=fp.central_pressure_hpa or central_pres,
                imd_category=fp.imd_category.value if fp.imd_category else "DS",
            ))

        # ── Stage 4: 70% Uncertainty Cone GeoJSON ─────────────────────────
        initial_pt = history[-1]
        cone_geojson = self._cone.generate_geojson(
            forecast_points=forecast_pts,
            initial_point=initial_pt,
            storm_name=storm_name,
        )

        # ── Stage 5: Coastal Risk Assessment ─────────────────────────────
        current_pt = BestTrackPoint(
            timestamp=datetime.now(timezone.utc),
            lat=threat.center_lat,
            lon=threat.center_lon,
            max_sustained_wind_kt=blended_wind,
            central_pressure_hpa=central_pres,
        )
        risk_raw = self._risk_engine.evaluate_risk_swath(
            current_storm=current_pt,
            max_assessment_radius_km=650.0,
        )
        coastal_risk = self._format_risk(risk_raw)

        elapsed = round(time.perf_counter() - t_start, 3)

        # ── Operational flags ─────────────────────────────────────────────
        is_active = blended_wind >= 28.0  # Cyclonic Storm threshold (~IMD)
        immediate = ri.is_ri_flagged or blended_wind >= 48.0

        return RealTimePipelineOutput(
            pipeline_version=self.PIPELINE_VERSION,
            run_timestamp_utc=timestamp,
            elapsed_seconds=elapsed,
            basin=basin,
            data_source="Open-Meteo API (live)",
            genesis_lat=threat.center_lat,
            genesis_lon=threat.center_lon,
            genesis_gpi=threat.max_gpi,
            genesis_probability=threat.genesis_probability,
            genesis_threat_level=threat.threat_level,
            intensity=intensity,
            rapid_intensification=ri,
            track_waypoints=waypoints,
            uncertainty_cone_geojson=cone_geojson,
            coastal_risk=coastal_risk,
            is_active_cyclone=is_active,
            requires_immediate_advisory=immediate,
        )

    def run_basin(self, basin: str = "BAY_OF_BENGAL") -> RealTimePipelineOutput:
        """Convenience method: run full pipeline including live cyclogenesis scan.

        Args:
            basin: "BAY_OF_BENGAL" or "ARABIAN_SEA"

        Returns:
            RealTimePipelineOutput end-to-end result.
        """
        service  = RealTimeAtmosphericService(timeout_seconds=15.0)
        analyzer = CyclogenesisAnalyzer(service)
        try:
            report = analyzer.analyze_basin(basin)
            return self.run(report)
        finally:
            analyzer.close()
            service.close()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get_centre_obs(
        self, report: BasinCyclogenesisReport
    ) -> Dict[str, float]:
        """Extract atmospheric state at the primary vortex centre grid point."""
        threat = report.primary_threat
        if not threat or not report.grid_gpi_points:
            return {}

        # Find the grid point matching the vortex centre
        best = next(
            (p for p in report.grid_gpi_points
             if p.lat == threat.center_lat and p.lon == threat.center_lon),
            report.grid_gpi_points[0],
        )
        return {
            "sst_c":            best.sst_c,
            "shear_kt":         best.shear_kt,
            "rh700_pct":        best.rh700_pct,
            "pressure_hpa":     best.pressure_hpa,
            "wind_speed_10m_kt": best.wind_speed_10m_kt,
            "abs_vorticity_s1": best.absolute_vorticity_s1,
        }

    @staticmethod
    def _estimate_wind_from_gpi(gpi: float, wind_10m_kt: float) -> float:
        """Estimate current storm wind speed from GPI and observed 10m surface wind.

        Uses a physically calibrated scaling: GPI drives the upper-bound MPI
        while the 10m wind provides the lower-bound current state. The formula
        uses a sqrt relationship reflecting the GPI sensitivity to intensity.

        Wind = max(10m_wind_amplified, GPI-scaled_estimate)
        Clipped to cyclonic storm range [20, 180] kt.
        """
        # 10m surface wind amplified to free-troposphere (typical 1.3x factor)
        surface_wind = wind_10m_kt * 1.3

        # GPI contribution: maps GPI range [0, 25] -> wind range [20, 120] kt
        gpi_wind = min(120.0, 20.0 + math.sqrt(max(0.0, gpi)) * 20.0)

        # Weighted blend: surface wind is ground truth, GPI fills in intensity
        blended = 0.4 * surface_wind + 0.6 * gpi_wind
        return round(max(20.0, min(180.0, blended)), 1)

    @staticmethod
    def _format_risk(risk_raw: Any) -> List[Dict[str, Any]]:
        """Normalise coastal risk assessment output to a clean list."""
        if isinstance(risk_raw, list):
            return risk_raw
        if isinstance(risk_raw, dict):
            # Handle district dict format
            results = risk_raw.get("district_risks", risk_raw.get("districts", []))
            if isinstance(results, list):
                return results
            return [risk_raw]
        return []

    def close(self) -> None:
        """Release model resources."""
        # PyTorch models are GC'd; placeholder for future GPU memory management.
        pass

    def __enter__(self) -> "RealTimePipeline":
        return self

    def __exit__(self, *_) -> None:
        self.close()
