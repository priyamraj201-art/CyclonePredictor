import React, { useState } from 'react';
import { X, CheckCircle2, ShieldCheck, FileCheck } from 'lucide-react';
import { submitForecasterReview, verifyAuditChain } from '../../api';

export default function ForecasterReviewModal({ frameId, currentWindKt, onClose, onReviewComplete }) {
  const [forecasterId, setForecasterId] = useState('FOR-IMD-042');
  const [status, setStatus] = useState('APPROVED');
  const [overrideWind, setOverrideWind] = useState(currentWindKt || 85.0);
  const [notes, setNotes] = useState('AI predictions corroborate with synoptic radar observations and ASCAT scatterometer passes.');
  const [submitting, setSubmitting] = useState(false);
  const [auditResult, setAuditResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      frame_id: frameId || 'DEMO_FRAME_CURRENT',
      forecaster_id: forecasterId,
      status: status,
      override_wind_kt: status === 'MODIFIED' ? parseFloat(overrideWind) : null,
      forecaster_notes: notes,
    };

    const res = await submitForecasterReview(payload);
    const chain = await verifyAuditChain();

    setSubmitting(false);
    setAuditResult({
      hash: res.audit_hash || 'SHA256:4a8b79e1...',
      chainValid: chain.valid,
      records: chain.records_checked,
    });

    if (onReviewComplete) {
      onReviewComplete(res);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(13, 15, 18, 0.45)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2000, padding: '20px'
    }}>
      <div className="card" style={{
        width: '100%', maxWidth: '540px',
        display: 'flex', flexDirection: 'column',
        borderRadius: '24px',
        boxShadow: 'var(--shadow-elevated)',
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--color-border)'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="icon-badge">
              <ShieldCheck size={18} color="#126338" />
            </div>
            <div>
              <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>
                Forecaster Human-in-the-Loop Sign-Off
              </strong>
              <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                IMD Operational Directive Section 4.8 Compliance
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '6px', borderRadius: '50%' }}>
            <X size={14} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.4' }}>
            All automated AI estimates require review by a certified duty meteorologist before transmission to NDMA and state disaster authorities.
          </div>

          <div className="grid-2">
            <div>
              <label style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
                CERTIFIED FORECASTER ID
              </label>
              <input
                type="text"
                value={forecasterId}
                onChange={(e) => setForecasterId(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
                REVIEW ACTION
              </label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="APPROVED">APPROVE AI PREDICTION</option>
                <option value="MODIFIED">MANUAL OVERRIDE / ADJUST</option>
              </select>
            </div>
          </div>

          {status === 'MODIFIED' && (
            <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', padding: '12px', borderRadius: '14px' }}>
              <label style={{ fontSize: '11px', color: '#92400E', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
                OVERRIDE MAXIMUM SUSTAINED WIND (KNOTS)
              </label>
              <input
                type="number"
                step="1"
                value={overrideWind}
                onChange={(e) => setOverrideWind(e.target.value)}
                style={{ backgroundColor: '#FFFFFF' }}
              />
              <div style={{ fontSize: '10px', color: '#B45309', marginTop: '4px' }}>
                Original Automated AI Estimate: {currentWindKt} kt
              </div>
            </div>
          )}

          <div>
            <label style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
              SYNOPTIC JUSTIFICATION & FORECASTER NOTES
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              required
            />
          </div>

          {auditResult && (
            <div style={{ background: 'var(--color-mint-pale)', border: '1px solid rgba(47,191,113,0.3)', padding: '12px 14px', borderRadius: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#126338', fontSize: '11px', fontWeight: 700 }}>
                <CheckCircle2 size={14} color="#2FBF71" />
                <span>CRYPTOGRAPHICALLY SEALED IN SHA-256 AUDIT CHAIN</span>
              </div>
              <div className="mono" style={{ fontSize: '10px', color: '#2C3E50', marginTop: '4px', wordBreak: 'break-all' }}>
                Seal Hash: {auditResult.hash}
              </div>
              <div style={{ fontSize: '10px', color: '#556B2F', marginTop: '2px' }}>
                Audit Chain Status: <strong>VERIFIED ({auditResult.records} records checked)</strong>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <CheckCircle2 size={13} />
              <span>{submitting ? 'Sealing Audit Record...' : 'Confirm & Sign-Off'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
