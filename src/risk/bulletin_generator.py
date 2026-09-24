"""Automated IMD Cyclone Warning Bulletin Generator.

Generates official-format meteorological bulletins adhering to the IMD 4-stage warning system:
Stage 1: Pre-Cyclone Watch | Stage 2: Cyclone Alert | Stage 3: Cyclone Warning | Stage 4: Post-Landfall Outlook.
Exports as structured JSON, plain text, and HTML formats.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from src.core.constants import CycloneStage
from src.core.schemas import BestTrackPoint


class IMDBulletinGenerator:
    """Formats official India Meteorological Department cyclone alert bulletins."""

    def __init__(self, bulletin_sequence: int = 1):
        self.bulletin_sequence = bulletin_sequence

    def determine_warning_stage(
        self,
        landfall_eta_hours: Optional[float] = None,
        wind_kt: float = 65.0,
    ) -> str:
        """Determine IMD 4-stage alert tier based on landfall proximity."""
        if landfall_eta_hours is None:
            return "STAGE 1: PRE-CYCLONE WATCH"

        if landfall_eta_hours <= 12.0:
            return "STAGE 4: POST-LANDFALL OUTLOOK / RED ALERT"
        elif landfall_eta_hours <= 24.0:
            return "STAGE 3: CYCLONE WARNING / ORANGE ALERT"
        elif landfall_eta_hours <= 48.0:
            return "STAGE 2: CYCLONE ALERT / YELLOW ALERT"
        else:
            return "STAGE 1: PRE-CYCLONE WATCH"

    def get_damage_expectations(self, stage_name: str) -> List[str]:
        """IMD standard expected damage descriptions for cyclone intensity."""
        if "Super" in stage_name or "Extremely Severe" in stage_name:
            return [
                "Total destruction of thatched and old asbestos/tin roof structures.",
                "Extensive damage to pucca structures, communication towers, and overhead power grids.",
                "Uprooting of large, mature avenue trees and complete disruption of road/rail networks.",
                "Catastrophic inundation of low-lying coastal tracts up to 5-10 km inland due to storm surge.",
                "Total suspension of fishing operations, coastal shipping, and port cargo logistics.",
            ]
        elif "Very Severe" in stage_name or "Severe" in stage_name:
            return [
                "Major damage to thatched houses and huts; partial damage to pucca houses.",
                "Minor disruption of power and communication lines due to branch breakage.",
                "Flooding of escape routes and inundation of standing agricultural crops and salt pans.",
                "Small boats and country crafts likely to get torn from moorings.",
            ]
        elif "Cyclonic Storm" in stage_name:
            return [
                "Damage to thatched huts and temporary coastal shelters.",
                "Breaking of tree branches and minor damage to banana and papaya plantations.",
                "Rough to very rough sea conditions making navigation hazardous.",
            ]
        else:
            return [
                "Squally weather with strong surface winds along coastal belts.",
                "Localized water logging in low-lying tracts and flash rain accumulation.",
            ]

    def get_action_recommendations(self, stage_name: str) -> List[str]:
        """Civil defense and administrative directives."""
        if "Super" in stage_name or "Extremely Severe" in stage_name or "Very Severe" in stage_name:
            return [
                "TOTAL SUSPENSION of all marine fishing operations across affected coastlines.",
                "IMMEDIATE EVACUATION of vulnerable coastal population to designated multi-purpose cyclone shelters.",
                "Hoisting of Great Danger Signals (Signal No. 8, 9, or 10) at impacted major ports.",
                "Suspension of rail, road, and flight operations in the landfall corridor during peak storm hours.",
                "Pre-positioning of NDRF / SDRF / Indian Coast Guard search and rescue battalions.",
            ]
        elif "Severe" in stage_name or "Cyclonic Storm" in stage_name:
            return [
                "Fishermen are strictly advised not to venture into deep sea or coastal waters.",
                "Local Cautionary Signals (Signal No. 3 or 4) hoisted at maritime ports.",
                "Coastal district administrations on high alert with shelters activated.",
                "Judicious regulation of traffic on coastal bridges and causeways.",
            ]
        else:
            return [
                "Fishermen out at deep sea advised to return to nearest safe harbor.",
                "Port authorities to monitor special weather advisories.",
            ]

    def generate_bulletin(
        self,
        storm_name: str,
        current_observation: BestTrackPoint,
        forecast_points: List[BestTrackPoint],
        landfall_info: Dict[str, Any],
        high_risk_districts: List[Dict[str, Any]],
        ri_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assemble structured IMD Cyclone Warning Bulletin."""
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + timedelta(hours=5, minutes=30)

        # Landfall hours calculation
        eta_h = None
        if landfall_info.get("has_landfall"):
            # Approximate lead time
            eta_h = 24.0

        stage_tier = self.determine_warning_stage(
            landfall_eta_hours=eta_h,
            wind_kt=current_observation.max_sustained_wind_kt,
        )

        stage_enum = current_observation.imd_category or CycloneStage.CS
        category_name = stage_enum.value

        damages = self.get_damage_expectations(category_name)
        actions = self.get_action_recommendations(category_name)

        # Plain Text format
        text_lines = [
            "================================================================================",
            "                   INDIA METEOROLOGICAL DEPARTMENT (IMD)",
            "               MINISTRY OF EARTH SCIENCES, GOVERNMENT OF INDIA",
            "                  CYCLONE WARNING DIVISION, NEW DELHI",
            "================================================================================",
            f"BULLETIN NO.: {self.bulletin_sequence:02d}                                    TIME OF ISSUE: {now_ist.strftime('%d-%b-%Y %H:%M IST')}",
            f"WARNING STATUS: {stage_tier}",
            "--------------------------------------------------------------------------------",
            f"SUBJECT: TROPICAL CYCLONE '{storm_name.upper()}' OVER {current_observation.basin.value.upper()}",
            "--------------------------------------------------------------------------------",
            "1. CURRENT INTENSITY AND LOCATION:",
            f"   The {category_name} '{storm_name}' lay centered at {current_observation.timestamp.strftime('%H:%M UTC of %d-%b-%Y')} "
            f"near Latitude {current_observation.lat:.2f}°N and Longitude {current_observation.lon:.2f}°E.",
            f"   - Maximum Sustained Surface Wind Speed: {current_observation.max_sustained_wind_kt:.0f} knots "
            f"({current_observation.max_sustained_wind_kmh:.0f} km/h) gusting higher.",
            f"   - Estimated Central Pressure: {current_observation.central_pressure_hpa} hPa.",
        ]

        if ri_info and ri_info.get("is_ri_flagged"):
            text_lines.append(f"   - ALERT: {ri_info['advisory']}")

        text_lines.append("\n2. FORECAST TRACK & LANDFALL OUTLOOK:")
        if landfall_info.get("has_landfall"):
            text_lines.extend([
                f"   - Expected Landfall: {landfall_info['district']}, {landfall_info['state_or_country']}",
                f"   - Landfall Timing: {landfall_info['eta_ist']} (+/- {landfall_info.get('uncertainty_window_hours', 4)}h)",
                f"   - Intensity at Landfall: {landfall_info['intensity_at_landfall_kt']} kt ({landfall_info['intensity_at_landfall_kmh']} km/h), as a {landfall_info['stage_at_landfall']}.",
            ])
        else:
            text_lines.append("   - Trajectory projected over open sea; no direct coastal landfall detected in 48 hours.")

        text_lines.append("\n3. HIGH-RISK VULNERABLE COASTAL DISTRICTS:")
        for dist in high_risk_districts[:5]:
            text_lines.append(
                f"   - {dist['district']} ({dist['state']}): Composite Risk Score {dist['composite_risk']} "
                f"[{dist['risk_category']}] | Est. Surge: {dist['surge_height_m']}m | Rain Alert: {dist['rainfall_alert']}"
            )

        text_lines.append("\n4. EXPECTED DAMAGES:")
        for d in damages:
            text_lines.append(f"   * {d}")

        text_lines.append("\n5. ACTION SUGGESTED / CIVIL DIRECTIVES:")
        for a in actions:
            text_lines.append(f"   * {a}")

        text_lines.extend([
            "--------------------------------------------------------------------------------",
            "This automated bulletin is issued by the AI-Enhanced IMD Decision Support Engine.",
            "Certified Forecaster Review: MANDATORY prior to public radio / SMS dissemination.",
            "================================================================================",
        ])
        plain_text_bulletin = "\n".join(text_lines)

        # HTML Snippet for dashboard rendering
        html_bulletin = f"""
        <div class="imd-bulletin font-mono text-sm leading-relaxed p-6 bg-slate-900 text-slate-100 rounded-lg border border-slate-700">
            <div class="text-center pb-4 border-b border-slate-700">
                <h3 class="text-lg font-bold tracking-wide text-amber-400">INDIA METEOROLOGICAL DEPARTMENT</h3>
                <p class="text-xs text-slate-400">Cyclone Warning Bulletin No. {self.bulletin_sequence:02d} | Issued: {now_ist.strftime('%d-%b-%Y %H:%M IST')}</p>
                <div class="mt-2 inline-block px-3 py-1 rounded bg-red-600/80 text-white font-bold text-xs">{stage_tier}</div>
            </div>
            <div class="mt-4 space-y-3">
                <p><span class="text-slate-400 font-semibold">Subject:</span> {category_name} '{storm_name}' over {current_observation.basin.value}</p>
                <p><span class="text-slate-400 font-semibold">Current State:</span> Lat {current_observation.lat:.2f}&deg;N, Lon {current_observation.lon:.2f}&deg;E | Winds: <strong>{current_observation.max_sustained_wind_kt:.0f} kt ({current_observation.max_sustained_wind_kmh:.0f} km/h)</strong> | Pressure: {current_observation.central_pressure_hpa} hPa</p>
                <div class="p-3 bg-slate-800/80 rounded border border-slate-700">
                    <h4 class="text-xs font-bold text-sky-400 uppercase">Landfall Outlook</h4>
                    <p class="text-xs mt-1">Target: <strong>{landfall_info.get('district', 'Open Sea')}, {landfall_info.get('state_or_country', '')}</strong></p>
                    <p class="text-xs">ETA: <strong>{landfall_info.get('eta_ist', 'N/A')}</strong> | Landfall Wind: <strong>{landfall_info.get('intensity_at_landfall_kt', 'N/A')} kt</strong></p>
                </div>
            </div>
        </div>
        """

        return {
            "bulletin_number": self.bulletin_sequence,
            "issued_at_utc": now_utc.isoformat(),
            "issued_at_ist": now_ist.strftime("%d-%b-%Y %H:%M IST"),
            "stage_tier": stage_tier,
            "storm_name": storm_name,
            "category": category_name,
            "damages": damages,
            "actions": actions,
            "plain_text": plain_text_bulletin,
            "html": html_bulletin,
        }
