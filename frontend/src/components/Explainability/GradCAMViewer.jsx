import React, { useState } from 'react';
import { Eye, Sliders, CheckCircle2 } from 'lucide-react';

export default function GradCAMViewer() {
  const [opacity, setOpacity] = useState(0.65);

  return (
    <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="icon-badge">
            <Eye size={15} color="#126338" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Explainability & Saliency Map
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
              Vision Transformer Eyewall Attention
            </div>
          </div>
        </div>
        <span className="badge badge-mint" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
          <CheckCircle2 size={12} color="#2FBF71" />
          <span>Eyewall Focused</span>
        </span>
      </div>

      {/* Satellite Imagery Simulation Box */}
      <div style={{
        position: 'relative', height: '140px', borderRadius: 'var(--radius-inner)',
        overflow: 'hidden', border: '1px solid var(--color-border)',
        background: '#0D0F12', display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {/* Synthetic Cyclone Cloud Pattern */}
        <svg width="100%" height="100%" viewBox="0 0 200 200" style={{ position: 'absolute', top: 0, left: 0 }}>
          <defs>
            <radialGradient id="cycloneGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#1E293B" />
              <stop offset="30%" stopColor="#334155" />
              <stop offset="65%" stopColor="#64748B" />
              <stop offset="100%" stopColor="#0D0F12" />
            </radialGradient>
            {/* Mint-Aqua Saliency Gradient */}
            <radialGradient id="saliencyGrad" cx="50%" cy="50%" r="45%">
              <stop offset="0%" stopColor="#A8F0C6" stopOpacity="0.95" />
              <stop offset="35%" stopColor="#7FE0D9" stopOpacity="0.8" />
              <stop offset="70%" stopColor="#2FBF71" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#14B8A6" stopOpacity="0.0" />
            </radialGradient>
          </defs>

          {/* Cloud spiral bands */}
          <circle cx="100" cy="100" r="85" fill="url(#cycloneGrad)" opacity="0.8" />
          <path d="M 100 100 Q 140 60 170 100 Q 150 150 100 160 Q 50 150 40 100 Q 45 40 100 30" fill="none" stroke="#94A3B8" strokeWidth="10" strokeLinecap="round" opacity="0.4" />
          <path d="M 100 100 Q 60 140 30 100 Q 50 50 100 40 Q 150 50 160 100" fill="none" stroke="#CBD5E1" strokeWidth="6" strokeLinecap="round" opacity="0.45" />

          {/* Cyclone Eye */}
          <circle cx="100" cy="100" r="9" fill="#0D0F12" stroke="#7FE0D9" strokeWidth="2" />

          {/* Grad-CAM Heatmap overlay */}
          <circle cx="100" cy="100" r="62" fill="url(#saliencyGrad)" opacity={opacity} style={{ mixBlendMode: 'screen' }} />

          {/* Center Crosshair */}
          <line x1="92" y1="100" x2="108" y2="100" stroke="#FFFFFF" strokeWidth="1.5" />
          <line x1="100" y1="92" x2="100" y2="108" stroke="#FFFFFF" strokeWidth="1.5" />
        </svg>

        <div style={{
          position: 'absolute', bottom: '8px', left: '10px',
          background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(8px)',
          padding: '2px 8px', borderRadius: 'var(--radius-pill)',
          fontSize: '9px', fontWeight: 600, color: '#0D0F12',
          border: '1px solid var(--color-border)'
        }}>
          INSAT-3D 10.8µm IR • ViT Eyewall Attention
        </div>
      </div>

      {/* Heatmap Opacity Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
          <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 500 }}>
            <Sliders size={12} />
            <span>Attention Opacity</span>
          </span>
          <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {Math.round(opacity * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={opacity}
          onChange={(e) => setOpacity(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--color-cta-black)', height: '4px', cursor: 'pointer' }}
        />
      </div>

      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', lineHeight: '1.4' }}>
        ViT self-attention validates <strong style={{ color: 'var(--color-text-primary)' }}>94.2% focal concentration</strong> on the dense overcast convective ring, providing transparent validation for operational forecasters.
      </div>
    </div>
  );
}
