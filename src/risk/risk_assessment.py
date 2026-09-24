"""GIS-Based Coastal Vulnerability & Dynamic Multi-Hazard Risk Assessment Engine.

Evaluates wind swaths, storm surge heights, and rainfall hazards across Indian coastal districts
(Odisha, West Bengal, Andhra Pradesh, Tamil Nadu, Gujarat, Maharashtra) to compute composite risk scores (0-100).
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from src.core.schemas import BestTrackPoint
from src.utils.geospatial import haversine_distance_km

# Comprehensive GIS database of vulnerable Indian coastal districts
COASTAL_DISTRICTS_DB: List[Dict[str, Any]] = [
    # Odisha
    {
        "district": "Kendrapara",
        "state": "Odisha",
        "lat": 20.50,
        "lon": 86.75,
        "population_density": 545,  # per km2
        "elevation_m": 4.5,
        "bathymetry_factor": 1.45,  # Shallow Bay of Bengal shelf -> high surge
        "cyclone_shelters": 72,
        "critical_infrastructure": ["Dhamra Port Access", "National Highway 5A"],
    },
    {
        "district": "Jagatsinghpur",
        "state": "Odisha",
        "lat": 20.25,
        "lon": 86.65,
        "population_density": 681,
        "elevation_m": 3.8,
        "bathymetry_factor": 1.50,
        "cyclone_shelters": 85,
        "critical_infrastructure": ["Paradip Port", "IOCL Refinery", "PPT Bulk Terminal"],
    },
    {
        "district": "Puri",
        "state": "Odisha",
        "lat": 19.80,
        "lon": 85.80,
        "population_density": 488,
        "elevation_m": 5.0,
        "bathymetry_factor": 1.30,
        "cyclone_shelters": 64,
        "critical_infrastructure": ["Chilika Biosphere", "Puri Tourism Hub", "Marine Drive"],
    },
    {
        "district": "Balasore",
        "state": "Odisha",
        "lat": 21.50,
        "lon": 87.05,
        "population_density": 609,
        "elevation_m": 6.2,
        "bathymetry_factor": 1.40,
        "cyclone_shelters": 55,
        "critical_infrastructure": ["ITR Chandipur", "Chandipur Defense Est."],
    },
    {
        "district": "Bhadrak",
        "state": "Odisha",
        "lat": 20.90,
        "lon": 86.90,
        "population_density": 601,
        "elevation_m": 4.0,
        "bathymetry_factor": 1.42,
        "cyclone_shelters": 48,
        "critical_infrastructure": ["Dhamra Port", "Adani LNG Terminal"],
    },
    {
        "district": "Ganjam",
        "state": "Odisha",
        "lat": 19.30,
        "lon": 85.05,
        "population_density": 430,
        "elevation_m": 8.0,
        "bathymetry_factor": 1.15,
        "cyclone_shelters": 52,
        "critical_infrastructure": ["Gopalpur Port", "Rare Earths Extraction"],
    },
    # West Bengal
    {
        "district": "South 24 Parganas",
        "state": "West Bengal",
        "lat": 21.60,
        "lon": 88.20,
        "population_density": 819,
        "elevation_m": 2.2,  # Very low-lying delta
        "bathymetry_factor": 1.65,  # Extreme surge risk
        "cyclone_shelters": 115,
        "critical_infrastructure": ["Sunderbans Biosphere", "Kolkata Port Approach", "Diamond Harbour"],
    },
    {
        "district": "East Medinipur",
        "state": "West Bengal",
        "lat": 21.65,
        "lon": 87.55,
        "population_density": 1076,
        "elevation_m": 4.0,
        "bathymetry_factor": 1.55,
        "cyclone_shelters": 90,
        "critical_infrastructure": ["Haldia Port", "Haldia Petrochemicals", "Digha Coastline"],
    },
    # Andhra Pradesh
    {
        "district": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "lat": 17.70,
        "lon": 83.30,
        "population_density": 384,
        "elevation_m": 12.0,
        "bathymetry_factor": 1.10,
        "cyclone_shelters": 60,
        "critical_infrastructure": ["Vizag Port", "Eastern Naval Command", "HPCL Refinery"],
    },
    {
        "district": "Krishna",
        "state": "Andhra Pradesh",
        "lat": 16.15,
        "lon": 81.15,
        "population_density": 518,
        "elevation_m": 3.5,
        "bathymetry_factor": 1.35,
        "cyclone_shelters": 70,
        "critical_infrastructure": ["Machilipatnam Port", "Krishna Delta Canal System"],
    },
    # Tamil Nadu
    {
        "district": "Chennai",
        "state": "Tamil Nadu",
        "lat": 13.10,
        "lon": 80.30,
        "population_density": 26553,  # Dense mega-city
        "elevation_m": 6.7,
        "bathymetry_factor": 1.15,
        "cyclone_shelters": 140,
        "critical_infrastructure": ["Chennai Port", "Ennore Kamarajar Port", "Metro Subways", "Airport"],
    },
    {
        "district": "Cuddalore",
        "state": "Tamil Nadu",
        "lat": 11.75,
        "lon": 79.75,
        "population_density": 701,
        "elevation_m": 4.2,
        "bathymetry_factor": 1.25,
        "cyclone_shelters": 45,
        "critical_infrastructure": ["SIPCOT Chemical Complex", "Cuddalore Port"],
    },
    # Gujarat
    {
        "district": "Kachchh",
        "state": "Gujarat",
        "lat": 23.25,
        "lon": 68.60,
        "population_density": 46,
        "elevation_m": 8.5,
        "bathymetry_factor": 1.45,
        "cyclone_shelters": 38,
        "critical_infrastructure": ["Kandla Port", "Mundra Port (Adani)", "Salt Works"],
    },
    {
        "district": "Devbhumi Dwarka",
        "state": "Gujarat",
        "lat": 22.25,
        "lon": 68.95,
        "population_density": 130,
        "elevation_m": 6.0,
        "bathymetry_factor": 1.30,
        "cyclone_shelters": 28,
        "critical_infrastructure": ["Okha Port", "Dwarka Cultural Heritage", "Wind Energy Farms"],
    },
    # Maharashtra
    {
        "district": "Mumbai",
        "state": "Maharashtra",
        "lat": 18.95,
        "lon": 72.80,
        "population_density": 21000,
        "elevation_m": 8.0,
        "bathymetry_factor": 1.20,
        "cyclone_shelters": 120,
        "critical_infrastructure": ["Mumbai Port", "JNPT", "Bandra-Worli Sea Link", "Financial Hub"],
    },
    {
        "district": "Raigad",
        "state": "Maharashtra",
        "lat": 18.30,
        "lon": 72.95,
        "population_density": 368,
        "elevation_m": 5.5,
        "bathymetry_factor": 1.25,
        "cyclone_shelters": 35,
        "critical_infrastructure": ["Alibaug Coastal Belt", "RCF Thal", "Dighi Port"],
    },
]


class CoastalRiskAssessmentEngine:
    """Calculates multi-hazard impact and dynamic risk scores for coastal districts."""

    def __init__(self, districts_db: Optional[List[Dict[str, Any]]] = None):
        self.districts = districts_db or COASTAL_DISTRICTS_DB

    def estimate_district_hazard(
        self,
        district: Dict[str, Any],
        storm_lat: float,
        storm_lon: float,
        storm_wind_kt: float,
        central_pressure_hpa: float,
    ) -> Dict[str, Any]:
        """Estimate wind swath, storm surge, and rainfall hazards for a single district."""
        dist_km = haversine_distance_km(storm_lat, storm_lon, district["lat"], district["lon"])

        # 1. Local Wind Speed Estimation via Holland modified radial decay
        rmax_km = 35.0  # Radius of maximum winds
        if dist_km <= rmax_km:
            local_wind_kt = storm_wind_kt
        else:
            # Decay with distance
            decay = (rmax_km / dist_km) ** 0.55
            local_wind_kt = storm_wind_kt * decay
        local_wind_kt = round(max(5.0, local_wind_kt), 1)
        local_wind_kmh = round(local_wind_kt * 1.852, 1)

        # Wind hazard classification
        if local_wind_kt >= 64.0:
            wind_hazard = "DESTRUCTIVE_CORE"
            wind_score = 100.0
        elif local_wind_kt >= 48.0:
            wind_hazard = "STORM_FORCE"
            wind_score = 75.0
        elif local_wind_kt >= 34.0:
            wind_hazard = "GALE_FORCE"
            wind_score = 50.0
        else:
            wind_hazard = "MODERATE_BREEZE"
            wind_score = 20.0

        # 2. Storm Surge Estimation (meters)
        # Delta P = 1010 - P_min
        pressure_deficit = max(0.0, 1010.0 - central_pressure_hpa)
        # Pressure contribution: ~1 cm per 1 hPa deficit
        static_surge_m = pressure_deficit * 0.01
        # Wind stress contribution scaled by bathymetry and proximity
        proximity_factor = math.exp(-dist_km / 120.0)
        dynamic_surge_m = (
            ((storm_wind_kt / 70.0) ** 2)
            * district["bathymetry_factor"]
            * 1.8
            * proximity_factor
        )
        surge_height_m = round(max(0.2, static_surge_m + dynamic_surge_m), 1)

        if surge_height_m >= 3.5:
            surge_severity = "CATASTROPHIC"
            surge_score = 100.0
        elif surge_height_m >= 2.0:
            surge_severity = "EXTENSIVE"
            surge_score = 75.0
        elif surge_height_m >= 1.0:
            surge_severity = "MODERATE"
            surge_score = 45.0
        else:
            surge_severity = "MINIMAL"
            surge_score = 15.0

        # 3. Rainfall Hazard (cm / 24h)
        rainfall_cm = round(max(2.0, (storm_wind_kt / 10.0) * 2.2 * proximity_factor), 1)
        if rainfall_cm >= 20.0:
            rain_alert = "RED (Extremely Heavy > 20 cm)"
            rain_score = 100.0
        elif rainfall_cm >= 11.5:
            rain_alert = "ORANGE (Heavy 12-20 cm)"
            rain_score = 70.0
        elif rainfall_cm >= 6.5:
            rain_alert = "YELLOW (Moderate 7-11 cm)"
            rain_score = 40.0
        else:
            rain_alert = "GREEN (Isolated Rain)"
            rain_score = 15.0

        # 4. Composite Hazard Score [0 - 100]
        hazard_index = 0.45 * wind_score + 0.35 * surge_score + 0.20 * rain_score

        # 5. Exposure Score [0 - 100] based on Population Density
        pop_dens = district["population_density"]
        exposure_score = min(100.0, max(15.0, math.log10(pop_dens) * 32.0))

        # 6. Vulnerability Score [0 - 100] based on Inverted Elevation & low lying
        elev = district["elevation_m"]
        vulnerability_score = min(100.0, max(20.0, 100.0 - elev * 8.5))

        # 7. Composite Dynamic Risk Index:
        # Risk = 0.40 * Hazard + 0.35 * Exposure + 0.25 * Vulnerability
        composite_risk = (
            0.40 * hazard_index
            + 0.35 * exposure_score
            + 0.25 * vulnerability_score
        )
        composite_risk = round(min(100.0, max(0.0, composite_risk)), 1)

        # Risk Classification
        if composite_risk >= 75.0:
            risk_category = "CRITICAL"
            color_code = "#d9381e"  # Red
        elif composite_risk >= 55.0:
            risk_category = "HIGH"
            color_code = "#ff9500"  # Orange
        elif composite_risk >= 35.0:
            risk_category = "MEDIUM"
            color_code = "#ffcc00"  # Yellow
        else:
            risk_category = "LOW"
            color_code = "#34c759"  # Green

        return {
            "district": district["district"],
            "state": district["state"],
            "lat": district["lat"],
            "lon": district["lon"],
            "distance_to_storm_km": round(dist_km, 1),
            "local_wind_kt": local_wind_kt,
            "local_wind_kmh": local_wind_kmh,
            "wind_hazard": wind_hazard,
            "surge_height_m": surge_height_m,
            "surge_severity": surge_severity,
            "rainfall_cm_24h": rainfall_cm,
            "rainfall_alert": rain_alert,
            "hazard_index": round(hazard_index, 1),
            "exposure_score": round(exposure_score, 1),
            "vulnerability_score": round(vulnerability_score, 1),
            "composite_risk": composite_risk,
            "risk_category": risk_category,
            "color_code": color_code,
            "critical_infrastructure": district["critical_infrastructure"],
            "cyclone_shelters": district["cyclone_shelters"],
        }

    def evaluate_risk_swath(
        self,
        current_storm: BestTrackPoint,
        landfall_point: Optional[Dict[str, Any]] = None,
        max_assessment_radius_km: float = 650.0,
    ) -> List[Dict[str, Any]]:
        """Evaluate and rank coastal districts by risk score."""
        target_lat = current_storm.lat
        target_lon = current_storm.lon
        wind_kt = current_storm.max_sustained_wind_kt
        press = current_storm.central_pressure_hpa or 960.0

        # If landfall predicted, use landfall location for impact assessment
        if landfall_point and landfall_point.get("has_landfall"):
            target_lat = landfall_point["landfall_lat"]
            target_lon = landfall_point["landfall_lon"]
            wind_kt = landfall_point.get("intensity_at_landfall_kt", wind_kt)

        evaluations = []
        for dist in self.districts:
            d_km = haversine_distance_km(target_lat, target_lon, dist["lat"], dist["lon"])
            if d_km <= max_assessment_radius_km:
                eval_res = self.estimate_district_hazard(
                    district=dist,
                    storm_lat=target_lat,
                    storm_lon=target_lon,
                    storm_wind_kt=wind_kt,
                    central_pressure_hpa=press,
                )
                evaluations.append(eval_res)

        # Sort descending by composite risk score
        evaluations.sort(key=lambda x: x["composite_risk"], reverse=True)
        return evaluations
