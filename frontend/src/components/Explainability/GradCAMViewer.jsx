import React, { useState } from 'react';
import { Eye, Sliders, CheckCircle2 } from 'lucide-react';

export default function GradCAMViewer() {
  const [opacity, setOpacity] = useState(0.65);

  return (
    <div className="card card-hover" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="icon-badge" style={{
            background: 'rgba(226,90,56,0.10)',
            borderColor: 'rgba(226,90,56,0.28)',
          }}>
            <Eye size={16} color="#A82B0A" />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Explainability & Saliency Map
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
              Vision Transformer Eyewall Attention
            </div>
          </div>
        </div>
        <span className="badge badge-yellow" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
          <CheckCircle2 size={11} color="#8A6500" />
          <span>Eyewall Focused</span>
        </span>
      </div>

      {/* Satellite Simulation — warm dark card aesthetic */}
      <div style={{
        position: 'relative', height: '145px',
        borderRadius: 'var(--radius-inner)',
        overflow: 'hidden',
        border: '1px solid rgba(0,0,0,0.10)',
        background: '#1E1F22',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {/* Ambient warm glow behind SVG */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          width: '100px', height: '100px',
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          background: 'rgba(255, 208, 67, 0.12)',
          filter: 'blur(24px)',
          pointerEvents: 'none',
        }} />

        <svg width="100%" height="100%" viewBox="0 0 200 200" style={{ position: 'absolute', top: 0, left: 0 }}>
          <defs>
            <radialGradient id="cycloneGradWarm" cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="#36383E" />
              <stop offset="30%"  stopColor="#2B2D31" />
              <stop offset="65%"  stopColor="#3A3C42" />
              <stop offset="100%" stopColor="#1E1F22" />
            </radialGradient>
            {/* Warm saliency: yellow → coral */}
            <radialGradient id="saliencyWarm" cx="50%" cy="50%" r="45%">
              <stop offset="0%"   stopColor="#FFD043" stopOpacity="0.90" />
              <stop offset="35%"  stopColor="#FF7E67" stopOpacity="0.65" />
              <stop offset="70%"  stopColor="#FF6B4A" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#FFD043" stopOpacity="0.00" />
            </radialGradient>
          </defs>

          {/* Cloud disk */}
          <circle cx="100" cy="100" r="85" fill="url(#cycloneGradWarm)" opacity="0.9" />
          {/* Spiral bands */}
          <path d="M 100 100 Q 140 60 170 100 Q 150 150 100 160 Q 50 150 40 100 Q 45 40 100 30"
            fill="none" stroke="#9B9FA8" strokeWidth="9" strokeLinecap="round" opacity="0.30" />
          <path d="M 100 100 Q 60 140 30 100 Q 50 50 100 40 Q 150 50 160 100"
            fill="none" stroke="#C8C3BC" strokeWidth="5" strokeLinecap="round" opacity="0.35" />
          {/* Eye */}
          <circle cx="100" cy="100" r="9" fill="#1E1F22" stroke="#FFD043" strokeWidth="1.5" />
          {/* Warm Grad-CAM saliency overlay */}
          <circle cx="100" cy="100" r="62" fill="url(#saliencyWarm)" opacity={opacity} style={{ mixBlendMode: 'screen' }} />
          {/* Crosshair */}
          <line x1="92" y1="100" x2="108" y2="100" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.8" />
          <line x1="100" y1="92"  x2="100" y2="108" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.8" />
        </svg>

        {/* Label pill */}
        <div style={{
          position: 'absolute', bottom: '8px', left: '10px',
          background: 'rgba(255,255,255,0.12)',
          backdropFilter: 'blur(8px)',
          padding: '3px 10px', borderRadius: '999px',
          fontSize: '9px', fontWeight: 600, color: '#FFFFFF',
          border: '1px solid rgba(255,255,255,0.15)',
          letterSpacing: '0.03em',
        }}>
          INSAT-3D 10.8µm IR • ViT Eyewall Attention
        </div>
      </div>

      {/* Opacity Slider */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
          <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 500 }}>
            <Sliders size={12} />
            <span>Attention Opacity</span>
          </span>
          <span style={{
            fontWeight: 700, fontSize: '11px', padding: '2px 10px',
            borderRadius: '999px',
            background: 'rgba(255,208,67,0.12)',
            color: '#7A5700',
            border: '1px solid rgba(255,208,67,0.28)',
          }}>
            {Math.round(opacity * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0" max="1" step="0.05"
          value={opacity}
          onChange={(e) => setOpacity(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#FFD043', height: '4px', cursor: 'pointer', borderRadius: '999px' }}
        />
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
        ViT self-attention validates <strong style={{ color: 'var(--text-primary)' }}>94.2% focal concentration</strong> on the dense overcast convective ring, providing transparent validation for operational forecasters.
      </div>
    </div>
  );
}
