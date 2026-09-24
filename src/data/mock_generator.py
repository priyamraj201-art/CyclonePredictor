"""Physics-Based Synthetic Satellite & Environmental Data Generator.

Simulates 4-channel INSAT-3D/3DR observations using modified Holland/Rankine vortex equations,
logarithmic spiral convective bands, sensor noise/missing scan masks, and matching ERA5/IBTrACS profiles.
"""

import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from src.core.constants import (
    CycloneStage,
    Basin,
    BASIN_BOUNDS,
    CHANNEL_NORMALIZATION_RANGES,
    DEFAULT_IMAGE_SIZE,
    SATELLITE_CHANNELS,
)
from src.core.schemas import (
    SatelliteFrameMeta,
    EnvironmentalFeatures,
    BestTrackPoint,
    CycloneObservation,
)
from src.utils.conversions import knots_to_stage, estimate_central_pressure
from src.utils.geospatial import pixel_to_latlon, latlon_to_pixel, identify_basin


class SyntheticCycloneGenerator:
    """Generates physically consistent multi-channel satellite arrays and associated meteorology."""

    def __init__(self, seed: Optional[int] = 42):
        if seed is not None:
            np.random.seed(seed)
        self.rng = np.random.default_rng(seed)

    def generate_vortex_pattern(
        self,
        image_shape: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        center_pixel: Optional[Tuple[float, float]] = None,
        intensity_kt: float = 65.0,
        eye_radius_px: float = 12.0,
        rmax_px: float = 28.0,
        num_spiral_arms: int = 2,
    ) -> np.ndarray:
        """Generate a 2D convective vorticity/density field using a logarithmic spiral Holland model.
        
        Returns:
            Normalized convection field in [0, 1] where 1.0 represents deep eyewall convection.
        """
        height, width = image_shape
        if center_pixel is None:
            # Place randomly in the central 50% of the image
            cx = self.rng.uniform(width * 0.25, width * 0.75)
            cy = self.rng.uniform(height * 0.25, height * 0.75)
        else:
            cx, cy = center_pixel

        y_coords, x_coords = np.ogrid[:height, :width]
        dx = x_coords - cx
        dy = y_coords - cy
        radius = np.sqrt(dx ** 2 + dy ** 2) + 1e-6
        theta = np.arctan2(dy, dx)  # Angle in radians [-pi, pi]

        # Normalized radial profile (Holland-like core)
        # B determines steepness of eyewall
        b = 1.2 + min(1.0, intensity_kt / 120.0)
        # Eyewall peak at rmax_px
        radial_core = (rmax_px / radius) ** b * np.exp(-(rmax_px / radius) ** b)
        radial_core = radial_core / (radial_core.max() + 1e-6)

        # Eye clearing effect for mature storms (intensity >= 50 kt)
        if intensity_kt >= 50.0:
            eye_mask = 1.0 - np.exp(-(radius / max(4.0, eye_radius_px)) ** 4)
            radial_core = radial_core * eye_mask

        # Logarithmic spiral feeder bands: theta - alpha * ln(r)
        alpha = 0.55  # Tightly wound spiral
        spiral_phase = theta - alpha * np.log(radius / (rmax_px + 1e-5))
        spiral_modulation = np.cos(num_spiral_arms * spiral_phase)
        spiral_modulation = np.clip(spiral_modulation, 0.0, 1.0)

        # Outer spiral arms decay with radius
        arm_envelope = np.exp(-radius / (width * 0.4)) * (radius > (rmax_px * 0.7))
        spiral_convection = spiral_modulation * arm_envelope

        # Combined convection density [0, 1]
        convection = 0.75 * radial_core + 0.45 * spiral_convection
        # Add turbulent cloud noise
        noise = self.rng.normal(0, 0.05, size=image_shape)
        convection = np.clip(convection + noise, 0.0, 1.0)

        return convection.astype(np.float32)

    def synthesize_4channel_frame(
        self,
        convection_field: np.ndarray,
        intensity_kt: float = 65.0,
        add_sensor_mask: bool = True,
        mask_fraction: float = 0.15,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert a 2D convection density field into physical 4-channel satellite imagery.
        
        Channels:
          0: IR (10.8 µm) - Brightness Temp in Kelvin [180.0, 310.0]
          1: WV (6.7 µm)  - Water Vapor Temp in Kelvin [200.0, 270.0]
          2: VIS (0.65 µm)- Visible Albedo [0.0, 1.0]
          3: PMW (89 GHz) - Microwave scattering proxy in Kelvin [150.0, 300.0]

        Returns:
            (raw_channels [4, H, W], mask [4, H, W] where 1 indicates valid, 0 indicates missing/masked)
        """
        h, w = convection_field.shape
        raw_channels = np.zeros((4, h, w), dtype=np.float32)
        valid_mask = np.ones((4, h, w), dtype=np.float32)

        # 1. IR Channel (10.8 µm): Cold cloud tops (190K - 210K) in deep convection, warm sea (295K - 305K)
        # If eye is clear and storm is strong, eye center is warmer
        ir_ambient = self.rng.uniform(295.0, 305.0)
        ir_core_cold = 190.0 + max(0.0, (120.0 - intensity_kt) * 0.2)
        ir_field = ir_ambient - convection_field * (ir_ambient - ir_core_cold)
        ir_noise = self.rng.normal(0.0, 1.2, size=(h, w))
        raw_channels[0] = np.clip(ir_field + ir_noise, 180.0, 310.0)

        # 2. WV Channel (6.7 µm): Upper tropospheric moisture (205K - 220K in moist core, 250K - 265K dry)
        wv_ambient = self.rng.uniform(250.0, 265.0)
        wv_core = 205.0 + max(0.0, (100.0 - intensity_kt) * 0.15)
        wv_field = wv_ambient - convection_field * (wv_ambient - wv_core)
        wv_noise = self.rng.normal(0.0, 1.0, size=(h, w))
        raw_channels[1] = np.clip(wv_field + wv_noise, 200.0, 270.0)

        # 3. VIS Channel (0.65 µm): Cloud reflectance albedo (0.05 ocean, 0.85-0.95 dense anvil)
        vis_field = 0.05 + convection_field * 0.85
        vis_noise = self.rng.normal(0.0, 0.02, size=(h, w))
        raw_channels[2] = np.clip(vis_field + vis_noise, 0.0, 1.0)

        # 4. PMW Channel (89 GHz): Ice scattering depresses brightness temp (down to ~160K in eyewall)
        pmw_ambient = self.rng.uniform(275.0, 290.0)
        pmw_core = 160.0 + max(0.0, (120.0 - intensity_kt) * 0.3)
        pmw_field = pmw_ambient - convection_field * (pmw_ambient - pmw_core)
        pmw_noise = self.rng.normal(0.0, 2.0, size=(h, w))
        raw_channels[3] = np.clip(pmw_field + pmw_noise, 150.0, 300.0)

        # Optional missing sensor patches / line dropout
        if add_sensor_mask and mask_fraction > 0.0:
            num_boxes = self.rng.integers(1, 4)
            for _ in range(num_boxes):
                bx = self.rng.integers(10, w - 50)
                by = self.rng.integers(10, h - 50)
                bw = int(w * self.rng.uniform(0.1, min(0.3, mask_fraction + 0.1)))
                bh = int(h * self.rng.uniform(0.1, min(0.3, mask_fraction + 0.1)))
                # Zero out selected patch across some or all channels
                affected_channels = self.rng.choice([0, 1, 2, 3], size=self.rng.integers(1, 5), replace=False)
                for ch in affected_channels:
                    valid_mask[ch, by:by+bh, bx:bx+bw] = 0.0
                    raw_channels[ch, by:by+bh, bx:bx+bw] = 0.0

            # Scan line dropouts (common in real INSAT-3D scans)
            if self.rng.random() < 0.4:
                line_idx = self.rng.integers(20, h - 20)
                valid_mask[:, line_idx:line_idx+2, :] = 0.0
                raw_channels[:, line_idx:line_idx+2, :] = 0.0

        return raw_channels, valid_mask

    def generate_single_observation(
        self,
        basin: Basin = Basin.BAY_OF_BENGAL,
        intensity_kt: Optional[float] = None,
        add_mask: bool = True,
        timestamp: Optional[datetime] = None,
        frame_idx: int = 1,
    ) -> Tuple[CycloneObservation, np.ndarray, np.ndarray]:
        """Generate a complete synthetic observation (metadata, environment, labels, arrays)."""
        if timestamp is None:
            timestamp = datetime(2026, 5, 12, 6, 0)

        min_lat, max_lat, min_lon, max_lon = BASIN_BOUNDS[basin]
        bbox = (min_lat, max_lat, min_lon, max_lon)

        # Sample storm intensity if not given
        if intensity_kt is None:
            # Favor realistic distribution across CS, SCS, VSCS
            intensity_kt = float(self.rng.choice([
                self.rng.uniform(20, 32),   # D / DD
                self.rng.uniform(35, 47),   # CS
                self.rng.uniform(50, 62),   # SCS
                self.rng.uniform(65, 88),   # VSCS
                self.rng.uniform(92, 115),  # ESCS
            ]))
        intensity_kt = round(intensity_kt, 1)

        # Place center inside basin with safe margins
        storm_lat = float(self.rng.uniform(min_lat + 2.0, max_lat - 2.0))
        storm_lon = float(self.rng.uniform(min_lon + 2.0, max_lon - 2.0))

        image_shape = DEFAULT_IMAGE_SIZE
        px, py = latlon_to_pixel(storm_lat, storm_lon, image_shape, bbox)

        # Synthesize convection field & 4-channel image
        convection = self.generate_vortex_pattern(
            image_shape=image_shape,
            center_pixel=(px, py),
            intensity_kt=intensity_kt,
        )
        raw_channels, valid_mask = self.synthesize_4channel_frame(
            convection_field=convection,
            intensity_kt=intensity_kt,
            add_sensor_mask=add_mask,
        )

        has_missing = bool(np.any(valid_mask == 0.0))

        # Metadata
        meta = SatelliteFrameMeta(
            frame_id=f"INSAT3D_{timestamp.strftime('%Y%m%d_%H%M')}_{basin.name[:3]}_{frame_idx:03d}",
            timestamp=timestamp,
            bounding_box=bbox,
            image_shape=image_shape,
            has_missing_mask=has_missing,
        )

        # Environmental Reanalysis Features (ERA5 proxy)
        # Warm SST, low shear, high humidity correlate with higher intensity / RI
        sst = round(float(self.rng.uniform(28.0, 31.5)), 2)
        shear = round(float(self.rng.uniform(6.0, 28.0)), 1)
        rh700 = round(float(self.rng.uniform(65.0, 92.0)), 1)
        ohc = round(float(self.rng.uniform(50.0, 130.0)), 1)
        vorticity = round(float(self.rng.uniform(12.0, 30.0)), 1)
        f_coriolis = round(2.0 * 7.292e-5 * math.sin(math.radians(storm_lat)) * 1e4, 4)

        env = EnvironmentalFeatures(
            sea_surface_temp_c=sst,
            vertical_wind_shear_kt=shear,
            relative_humidity_700hpa=rh700,
            ocean_heat_content_kj_cm2=ohc,
            vorticity_850hpa=vorticity,
            coriolis_parameter=f_coriolis,
        )

        # Rapid intensification heuristic: warm sea >29C, shear < 15kt, rh > 75%
        is_ri = (sst >= 29.2 and shear <= 14.0 and rh700 >= 78.0 and intensity_kt >= 35.0)

        # Ground truth best track point
        best_track = BestTrackPoint(
            timestamp=timestamp,
            lat=storm_lat,
            lon=storm_lon,
            max_sustained_wind_kt=intensity_kt,
            is_rapid_intensification=is_ri,
            translation_speed_kmh=round(float(self.rng.uniform(10.0, 22.0)), 1),
            heading_deg=round(float(self.rng.uniform(290.0, 340.0)), 1),  # Typical NW track in NIO
        )

        obs = CycloneObservation(
            frame_id=meta.frame_id,
            satellite_meta=meta,
            env_features=env,
            best_track=best_track,
        )

        return obs, raw_channels, valid_mask

    def generate_synthetic_trajectory(
        self,
        storm_name: str = "SYNTHETIC_STORM",
        basin: Basin = Basin.BAY_OF_BENGAL,
        num_steps: int = 9,  # 0h to 48h at 6h steps
        start_lat: float = 10.5,
        start_lon: float = 88.5,
        initial_wind_kt: float = 30.0,
        peak_wind_kt: float = 85.0,
        start_time: Optional[datetime] = None,
    ) -> List[Tuple[CycloneObservation, np.ndarray, np.ndarray]]:
        """Generate a coherent historical multi-timestep sequence (e.g. 48-hour storm lifecycle)."""
        if start_time is None:
            start_time = datetime(2026, 5, 10, 0, 0)

        sequence = []
        cur_lat = start_lat
        cur_lon = start_lon

        # Build an intensity curve that rises to peak then stabilizes
        intensity_curve = np.linspace(initial_wind_kt, peak_wind_kt, num_steps // 2 + 1)
        decay_curve = np.linspace(peak_wind_kt, peak_wind_kt * 0.85, num_steps - len(intensity_curve))
        winds = np.concatenate([intensity_curve, decay_curve])

        for step in range(num_steps):
            step_time = start_time + timedelta(hours=6 * step)
            wind_kt = round(float(winds[step]), 1)

            # Move typically North-Northwest
            cur_lat += self.rng.uniform(0.6, 1.1)
            cur_lon -= self.rng.uniform(0.3, 0.8)

            obs, raw, mask = self.generate_single_observation(
                basin=basin,
                intensity_kt=wind_kt,
                timestamp=step_time,
                frame_idx=step + 1,
            )
            # Override coordinates to match trajectory
            obs.best_track.lat = round(cur_lat, 4)
            obs.best_track.lon = round(cur_lon, 4)

            sequence.append((obs, raw, mask))

        return sequence

    def save_observation_npz(
        self,
        obs: CycloneObservation,
        raw_channels: np.ndarray,
        valid_mask: np.ndarray,
        output_dir: Path,
    ) -> Path:
        """Save observation and arrays into compressed .npz archive with metadata JSON."""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{obs.frame_id}.npz"
        filepath = output_dir / filename

        np.savez_compressed(
            filepath,
            channels=raw_channels,
            mask=valid_mask,
            metadata=obs.model_dump_json(),
        )
        obs.raw_array_path = str(filepath)
        return filepath
