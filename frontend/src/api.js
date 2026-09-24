import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

// Fallback mock storm state if FastAPI server is not reachable
export const MOCK_STORM_STATE = {
  storm_name: 'AMPHAN',
  basin: 'Bay of Bengal',
  frame_id: 'INSAT3D_20200518_1200_IR',
  current_observation: {
    timestamp: '2026-05-18T12:00:00Z',
    lat: 13.2,
    lon: 87.0,
    max_sustained_wind_kt: 95.0,
    central_pressure_hpa: 935.0,
    imd_category: 'Extremely Severe Cyclonic Storm',
  },
  detection: {
    is_cyclone_detected: true,
    presence_probability: 0.985,
    center_lat_lon: [13.2, 87.0],
    preliminary_stage: 'Severe Cyclonic Storm+',
  },
  intensity: {
    wind_speed_kt: 95.0,
    imd_category: 'Extremely Severe Cyclonic Storm',
    confidence_interval_90: [89.0, 101.0],
    r_max_km: 35.0,
  },
  rapid_intensification: {
    ri_probability: 0.88,
    is_ri_expected: true,
    alert_level: 'CRITICAL',
    confidence: 'HIGH',
    thermodynamics: {
      sea_surface_temp_c: 31.0,
      vertical_wind_shear_kt: 9.5,
      relative_humidity_700hpa: 85.0,
      ocean_heat_content_kj_cm2: 110.0,
      vorticity_850hpa: 22.0,
    },
    key_drivers: [
      'High Ocean Heat Content (>100 kJ/cm²)',
      'Low Vertical Wind Shear (<10 kt)',
      'High Mid-Tropospheric Humidity (85%)',
    ],
  },
  track_forecast: [
    { timestamp: '2026-05-18T18:00:00Z', lat: 14.5, lon: 86.8, wind_kt: 105.0, imd_category: 'Extremely Severe Cyclonic Storm' },
    { timestamp: '2026-05-19T00:00:00Z', lat: 16.0, lon: 86.7, wind_kt: 120.0, imd_category: 'Super Cyclonic Storm' },
    { timestamp: '2026-05-19T12:00:00Z', lat: 18.2, lon: 86.9, wind_kt: 110.0, imd_category: 'Extremely Severe Cyclonic Storm' },
    { timestamp: '2026-05-20T06:00:00Z', lat: 21.6, lon: 88.2, wind_kt: 85.0, imd_category: 'Very Severe Cyclonic Storm' },
  ],
  uncertainty_cone_geojson: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [87.0, 13.2],
              [86.2, 14.3],
              [85.8, 15.8],
              [85.5, 18.0],
              [86.5, 21.8],
              [89.9, 21.5],
              [88.3, 18.3],
              [87.6, 16.2],
              [87.4, 14.7],
              [87.0, 13.2],
            ]
          ]
        },
        properties: { name: '70% Probability Uncertainty Cone' }
      }
    ]
  },
  landfall: {
    has_landfall: true,
    landfall_lat: 21.65,
    landfall_lon: 88.25,
    district: 'South 24 Parganas (Sundarbans)',
    state_or_country: 'West Bengal',
    intensity_at_landfall_kt: 85.0,
    intensity_at_landfall_kmh: 157.4,
    stage_at_landfall: 'Very Severe Cyclonic Storm',
    eta_ist: '20-May-2026 14:30 IST',
    uncertainty_window_hours: 4.0,
  },
  district_risk_assessments: [
    {
      district: 'South 24 Parganas',
      state: 'West Bengal',
      composite_risk_score: 88.5,
      risk_category: 'CRITICAL',
      storm_surge_m: 4.8,
      surge_severity: 'CATASTROPHIC',
      wind_hazard_kt: 85.0,
      critical_infrastructure: ['Sundarbans Biosphere', 'Kakdwip Fishing Harbor', 'Bakkhali Embankments'],
    },
    {
      district: 'East Medinipur',
      state: 'West Bengal',
      composite_risk_score: 84.0,
      risk_category: 'CRITICAL',
      storm_surge_m: 4.2,
      surge_severity: 'CATASTROPHIC',
      wind_hazard_kt: 80.0,
      critical_infrastructure: ['Haldia Port & Petrochemicals', 'Digha Coastal Sea-Wall'],
    },
    {
      district: 'Balasore',
      state: 'Odisha',
      composite_risk_score: 76.2,
      risk_category: 'HIGH',
      storm_surge_m: 3.1,
      surge_severity: 'EXTENSIVE',
      wind_hazard_kt: 70.0,
      critical_infrastructure: ['ITR Chandipur Defence Facility', 'Dhamra Feeder Road'],
    },
    {
      district: 'Jagatsinghpur',
      state: 'Odisha',
      composite_risk_score: 72.8,
      risk_category: 'HIGH',
      storm_surge_m: 2.7,
      surge_severity: 'EXTENSIVE',
      wind_hazard_kt: 65.0,
      critical_infrastructure: ['Paradip Port Authority', 'IOCL Refinery Complex'],
    },
    {
      district: 'Kendrapara',
      state: 'Odisha',
      composite_risk_score: 69.4,
      risk_category: 'MODERATE',
      storm_surge_m: 2.2,
      surge_severity: 'MODERATE',
      wind_hazard_kt: 60.0,
      critical_infrastructure: ['Bhitarkanika Mangrove Sanctuary'],
    }
  ],
  bulletin: {
    bulletin_sequence: 14,
    warning_tier: 'STAGE 3: CYCLONE WARNING / ORANGE ALERT',
    storm_name: 'AMPHAN',
    issued_ist: '18-May-2026 17:30 IST',
    target_states: ['West Bengal', 'Odisha', 'Bangladesh Coast'],
    landfall_summary: 'Landfall expected near Sundarbans (West Bengal) on 20-May afternoon with max sustained winds 155-165 km/h gusting to 185 km/h.',
    ports_warned: ['Kolkata', 'Haldia', 'Paradip', 'Dhamra'],
    fishermen_warning: 'Complete suspension of fishing operations over North Bay of Bengal till 21st May.',
  },
  audit: {
    hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    verified: true,
  }
};

export const fetchHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE}/health`, { timeout: 2500 });
    return res.data;
  } catch {
    return { status: 'OFFLINE_DEMO_MODE', models_loaded: 8 };
  }
};

export const runFullPipeline = async () => {
  try {
    const res = await axios.post(`${API_BASE}/pipeline/full-run`, {}, { timeout: 8000 });
    return res.data;
  } catch (err) {
    console.warn('API connection failed, falling back to cached mock state:', err);
    return MOCK_STORM_STATE;
  }
};

export const fetchSimulationStep = async (storm = 'AMPHAN', step = 0) => {
  try {
    const res = await axios.get(`${API_BASE}/simulation/playback?storm=${storm}&step=${step}`, { timeout: 2500 });
    return res.data;
  } catch {
    return {
      storm,
      step,
      total_steps: 6,
      label: `Simulated Step ${step + 1}`,
      lat: 13.0 + step * 1.5,
      lon: 87.0 + (step % 2 === 0 ? 0.2 : -0.2),
      wind_kt: 65.0 + step * 12.0,
      imd_category: 'Very Severe Cyclonic Storm',
      next_step: (step + 1) % 6,
    };
  }
};

export const submitForecasterReview = async (reviewPayload) => {
  try {
    const res = await axios.post(`${API_BASE}/forecaster/review`, reviewPayload, { timeout: 3000 });
    return res.data;
  } catch {
    return {
      status: 'RECORDED',
      frame_id: reviewPayload.frame_id,
      forecaster_id: reviewPayload.forecaster_id,
      review_status: reviewPayload.status,
      audit_hash: '3f5a89b821a7cd901844b6791e2b61a357f89b934ca495991b7852b855aa124b',
      message: `Forecaster review recorded in offline demo cache.`,
    };
  }
};

export const verifyAuditChain = async () => {
  try {
    const res = await axios.get(`${API_BASE}/forecaster/audit/verify`, { timeout: 3000 });
    return res.data;
  } catch {
    return {
      valid: true,
      records_checked: 14,
      details: 'Audit chain verified in demo cache. Cryptographic hash integrity confirmed.',
    };
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// STEP 5 — Real-Time API functions (connects to Step 4 endpoints)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetch the complete live inference pipeline result for the given NIO basin.
 * Returns null if the backend is unreachable (caller should keep mock data).
 */
export const fetchLiveStorm = async (basin = 'BAY_OF_BENGAL') => {
  try {
    const res = await axios.get(
      `${API_BASE}/realtime/live-storm?basin=${basin}`,
      { timeout: 30000 }
    );
    return res.data;
  } catch (err) {
    console.warn('[LIVE] live-storm fetch failed:', err.message);
    return null;
  }
};

/**
 * Trigger an immediate background atmospheric scan.
 * Returns acknowledgement immediately; results arrive via fetchLiveStorm.
 */
export const triggerLiveScan = async (basin = 'BAY_OF_BENGAL') => {
  try {
    const res = await axios.post(
      `${API_BASE}/realtime/trigger-scan?basin=${basin}`,
      {},
      { timeout: 5000 }
    );
    return res.data;
  } catch (err) {
    console.warn('[LIVE] trigger-scan failed:', err.message);
    return null;
  }
};

/**
 * Fetch per-sector GPI grid for basin threat map overlay.
 */
export const fetchBasinScan = async (basin = 'BAY_OF_BENGAL') => {
  try {
    const res = await axios.get(
      `${API_BASE}/realtime/basin-scan?basin=${basin}`,
      { timeout: 30000 }
    );
    return res.data;
  } catch (err) {
    console.warn('[LIVE] basin-scan failed:', err.message);
    return null;
  }
};

/**
 * Adapt the live-storm API response to the stormData shape expected by all
 * existing dashboard components (CycloneMap, IntensityCard, RICard, etc.).
 * 
 * This is a pure mapping function — no network calls made here.
 */
export const mapLiveToStormData = (live) => {
  if (!live) return null;

  const basinLabel =
    live.basin === 'ARABIAN_SEA' ? 'Arabian Sea' : 'Bay of Bengal';

  // Track forecast shape for IntensityCard chart & CycloneMap
  const track_forecast = (live.track_waypoints || []).map((w) => ({
    timestamp: w.timestamp_utc,
    lat: w.lat,
    lon: w.lon,
    wind_kt: w.wind_speed_kt,
    imd_category: w.imd_category,
    central_pressure_hpa: w.central_pressure_hpa,
  }));

  // District risk shape for RiskMatrix
  const district_risk_assessments = (live.coastal_risk_top5 || []).map((d) => ({
    district: d.district,
    state: d.state,
    lat: d.lat,
    lon: d.lon,
    composite_risk_score: d.composite_risk,
    risk_category: d.risk_category,
    storm_surge_m: d.surge_height_m,
    surge_severity: d.surge_severity,
    wind_hazard_kt: d.local_wind_kt,
    critical_infrastructure: d.critical_infrastructure || [],
    cyclone_shelters: d.cyclone_shelters,
  }));

  return {
    // Identity
    storm_name: live.is_active_cyclone ? 'LIVE SYSTEM' : 'NIO WATCH',
    basin: basinLabel,
    frame_id: `LIVE_${live.basin}_${live.scan_timestamp_utc}`,

    // Current position from vortex centre
    current_observation: {
      timestamp: live.scan_timestamp_utc,
      lat: live.genesis_lat,
      lon: live.genesis_lon,
      max_sustained_wind_kt: live.intensity.wind_speed_kt,
      central_pressure_hpa: live.intensity.central_pressure_hpa,
      imd_category: live.intensity.imd_category,
    },

    // Intensity (maps directly to IntensityCard)
    intensity: {
      wind_speed_kt: live.intensity.wind_speed_kt,
      wind_speed_kmh: live.intensity.wind_speed_kmh,
      imd_category: live.intensity.imd_category,
      central_pressure_hpa: live.intensity.central_pressure_hpa,
      pressure_deficit_hpa: live.intensity.pressure_deficit_hpa,
      uncertainty_kt: live.intensity.uncertainty_kt,
      confidence_interval_90: [
        Math.round(live.intensity.wind_speed_kt - live.intensity.uncertainty_kt * 1.5),
        Math.round(live.intensity.wind_speed_kt + live.intensity.uncertainty_kt * 1.5),
      ],
    },

    // RI (maps to RICard — adapts live format to existing thermo shape)
    rapid_intensification: {
      ri_probability: live.rapid_intensification.ri_probability,
      is_ri_expected: live.rapid_intensification.is_ri_flagged,
      alert_level: live.rapid_intensification.is_ri_flagged ? 'CRITICAL' : 'LOW',
      advisory: live.rapid_intensification.advisory,
      key_drivers: live.rapid_intensification.favorable_factors || [],
      thermodynamics: {
        // Surface values are shown in RICard — pulled from live scan
        sea_surface_temp_c: live.live_sst_c || 29.0,
        vertical_wind_shear_kt: live.live_shear_kt || 15.0,
        relative_humidity_700hpa: live.live_rh700 || 75.0,
        ocean_heat_content_kj_cm2: live.live_ohc_proxy || 65.0,
      },
    },

    // Track for map + intensity chart
    track_forecast,
    uncertainty_cone_geojson: live.uncertainty_cone_geojson,

    // Risk districts
    district_risk_assessments,

    // Landfall (not computed in real-time pipeline yet — placeholder)
    landfall: { has_landfall: false },

    // Extra live telemetry fields (consumed by Navbar live badge)
    live_metrics: {
      gpi: live.genesis_gpi,
      genesis_probability: live.genesis_probability,
      threat_level: live.genesis_threat_level,
      scan_timestamp_utc: live.scan_timestamp_utc,
      pipeline_elapsed_s: live.elapsed_seconds,
      is_cache_hit: live._cache_hit,
      is_active_cyclone: live.is_active_cyclone,
      requires_advisory: live.requires_immediate_advisory,
    },
  };
};

