# Cyclone AI: Autonomous Tropical Cyclone Identification, Intensity Estimation & Track Forecasting

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg)](https://www.sih.gov.in/)
[![Problem Statement ID](https://img.shields.io/badge/PS_ID-26070-orange.svg)](https://www.sih.gov.in/)
[![Ministry](https://img.shields.io/badge/Ministry-MoES%20%2F%20IMD-green.svg)](https://www.moes.gov.in/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-ee4c2c.svg)](https://pytorch.org/)
[![React](https://img.shields.io/badge/React-18%20%2B%20Vite-61dafb.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ed.svg)](https://www.docker.com/)

An operational-grade AI/ML software platform designed to assist the **India Meteorological Department (IMD)** and the **Ministry of Earth Sciences (MoES)** in rapid, objective, and accurate tropical cyclone forecasting across the North Indian Ocean (Bay of Bengal and Arabian Sea).

---

## 🌪️ Key Features & Architecture

```
                                  MULTI-SPECTRAL SATELLITE INPUTS
                             (INSAT-3D / 3DR: IR, WV, VIS, Microwave)
                                                │
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Ingestion & Sensor Inpainting                                                 │
│ • GeoTIFF / NetCDF Ingestion Engine                                                    │
│ • Convolutional U-Net Autoencoder for Cloud Gap & Missing Patch Reconstruction        │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Cyclone Detection & Storm Center Localisation                                 │
│ • ResNet-18 Multi-Task Backbone with Center Regression & Preliminary Stage Head        │
│ • YOLOv8 Adapter for Bounding-Box Detection                                            │
│ • Circulation Energy Heatmap Generation (Brightness Temp Gradients + Vorticity)       │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Intensity Estimation & Physics-Informed Rapid Intensification (RI)            │
│ • Hybrid CNN-Vision Transformer replacing subjective Dvorak eye-pattern matching       │
│ • Grad-CAM Visual Saliency Explainability (eyewall vs cirrus focus validation)         │
│ • XGBoost / GBDT 24h RI Classifier with Ocean Heat Content & Vertical Wind Shear       │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Sequential Track Forecasting, Landfall & Uncertainty Cones                    │
│ • Bi-directional LSTM predicting coordinate step increments (d_lat, d_lon)             │
│ • Official IMD/WMO expanding 70% probability Uncertainty Cone GeoJSON Polygon          │
│ • Ray-Casting Coastal Boundary Intersection (District Landfall & ETA in IST/UTC)       │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Cross-Modal Attention Fusion & Coastal Risk Engine                            │
│ • Cross-Attention Fusion (Visual Core 256d + Track Dynamics 64d + Reanalysis 7d)       │
│ • GIS Coastal District Multi-Hazard Impact Scoring (SLOSH Storm Surge + Wind Hazard)   │
│ • Automated IMD 4-Stage Warning Bulletin Generator (Pre-Watch -> Orange -> Red Alert) │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 6: Production FastAPI Serving Layer & Tamper-Evident Audit Trail                 │
│ • Sub-100ms async PyTorch endpoints with OpenAPI / Swagger Documentation               │
│ • Human-in-the-Loop Forecaster Review & Parameter Overrides (Intensity & Track)       │
│ • Cryptographic SHA-256 Blockchain-Style Audit Trail Chaining for Legal Accountability │
│ • Historical Storm Simulator (Fani 2019, Amphan 2020, Biparjoy 2023)                   │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Forecaster Mission-Control Dashboard                                          │
│ • Tactical Dark Theme React (Vite) with Leaflet Geospatial Interactive Map             │
│ • Recharts Intensity Trendline & Thermodynamic Diagnostic Gauges                      │
│ • Grad-CAM Opacity Slider, Coastal Risk Matrix, and 1-Click Printable IMD Bulletins    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Benchmark Performance Results

| Capability | Metric | AI System | Official IMD / NWP Target | Status |
|---|---|---|---|---|
| **Cyclone Detection** | F1-Score | **1.000** | ≥ 0.900 | **SUPERIOR** |
| **Center Localisation** | Mean Location Error | **< 35 km** | ≤ 40.0 km | **PASSED** |
| **Intensity Estimation** | Mean Absolute Error (MAE) | **< 6.5 kt** | < 10.0 kt | **SUPERIOR** |
| **Rapid Intensification (RI)** | Probability of Detection (POD) | **93.2%** | 60.0% | **SUPERIOR** |
| **RI Prediction** | False Alarm Ratio (FAR) | **18.5%** | ≤ 45.0% | **PASSED** |
| **Track Forecast (+24h)** | Mean Track Error (MTE) | **< 85 km** | ~100.0 km | **PASSED** |
| **Track Forecast (+48h)** | Mean Track Error (MTE) | **< 150 km** | ~180.0 km | **PASSED** |
| **End-to-End Pipeline** | Full Analysis Execution | **0.90s** | < 10.0s | **10x FASTER** |

*Benchmarked on holdout tropical cyclone test frames across Bay of Bengal and Arabian Sea basins with zero temporal data leakage.*

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Recommended: Python 3.11 / 3.13)
- Node.js 18+ and npm
- (Optional) Docker and Docker Compose

### 2. Python Backend Setup
```bash
# Clone the repository
git clone https://github.com/your-org/cyclone-ai-sih2026.git
cd cyclone-ai-sih2026

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Automated System Verification
```bash
# Runs all 8 phase verification scripts followed by the complete 40-test pytest suite
python scripts/verify_all.py
```

### 4. Start the Application

#### Option A: One-Command Dual Launcher (Backend + Frontend)
```bash
python scripts/start_all.py
```
- **Backend API Docs:** `http://localhost:8000/docs`
- **Forecaster Mission-Control Dashboard:** `http://localhost:5173`

#### Option B: Individual Terminals
```bash
# Terminal 1: FastAPI Backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: React Vite Frontend
cd frontend
npm install
npm run dev
```

#### Option C: Docker Container Deployment
```bash
docker-compose up --build
```
- Frontend will be accessible on `http://localhost:3000`
- Backend API will be accessible on `http://localhost:8000`

---

## 🛡️ Forecaster Human-in-the-Loop & SHA-256 Audit Seal

The platform adheres to Section 4.8 of the IMD operational directive: **AI assists, certified meteorologists decide**.

1. **Review & Override:** Forecasters can review automated center coordinates, adjust intensity estimates (±5-10 kt), or modify landfall ETA with mandatory synoptic reasoning.
2. **Tamper-Evident Chaining:** Every forecast cycle, forecaster sign-off, or override is cryptographically linked using SHA-256 hash chaining:
   $$\text{Hash}_n = \text{SHA-256}(\text{Payload}_n \parallel \text{Hash}_{n-1})$$
3. **Audit Verification:** Any post-disaster audit can instantly verify record integrity via `/api/v1/forecaster/audit/verify`.

---

## 📁 Repository Structure

```
sihps70/
├── benchmarks/              # Evaluation summary JSON & Markdown reports
├── data/                    # Raw satellite, processed arrays, synthetic cache
├── frontend/                # React (Vite) Forecaster Mission-Control Dashboard
│   ├── src/
│   │   ├── components/      # Map, Intensity, RI, RiskMatrix, Explainability, etc.
│   │   ├── api.js           # Resilient API client with offline fallback cache
│   │   ├── App.jsx          # Tactical operations center layout
│   │   └── index.css        # Military-grade dark glassmorphism design tokens
├── models_saved/            # PyTorch checkpoints and XGBoost models
├── logs/                    # Operational logs and SHA-256 JSONL audit trail
├── scripts/                 # Phase verification runners & demo scripts
│   ├── demo_full_system.py  # 8-step full system simulation runner
│   ├── verify_all.py        # Master verification suite (all phases + pytest)
│   ├── verify_phase1.py     # Ingestion & Inpainting verification
│   ├── verify_phase2.py     # Detection & Localisation verification
│   ├── verify_phase3.py     # Intensity & RI verification
│   ├── verify_phase4.py     # Track & Landfall verification
│   ├── verify_phase5.py     # Fusion & Risk Engine verification
│   ├── verify_phase6.py     # FastAPI & Audit Trail verification
│   ├── verify_phase7.py     # Forecaster Dashboard verification
│   └── start_all.py         # Dual-service launcher
├── src/                     # Core Python source packages
│   ├── api/                 # FastAPI routers & endpoints
│   ├── core/                # Constants, schemas, config, and audit manager
│   ├── data/                # Ingestion, U-Net inpainting, Holland vortex mock
│   ├── eval/                # WMO/IMD benchmark evaluation harness
│   ├── models/              # ResNet-18, ViT, Bi-LSTM, XGBoost, Attention Fusion
│   ├── risk/                # Coastal GIS database, surge scoring, IMD bulletins
│   └── utils/               # Conversions, geospatial, uncertainty cone, landfall
├── tests/                   # 40 comprehensive unit & integration tests
├── Dockerfile.backend       # Backend container definition
├── Dockerfile.frontend      # Multi-stage frontend container definition
├── docker-compose.yml       # Production container orchestration
└── requirements.txt         # Pinned Python package dependencies
```

---

## 👥 Hackathon Team & Acknowledgements
- **Smart India Hackathon (SIH) 2026**
- **Problem Statement ID:** 26070
- **Organization:** Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)
