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
    if (onStepChange) {
      onStepChange(data);
    }
  };

  const handleNext = () => {
    advanceStep((step + 1) % totalSteps);
  };

  const handleReset = () => {
    setIsPlaying(false);
    advanceStep(0);
  };

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
      margin: '0 18px 8px 18px',
      padding: '6px 14px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: '#FFFFFF',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-pill)',
      boxShadow: 'var(--shadow-sm)'
    }}>
      {/* Simulation Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span className="badge badge-sky" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '3px 10px' }}>
          <Compass size={12} />
          <span>HISTORICAL PLAYBACK</span>
        </span>

        <select
          value={currentStorm}
          onChange={(e) => {
            setIsPlaying(false);
            onStormSelect(e.target.value);
            advanceStep(0);
          }}
          style={{
            width: '180px',
            padding: '4px 12px',
            fontSize: '11px',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--color-border)',
            backgroundColor: '#FAFBFC',
            fontWeight: 600,
            cursor: 'pointer'
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
          {isPlaying ? <Pause size={12} color="var(--color-alert-red)" /> : <Play size={12} color="var(--color-success-mint)" />}
          <span>{isPlaying ? 'Pause' : 'Play Timeline'}</span>
        </button>

        <button
          className="btn btn-secondary"
          onClick={handleNext}
          style={{ padding: '5px 12px', fontSize: '11px' }}
        >
          <SkipForward size={12} />
          <span>Next Step</span>
        </button>

        <button
          className="btn btn-secondary"
          onClick={handleReset}
          style={{ padding: '5px 10px', fontSize: '11px' }}
        >
          <RotateCcw size={12} />
        </button>
      </div>

      {/* Step Status Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px' }}>
        <span style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>SYNOPTIC STAGE:</span>
        <strong style={{ color: 'var(--color-text-primary)' }}>{stepLabel}</strong>
        <span className="badge badge-mint mono" style={{ fontSize: '10px', padding: '2px 8px' }}>
          {step + 1} / {totalSteps}
        </span>
      </div>
    </div>
  );
}
