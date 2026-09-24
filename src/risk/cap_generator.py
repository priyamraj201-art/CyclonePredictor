"""OASIS Common Alerting Protocol (CAP v1.2 XML) & WMO Advisory Generator.

Produces machine-readable XML alert documents compliant with:
- OASIS CAP v1.2 Standard (ITU-T Rec. X.1303)
- National Disaster Management Authority (NDMA) Sachet Broadcast Protocol
- WMO Tropical Cyclone Advisory (TCA) format
"""

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.schemas import BestTrackPoint


def generate_cap_xml(
    storm_name: str,
    current_obs: BestTrackPoint,
    landfall_info: Optional[Dict[str, Any]] = None,
    affected_districts: Optional[List[Dict[str, Any]]] = None,
    severity: str = "Severe",
    urgency: str = "Expected",
    certainty: str = "Observed",
    bulletin_seq: int = 1,
) -> str:
    """Generate official OASIS CAP v1.2 XML document for cyclone warnings.
    
    Args:
        storm_name: Name of the cyclone (e.g., 'FANI')
        current_obs: Center coordinates and wind speed
        landfall_info: Dict with landfall ETA, district, and state
        affected_districts: List of high-risk coastal districts
        severity: Extreme / Severe / Moderate / Minor
        urgency: Immediate / Expected / Future / Past
        certainty: Observed / Likely / Possible / Unlikely
        bulletin_seq: Sequence number of the bulletin
    Returns:
        Formatted XML string
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    identifier = f"IN-IMD-CYCLONE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{bulletin_seq:03d}"

    # Root <alert> element
    alert = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")

    ET.SubElement(alert, "identifier").text = identifier
    ET.SubElement(alert, "sender").text = "imd-hq-cyclone@moes.gov.in"
    ET.SubElement(alert, "sent").text = now_iso
    ET.SubElement(alert, "status").text = "Actual"
    ET.SubElement(alert, "msgType").text = "Alert"
    ET.SubElement(alert, "scope").text = "Public"
    ET.SubElement(alert, "code").text = "IMD-CYCLONE-WARNING"

    # <info> block
    info = ET.SubElement(alert, "info")
    ET.SubElement(info, "language").text = "en-IN"
    ET.SubElement(info, "category").text = "Met"
    ET.SubElement(info, "event").text = f"Tropical Cyclone Warning - {storm_name}"
    ET.SubElement(info, "urgency").text = urgency
    ET.SubElement(info, "severity").text = severity
    ET.SubElement(info, "certainty").text = certainty

    stage_desc = current_obs.imd_category.value if current_obs.imd_category else "Cyclonic Storm"
    headline = (
        f"CYCLONE WARNING BULLETIN #{bulletin_seq:02d}: {stage_desc.upper()} '{storm_name}' "
        f"OVER NORTH INDIAN OCEAN"
    )
    ET.SubElement(info, "headline").text = headline

    # Detailed description
    desc_lines = [
        f"Storm Center: {current_obs.lat:.2f}N, {current_obs.lon:.2f}E",
        f"Max Sustained Surface Winds: {current_obs.max_sustained_wind_kt:.0f} knots ({current_obs.max_sustained_wind_kt * 1.852:.0f} km/h)",
        f"Estimated Central Pressure: {current_obs.central_pressure_hpa:.0f} hPa",
    ]
    if landfall_info and landfall_info.get("has_landfall"):
        desc_lines.append(
            f"Landfall Outlook: Expected crossing near {landfall_info.get('district')}, "
            f"{landfall_info.get('state_or_country')} with ETA: {landfall_info.get('eta_ist')}."
        )
    ET.SubElement(info, "description").text = "\n".join(desc_lines)

    # Instruction block for public & disaster management agencies
    instructions = [
        "1. Total suspension of fishing operations along and off affected coastal belts.",
        "2. Coastal hutment dwellers and vulnerable populations advised to move to designated Cyclone Shelters.",
        "3. Major and minor port authorities advised to hoist Local Warning Signal VI.",
        "4. Disaster management authorities (NDRF / SDRF) placed on standby.",
    ]
    ET.SubElement(info, "instruction").text = "\n".join(instructions)

    # <area> block with affected districts and polygon
    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = (
        f"North Indian Ocean Coastal Belt & Storm Vicinity (Center: {current_obs.lat:.2f}N, {current_obs.lon:.2f}E)"
    )

    # Circle around cyclone center (Lat,Lon Radius_in_km)
    circle_radius_km = 150.0
    ET.SubElement(area, "circle").text = f"{current_obs.lat:.4f},{current_obs.lon:.4f} {circle_radius_km:.1f}"

    # Affected districts geocodes
    if affected_districts:
        for dist in affected_districts[:5]:
            geocode = ET.SubElement(area, "geocode")
            ET.SubElement(geocode, "valueName").text = "District"
            ET.SubElement(geocode, "value").text = f"{dist.get('district_name')}, {dist.get('state_name')}"

    return ET.tostring(alert, encoding="utf-8", xml_declaration=True).decode("utf-8")


def generate_wmo_tca(
    storm_name: str,
    current_obs: BestTrackPoint,
    forecast_points: List[BestTrackPoint],
) -> str:
    """Generate formal WMO Tropical Cyclone Advisory (TCA) alphanumeric bulletin."""
    now_dt = datetime.now(timezone.utc)
    tca_lines = [
        f"TC ADVISORY",
        f"DTG: {now_dt.strftime('%Y%m%d/%H%M')}Z",
        f"TCAC: NEW DELHI",
        f"TC: {storm_name.upper()}",
        f"NR: 01",
        f"PSN: N{abs(current_obs.lat):.2f} E{abs(current_obs.lon):.2f}",
        f"MOV: NW 15KT",
        f"C: {current_obs.central_pressure_hpa:.0f}HPA",
        f"MAX WIND: {current_obs.max_sustained_wind_kt:.0f}KT",
        f"FCST PSN +06HR: N{forecast_points[0].lat:.2f} E{forecast_points[0].lon:.2f} MAX WIND {forecast_points[0].max_sustained_wind_kt:.0f}KT" if len(forecast_points) > 0 else "FCST +06HR: NIL",
        f"FCST PSN +12HR: N{forecast_points[1].lat:.2f} E{forecast_points[1].lon:.2f} MAX WIND {forecast_points[1].max_sustained_wind_kt:.0f}KT" if len(forecast_points) > 1 else "FCST +12HR: NIL",
        f"FCST PSN +24HR: N{forecast_points[2].lat:.2f} E{forecast_points[2].lon:.2f} MAX WIND {forecast_points[2].max_sustained_wind_kt:.0f}KT" if len(forecast_points) > 2 else "FCST +24HR: NIL",
        f"RMK: NIL",
        f"NXT MSG: {now_dt.strftime('%Y%m%d')}/1200Z",
    ]
    return "\n".join(tca_lines)
