import React from 'react';
import { Wind, Activity } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

export default function IntensityCard({ intensity, trackForecast = [] }) {
  const windKt = intensity?.wind_speed_kt || 85.0;
  const windKmh = Math.round(windKt * 1.852);
  const pressureHpa = intensity?.central_pressure_hpa || 945.0;
  const ciLower = intensity?.confidence_interval_90?.[0] || Math.round(windKt - 6);
  const ciUpper = intensity?.confidence_interval_90?.[1] || Math.round(windKt + 6);
  const rMax = intensity?.r_max_km || 35.0;

  // Build trend chart data
  const chartData = [
    { time: '-12h', wind: Math.max(35, windKt - 20) },
    { time: '-6h', wind: Math.max(45, windKt - 10) },
    { time: 'Now', wind: windKt },
    ...trackForecast.map((pt, i) => ({
      time: `+${(i + 1) * 12}h`,
      wind: pt.wind_kt || pt.max_sustained_wind_kt || windKt,
    })),
  ];

  return (
    <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="icon-badge">
            <Wind size={15} color="#126338" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Intensity & Wind Dynamics
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
              AI Dvorak Hybrid Estimation
            </div>
          </div>
        </div>
        <span className="badge badge-mint" style={{ fontSize: '10px' }}>
          CNN-ViT Model
        </span>
      </div>

      {/* Main Figures Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <div style={{
          background: '#FAFBFC',
          padding: '12px 14px',
          borderRadius: 'var(--radius-inner)',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.4px', textTransform: 'uppercase' }}>
            Max Sustained Wind
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '2px' }}>
            <span className="value-large">{windKt}</span>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontWeight: 600 }}>kt</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            ≈ {windKmh} km/h (3-min avg)
          </div>
        </div>

        <div style={{
          background: '#FAFBFC',
          padding: '12px 14px',
          borderRadius: 'var(--radius-inner)',
          border: '1px solid var(--color-border)'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.4px', textTransform: 'uppercase' }}>
            Central Pressure
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '2px' }}>
            <span className="value-large">{pressureHpa}</span>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontWeight: 600 }}>hPa</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            ΔP: -{(1005 - pressureHpa).toFixed(0)} hPa drop
          </div>
        </div>
      </div>

      {/* Confidence & Geometry */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: '11px', color: 'var(--color-text-secondary)',
        padding: '0 4px', background: '#FAFBFC', borderRadius: '8px', padding: '6px 10px',
        border: '1px solid var(--color-border-subtle)'
      }}>
        <div>
          <span style={{ color: 'var(--color-text-muted)' }}>90% Confidence: </span>
          <strong style={{ color: 'var(--color-text-primary)' }}>[{ciLower}, {ciUpper}] kt</strong>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-muted)' }}>Eyewall Rmax: </span>
          <strong style={{ color: 'var(--color-text-primary)' }}>{rMax} km</strong>
        </div>
      </div>

      {/* Recharts Soft Mint Area Chart */}
      <div style={{ height: '76px', marginTop: '2px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="mintGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#A8F0C6" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#7FE0D9" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" stroke="#9FA6AE" fontSize={9} tickLine={false} axisLine={{ stroke: '#E7EAEC' }} />
            <YAxis stroke="#9FA6AE" fontSize={9} tickLine={false} axisLine={{ stroke: '#E7EAEC' }} domain={['dataMin - 10', 'dataMax + 10']} />
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #E7EAEC',
                borderRadius: '10px',
                fontSize: '11px',
                color: '#0D0F12',
                boxShadow: '0 4px 14px rgba(13, 15, 18, 0.08)'
              }}
              labelStyle={{ color: '#4A4F55', fontWeight: 600 }}
            />
            <Area
              type="monotone"
              dataKey="wind"
              stroke="#2FBF71"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#mintGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
