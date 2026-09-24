import React, { useState, useEffect } from 'react';
import { Shield, RefreshCw, CheckCircle2, FileText, Activity } from 'lucide-react';

export default function Navbar({
  stormName,
  basin,
  category,
  isRI,
  backendStatus,
  onRefresh,
  onOpenReview,
  onOpenBulletin,
  loading
}) {
  const [timeStr, setTimeStr] = useState({ utc: '', ist: '' });

  useEffect(() => {
    const updateClocks = () => {
      const now = new Date();
      setTimeStr({
        utc: now.toISOString().slice(11, 19) + ' UTC',
        ist: new Intl.DateTimeFormat('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        }).format(now) + ' IST'
      });
    };
    updateClocks();
    const timer = setInterval(updateClocks, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header style={{
      margin: '12px 18px 8px 18px',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      backdropFilter: 'blur(16px)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-pill)',
      boxShadow: 'var(--shadow-card)'
    }}>
      {/* Brand & Storm Details */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="icon-badge">
          <Shield size={18} color="#126338" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: 800, letterSpacing: '-0.3px', color: 'var(--color-text-primary)' }}>
              CYCLONE AI
            </span>
            <span className="badge badge-mint" style={{ fontSize: '10px', padding: '2px 8px' }}>
              MoES PS 26070
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', marginTop: '1px' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>
              STORM: <strong style={{ color: 'var(--color-text-primary)' }}>{stormName || 'CYCLONE'}</strong>
            </span>
            <span style={{ color: 'var(--color-border)' }}>•</span>
            <span style={{ color: 'var(--color-text-muted)' }}>
              BASIN: <strong style={{ color: 'var(--color-text-secondary)' }}>{basin || 'Bay of Bengal'}</strong>
            </span>
            <span style={{ color: 'var(--color-border)' }}>•</span>
            <span className="mono" style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>
              {timeStr.utc} / {timeStr.ist}
            </span>
          </div>
        </div>
      </div>

      {/* Category Status & RI Pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span className="badge badge-aqua" style={{ fontSize: '11px', padding: '4px 12px' }}>
          {category || 'Very Severe Cyclonic Storm'}
        </span>

        {isRI && (
          <span className="badge badge-critical pulse-ring-mint" style={{ fontSize: '10px', padding: '4px 10px' }}>
            <Activity size={12} />
            <span>RI ACTIVE (ΔV ≥ 30 KT)</span>
          </span>
        )}

        <div className="badge badge-neutral" style={{ fontSize: '11px', gap: '6px' }}>
          <span style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: backendStatus === 'HEALTHY' ? 'var(--color-success-mint)' : 'var(--color-warning-amber)'
          }} />
          <span style={{ fontSize: '10px', fontWeight: 600 }}>{backendStatus === 'HEALTHY' ? 'SYSTEM ONLINE' : 'DEMO MODE'}</span>
        </div>
      </div>

      {/* Action Buttons (Pill Aesthetic) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button className="btn btn-secondary" onClick={onOpenBulletin}>
          <FileText size={13} />
          <span>IMD Bulletin</span>
        </button>

        <button className="btn btn-secondary" onClick={onOpenReview}>
          <CheckCircle2 size={13} color="var(--color-success-mint)" />
          <span>Forecaster Sign-Off</span>
        </button>

        <button className="btn btn-primary" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={13} className={loading ? 'spinner' : ''} />
          <span>{loading ? 'Analyzing...' : 'Run Pipeline'}</span>
        </button>
      </div>
    </header>
  );
}
