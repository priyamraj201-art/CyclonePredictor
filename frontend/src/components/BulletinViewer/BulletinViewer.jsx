import React, { useState } from 'react';
import { X, Copy, Printer, Check, FileText } from 'lucide-react';

export default function BulletinViewer({ bulletin, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!bulletin) return null;

  const fullText = bulletin.plain_text || `
INDIA METEOROLOGICAL DEPARTMENT
CYCLONE WARNING DIVISION, NEW DELHI
TROPICAL CYCLONE ADVISORY BULLETIN NO. ${bulletin.bulletin_sequence || 1}

WARNING TIER: ${bulletin.warning_tier || 'STAGE 3: CYCLONE WARNING (ORANGE ALERT)'}
STORM IDENTIFIER: ${bulletin.storm_name || 'CYCLONE'}
ISSUED AT: ${bulletin.issued_ist || new Date().toLocaleString()}

1. SYNOPTIC SITUATION & INTENSITY:
The system is moving north-northwestwards and is undergoing rapid intensification over North Indian Ocean.
Maximum sustained surface wind speed is estimated around 95-105 knots gusting to 120 knots.

2. PROJECTED TRACK & LANDFALL:
${bulletin.landfall_summary || 'Landfall expected within the next 24-36 hours along the east coast of India.'}

3. IMPACT ASSESSMENT & WARNINGS:
- Storm Surge: Astronomical tidal surge of 3.5m to 5.0m expected above normal tide at landfall.
- Wind Hazard: Gale wind speed reaching 150-165 km/h gusting to 185 km/h.
- Ports Warned: ${Array.isArray(bulletin.ports_warned) ? bulletin.ports_warned.join(', ') : 'All Major East Coast Ports'}.
- Fishermen Advisory: ${bulletin.fishermen_warning || 'Total suspension of marine operations. Fishermen advised not to venture into deep sea.'}

DISASTER MANAGEMENT ACTION RECOMMENDED:
1. Total suspension of marine and fishing operations in affected coastal belts.
2. Evacuate low-lying coastal populations to cyclone shelters immediately.
3. Halt coastal rail and vehicular traffic in Red and Orange alert districts.
  `.trim();

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(13, 15, 18, 0.45)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2000, padding: '20px'
    }}>
      <div className="card printable-bulletin" style={{
        width: '100%', maxWidth: '700px', maxHeight: '85vh',
        display: 'flex', flexDirection: 'column',
        borderRadius: '24px',
        boxShadow: 'var(--shadow-elevated)',
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--color-border)'
      }}>
        {/* Header */}
        <div className="no-print" style={{
          padding: '16px 20px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="icon-badge">
              <FileText size={16} color="#126338" />
            </div>
            <div>
              <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>
                Official IMD Warning Bulletin
              </strong>
              <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                National Disaster Alert Dissemination Document
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button className="btn btn-secondary" onClick={handleCopy} style={{ padding: '6px 14px' }}>
              {copied ? <Check size={13} color="var(--color-success-mint)" /> : <Copy size={13} />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
            <button className="btn btn-primary" onClick={handlePrint} style={{ padding: '6px 14px' }}>
              <Printer size={13} />
              <span>Print Bulletin</span>
            </button>
            <button className="btn btn-secondary" onClick={onClose} style={{ padding: '6px', borderRadius: '50%' }}>
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Warning Tier Pastel Ribbon */}
        <div style={{
          background: 'var(--color-mint-pale)',
          borderBottom: '1px solid rgba(47,191,113,0.2)',
          padding: '10px 20px', fontSize: '11px', fontWeight: 700,
          color: '#126338', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{bulletin.warning_tier || 'STAGE 3: CYCLONE WARNING (ORANGE ALERT)'}</span>
          <span className="badge badge-sky" style={{ fontSize: '10px' }}>
            BULLETIN #{bulletin.bulletin_sequence || 1}
          </span>
        </div>

        {/* Bulletin Body */}
        <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
          <pre style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: '1.6',
            color: 'var(--color-text-primary)', whiteSpace: 'pre-wrap',
            background: '#FAFBFC',
            padding: '16px', borderRadius: 'var(--radius-inner)',
            border: '1px solid var(--color-border)'
          }}>
            {fullText}
          </pre>
        </div>
      </div>
    </div>
  );
}
