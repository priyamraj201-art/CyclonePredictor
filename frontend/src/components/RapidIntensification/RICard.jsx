import React from 'react';
import { Zap, Thermometer, CloudRain, Droplets, Flame } from 'lucide-react';

export default function RICard({ ri }) {
  const prob = ri?.ri_probability !== undefined ? ri.ri_probability : 0.75;
  const pct  = Math.round(prob * 100);
  const isHigh = pct >= 50;
  const thermo = ri?.thermodynamics || {
    sea_surface_temp_c:           30.5,
    vertical_wind_shear_kt:       10.2,
    relative_humidity_700hpa:     82.0,
    ocean_heat_content_kj_cm2:    95.0,
  };

  // Pick ring colour from the health gradient
  const ringColor   = isHigh ? '#FF6B4A' : '#FFD043';
  const ringTrack   = 'rgba(0,0,0,0.07)';

  return (
    <div className="card card-hover" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="icon-badge" style={{
            background: isHigh ? 'rgba(226,90,56,0.10)' : 'rgba(255,208,67,0.12)',
            borderColor: isHigh ? 'rgba(226,90,56,0.28)' : 'rgba(255,208,67,0.35)',
          }}>
            <Zap size={16} color={isHigh ? '#A82B0A' : '#8A6500'} />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Rapid Intensification (24h)
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
              Physics-Informed XGBoost Model
            </div>
          </div>
        </div>
        <span className={`badge ${isHigh ? 'badge-critical' : 'badge-yellow'}`}>
          {isHigh ? 'High Probability' : 'Low Probability'}
        </span>
      </div>

      {/* Gauge + Narrative */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {/* Conic ring — organic style */}
        <div style={{
          width: '76px', height: '76px', borderRadius: '50%', flexShrink: 0,
          background: `conic-gradient(${ringColor} ${pct * 3.6}deg, ${ringTrack} 0deg)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: isHigh
            ? '0 0 0 3px rgba(226,90,56,0.12), 0 6px 18px rgba(226,90,56,0.18)'
            : '0 0 0 3px rgba(255,208,67,0.14), 0 6px 18px rgba(255,208,67,0.15)',
          animation: isHigh ? 'breathing 3s ease-in-out infinite' : 'none',
        }}>
          <div style={{
            width: '58px', height: '58px', borderRadius: '50%',
            background: '#FFFFFF',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)',
          }}>
            <span className="value-medium" style={{ fontSize: '20px', color: isHigh ? '#A82B0A' : '#8A6500' }}>
              {pct}%
            </span>
            <span style={{ fontSize: '8px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.03em' }}>
              P(ΔV≥30kt)
            </span>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: '12px', color: 'var(--text-secondary)',
            lineHeight: '1.5', marginBottom: '10px',
          }}>
            {ri?.advisory ||
              (isHigh
                ? 'Oceanic heat and low atmospheric shear create prime conditions for explosive cyclogenesis.'
                : 'Atmospheric shear and dry air intrusion actively suppress rapid intensification.')}
          </div>
          {/* Progress bar */}
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${pct}%`,
                background: isHigh
                  ? 'linear-gradient(90deg, #FF6B4A, #FFB834)'
                  : 'linear-gradient(90deg, #FFD043, #FFB834)',
              }}
            />
          </div>
        </div>
      </div>

      {/* Environmental Diagnostic Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {[
          {
            label: 'Sea Surface Temp',
            value: `${thermo.sea_surface_temp_c.toFixed(1)} °C`,
            icon: <Thermometer size={14} color="#FF7E67" />,
            bg: 'rgba(255,126,103,0.07)',
            border: 'rgba(255,126,103,0.18)',
          },
          {
            label: 'Vertical Wind Shear',
            value: `${thermo.vertical_wind_shear_kt.toFixed(1)} kt`,
            icon: <CloudRain size={14} color="#8A6500" />,
            bg: 'rgba(255,208,67,0.07)',
            border: 'rgba(255,208,67,0.20)',
          },
          {
            label: 'Mid-Trop Humidity',
            value: `${thermo.relative_humidity_700hpa.toFixed(0)}%`,
            icon: <Droplets size={14} color="#4CAF7D" />,
            bg: 'rgba(76,175,125,0.07)',
            border: 'rgba(76,175,125,0.18)',
          },
          {
            label: 'Ocean Heat Content',
            value: `${thermo.ocean_heat_content_kj_cm2.toFixed(0)} kJ/cm²`,
            icon: <Flame size={14} color="#E25A38" />,
            bg: 'rgba(226,90,56,0.07)',
            border: 'rgba(226,90,56,0.18)',
          },
        ].map(({ label, value, icon, bg, border }) => (
          <div key={label} style={{
            background: bg, padding: '10px 14px',
            borderRadius: 'var(--radius-item)',
            border: `1px solid ${border}`,
          }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {label}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
              {icon}
              <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>
                {value}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
