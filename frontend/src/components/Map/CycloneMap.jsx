import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Polygon, CircleMarker, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix standard Leaflet default icon issues in bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Mint Fintech storm center reticle icon
const stormIcon = L.divIcon({
  className: 'custom-storm-marker',
  html: `
    <div style="position: relative; width: 26px; height: 26px;">
      <div style="position: absolute; width: 26px; height: 26px; border-radius: 50%; background: rgba(47,191,113,0.35); animation: pulse-ring-mint 1.8s infinite;"></div>
      <div style="position: absolute; top: 4px; left: 4px; width: 18px; height: 18px; border-radius: 50%; background: #0D0F12; border: 3px solid #2FBF71; box-shadow: 0 2px 8px rgba(0,0,0,0.15);"></div>
    </div>
  `,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

// Mint Fintech solid black pill landfall marker
const landfallIcon = L.divIcon({
  className: 'custom-landfall-marker',
  html: `
    <div style="background: #0D0F12; color: #FFFFFF; font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 999px; box-shadow: 0 4px 12px rgba(13,15,18,0.25); white-space: nowrap; display: flex; align-items: center; gap: 4px;">
      <span style="width: 6px; height: 6px; border-radius: 50%; background: #F14C4C;"></span>
      PROJECTED LANDFALL
    </div>
  `,
  iconSize: [140, 22],
  iconAnchor: [70, 11],
});

function RecenterMap({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.panTo(center, { animate: true });
    }
  }, [center, map]);
  return null;
}

export default function CycloneMap({
  currentLatLon = [13.2, 87.0],
  trackPoints = [],
  coneGeoJson = null,
  landfall = null,
  districts = [],
}) {
  const center = [currentLatLon[0] || 13.2, currentLatLon[1] || 87.0];

  // Build track coordinates
  const polylineCoords = [
    center,
    ...trackPoints.map((pt) => [pt.lat, pt.lon]),
  ];

  // Extract coordinates for the cone polygon if present
  let coneCoords = [];
  if (
    coneGeoJson &&
    coneGeoJson.features &&
    coneGeoJson.features[0] &&
    coneGeoJson.features[0].geometry &&
    coneGeoJson.features[0].geometry.coordinates
  ) {
    const rawCoords = coneGeoJson.features[0].geometry.coordinates[0];
    coneCoords = rawCoords.map((c) => [c[1], c[0]]); // GeoJSON [lon, lat] -> Leaflet [lat, lon]
  }

  return (
    <div className="card" style={{ height: '100%', position: 'relative', overflow: 'hidden', minHeight: '380px' }}>
      {/* Floating Pill Legend Overlay */}
      <div style={{
        position: 'absolute', top: '12px', left: '14px', zIndex: 1000,
        background: 'rgba(255, 255, 255, 0.94)', backdropFilter: 'blur(12px)',
        padding: '6px 14px', borderRadius: 'var(--radius-pill)', border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-card)',
        fontSize: '11px', display: 'flex', gap: '14px', fontWeight: 500
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0D0F12', border: '2px solid #2FBF71' }} />
          <span style={{ color: 'var(--color-text-primary)' }}>Eye Center</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '12px', height: '3px', background: '#0D0F12', borderRadius: '2px' }} />
          <span style={{ color: 'var(--color-text-secondary)' }}>Bi-LSTM Track (+48h)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '12px', height: '10px', background: 'rgba(127, 224, 217, 0.35)', border: '1px dashed #14B8A6', borderRadius: '2px' }} />
          <span style={{ color: 'var(--color-text-secondary)' }}>70% Uncertainty Cone</span>
        </div>
      </div>

      <MapContainer
        center={center}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        attributionControl={false}
      >
        <RecenterMap center={center} />

        {/* Clean Light Gray Basemap (Free, No Watermark, No API Key Required) */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
        />
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
          opacity={0.85}
        />

        {/* Soft Aqua Uncertainty Cone Polygon */}
        {coneCoords.length > 2 && (
          <Polygon
            positions={coneCoords}
            pathOptions={{
              color: '#14B8A6',
              weight: 1.5,
              dashArray: '5, 5',
              fillColor: '#7FE0D9',
              fillOpacity: 0.28,
            }}
          />
        )}

        {/* Track Forecast Polyline (Near-black sleek trajectory) */}
        {polylineCoords.length > 1 && (
          <Polyline
            positions={polylineCoords}
            pathOptions={{
              color: '#0D0F12',
              weight: 3,
              opacity: 0.9,
            }}
          />
        )}

        {/* Forecast Waypoint Markers */}
        {trackPoints.map((pt, idx) => (
          <CircleMarker
            key={idx}
            center={[pt.lat, pt.lon]}
            radius={5}
            pathOptions={{
              color: '#0D0F12',
              fillColor: '#FFFFFF',
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Popup>
              <div style={{ fontSize: '11px', color: '#0D0F12', fontFamily: 'Inter, sans-serif' }}>
                <strong style={{ display: 'block', marginBottom: '2px' }}>Lead Time: +{(idx + 1) * 12}h</strong>
                Wind: <strong>{pt.wind_kt || pt.max_sustained_wind_kt} kt</strong><br />
                Category: {pt.imd_category || 'N/A'}<br />
                Coordinates: {pt.lat.toFixed(2)}°N, {pt.lon.toFixed(2)}°E
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Storm Center Marker */}
        <Marker position={center} icon={stormIcon}>
          <Popup>
            <div style={{ fontSize: '12px', color: '#0D0F12', fontFamily: 'Inter, sans-serif' }}>
              <strong>Cyclonic Circulation Center</strong><br />
              Latitude: {center[0].toFixed(2)}°N<br />
              Longitude: {center[1].toFixed(2)}°E<br />
            </div>
          </Popup>
        </Marker>

        {/* Landfall Marker */}
        {landfall && landfall.has_landfall && landfall.landfall_lat && (
          <Marker position={[landfall.landfall_lat, landfall.landfall_lon]} icon={landfallIcon}>
            <Popup>
              <div style={{ fontSize: '12px', color: '#0D0F12', fontFamily: 'Inter, sans-serif' }}>
                <strong style={{ color: '#0D0F12' }}>Target Landfall Crossing</strong><br />
                District: <strong>{landfall.district}, {landfall.state_or_country}</strong><br />
                ETA: <strong>{landfall.eta_ist}</strong><br />
                Intensity: {landfall.intensity_at_landfall_kmh} km/h ({landfall.intensity_at_landfall_kt} kt)<br />
                Uncertainty Window: ±{landfall.uncertainty_window_hours}h
              </div>
            </Popup>
          </Marker>
        )}

        {/* Coastal District Risk Markers */}
        {districts.map((d, i) => {
          const lat = d.lat || (21.5 - i * 0.45);
          const lon = d.lon || (87.8 + (i % 2 === 0 ? 0.4 : -0.3));
          const color = d.risk_category === 'CRITICAL' ? '#F14C4C' : d.risk_category === 'HIGH' ? '#EAA11F' : '#2FBF71';
          return (
            <CircleMarker
              key={i}
              center={[lat, lon]}
              radius={7}
              pathOptions={{
                color: '#FFFFFF',
                fillColor: color,
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Popup>
                <div style={{ fontSize: '11px', color: '#0D0F12', fontFamily: 'Inter, sans-serif' }}>
                  <strong>{d.district} ({d.state})</strong><br />
                  Composite Risk: <strong>{d.composite_risk_score}</strong> ({d.risk_category})<br />
                  Storm Surge: <strong>{d.storm_surge_m} m</strong><br />
                  Wind Hazard: {d.wind_hazard_kt} kt
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
