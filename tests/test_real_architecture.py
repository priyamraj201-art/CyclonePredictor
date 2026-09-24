"""Unit and Integration Tests for Real-World Architecture Components.

Tests:
1. Radiometric calibration (Planck's inversion & LUT).
2. Spatial reprojection and basin crop.
3. Real-world ingestion manager (IBTrACS parsing, official storm catalogs).
4. OASIS Common Alerting Protocol (CAP v1.2 XML) generation.
5. Database engine observation persistence.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import numpy as np
import pytest

from src.core.database import DatabaseEngine
from src.core.schemas import BestTrackPoint
from src.data.calibration import RadiometricCalibrator, SpatialReprojector
from src.data.ingestion_real import RealDataIngestionManager, OFFICIAL_NIO_STORMS
from src.risk.cap_generator import generate_cap_xml, generate_wmo_tca


def test_radiometric_calibration_planck():
    """Verify Planck inversion produces physically valid Kelvin temperatures."""
    calibrator = RadiometricCalibrator()
    # Test synthetic radiance
    radiance = np.array([[10.0, 50.0], [100.0, 150.0]], dtype=np.float32)
    tb = calibrator.planck_inversion(radiance, 10.8e-6)
    assert tb.shape == (2, 2)
    assert np.all(tb >= 150.0)
    assert np.all(tb <= 340.0)


def test_radiometric_calibration_counts_to_albedo():
    """Verify visible channel counts convert to [0.0, 1.0] albedo."""
    calibrator = RadiometricCalibrator()
    counts = np.array([0, 512, 1023], dtype=np.float32)
    albedo = calibrator.counts_to_albedo(counts, max_count=1023.0)
    assert np.isclose(albedo[0], 0.0)
    assert np.isclose(albedo[2], 1.0)


def test_spatial_reprojection():
    """Verify geostationary to lat/lon coordinate conversion."""
    reprojector = SpatialReprojector(sub_satellite_lon=82.0)
    scan_x = np.array([0.0, 0.05])
    scan_y = np.array([0.0, 0.05])
    lats, lons = reprojector.geostationary_to_latlon(scan_x, scan_y)
    assert len(lats) == 2
    assert np.all(lons >= 70.0) and np.all(lons <= 95.0)


def test_real_data_ingestion_official_storms():
    """Verify official NIO storm trajectories (FANI, AMPHAN, BIPARJOY) are loaded correctly."""
    manager = RealDataIngestionManager()
    fani = manager.load_official_storm_trajectory("FANI")
    assert fani["name"] == "FANI"
    assert fani["max_wind_kt"] == 115.0
    assert len(fani["track"]) >= 6

    amphan = manager.load_official_storm_trajectory("AMPHAN")
    assert amphan["peak_category"] == "Super Cyclonic Storm"


def test_ibtracs_csv_parsing():
    """Verify parsing of NOAA IBTrACS CSV data."""
    manager = RealDataIngestionManager()
    csv_sample = (
        "SID,NAME,ISO_TIME,LAT,LON,WMO_WIND,WMO_PRES\n"
        "2019116N03086,FANI,2019-04-26 06:00:00,5.2,88.5,25,1004\n"
        "2019116N03086,FANI,2019-04-27 06:00:00,7.1,87.8,35,998\n"
    )
    records = manager.parse_ibtracs_csv(csv_sample)
    assert len(records) == 2
    assert records[0]["storm_name"] == "FANI"
    assert records[0]["lat"] == 5.2
    assert records[1]["wind_kt"] == 35.0


def test_cap_xml_generation():
    """Verify OASIS CAP v1.2 XML document is well-formed and adheres to the standard."""
    current_obs = BestTrackPoint(
        timestamp=datetime.now(timezone.utc),
        lat=19.8,
        lon=85.8,
        max_sustained_wind_kt=105.0,
        central_pressure_hpa=940.0,
    )
    xml_str = generate_cap_xml(
        storm_name="FANI",
        current_obs=current_obs,
        landfall_info={"has_landfall": True, "district": "Puri", "state_or_country": "Odisha", "eta_ist": "03-May-2019 08:00 IST"},
        affected_districts=[{"district_name": "Puri", "state_name": "Odisha"}],
        bulletin_seq=12,
    )
    assert "urn:oasis:names:tc:emergency:cap:1.2" in xml_str
    root = ET.fromstring(xml_str)
    assert root.tag.endswith("alert")
    info = root.find("{urn:oasis:names:tc:emergency:cap:1.2}info")
    assert info is not None
    assert "FANI" in info.find("{urn:oasis:names:tc:emergency:cap:1.2}event").text


def test_wmo_tca_generation():
    """Verify WMO Tropical Cyclone Advisory formatting."""
    current_obs = BestTrackPoint(
        timestamp=datetime.now(timezone.utc),
        lat=17.5,
        lon=85.0,
        max_sustained_wind_kt=90.0,
        central_pressure_hpa=960.0,
    )
    tca = generate_wmo_tca("FANI", current_obs, [])
    assert "TC ADVISORY" in tca
    assert "TCAC: NEW DELHI" in tca
    assert "TC: FANI" in tca


def test_database_engine_insert_and_query():
    """Verify operational database insert and query."""
    db = DatabaseEngine()
    rec = db.insert_observation(
        storm_id="STORM_TEST_001",
        timestamp=datetime.now(timezone.utc),
        lat=15.2,
        lon=88.4,
        wind_kt=65.0,
        pressure_hpa=982.0,
        category="Severe Cyclonic Storm",
    )
    assert rec["storm_id"] == "STORM_TEST_001"
    history = db.query_storm_history("STORM_TEST_001")
    assert len(history) >= 1
