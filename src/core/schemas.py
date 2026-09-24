"""Pydantic Domain Schemas and Data Contracts for Cyclone AI System.

Ensures strict typing across data ingestion, model inference, and forecaster operations.
"""

from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from src.core.constants import (
    CycloneStage,
    Basin,
    SATELLITE_CHANNELS,
    DEFAULT_IMAGE_SIZE,
)
from src.utils.conversions import knots_to_stage, knots_to_kmh, estimate_central_pressure
from src.utils.geospatial import identify_basin


class SatelliteFrameMeta(BaseModel):
    """Metadata for a multi-channel satellite observation."""
    frame_id: str = Field(..., description="Unique scan identifier, e.g., 'INSAT3D_20260515_0600_IR'")
    timestamp: datetime = Field(..., description="Observation capture time (UTC)")
    sensor: str = Field(default="INSAT-3D/3DR Imager & Sounder", description="Satellite sensor payload")
    channels: List[str] = Field(default_factory=lambda: list(SATELLITE_CHANNELS))
    spatial_resolution_km: float = Field(default=4.0, description="Nadir spatial resolution in km")
    bounding_box: Tuple[float, float, float, float] = Field(
        default=(5.0, 25.0, 80.0, 100.0),
        description="(min_lat, max_lat, min_lon, max_lon)"
    )
    image_shape: Tuple[int, int] = Field(default=DEFAULT_IMAGE_SIZE, description="(height, width)")
    has_missing_mask: bool = Field(default=False, description="True if image has missing sensor patches")


class EnvironmentalFeatures(BaseModel):
    """Atmospheric and oceanic thermodynamic features (ERA5 / reanalysis proxy)."""
    sea_surface_temp_c: float = Field(
        ..., ge=20.0, le=35.0, description="Sea Surface Temperature (SST) in °C"
    )
    vertical_wind_shear_kt: float = Field(
        ..., ge=0.0, le=100.0, description="850-200 hPa Vertical Wind Shear in knots"
    )
    relative_humidity_700hpa: float = Field(
        ..., ge=10.0, le=100.0, description="Mid-tropospheric (700 hPa) Relative Humidity in %"
    )
    ocean_heat_content_kj_cm2: float = Field(
        ..., ge=0.0, le=200.0, description="Upper Ocean Heat Content (OHC) in kJ/cm²"
    )
    vorticity_850hpa: Optional[float] = Field(
        default=15.0, description="Low-level relative vorticity (10^-5 s^-1)"
    )
    coriolis_parameter: Optional[float] = Field(
        default=None, description="Coriolis parameter f = 2*omega*sin(phi) (10^-4 s^-1)"
    )


class BestTrackPoint(BaseModel):
    """Ground truth or predicted storm state at a specific observation timestep."""
    timestamp: datetime
    lat: float = Field(..., ge=-10.0, le=40.0)
    lon: float = Field(..., ge=40.0, le=110.0)
    max_sustained_wind_kt: float = Field(..., ge=0.0, le=250.0)
    max_sustained_wind_kmh: Optional[float] = None
    central_pressure_hpa: Optional[float] = None
    imd_category: Optional[CycloneStage] = None
    basin: Optional[Basin] = None
    is_rapid_intensification: bool = Field(default=False)
    translation_speed_kmh: Optional[float] = Field(default=15.0)
    heading_deg: Optional[float] = Field(default=315.0, description="Degrees from true North (0-360)")

    @field_validator("max_sustained_wind_kmh", mode="before")
    def compute_kmh(cls, v, values):
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.max_sustained_wind_kmh is None:
            self.max_sustained_wind_kmh = knots_to_kmh(self.max_sustained_wind_kt)
        if self.imd_category is None:
            self.imd_category = knots_to_stage(self.max_sustained_wind_kt)
        if self.central_pressure_hpa is None:
            self.central_pressure_hpa = estimate_central_pressure(self.max_sustained_wind_kt)
        if self.basin is None:
            self.basin = identify_basin(self.lat, self.lon)


class CycloneObservation(BaseModel):
    """Unified container joining satellite frame metadata, environment, and ground truth."""
    frame_id: str
    satellite_meta: SatelliteFrameMeta
    env_features: EnvironmentalFeatures
    best_track: BestTrackPoint
    raw_array_path: Optional[str] = None


class ForecasterAction(BaseModel):
    """Human-in-the-loop review and modification record."""
    action_id: str
    frame_id: str
    forecaster_id: str
    status: str = Field(..., description="'APPROVED', 'MODIFIED', or 'PENDING'")
    override_wind_kt: Optional[float] = None
    override_center_lat: Optional[float] = None
    override_center_lon: Optional[float] = None
    override_landfall_eta: Optional[datetime] = None
    forecaster_notes: str = Field(..., min_length=5)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hash_signature: Optional[str] = None
