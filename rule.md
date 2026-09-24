# Real-Time Data Ingestion & Live Cyclone Prediction: Operational Rules & Step-by-Step Plan

This document establishes the strict workflow rules and sequential milestones for upgrading the **Cyclone AI** system from simulated/historical mode to **live real-time data ingestion, instant cyclogenesis scanning, and automated cyclone track/risk prediction**.

---

## 📜 Core Operational Rules

1. **Step-by-Step Execution**: Work must proceed strictly in numbered order. No step may begin until the previous step's verification criteria have fully passed.
2. **Mandatory Live Verification at Each Step**:
   - Every step must have an automated Python or test script to verify actual live network fetching, mathematical correctness, or endpoint responses.
   - Mock data is strictly prohibited during live verification passes.
3. **No Breaking Changes**: Existing historical simulation endpoints (`/api/v1/pipeline/run`, `/api/v1/simulation/storms`) must remain 100% operational alongside the new real-time endpoints.
4. **Git Version Control & Push Protocol**:
   - After each milestone is verified and passes all tests, the changes will be staged, committed with a descriptive conventional commit message, and pushed to the upstream repository.

5. **Branching Strategy** *(updated 2026-09-25)*:
   - All step implementations (Step 1 through Step 6) must be developed and pushed on a dedicated feature branch: **`feature/realtime-pipeline`**.
   - `master` is the stable base. No step work is pushed directly to `master`.
   - After all steps pass final verification (Step 6), a Pull Request from `feature/realtime-pipeline` → `master` will be raised for the release merge.

---

## 🗺️ Step-by-Step Implementation Roadmap

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 0: Git Repository & Remote Setup                                                  │
│ • Initialize local git repository if not present                                       │
│ • Ensure .gitignore excludes node_modules, cache, logs, and venv                       │
│ • Link remote repository URL (GitHub/GitLab)                                          │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Real-Time Oceanic & Atmospheric Ingestion Engine                               │
│ • Module: `src/data/realtime_service.py`                                               │
│ • Live query grid: Bay of Bengal (5°N–22°N, 80°E–95°E) & Arabian Sea (5°N–25°N)       │
│ • Features: SST, 200/850 hPa wind shear, 700 hPa RH, surface pressure, 10m wind speed  │
│ ➔ VERIFICATION: Run `scripts/verify_realtime_ingest.py` (Must fetch HTTP 200 live)    │
│ ➔ GIT: Commit & push Step 1                                                            │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Real-Time Cyclogenesis Potential Index (GPI) & Low-Pressure Scanner            │
│ • Module: `src/data/cyclogenesis.py`                                                   │
│ • Evaluates thermodynamic thresholds (SST ≥ 26.5°C, Shear ≤ 15 kt, RH ≥ 75%)          │
│ • Computes Genesis Potential Index (GPI) and probability of cyclonic development       │
│ • Identifies primary vortex center (latitude, longitude) of strongest circulation     │
│ ➔ VERIFICATION: Run `scripts/verify_cyclogenesis.py` (Validate GPI score & coordinates)│
│ ➔ GIT: Commit & push Step 2                                                            │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Live Pipeline Integration (Intensity, Bi-LSTM Track, Landfall, Risk)           │
│ • Module: `src/models/realtime_pipeline.py`                                            │
│ • Connects real-time coordinates to:                                                   │
│   1. Intensity Estimator (Current wind speed & central pressure)                       │
│   2. Rapid Intensification Classifier (XGBoost RI probability)                         │
│   3. Bi-LSTM Track Predictor (+12h, +24h, +36h, +48h trajectory)                      │
│   4. Uncertainty Cone (70% IMD/WMO polygon) & Coastal Risk Engine                       │
│ ➔ VERIFICATION: Run `scripts/verify_realtime_pipeline.py` (Full end-to-end inference)  │
│ ➔ GIT: Commit & push Step 3                                                            │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Production FastAPI Real-Time Endpoints                                         │
│ • Add REST endpoints in `src/api/main.py`:                                             │
│   - `GET /api/v1/realtime/basin-scan`: Scans active basins for cyclonic threats        │
│   - `GET /api/v1/realtime/live-storm`: Returns complete real-time prediction payload   │
│   - `POST /api/v1/realtime/trigger-scan`: Triggers live refresh on demand              │
│ ➔ VERIFICATION: Run `pytest tests/test_realtime_api.py` (Validate HTTP response & JSON)│
│ ➔ GIT: Commit & push Step 4                                                            │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Forecaster Mission-Control Frontend Live Integration                           │
│ • Update `frontend/src/components/Navbar.jsx` with `[🔴 LIVE SATELLITE FEED]` toggle   │
│ • Update `frontend/src/api.js` to call `/api/v1/realtime/live-storm`                   │
│ • Dynamic live status badge: `LIVE TELEMETRY ACTIVE (AUTOREFRESH 15m)`                 │
│ • Render real-time coordinates, live SST, shear, and live projected uncertainty cone   │
│ ➔ VERIFICATION: Frontend build & UI component smoke test via `npm run build`           │
│ ➔ GIT: Commit & push Step 5                                                            │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: Master End-to-End System Verification & Final Release Push                     │
│ • Run master test suite (`python scripts/verify_all.py` + all unit tests)              │
│ • Validate tamper-evident SHA-256 audit chaining for real-time forecast cycles         │
│ ➔ VERIFICATION: All test assertions green, zero regressions                            │
│ ➔ GIT: Final release tag & push to upstream repository                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Detailed Verification Checklist by Step

### Step 0: Git & Remote Setup
- [ ] Initialize git if `.git` does not exist (`git init`)
- [ ] Ensure `.gitignore` ignores `node_modules`, `__pycache__`, `.pytest_cache`, `dist/`
- [ ] Configure remote repository URL (`git remote add origin <URL>`)

### Step 1: Real-Time Ingestion
- [ ] Connect to live Open-Meteo & marine atmospheric endpoints for North Indian Ocean
- [ ] Query coordinates across Bay of Bengal and Arabian Sea
- [ ] Verify live HTTP response (status code 200, valid float values for SST, Shear, RH, Wind)
- [ ] Confirm execution completes in < 3.0 seconds

### Step 2: Cyclogenesis & Threat Scoring
- [ ] Calculate Genesis Potential Index (GPI):
  $$\text{GPI} = |10^5 \eta|^{3/2} \times \left(\frac{\mathcal{H}}{50}\right)^3 \times \left(\frac{V_{pot}}{70}\right)^3 \times (1 + 0.1 \times V_{shear})^{-2}$$
- [ ] Verify cyclogenesis probability score outputs in valid range `[0.0, 1.0]`
- [ ] Verify detection of candidate low-pressure center coordinates `(lat, lon)`

### Step 3: Live Pipeline Integration
- [ ] Pass detected live center into Bi-LSTM track model to produce 4-step forecast
- [ ] Calculate 70% uncertainty cone polygon GeoJSON around forecasted positions
- [ ] Match coordinates with coastal GIS database to extract vulnerable districts
- [ ] Verify pipeline execution time is under 1.5 seconds

### Step 4: FastAPI REST Endpoints
- [ ] `GET /api/v1/realtime/basin-scan` returns HTTP 200 with list of monitored basin sectors
- [ ] `GET /api/v1/realtime/live-storm` returns complete operational schema
- [ ] Swagger documentation at `http://localhost:8000/docs` includes Real-Time tags
- [ ] Write dedicated automated test `tests/test_realtime_api.py`

### Step 5: Frontend Dashboard Live Integration
- [ ] Add `LIVE FEED` vs `HISTORICAL PLAYBACK` mode switch to Navbar
- [ ] In Live Feed mode:
  - Fetch live observation from `/api/v1/realtime/live-storm`
  - Display live atmospheric metrics (SST, wind shear, humidity)
  - Display live cyclogenesis chance gauge and projected track
- [ ] Test frontend compilation with `npm run build` (zero build errors)

### Step 6: Final Verification & Git Push
- [ ] Run full test suite: `python scripts/verify_all.py`
- [ ] Verify SHA-256 audit log records live real-time cycles
- [ ] `git push origin main`
