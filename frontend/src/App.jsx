import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SimulationBar from './components/SimulationControls/SimulationBar';
import CycloneMap from './components/Map/CycloneMap';
import IntensityCard from './components/Intensity/IntensityCard';
import RICard from './components/RapidIntensification/RICard';
import GradCAMViewer from './components/Explainability/GradCAMViewer';
import RiskMatrix from './components/RiskMatrix/RiskMatrix';
import BulletinViewer from './components/BulletinViewer/BulletinViewer';
import ForecasterReviewModal from './components/ForecasterReview/ForecasterReviewModal';
import { fetchHealth, runFullPipeline, MOCK_STORM_STATE } from './api';

export default function App() {
  const [stormData, setStormData] = useState(MOCK_STORM_STATE);
  const [backendStatus, setBackendStatus] = useState('CHECKING');
  const [loading, setLoading] = useState(false);
  const [showBulletin, setShowBulletin] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [selectedStorm, setSelectedStorm] = useState('AMPHAN');

  // Check health on mount
  useEffect(() => {
    const checkSystem = async () => {
      const health = await fetchHealth();
      setBackendStatus(health.status);
    };
    checkSystem();
  }, []);

  const handleRunPipeline = async () => {
    setLoading(true);
    const result = await runFullPipeline();
    // Merge result with default mock structure if partial
    setStormData((prev) => ({
      ...prev,
      storm_name: selectedStorm,
      current_observation: {
        ...prev.current_observation,
        lat: result.detection?.center_lat_lon?.[0] || result.current_observation?.lat || prev.current_observation.lat,
        lon: result.detection?.center_lat_lon?.[1] || result.current_observation?.lon || prev.current_observation.lon,
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

  return (
    <div className="app-container">
      {/* Top Navigation */}
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
      />

      {/* Historic Storm Simulation Bar */}
      <SimulationBar
        currentStorm={selectedStorm}
        onStormSelect={setSelectedStorm}
        onStepChange={handleSimulationStep}
      />

      {/* Main Dashboard Layout */}
      <main style={{
        flex: 1,
        padding: '0 14px 14px 14px',
        display: 'grid',
        gridTemplateColumns: '1.75fr 1fr',
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

      {/* Modals */}
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
    </div>
  );
}
