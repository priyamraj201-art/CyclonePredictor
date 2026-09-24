# Implementation Plan: AI/ML-Based Tropical Cyclone System (SIH 2026 - PS 26070)

Build an end-to-end, operational-grade AI/ML system to identify, classify, and predict tropical cyclone patterns in the North Indian Ocean (Bay of Bengal and Arabian Sea), designed for the Ministry of Earth Sciences (MoES) and the India Meteorological Department (IMD).

## User Review Required

> [!IMPORTANT]
> The system is architected as an **8-phase progressive build** with immediate standalone testability via physics-based synthetic satellite and environmental generators (simulating INSAT-3D/3DR 4-channel imagery and ERA5 tabular reanalysis). This enables complete local development, unit testing, and demonstration without requiring immediate external multi-gigabyte satellite archive downloads.

> [!NOTE]
> We will implement the full stack:
> 1. Python ML Engine (PyTorch, Torchvision, Scikit-learn, XGBoost, Grad-CAM, GeoJSON)
> 2. FastAPI Production Inference Backend with SHA-256 Tamper-Evident Audit Trail
> 3. React + Leaflet + Chart.js Forecaster Mission-Control Dashboard

---

## Proposed System Architecture & Modules

```mermaid
flowchart TD
    subgraph DataEngine["1. Data Engine & Inpainting"]
        RAW[Multi-Channel Satellite & ERA5 Data] --> AE[PyTorch Inpainting Autoencoder]
        AE --> NORM[Normalized Tensor (4, 256, 256)]
    end

    subgraph CoreModels["2. Core Model Heads"]
        NORM --> DET[Cyclone Detection & Centre Localisation]
        NORM --> INT[Intensity Regression + Grad-CAM]
        NORM --> RI[Rapid Intensification XGBoost/Tabular]
        NORM --> TRK[Track Forecaster + Uncertainty Cone]
    end

    subgraph FusionAndRisk["3. Fusion & Coastal Risk Engine"]
        DET & INT & RI & TRK --> FUS[Multimodal Fusion & Attention]
        FUS --> RISK[GIS Coastal Vulnerability & Storm Surge Engine]
        RISK --> BLT[Automated IMD Warning Bulletin]
    end

    subgraph OpsAndTrust["4. Operations & Forecaster Trust"]
        BLT --> API[FastAPI Serving Layer]
        API --> AUD[SHA-256 Hashed Audit Trail]
        API --> UI[React + Leaflet Forecaster Mission Control]
    end
```

---

## Proposed Changes

### Phase 1: Core Schemas, Data Ingestion & Autoencoder Inpainting
Set up the foundational workspace, domain models, synthetic physical data generators, and inpainting autoencoder.

#### [NEW] [src/core/schemas.py](file:///d:/code/sihps70/src/core/schemas.py)
- IMD intensity enums: `Low Pressure Area (LPA)`, `Depression (D)`, `Deep Depression (DD)`, `Cyclonic Storm (CS)`, `Severe Cyclonic Storm (SCS)`, `Very Severe Cyclonic Storm (VSCS)`, `Extremely Severe Cyclonic Storm (ESCS)`, `Super Cyclonic Storm (SuCS)`.
- Pydantic models: `SatelliteFrameMeta`, `EnvironmentalFeatures`, `BestTrackPoint`, `CycloneObservation`, `ForecasterAction`.

#### [NEW] [src/core/constants.py](file:///d:/code/sihps70/src/core/constants.py)
- IMD wind thresholds, Bay of Bengal and Arabian Sea spatial bounds, physical constants, standard uncertainty cone radii.

#### [NEW] [src/data/mock_generator.py](file:///d:/code/sihps70/src/data/mock_generator.py)
- Physics-based synthetic generator producing 4-channel tensors (IR $10.8\,\mu\text{m}$, WV $6.7\,\mu\text{m}$, VIS $0.65\,\mu\text{m}$, PMW $89\,\text{GHz}$) using Holland/Rankine vortex equations with realistic cloud obscuration and sensor noise masks.
- Corresponding historical IBTrACS trajectories and ERA5 thermodynamic variables (SST, vertical wind shear, relative humidity, OHC).

#### [NEW] [src/data/autoencoder.py](file:///d:/code/sihps70/src/data/autoencoder.py) & [src/data/preprocessing.py](file:///d:/code/sihps70/src/data/preprocessing.py)
- PyTorch convolutional autoencoder for masked-patch inpainting of missing satellite scans.
- Preprocessing pipeline: calibration, brightness temperature normalization ($[0, 1]$), spatial registration, and tensor formatting.

---

### Phase 2: Cyclone Detection & Centre Localisation Engine
#### [NEW] [src/models/detection.py](file:///d:/code/sihps70/src/models/detection.py)
- PyTorch dual-head network (ResNet-18 / EfficientNet backbone):
  - Binary classification: cyclonic presence vs ambient atmosphere.
  - Continuous regression: normalized $(x, y)$ coordinates of circulation center.
  - Multi-class stage classifier: Depression vs Cyclonic Storm vs Severe+.
- Interface adapter for YOLOv8 bounding box and center extraction.

#### [NEW] [src/utils/geospatial.py](file:///d:/code/sihps70/src/utils/geospatial.py)
- Coordinate transformation between satellite pixel space and geographic decimal Lat/Lon.
- Haversine distance calculator for computing center localisation error in kilometers.

---

### Phase 3: Intensity Estimation, Rapid Intensification & Grad-CAM Explainability
#### [NEW] [src/models/intensity.py](file:///d:/code/sihps70/src/models/intensity.py)
- CNN + Self-Attention feature extractor predicting maximum sustained wind speed (knots) and central pressure deficit (hPa) with heteroscedastic uncertainty.
- Conversion functions from wind speed to IMD operational categories.

#### [NEW] [src/models/rapid_intensification.py](file:///d:/code/sihps70/src/models/rapid_intensification.py)
- GBDT / tabular neural model predicting Rapid Intensification ($\ge 30\text{ kt}$ increase within 24h) from SST, vertical wind shear, relative humidity, and upper-ocean heat content, with class weighting and focal loss.

#### [NEW] [src/models/explainability.py](file:///d:/code/sihps70/src/models/explainability.py)
- Grad-CAM visual saliency engine generating heatmaps highlighting eyewall and convective feeder bands, with base64 export for frontend overlay.

---

### Phase 4: Track Forecasting, Landfall Prediction & Uncertainty Cones
#### [NEW] [src/models/track.py](file:///d:/code/sihps70/src/models/track.py)
- PyTorch LSTM/GRU sequence model predicting incremental $(\Delta \text{lat}, \Delta \text{lon})$ at $+6\text{h}$, $+12\text{h}$, $+24\text{h}$, and $+48\text{h}$ lead times.

#### [NEW] [src/utils/uncertainty_cone.py](file:///d:/code/sihps70/src/utils/uncertainty_cone.py)
- Computes expanding error radii ($30\text{ km}$, $55\text{ km}$, $100\text{ km}$, $180\text{ km}$) and generates smooth GeoJSON polygons representing the standard 70% probability envelope.

#### [NEW] [src/utils/landfall.py](file:///d:/code/sihps70/src/utils/landfall.py)
- North Indian Ocean coastal boundary ray-casting to detect landfall coordinates, district/state identification, estimated time of arrival (ETA in UTC/IST), and intensity at landfall.

---

### Phase 5: Multimodal Fusion & Dynamic Coastal Risk Assessment
#### [NEW] [src/models/fusion.py](file:///d:/code/sihps70/src/models/fusion.py)
- Cross-modal attention mechanism fusing visual latent embeddings, track velocity vectors, and thermodynamic tabular features into a unified 128-dimensional representation.

#### [NEW] [src/risk/risk_assessment.py](file:///d:/code/sihps70/src/risk/risk_assessment.py)
- GIS coastal districts database (Odisha, Andhra Pradesh, Tamil Nadu, West Bengal, Gujarat, Maharashtra).
- Multi-hazard impact estimation: gale/storm wind swaths, storm surge heights (meters), convective heavy rainfall tiers, and composite risk scoring ($0-100$).

#### [NEW] [src/risk/bulletin_generator.py](file:///d:/code/sihps70/src/risk/bulletin_generator.py)
- Automated generation of official IMD cyclone warning bulletins (Pre-Cyclone Watch, Cyclone Alert, Cyclone Warning, Post-Landfall Outlook).

---

### Phase 6: FastAPI Serving Layer & Cryptographic Audit Trail
#### [NEW] [src/core/audit.py](file:///d:/code/sihps70/src/core/audit.py)
- Cryptographic SHA-256 blockchain-style hash chain logging all model predictions, forecaster review sign-offs, and parameter overrides with tamper-verification.

#### [NEW] [src/api/main.py](file:///d:/code/sihps70/src/api/main.py) & [src/api/routes.py](file:///d:/code/sihps70/src/api/routes.py)
- REST endpoints:
  - `/api/v1/health`
  - `/api/v1/detect`
  - `/api/v1/intensity`
  - `/api/v1/ri`
  - `/api/v1/track`
  - `/api/v1/risk`
  - `/api/v1/bulletin`
  - `/api/v1/pipeline/full-run`
  - `/api/v1/simulation/playback`
  - `/api/v1/forecaster/review` & `/api/v1/forecaster/audit/verify`

---

### Phase 7: Forecaster Mission-Control Dashboard (React + Leaflet + Chart.js)
#### [NEW] [frontend/](file:///d:/code/sihps70/frontend)
- Modern Vite + React tactical dashboard:
  - Interactive Leaflet.js map with satellite layer, track forecast, uncertainty cone polygon, and district risk heatmaps.
  - Grad-CAM visual saliency viewer with opacity slider over infrared satellite imagery.
  - Chart.js intensity progression & rapid intensification gauge.
  - Forecaster Human-in-the-Loop review & override panel with SHA-256 audit badge.
  - Live simulation playback controls (Play, Pause, Step Forward) for historic storm scenarios (e.g. Cyclone Fani, Amphan, Biparjoy).

---

### Phase 8: Evaluation Harness, Benchmarks & Deployment
#### [NEW] [src/eval/benchmark.py](file:///d:/code/sihps70/src/eval/benchmark.py)
- Computes official metrics: Detection F1, Center Localisation Error (km), Intensity MAE & RMSE (knots), RI POD / FAR / CSI, Track Error (km) at 24h and 48h with temporal split validation.

#### [NEW] [scripts/demo_full_system.py](file:///d:/code/sihps70/scripts/demo_full_system.py) & [scripts/verify_all.py](file:///d:/code/sihps70/scripts/verify_all.py)
- One-command end-to-end simulation script demonstrating ingestion $\to$ inpainting $\to$ detection $\to$ intensity $\to$ track $\to$ risk $\to$ forecaster sign-off $\to$ bulletin output.
- Automated test runner verifying all phases.

#### [NEW] [docker-compose.yml](file:///d:/code/sihps70/docker-compose.yml), [Dockerfile.backend](file:///d:/code/sihps70/Dockerfile.backend), [Dockerfile.frontend](file:///d:/code/sihps70/Dockerfile.frontend)
- Turnkey multi-container deployment setup.

---

## Verification Plan

### Automated Tests
- `pytest tests/test_phase1_data.py`: Tests synthetic generation, schema validation, and autoencoder inpainting.
- `pytest tests/test_phase2_detection.py`: Tests cyclone detection, center coordinates, and Haversine distance calculations.
- `pytest tests/test_phase3_intensity_ri.py`: Tests wind speed regression, IMD category mapping, RI classifier, and Grad-CAM generation.
- `pytest tests/test_phase4_track.py`: Tests LSTM multi-step track prediction, GeoJSON uncertainty cone generation, and landfall detection.
- `pytest tests/test_phase5_risk.py`: Tests multimodal fusion attention, district risk scoring, and IMD bulletin generation.
- `pytest tests/test_phase6_api.py`: Tests FastAPI endpoints, simulation playback, and SHA-256 tamper detection.
- `python scripts/verify_all.py`: Master test suite executing all tests and outputting a benchmark report.

### Manual / Operational Verification
- Start FastAPI server on port 8000 and verify Swagger docs at `http://localhost:8000/docs`.
- Launch React dashboard on port 5173 / 3000 and test:
  1. Live playback of simulated cyclone trajectory.
  2. Toggle of Grad-CAM visual saliency overlay over raw infrared imagery.
  3. Interactive forecaster review: modify wind speed, approve bulletin, and verify that the SHA-256 audit record updates correctly.
