import React from 'react';
import { Zap, Thermometer, CloudRain, Droplets, Flame } from 'lucide-react';

export default function RICard({ ri }) {
  const prob = ri?.ri_probability !== undefined ? ri.ri_probability : 0.75;
  const pct = Math.round(prob * 100);
  const isHigh = pct >= 50;
  const thermo = ri?.thermodynamics || {
    sea_surface_temp_c: 30.5,
    vertical_wind_shear_kt: 10.2,
    relative_humidity_700hpa: 82.0,
    ocean_heat_content_kj_cm2: 95.0,
  };

  return (
    <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="icon-badge">
            <Zap size={15} color="#126338" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Rapid Intensification (24h)
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
              Physics-Informed XGBoost Model
            </div>
          </div>
        </div>
        <span className={`badge ${isHigh ? 'badge-critical' : 'badge-mint'}`}>
          {isHigh ? 'High Probability' : 'Low Probability'}
        </span>
      </div>

      {/* Main Gauge & Narrative */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Soft Conic Ring */}
        <div style={{
          width: '70px', height: '70px', borderRadius: '50%',
          background: `conic-gradient(#2FBF71 ${pct * 3.6}deg, #E7EAEC 0deg)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{
            width: '54px', height: '54px', borderRadius: '50%',
            background: '#FFFFFF',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
          }}>
            <span className="value-medium">{pct}%</span>
            <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 600 }}>P(ΔV≥30kt)</span>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginBottom: '6px', lineHeight: '1.4' }}>
            {isHigh
              ? 'Oceanic heat and low atmospheric shear create prime conditions for explosive cyclogenesis.'
              : 'Atmospheric shear and dry air intrusion actively suppress rapid intensification.'}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${pct}%`,
                background: isHigh ? 'linear-gradient(90deg, #2FBF71 0%, #7FE0D9 100%)' : '#A8F0C6'
              }}
            />
          </div>
        </div>
      </div>

      {/* 4 Environmental Diagnostic Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div style={{
          background: '#FAFBFC',
          padding: '8px 12px',
          borderRadius: '12px',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Sea Surface Temp
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            <Thermometer size={14} color="#14B8A6" />
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--color-text-primary)' }}>
              {thermo.sea_surface_temp_c.toFixed(1)} °C
            </span>
          </div>
        </div>

        <div style={{
          background: '#FAFBFC',
          padding: '8px 12px',
          borderRadius: '12px',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Vertical Wind Shear
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            <CloudRain size={14} color="#14B8A6" />
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--color-text-primary)' }}>
              {thermo.vertical_wind_shear_kt.toFixed(1)} kt
            </span>
          </div>
        </div>

        <div style={{
          background: '#FAFBFC',
          padding: '8px 12px',
          borderRadius: '12px',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Mid-Trop Humidity
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            <Droplets size={14} color="#2FBF71" />
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--color-text-primary)' }}>
              {thermo.relative_humidity_700hpa.toFixed(0)} %
            </span>
          </div>
        </div>

        <div style={{
          background: '#FAFBFC',
          padding: '8px 12px',
          borderRadius: '12px',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Ocean Heat Content
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            <Flame size={14} color="#2FBF71" />
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--color-text-primary)' }}>
              {thermo.ocean_heat_content_kj_cm2.toFixed(0)} kJ/cm²
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
