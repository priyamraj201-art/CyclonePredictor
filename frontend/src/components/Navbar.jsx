import React, { useState, useEffect } from 'react';
import { Shield, RefreshCw, CheckCircle2, FileText, Activity, Radio } from 'lucide-react';

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

  const refreshLabel = lastLiveRefresh
    ? `LAST REFRESH ${new Date(lastLiveRefresh).toISOString().slice(11, 19)} UTC`
    : null;

  return (
    <header style={{
      margin: '10px 14px 6px 14px',
      padding: '10px 18px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: 'rgba(255, 255, 255, 0.88)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      border: liveMode
        ? '1.5px solid rgba(226, 90, 56, 0.30)'
        : '1px solid rgba(0, 0, 0, 0.07)',
      borderRadius: '999px',
      boxShadow: '0 12px 28px -6px rgba(0, 0, 0, 0.06), 0 2px 6px rgba(0,0,0,0.04)',
      transition: 'border 0.3s ease, background 0.3s ease',
      gap: '12px',
    }}>

      {/* ── Brand & Storm Details ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
        {/* Logo badge */}
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: liveMode
            ? 'linear-gradient(135deg, rgba(226,90,56,0.15), rgba(255,184,52,0.15))'
            : 'rgba(255, 208, 67, 0.15)',
          border: liveMode ? '1.5px solid rgba(226,90,56,0.3)' : '1.5px solid rgba(255,208,67,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <Shield size={17} color={liveMode ? '#C04020' : '#8A6500'} />
        </div>

        <div style={{ minWidth: 0 }}>
          {/* Top row: brand + badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{
              fontSize: '14px', fontWeight: 800, letterSpacing: '-0.03em',
              color: 'var(--text-primary)'
            }}>
              CYCLONE AI
            </span>

            <span style={{
              fontSize: '10px', fontWeight: 600, padding: '3px 10px',
              borderRadius: '999px',
              background: 'rgba(0,0,0,0.05)',
              color: 'var(--text-secondary)',
              border: '1px solid rgba(0,0,0,0.08)',
              letterSpacing: '0.02em',
            }}>
              MoES PS 26070
            </span>

            {/* LIVE mode badge */}
            {liveMode && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '5px',
                fontSize: '10px', fontWeight: 700, padding: '3px 10px',
                borderRadius: '999px', letterSpacing: '0.03em',
                background: 'rgba(226,90,56,0.10)',
                color: '#B8350A',
                border: '1.5px solid rgba(226,90,56,0.28)',
              }}>
                <span style={{
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: liveLoading ? 'var(--yellow-base)' : 'var(--danger)',
                  display: 'inline-block',
                  boxShadow: liveLoading ? '0 0 6px var(--yellow-base)' : '0 0 6px var(--danger)',
                  animation: 'pulse-live 1.2s infinite',
                }} />
                {liveLoading ? 'SCANNING…' : 'LIVE TELEMETRY ACTIVE'}
              </span>
            )}
          </div>

          {/* Sub-row: storm / basin / live metrics */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', marginTop: '2px', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--text-muted)' }}>
              {liveMode
                ? <><strong style={{ color: 'var(--danger)' }}>LIVE:</strong> {stormName || 'NIO WATCH'}</>
                : <><span style={{ color: 'var(--text-muted)' }}>STORM:</span> <strong style={{ color: 'var(--text-primary)' }}>{stormName || 'CYCLONE'}</strong></>
              }
            </span>
            <span style={{ color: 'var(--border-warm)', fontWeight: 300 }}>·</span>
            <span style={{ color: 'var(--text-muted)' }}>
              BASIN: <strong style={{ color: 'var(--text-secondary)' }}>{basin || 'Bay of Bengal'}</strong>
            </span>

            {liveMode && liveMetrics && (
              <>
                <span style={{ color: 'var(--border-warm)', fontWeight: 300 }}>·</span>
                <span style={{ color: '#7A5700', fontWeight: 600 }}>
                  GPI {liveMetrics.gpi?.toFixed(2)}
                </span>
                <span style={{ color: 'var(--border-warm)', fontWeight: 300 }}>·</span>
                <span style={{
                  color: liveMetrics.threat_level === 'EXTREME' ? '#A82B0A'
                    : liveMetrics.threat_level === 'HIGH' ? '#8A5500' : '#1B6B40',
                  fontWeight: 700, fontSize: '10px'
                }}>
                  {liveMetrics.threat_level}
                </span>
                {refreshLabel && (
                  <>
                    <span style={{ color: 'var(--border-warm)', fontWeight: 300 }}>·</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                      {refreshLabel}
                    </span>
                  </>
                )}
              </>
            )}

            {!liveMode && (
              <>
                <span style={{ color: 'var(--border-warm)', fontWeight: 300 }}>·</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                  {timeStr.utc} / {timeStr.ist}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Centre: Category & RI status ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <span className="badge badge-moderate" style={{ fontSize: '11px', padding: '4px 14px' }}>
          {category || 'Very Severe Cyclonic Storm'}
        </span>

        {isRI && (
          <span className="badge badge-critical pulse-ring-warm" style={{ fontSize: '10px', padding: '4px 12px' }}>
            <Activity size={11} />
            <span>RI ACTIVE</span>
          </span>
        )}

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          padding: '4px 12px', borderRadius: '999px',
          background: 'rgba(0,0,0,0.04)',
          border: '1px solid var(--border-light)',
          fontSize: '10px', fontWeight: 600, color: 'var(--text-secondary)',
        }}>
          <span style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: backendStatus === 'HEALTHY' ? 'var(--success)' : 'var(--warning)'
          }} />
          {backendStatus === 'HEALTHY' ? 'SYSTEM ONLINE' : 'DEMO MODE'}
        </div>
      </div>

      {/* ── Right: Action Buttons ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <button className="btn btn-secondary" onClick={onOpenBulletin} style={{ fontSize: '12px' }}>
          <FileText size={13} />
          <span>IMD Bulletin</span>
        </button>

        <button className="btn btn-secondary" onClick={onOpenReview} style={{ fontSize: '12px' }}>
          <CheckCircle2 size={13} color="var(--success)" />
          <span>Forecaster Sign-Off</span>
        </button>

        {/* LIVE FEED Toggle */}
        <button
          onClick={onToggleLive}
          disabled={liveLoading}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '8px 16px', borderRadius: '999px',
            fontSize: '11px', fontWeight: 700, letterSpacing: '0.02em',
            cursor: liveLoading ? 'not-allowed' : 'pointer',
            border: liveMode
              ? '1.5px solid rgba(226,90,56,0.40)'
              : '1.5px solid rgba(0,0,0,0.10)',
            background: liveMode
              ? 'rgba(226,90,56,0.10)'
              : 'rgba(255,208,67,0.08)',
            color: liveMode ? '#A82B0A' : 'var(--text-secondary)',
            transition: 'all 0.22s ease',
          }}
          title={liveMode
            ? 'Switch to Historical Simulation Mode'
            : 'Switch to Live Satellite Feed (Open-Meteo API)'}
        >
          {liveLoading
            ? <RefreshCw size={12} style={{ animation: 'spin 0.7s linear infinite' }} />
            : <Radio size={12} style={{ color: liveMode ? '#A82B0A' : undefined }} />
          }
          <span>{liveMode ? '🔴 LIVE FEED ON' : 'LIVE SATELLITE FEED'}</span>
        </button>

        {/* Run Pipeline / Historical Mode */}
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

      {/* Keyframes injected inline (kept for the pulsing dot) */}
      <style>{`
        @keyframes pulse-live {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.50; transform: scale(1.35); }
        }
      `}</style>
    </header>
  );
}
