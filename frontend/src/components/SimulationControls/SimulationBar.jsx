import React, { useState, useEffect } from 'react';
import { Play, Pause, SkipForward, RotateCcw, Compass } from 'lucide-react';
import { fetchSimulationStep } from '../../api';

export default function SimulationBar({ onStepChange, currentStorm, onStormSelect }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(6);
  const [stepLabel, setStepLabel] = useState('Step 1: Depression');

  const advanceStep = async (targetStep) => {
    const data = await fetchSimulationStep(currentStorm, targetStep);
    setStep(data.step);
    setTotalSteps(data.total_steps || 6);
    setStepLabel(data.label || `Step ${data.step + 1}`);
    if (onStepChange) onStepChange(data);
  };

  const handleNext  = () => advanceStep((step + 1) % totalSteps);
  const handleReset = () => { setIsPlaying(false); advanceStep(0); };

  useEffect(() => {
    let timer = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setStep((prev) => {
          const next = (prev + 1) % totalSteps;
          advanceStep(next);
          return next;
        });
      }, 4000);
    }
    return () => clearInterval(timer);
  }, [isPlaying, totalSteps, currentStorm]);

  return (
    <div style={{
      margin: '0 14px 6px 14px',
      padding: '7px 18px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '10px',
      backgroundColor: 'rgba(255, 255, 255, 0.80)',
      backdropFilter: 'blur(12px)',
      border: '1px solid rgba(0, 0, 0, 0.07)',
      borderRadius: '999px',
      boxShadow: '0 4px 14px rgba(50, 40, 25, 0.06)',
    }}>
      {/* Storm Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '5px',
          fontSize: '10px', fontWeight: 700, padding: '3px 10px',
          borderRadius: '999px', letterSpacing: '0.04em',
          background: 'rgba(255, 208, 67, 0.12)',
          color: '#7A5700',
          border: '1px solid rgba(255, 208, 67, 0.32)',
        }}>
          <Compass size={11} />
          HISTORICAL PLAYBACK
        </span>

        <select
          value={currentStorm}
          onChange={(e) => {
            setIsPlaying(false);
            onStormSelect(e.target.value);
            advanceStep(0);
          }}
          style={{
            width: '185px',
            padding: '5px 14px',
            fontSize: '11px',
            borderRadius: '999px',
            border: '1px solid rgba(0,0,0,0.09)',
            background: '#FDFCFA',
            fontWeight: 600,
            color: 'var(--text-primary)',
            cursor: 'pointer',
          }}
        >
          <option value="FANI">Cyclone Fani (2019)</option>
          <option value="AMPHAN">Cyclone Amphan (2020)</option>
          <option value="BIPARJOY">Cyclone Biparjoy (2023)</option>
        </select>
      </div>

      {/* Playback Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <button
          className="btn btn-secondary"
          onClick={() => setIsPlaying(!isPlaying)}
          style={{ padding: '5px 14px', fontSize: '11px' }}
        >
          {isPlaying
            ? <Pause size={12} color="var(--danger)" />
            : <Play  size={12} color="var(--success)" />}
          <span>{isPlaying ? 'Pause' : 'Play Timeline'}</span>
        </button>

        <button className="btn btn-secondary" onClick={handleNext} style={{ padding: '5px 12px', fontSize: '11px' }}>
          <SkipForward size={12} />
          <span>Next Step</span>
        </button>

        <button className="btn btn-secondary" onClick={handleReset} style={{ padding: '5px 10px', fontSize: '11px' }}>
          <RotateCcw size={12} />
        </button>
      </div>

      {/* Step Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px' }}>
        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>STAGE:</span>
        <strong style={{ color: 'var(--text-primary)' }}>{stepLabel}</strong>
        <span style={{
          padding: '2px 10px', borderRadius: '999px',
          fontSize: '10px', fontWeight: 700,
          background: 'rgba(255,208,67,0.12)',
          color: '#7A5700',
          border: '1px solid rgba(255,208,67,0.28)',
        }}>
          {step + 1} / {totalSteps}
        </span>
      </div>
    </div>
  );
}
