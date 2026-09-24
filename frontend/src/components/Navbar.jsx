import React, { useState, useEffect } from 'react';
import { Shield, RefreshCw, CheckCircle2, FileText, Activity, Radio, Satellite } from 'lucide-react';

export default function Navbar({
  stormName,
  basin,
  category,
  isRI,
  backendStatus,
  onRefresh,
  onOpenReview,
  onOpenBulletin,
  loading,
  // STEP 5 — live mode props
  liveMode = false,
  onToggleLive,
  liveMetrics = null,
  liveLoading = false,
  lastLiveRefresh = null,
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

  // Format last-refresh timestamp for display
  const refreshLabel = lastLiveRefresh
    ? `REFRESHED ${new Date(lastLiveRefresh).toISOString().slice(11, 19)} UTC`
    : null;

  return (
    <header style={{
      margin: '12px 18px 8px 18px',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: liveMode
        ? 'rgba(18, 99, 56, 0.07)'
        : 'rgba(255, 255, 255, 0.95)',
      backdropFilter: 'blur(16px)',
      border: liveMode
        ? '1px solid rgba(18, 99, 56, 0.35)'
        : '1px solid var(--color-border)',
      borderRadius: 'var(--radius-pill)',
      boxShadow: liveMode
        ? '0 0 0 1px rgba(18,99,56,0.10), var(--shadow-card)'
        : 'var(--shadow-card)',
      transition: 'border 0.3s, background 0.3s, box-shadow 0.3s',
    }}>

      {/* ── Brand & Storm Details ─────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="icon-badge" style={{
          background: liveMode ? 'rgba(18,99,56,0.12)' : undefined,
        }}>
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

            {/* LIVE mode telemetry badge */}
            {liveMode && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '5px',
                fontSize: '10px', fontWeight: 700, padding: '2px 9px',
                borderRadius: '999px', letterSpacing: '0.3px',
                background: 'rgba(18,99,56,0.10)',
                color: '#126338',
                border: '1px solid rgba(18,99,56,0.3)',
                animation: liveLoading ? 'none' : undefined,
              }}>
                {/* Pulsing red dot */}
                <span style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: liveLoading ? '#f0a500' : '#e53935',
                  display: 'inline-block',
                  boxShadow: liveLoading ? '0 0 6px #f0a500' : '0 0 6px #e53935',
                  animation: 'pulse-live 1.2s infinite',
                }} />
                {liveLoading ? 'SCANNING…' : 'LIVE TELEMETRY ACTIVE'}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', marginTop: '1px' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>
              {liveMode
                ? <><strong style={{ color: '#126338' }}>LIVE:</strong> {stormName || 'NIO WATCH'}</>
                : <>STORM: <strong style={{ color: 'var(--color-text-primary)' }}>{stormName || 'CYCLONE'}</strong></>
              }
            </span>
            <span style={{ color: 'var(--color-border)' }}>•</span>
            <span style={{ color: 'var(--color-text-muted)' }}>
              BASIN: <strong style={{ color: 'var(--color-text-secondary)' }}>{basin || 'Bay of Bengal'}</strong>
            </span>

            {/* Live GPI + threat level when in live mode */}
            {liveMode && liveMetrics && (
              <>
                <span style={{ color: 'var(--color-border)' }}>•</span>
                <span style={{ color: '#126338', fontWeight: 600 }}>
                  GPI {liveMetrics.gpi?.toFixed(2)}
                </span>
                <span style={{ color: 'var(--color-border)' }}>•</span>
                <span style={{
                  color: liveMetrics.threat_level === 'EXTREME' ? '#e53935' :
                    liveMetrics.threat_level === 'HIGH' ? '#f0a500' : '#126338',
                  fontWeight: 700, fontSize: '10px'
                }}>
                  {liveMetrics.threat_level}
                </span>
                {refreshLabel && (
                  <>
                    <span style={{ color: 'var(--color-border)' }}>•</span>
                    <span className="mono" style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>
                      {refreshLabel}
                    </span>
                  </>
                )}
              </>
            )}

            {/* Normal UTC/IST clock when not in live mode */}
            {!liveMode && (
              <>
                <span style={{ color: 'var(--color-border)' }}>•</span>
                <span className="mono" style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>
                  {timeStr.utc} / {timeStr.ist}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Category Status & RI Pill ─────────────────────────────────── */}
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
          <span style={{ fontSize: '10px', fontWeight: 600 }}>
            {backendStatus === 'HEALTHY' ? 'SYSTEM ONLINE' : 'DEMO MODE'}
          </span>
        </div>
      </div>

      {/* ── Action Buttons ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button className="btn btn-secondary" onClick={onOpenBulletin}>
          <FileText size={13} />
          <span>IMD Bulletin</span>
        </button>

        <button className="btn btn-secondary" onClick={onOpenReview}>
          <CheckCircle2 size={13} color="var(--color-success-mint)" />
          <span>Forecaster Sign-Off</span>
        </button>

        {/* LIVE SATELLITE FEED Toggle */}
        <button
          onClick={onToggleLive}
          disabled={liveLoading}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '6px 14px', borderRadius: '999px',
            fontSize: '11px', fontWeight: 700, letterSpacing: '0.2px',
            cursor: liveLoading ? 'not-allowed' : 'pointer',
            border: liveMode
              ? '1.5px solid rgba(229,57,53,0.5)'
              : '1.5px solid var(--color-border)',
            background: liveMode
              ? 'rgba(229,57,53,0.08)'
              : 'rgba(255,255,255,0.7)',
            color: liveMode ? '#e53935' : 'var(--color-text-secondary)',
            transition: 'all 0.25s ease',
            backdropFilter: 'blur(8px)',
          }}
          title={liveMode
            ? 'Switch to Historical Simulation Mode'
            : 'Switch to Live Satellite Feed (Open-Meteo API)'}
        >
          {liveLoading
            ? <RefreshCw size={12} className="spinner" />
            : <Radio size={12} style={{ color: liveMode ? '#e53935' : undefined }} />
          }
          <span>{liveMode ? '🔴 LIVE FEED ON' : 'LIVE SATELLITE FEED'}</span>
        </button>

        {/* Run Pipeline / Refresh button */}
        <button
          className="btn btn-primary"
          onClick={liveMode ? onToggleLive : onRefresh}
          disabled={loading || liveLoading}
          title={liveMode ? 'Exit live mode' : 'Run pipeline on synthetic storm'}
        >
          <RefreshCw size={13} className={loading ? 'spinner' : ''} />
          <span>{loading ? 'Analyzing…' : liveMode ? 'Historical Mode' : 'Run Pipeline'}</span>
        </button>
      </div>

      {/* Keyframe for live pulsing dot */}
      <style>{`
        @keyframes pulse-live {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.55; transform: scale(1.25); }
        }
      `}</style>
    </header>
  );
}
