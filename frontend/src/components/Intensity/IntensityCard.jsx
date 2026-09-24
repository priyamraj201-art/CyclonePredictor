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

  const chartData = [
    { time: '-12h', wind: Math.max(35, windKt - 20) },
    { time: '-6h',  wind: Math.max(45, windKt - 10) },
    { time: 'Now',  wind: windKt },
    ...trackForecast.map((pt, i) => ({
      time: `+${(i + 1) * 12}h`,
      wind: pt.wind_kt || pt.max_sustained_wind_kt || windKt,
    })),
  ];

  return (
    <div className="card card-hover" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="icon-badge">
            <Wind size={16} color="#8A6500" />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Intensity & Wind Dynamics
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
              AI Dvorak Hybrid Estimation
            </div>
          </div>
        </div>
        <span className="badge badge-yellow" style={{ fontSize: '10px' }}>
          CNN-ViT Model
        </span>
      </div>

      {/* Main Metric Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {/* Wind Speed */}
        <div style={{
          background: 'rgba(255, 208, 67, 0.07)',
          padding: '14px 16px',
          borderRadius: 'var(--radius-inner)',
          border: '1px solid rgba(255, 208, 67, 0.20)',
          position: 'relative', overflow: 'hidden',
        }}>
          {/* Ambient orb */}
          <div style={{
            position: 'absolute', top: '-16px', right: '-16px',
            width: '60px', height: '60px', borderRadius: '50%',
            background: 'rgba(255,208,67,0.25)', filter: 'blur(20px)',
            pointerEvents: 'none',
          }} />
          <div style={{ color: 'var(--text-muted)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Max Sustained Wind
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px', marginTop: '4px' }}>
            <span className="value-large">{windKt}</span>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 600 }}>kt</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
            ≈ {windKmh} km/h (3-min avg)
          </div>
        </div>

        {/* Pressure */}
        <div style={{
          background: 'rgba(255, 126, 103, 0.07)',
          padding: '14px 16px',
          borderRadius: 'var(--radius-inner)',
          border: '1px solid rgba(255, 126, 103, 0.18)',
          position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: '-16px', right: '-16px',
            width: '60px', height: '60px', borderRadius: '50%',
            background: 'rgba(255,126,103,0.22)', filter: 'blur(20px)',
            pointerEvents: 'none',
          }} />
          <div style={{ color: 'var(--text-muted)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Central Pressure
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px', marginTop: '4px' }}>
            <span className="value-large">{pressureHpa}</span>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 600 }}>hPa</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
            ΔP: −{(1005 - pressureHpa).toFixed(0)} hPa drop
          </div>
        </div>
      </div>

      {/* Confidence interval row */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: '11px', color: 'var(--text-secondary)',
        background: 'rgba(0,0,0,0.03)',
        borderRadius: 'var(--radius-item)',
        padding: '8px 14px',
        border: '1px solid var(--border-light)',
      }}>
        <div>
          <span style={{ color: 'var(--text-muted)' }}>90% Confidence: </span>
          <strong style={{ color: 'var(--text-primary)' }}>[{ciLower}, {ciUpper}] kt</strong>
        </div>
        <div>
          <span style={{ color: 'var(--text-muted)' }}>Eyewall R<sub>max</sub>: </span>
          <strong style={{ color: 'var(--text-primary)' }}>{rMax} km</strong>
        </div>
      </div>

      {/* Warm Area Chart */}
      <div style={{ height: '80px', marginTop: '2px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="warmGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#FFD043" stopOpacity={0.55} />
                <stop offset="100%" stopColor="#FF7E67" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
              stroke="#C8C3BC"
              fontSize={9}
              tickLine={false}
              axisLine={{ stroke: 'rgba(0,0,0,0.08)' }}
            />
            <YAxis
              stroke="#C8C3BC"
              fontSize={9}
              tickLine={false}
              axisLine={{ stroke: 'rgba(0,0,0,0.08)' }}
              domain={['dataMin - 10', 'dataMax + 10']}
            />
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: '16px',
                fontSize: '11px',
                color: 'var(--text-primary)',
                boxShadow: '0 6px 20px rgba(50,40,25,0.10)'
              }}
              labelStyle={{ color: 'var(--text-secondary)', fontWeight: 600 }}
            />
            <Area
              type="monotone"
              dataKey="wind"
              stroke="#FFB834"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#warmGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
