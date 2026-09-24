"""Unit conversion utilities for cyclone meteorological parameters."""

from src.core.constants import CycloneStage


def knots_to_stage(wind_kt: float) -> CycloneStage:
    """Convert maximum sustained wind speed in knots to the IMD cyclone stage."""
    if wind_kt < 17.0:
        return CycloneStage.LPA
    elif wind_kt < 28.0:
        return CycloneStage.D
    elif wind_kt < 34.0:
        return CycloneStage.DD
    elif wind_kt < 48.0:
        return CycloneStage.CS
    elif wind_kt < 64.0:
        return CycloneStage.SCS
    elif wind_kt < 90.0:
        return CycloneStage.VSCS
    elif wind_kt < 120.0:
        return CycloneStage.ESCS
    else:
        return CycloneStage.SuCS


def knots_to_kmh(knots: float) -> float:
    """Convert knots to kilometres per hour."""
    return round(knots * 1.852, 1)


def kmh_to_knots(kmh: float) -> float:
    """Convert kilometres per hour to knots."""
    return round(kmh / 1.852, 1)


def estimate_central_pressure(wind_kt: float, env_pressure_hpa: float = 1005.0) -> float:
    """Estimate central pressure using an empirical wind-pressure relationship.

    Uses Atkinson-Holliday (1977) formula adapted for the North Indian Ocean:
        ΔP = (wind_kt / 6.3) ^ (1/0.644)
    """
    if wind_kt <= 0:
        return env_pressure_hpa
    delta_p = (wind_kt / 6.3) ** (1.0 / 0.644)
    return round(max(870.0, env_pressure_hpa - delta_p), 1)
