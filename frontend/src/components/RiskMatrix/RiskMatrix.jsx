import React from 'react';
import { ShieldAlert, Waves, Wind } from 'lucide-react';

const RISK_CONFIG = {
  CRITICAL: { bg: 'rgba(226,90,56,0.10)',  border: 'rgba(226,90,56,0.28)',  text: '#A82B0A', dot: '#E25A38' },
  HIGH:     { bg: 'rgba(255,126,103,0.10)', border: 'rgba(255,126,103,0.25)',text: '#9E2D0D', dot: '#FF7E67' },
  MODERATE: { bg: 'rgba(255,208,67,0.12)',  border: 'rgba(255,208,67,0.30)', text: '#7A5700', dot: '#FFD043' },
  LOW:      { bg: 'rgba(0,0,0,0.04)',        border: 'rgba(0,0,0,0.08)',       text: 'var(--text-secondary)', dot: '#C8C3BC' },
};

export default function RiskMatrix({ districts = [] }) {
  const getRiskCfg = (cat) => RISK_CONFIG[cat] || RISK_CONFIG.LOW;

  return (
    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="icon-badge icon-badge-coral">
            <ShieldAlert size={16} color="#B8350A" />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Coastal District Vulnerability
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
              SLOSH Surge & High-Resolution Inundation Engine
            </div>
          </div>
        </div>
        <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
          {districts.length} Sectors
        </span>
      </div>

      {/* District Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {districts.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '24px 16px',
            color: 'var(--text-muted)', fontSize: '12px',
            background: 'rgba(0,0,0,0.03)', borderRadius: 'var(--radius-inner)',
          }}>
            No coastal districts in threat radius
          </div>
        ) : districts.map((d, idx) => {
          const cfg = getRiskCfg(d.risk_category);
          const assets = Array.isArray(d.critical_infrastructure)
            ? d.critical_infrastructure.slice(0, 2).join(', ')
            : (d.critical_infrastructure || '—');
          return (
            <div
              key={idx}
              style={{
                display: 'grid',
                gridTemplateColumns: '1.6fr 1fr 1fr 1fr',
                gap: '8px',
                alignItems: 'center',
                padding: '12px 14px',
                borderRadius: 'var(--radius-item)',
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
                transition: 'transform 0.18s ease, box-shadow 0.18s ease',
                cursor: 'default',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = 'var(--shadow-card)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {/* District */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                  <span style={{
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: cfg.dot, flexShrink: 0,
                    boxShadow: `0 0 5px ${cfg.dot}88`,
                  }} />
                  <span style={{ fontWeight: 700, fontSize: '12px', color: 'var(--text-primary)' }}>
                    {d.district}
                  </span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px', paddingLeft: '15px' }}>
                  {d.state}
                </div>
              </div>

              {/* Composite score */}
              <div>
                <span style={{
                  display: 'inline-block',
                  padding: '3px 10px', borderRadius: '999px',
                  fontSize: '11px', fontWeight: 700,
                  background: 'rgba(255,255,255,0.60)',
                  color: cfg.text,
                  border: `1px solid ${cfg.border}`,
                }}>
                  {d.composite_risk_score.toFixed(1)}
                </span>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px', fontWeight: 600 }}>
                  {d.risk_category}
                </div>
              </div>

              {/* Surge */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Waves size={12} color="#FF7E67" />
                  <span style={{ fontWeight: 700, fontSize: '12px', color: 'var(--text-primary)' }}>
                    {d.storm_surge_m.toFixed(1)} m
                  </span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {d.surge_severity}
                </div>
              </div>

              {/* Wind */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Wind size={12} color="#FFD043" />
                  <span style={{ fontWeight: 700, fontSize: '12px', color: 'var(--text-primary)' }}>
                    {d.wind_hazard_kt} kt
                  </span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {assets}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
