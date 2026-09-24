import React from 'react';
import { ShieldAlert, Waves, Wind } from 'lucide-react';

export default function RiskMatrix({ districts = [] }) {
  const getBadgeClass = (cat) => {
    switch (cat) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-extreme';
      case 'MODERATE': return 'badge-moderate';
      default: return 'badge-low';
    }
  };

  return (
    <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="icon-badge">
            <ShieldAlert size={15} color="#126338" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Coastal District Vulnerability Matrix
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
              SLOSH Surge & High-Resolution Inundation Engine
            </div>
          </div>
        </div>
        <span className="badge badge-sky" style={{ fontSize: '10px' }}>
          {districts.length} Sectors Monitored
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '8px 10px', fontWeight: 600 }}>DISTRICT / STATE</th>
              <th style={{ padding: '8px 10px', fontWeight: 600 }}>COMPOSITE RISK</th>
              <th style={{ padding: '8px 10px', fontWeight: 600 }}>STORM SURGE</th>
              <th style={{ padding: '8px 10px', fontWeight: 600 }}>PEAK GALE WIND</th>
              <th style={{ padding: '8px 10px', fontWeight: 600 }}>CRITICAL ASSETS</th>
            </tr>
          </thead>
          <tbody>
            {districts.map((d, idx) => (
              <tr
                key={idx}
                style={{
                  borderBottom: '1px solid var(--color-border-subtle)',
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#FAFBFC'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{ padding: '10px 10px' }}>
                  <div style={{ color: 'var(--color-text-primary)', fontWeight: 700 }}>{d.district}</div>
                  <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '1px' }}>{d.state}</div>
                </td>
                <td style={{ padding: '10px 10px' }}>
                  <span className={`badge ${getBadgeClass(d.risk_category)}`}>
                    {d.composite_risk_score.toFixed(1)} {d.risk_category}
                  </span>
                </td>
                <td style={{ padding: '10px 10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--color-text-primary)' }}>
                    <Waves size={13} color="#14B8A6" />
                    <span style={{ fontWeight: 700 }}>{d.storm_surge_m.toFixed(1)} m</span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '1px' }}>
                    {d.surge_severity}
                  </div>
                </td>
                <td style={{ padding: '10px 10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--color-text-primary)' }}>
                    <Wind size={13} color="#2FBF71" />
                    <span style={{ fontWeight: 700 }}>{d.wind_hazard_kt} kt</span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '1px' }}>
                    ≈ {Math.round(d.wind_hazard_kt * 1.852)} km/h
                  </div>
                </td>
                <td style={{ padding: '10px 10px', color: 'var(--color-text-secondary)', maxWidth: '200px', fontSize: '11px', lineHeight: '1.3' }}>
                  {Array.isArray(d.critical_infrastructure)
                    ? d.critical_infrastructure.slice(0, 2).join(', ')
                    : d.critical_infrastructure || 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
