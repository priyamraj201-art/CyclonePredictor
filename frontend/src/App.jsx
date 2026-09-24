import React, { useState, useEffect, useRef, useCallback } from 'react';
import Navbar from './components/Navbar';
import SimulationBar from './components/SimulationControls/SimulationBar';
import CycloneMap from './components/Map/CycloneMap';
import IntensityCard from './components/Intensity/IntensityCard';
import RICard from './components/RapidIntensification/RICard';
import GradCAMViewer from './components/Explainability/GradCAMViewer';
import RiskMatrix from './components/RiskMatrix/RiskMatrix';
import BulletinViewer from './components/BulletinViewer/BulletinViewer';
import ForecasterReviewModal from './components/ForecasterReview/ForecasterReviewModal';
import {
  fetchHealth,
  runFullPipeline,
  fetchLiveStorm,
  triggerLiveScan,
  mapLiveToStormData,
  MOCK_STORM_STATE,
} from './api';

// Auto-refresh cadence for live mode (15 minutes)
const LIVE_REFRESH_INTERVAL_MS = 15 * 60 * 1000;

export default function App() {
  const [stormData, setStormData]         = useState(MOCK_STORM_STATE);
  const [backendStatus, setBackendStatus] = useState('CHECKING');
  const [loading, setLoading]             = useState(false);
  const [showBulletin, setShowBulletin]   = useState(false);
  const [showReview, setShowReview]       = useState(false);
  const [selectedStorm, setSelectedStorm] = useState('AMPHAN');

  // ── STEP 5: Live mode state ────────────────────────────────────────────
  const [liveMode, setLiveMode]           = useState(false);
  const [liveLoading, setLiveLoading]     = useState(false);
  const [lastLiveRefresh, setLastLiveRefresh] = useState(null);
  const [liveBasin, setLiveBasin]         = useState('BAY_OF_BENGAL');
  const [liveBanner, setLiveBanner]       = useState(null); // toast message
  const autoRefreshRef = useRef(null);

  // ── Health check on mount ─────────────────────────────────────────────
  useEffect(() => {
    const checkSystem = async () => {
      const health = await fetchHealth();
      setBackendStatus(health.status);
    };
    checkSystem();
  }, []);

  // ── Live data fetch ───────────────────────────────────────────────────
  const fetchLiveData = useCallback(async (basin = liveBasin, silent = false) => {
    if (!silent) setLiveLoading(true);
    try {
      const raw = await fetchLiveStorm(basin);
      if (raw) {
        const mapped = mapLiveToStormData(raw);
        if (mapped) {
          setStormData(mapped);
          setLastLiveRefresh(new Date().toISOString());
          if (!silent) {
            const cacheNote = raw._cache_hit ? ' (cached)' : ' (fresh scan)';
            setLiveBanner(`✅ Live data updated — GPI ${raw.genesis_gpi?.toFixed(2)} · ${raw.genesis_threat_level}${cacheNote}`);
            setTimeout(() => setLiveBanner(null), 5000);
          }
        }
      } else {
        if (!silent) {
          setLiveBanner('⚠️ Backend unreachable — showing last known data. Retrying in 15 min.');
          setTimeout(() => setLiveBanner(null), 6000);
        }
      }
    } catch (err) {
      console.error('[LIVE] fetchLiveData error:', err);
    } finally {
      if (!silent) setLiveLoading(false);
    }
  }, [liveBasin]);

  // ── Start / stop auto-refresh when liveMode changes ──────────────────
  useEffect(() => {
    if (autoRefreshRef.current) {
      clearInterval(autoRefreshRef.current);
      autoRefreshRef.current = null;
    }
    if (liveMode) {
      // Immediate first fetch
      fetchLiveData(liveBasin);
      // Then every 15 minutes silently
      autoRefreshRef.current = setInterval(() => {
        fetchLiveData(liveBasin, true);
      }, LIVE_REFRESH_INTERVAL_MS);
    }
    return () => {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    };
  }, [liveMode, liveBasin]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Toggle LIVE / HISTORICAL mode ────────────────────────────────────
  const handleToggleLive = async () => {
    if (liveMode) {
      // Return to historical / mock mode
      setLiveMode(false);
      setStormData(MOCK_STORM_STATE);
      setLastLiveRefresh(null);
      setLiveBanner('📡 Switched to Historical Simulation mode.');
      setTimeout(() => setLiveBanner(null), 4000);
    } else {
      // Trigger a background scan first for fresh data
      setLiveLoading(true);
      await triggerLiveScan(liveBasin);
      setLiveMode(true); // useEffect will fire fetchLiveData
    }
  };

  // ── Historical pipeline run ───────────────────────────────────────────
  const handleRunPipeline = async () => {
    setLoading(true);
    const result = await runFullPipeline();
    setStormData((prev) => ({
      ...prev,
      storm_name: selectedStorm,
      current_observation: {
        ...prev.current_observation,
        lat: result.detection?.center_lat_lon?.[0] || prev.current_observation.lat,
        lon: result.detection?.center_lat_lon?.[1] || prev.current_observation.lon,
        max_sustained_wind_kt: result.intensity?.wind_speed_kt || prev.current_observation.max_sustained_wind_kt,
        central_pressure_hpa: result.intensity?.central_pressure_hpa || prev.current_observation.central_pressure_hpa,
        imd_category: result.intensity?.imd_category || prev.current_observation.imd_category,
      },
      intensity: result.intensity || prev.intensity,
      rapid_intensification: result.rapid_intensification || prev.rapid_intensification,
      track_forecast: result.track_forecast || prev.track_forecast,
      landfall: result.landfall || prev.landfall,
      district_risk_assessments: result.top_risk_districts || prev.district_risk_assessments,
      bulletin: result.bulletin_summary || prev.bulletin,
    }));
    setLoading(false);
  };

  // ── Simulation step (historic storms) ────────────────────────────────
  const handleSimulationStep = (sim) => {
    setStormData((prev) => ({
      ...prev,
      storm_name: sim.storm,
      current_observation: {
        ...prev.current_observation,
        lat: sim.lat,
        lon: sim.lon,
        max_sustained_wind_kt: sim.wind_kt,
        imd_category: sim.imd_category,
      },
      intensity: {
        ...prev.intensity,
        wind_speed_kt: sim.wind_kt,
        imd_category: sim.imd_category,
      },
    }));
  };

  const currentLat = stormData.current_observation?.lat || 13.2;
  const currentLon = stormData.current_observation?.lon || 87.0;
  const liveMetrics = stormData.live_metrics || null;

  return (
    <div className="app-container">

      {/* ── Toast banner ───────────────────────────────────────────────── */}
      {liveBanner && (
        <div style={{
          position: 'fixed', top: '14px', left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9999,
          background: liveBanner.startsWith('⚠️')
            ? 'rgba(226, 90, 56, 0.92)'
            : 'rgba(30, 31, 34, 0.92)',
          color: '#FFFFFF',
          fontSize: '12px', fontWeight: 600,
          padding: '9px 22px',
          borderRadius: '999px',
          boxShadow: '0 8px 28px rgba(30,31,34,0.20)',
          backdropFilter: 'blur(16px)',
          letterSpacing: '0.02em',
          pointerEvents: 'none',
          animation: 'fadeInDown 0.3s ease',
          whiteSpace: 'nowrap',
          border: '1px solid rgba(255,255,255,0.15)',
        }}>
          {liveBanner}
        </div>
      )}

      {/* ── Top Navigation ─────────────────────────────────────────────── */}
      <Navbar
        stormName={stormData.storm_name}
        basin={stormData.basin}
        category={stormData.intensity?.imd_category || stormData.current_observation?.imd_category}
        isRI={stormData.rapid_intensification?.is_ri_expected}
        backendStatus={backendStatus}
        onRefresh={handleRunPipeline}
        onOpenReview={() => setShowReview(true)}
        onOpenBulletin={() => setShowBulletin(true)}
        loading={loading}
        // STEP 5 live props
        liveMode={liveMode}
        onToggleLive={handleToggleLive}
        liveMetrics={liveMetrics}
        liveLoading={liveLoading}
        lastLiveRefresh={lastLiveRefresh}
      />

      {/* ── Live Telemetry Status Bar (visible in live mode only) ─────── */}
      {liveMode && (
        <div style={{
          margin: '0 14px 6px 14px',
          padding: '8px 20px',
          background: 'rgba(255, 255, 255, 0.70)',
          backdropFilter: 'blur(12px)',
          border: liveMetrics
            ? '1px solid rgba(226, 90, 56, 0.20)'
            : '1px solid rgba(255, 208, 67, 0.25)',
          borderRadius: '999px',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          fontSize: '11px',
          color: 'var(--text-secondary)',
          flexWrap: 'wrap',
        }}>
          {/* Live dot + label */}
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: 'var(--text-primary)' }}>
            <span style={{
              width: '7px', height: '7px', borderRadius: '50%',
              background: liveLoading ? 'var(--yellow-base)' : 'var(--danger)',
              display: 'inline-block',
              boxShadow: liveLoading ? '0 0 6px var(--yellow-base)' : '0 0 6px var(--danger)',
              animation: 'pulse-live 1.2s infinite',
            }} />
            OPEN-METEO LIVE
          </span>

          {liveMetrics ? (
            <>
              <span>
                📡 <strong>Vortex:</strong>{' '}
                {stormData.current_observation?.lat?.toFixed(2)}°N,{' '}
                {stormData.current_observation?.lon?.toFixed(2)}°E
              </span>
              <span>
                🌡 <strong>GPI:</strong> {liveMetrics.gpi?.toFixed(3)}
              </span>
              <span>
                🎯 <strong>P(genesis):</strong> {(liveMetrics.genesis_probability * 100)?.toFixed(1)}%
              </span>
              <span style={{
                fontWeight: 700,
                color: liveMetrics.threat_level === 'EXTREME' ? 'var(--danger)'
                  : liveMetrics.threat_level === 'HIGH' ? '#8A5500' : '#1B6B40',
              }}>
                ⚠ {liveMetrics.threat_level}
              </span>
              <span>💨 {stormData.intensity?.wind_speed_kt} kt</span>
              <span>📉 {stormData.intensity?.central_pressure_hpa} hPa</span>
              {liveMetrics.requires_advisory && (
                <span style={{
                  fontWeight: 700, color: 'var(--danger)',
                  padding: '2px 12px', borderRadius: '999px',
                  background: 'rgba(226,90,56,0.09)',
                  border: '1px solid rgba(226,90,56,0.22)',
                }}>
                  ⚡ IMMEDIATE ADVISORY
                </span>
              )}
              <span style={{ marginLeft: 'auto', fontSize: '10px', color: 'var(--text-muted)' }}>
                AUTO-REFRESH 15min · {lastLiveRefresh
                  ? `LAST: ${new Date(lastLiveRefresh).toISOString().slice(11, 19)} UTC`
                  : 'SCANNING…'}
              </span>
            </>
          ) : (
            <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
              {liveLoading ? 'Scanning NIO basin for active disturbances…' : 'Awaiting live telemetry…'}
            </span>
          )}
        </div>
      )}

      {/* ── Historic Storm Simulation Bar (hidden in live mode) ─────────── */}
      {!liveMode && (
        <SimulationBar
          currentStorm={selectedStorm}
          onStormSelect={setSelectedStorm}
          onStepChange={handleSimulationStep}
        />
      )}

      {/* ── Main Dashboard Layout ─────────────────────────────────────── */}
      <main style={{
        flex: 1,
        padding: '0 14px 14px 14px',
        display: 'grid',
        gridTemplateColumns: '1.65fr 1fr',
        gap: '14px',
        minHeight: 0,
        overflow: 'hidden'
      }}>
        {/* Left Column: Map & Coastal Risk */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', minHeight: 0 }}>
          <div style={{ flex: '1.4', minHeight: 0 }}>
            <CycloneMap
              currentLatLon={[currentLat, currentLon]}
              trackPoints={stormData.track_forecast || []}
              coneGeoJson={stormData.uncertainty_cone_geojson}
              landfall={stormData.landfall}
              districts={stormData.district_risk_assessments || []}
            />
          </div>

          <div style={{ flex: '1', minHeight: 0, overflowY: 'auto' }}>
            <RiskMatrix districts={stormData.district_risk_assessments || []} />
          </div>
        </section>

        {/* Right Column: AI Model Diagnostics */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', overflowY: 'auto', paddingRight: '2px' }}>
          <IntensityCard
            intensity={stormData.intensity}
            trackForecast={stormData.track_forecast}
          />

          <RICard ri={stormData.rapid_intensification} />

          <GradCAMViewer />
        </section>
      </main>

      {/* ── Modals ─────────────────────────────────────────────────────── */}
      {showBulletin && (
        <BulletinViewer
          bulletin={stormData.bulletin}
          onClose={() => setShowBulletin(false)}
        />
      )}

      {showReview && (
        <ForecasterReviewModal
          frameId={stormData.frame_id}
          currentWindKt={stormData.intensity?.wind_speed_kt}
          onClose={() => setShowReview(false)}
          onReviewComplete={(res) => {
            console.log('Forecaster sign-off recorded:', res);
          }}
        />
      )}

      {/* Animations */}
      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0);     }
        }
      `}</style>
    </div>
  );
}
