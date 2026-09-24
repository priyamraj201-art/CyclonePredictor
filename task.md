# Cyclone AI — Master Phase-Wise Implementation Task Board
**Tracking Document: Operationalization of `architecture.md` & UI Modernization of `design.md`**  
**Target Ministry:** Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)  
**Problem Statement ID:** 26070 | Disaster Management

---

## 📋 Project Roadmap Overview

```
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   IMPLEMENTATION TIMELINE                                        │
 ├─────────┬──────────────────────────────────────────┬──────────────────────┬──────────────────────┤
 │ Phase   │ Scope & Module                           │ Primary Technology   │ Target Completion    │
 ├─────────┼──────────────────────────────────────────┼──────────────────────┼──────────────────────┤
 │ Phase 1 │ Real-World Multi-Source Ingestion Engine │ h5py, NetCDF4, CDS   │ Sprint 1             │
 │ Phase 2 │ Preprocessing, Calibration & Projection  │ GDAL, Rasterio, U-Net│ Sprint 1 - 2         │
 │ Phase 3 │ Historical Curation & Model Training     │ PyTorch, ViT, XGBoost│ Sprint 2 - 3         │
 │ Phase 4 │ PostgreSQL 16 + PostGIS 3.4 Migration    │ PostGIS, SQLAlchemy  │ Sprint 3             │
 │ Phase 5 │ Production Serving & Low-Latency Runtime │ ONNX, TensorRT, FastAPI│ Sprint 4           │
 │ Phase 6 │ Forecaster Review & Cryptographic Audit  │ SHA-256, Ed25519     │ Sprint 4             │
 │ Phase 7 │ Government Alert Dissemination (CAP/GTS) │ OASIS CAP XML, BUFR  │ Sprint 5             │
 │ Phase 8 │ High-Availability Deployment & Failover  │ Kubernetes, MinIO, DR│ Sprint 5             │
 │ Phase 9 │ Minimalist Black-White-Blue UI (At Last) │ React 18, Leaflet, CSS│ Sprint 6 (Final)    │
 └─────────┴──────────────────────────────────────────┴──────────────────────┴──────────────────────┘
```

---

## Phase 1: Real-World Multi-Source Data Ingestion Engine

**Objective:** Replace the synthetic Holland vortex generator with real, automated ingestion pipelines for operational satellite, atmospheric, and oceanographic data sources.

- [ ] **Task 1.1: ISRO MOSDAC INSAT-3D/3DR Ingestion Driver**
  - **Target File:** `src/data/ingestion_mosdac.py`
  - **Description:** Implement an authenticated automated SFTP/REST client to ingest 15-minute INSAT-3D/3DR Level-1B and Level-2B HDF5 (`.h5`) files from MOSDAC.
  - **Channels Handled:** `TIR1` ($10.8\,\mu\text{m}$), `TIR2` ($12.0\,\mu\text{m}$), `WV` ($6.7\,\mu\text{m}$), `MIR` ($3.9\,\mu\text{m}$), `VIS` ($0.65\,\mu\text{m}$).
  - **Verification:** Unit tests confirming valid extraction of raw digital count arrays and metadata payloads.

- [ ] **Task 1.2: ECMWF ERA5 & GFS Reanalysis Connector**
  - **Target File:** `src/data/ingestion_era5.py`
  - **Description:** Build a Climate Data Store (CDS) API client to download and parse GRIB2/NetCDF atmospheric grids.
  - **Variables Extracted:** Sea Surface Temperature ($\text{SST}$), Vertical Wind Shear ($200 - 850\,\text{hPa}$), Relative Humidity at $700\,\text{hPa}$, Vorticity at $850\,\text{hPa}$, and Ocean Heat Content ($\text{OHC}$).
  - **Verification:** Verification script parsing a regional slice $[5^\circ\text{N} - 25^\circ\text{N}, 80^\circ\text{E} - 100^\circ\text{E}]$ into uniform arrays.

- [ ] **Task 1.3: NOAA & IMD Best-Track (IBTrACS) Ingestion**
  - **Target File:** `src/data/ingestion_ibtracs.py`
  - **Description:** Parse NOAA IBTrACS (v04r00) North Indian Ocean CSV archive and IMD official cyclone e-Atlas reports (1999–2025).
  - **Output Schema:** 3-hourly time-series containing storm center $(\text{lat}, \text{lon})$, pressure, max sustained wind, and Dvorak T-number.
  - **Verification:** Script verifying ground-truth alignment for historical storms (*Fani*, *Amphan*, *Biparjoy*).

- [ ] **Task 1.4: Scatterometer Ocean Wind Vector Ingestion**
  - **Target File:** `src/data/ingestion_scatsat.py`
  - **Description:** Ingest SCATSAT-1 and Oceansat-3 OSCAT Level-2B $12.5\,\text{km}$ vector wind grids to detect early surface circulation centers before eye formation.

---

## Phase 2: Sensor Calibration, Inpainting & Spatial Reprojection

**Objective:** Transform raw satellite detector counts into calibrated, georeferenced, and cloud-inpainted tensors ready for deep learning inference.

- [ ] **Task 2.1: Radiometric Calibration & Planck Inversion**
  - **Target File:** `src/data/calibration.py`
  - **Description:** Implement lookup-table (LUT) and Planck function inversion to convert raw digital counts into physical Brightness Temperatures ($T_B$) in Kelvin ($180\,\text{K} - 310\,\text{K}$) and Visible Albedo ($0.0 - 1.0$).
  - **Verification:** Bounds assertion verifying $180 \le T_B \le 310$ across all valid pixels.

- [ ] **Task 2.2: Geospatial Reprojection Engine (`Rasterio` / `GDAL`)**
  - **Target File:** `src/data/reprojection.py`
  - **Description:** Reproject geostationary coordinate matrices (`+proj=geos +lon_0=74.0` for INSAT-3D, `+lon_0=82.0` for INSAT-3DR) into standard World Geodetic System 1984 (`EPSG:4326`).
  - **Output:** Resampled uniform $256 \times 256$ spatial patches centered over the Bay of Bengal or Arabian Sea basin.

- [ ] **Task 2.3: Production U-Net Cloud-Gap Inpainting Model**
  - **Target File:** `src/data/autoencoder.py`
  - **Description:** Train and export a lightweight PyTorch U-Net with partial convolutions to reconstruct sensor striping, missing scan lines, and high-altitude cirrus obstructions.
  - **Verification:** Masked reconstruction benchmark achieving $\text{PSNR} \ge 34\,\text{dB}$ on holdout satellite patches.

---

## Phase 3: Historical Curation & Production Model Training

**Objective:** Train, evaluate, and save real production checkpoints using 25 years of North Indian Ocean cyclone events (2000–2025).

- [ ] **Task 3.1: Historical Dataset Synchronization & Splitting**
  - **Target File:** `scripts/prepare_historical_dataset.py`
  - **Description:** Align 15-minute INSAT imagery with 3-hourly IBTrACS best-track points using cubic spline interpolation. Partition into strict chronologically split sets:
    - Training Set: 2000–2018 (e.g., *Phailin*, *Hudhud*)
    - Validation Set: 2019–2021 (e.g., *Fani*, *Amphan*, *Tauktae*)
    - Benchmark Test Set: 2022–2025 (e.g., *Biparjoy*, *Michaung*, *Remal*)
  - **Leakage Prevention:** Zero temporal data leakage across storm lifecycles.

- [ ] **Task 3.2: ResNet-50 Cyclone Detection & Center Localizer Training**
  - **Target File:** `src/models/train_detection.py`
  - **Description:** Fine-tune ResNet-50 / ConvNeXt backbone with compound Haversine loss to regress storm centers $(\text{lat}, \text{lon})$.
  - **Target Metric:** Mean Localisation Error $\le 35.0\,\text{km}$ on the test set.

- [ ] **Task 3.3: Vision Transformer (ViT-B/16) Intensity Estimator Training**
  - **Target File:** `src/models/train_intensity.py`
  - **Description:** Train ViT-B/16 with multi-head self-attention on multi-spectral patches combined with Grad-CAM eyewall attention regularization.
  - **Target Metric:** Mean Absolute Error (MAE) $< 6.5\,\text{kt}$ against official IMD best-track wind speeds.

- [ ] **Task 3.4: XGBoost / LightGBM Rapid Intensification (RI) Classifier**
  - **Target File:** `src/models/train_ri.py`
  - **Description:** Train GBDT classifier using Focal Loss on environmental features ($\text{SST}, \text{VWS}, \text{OHC}, \text{RH}_{700}$) combined with ViT latent embeddings.
  - **Target Metric:** Probability of Detection ($\text{POD}$) $\ge 85\%$ and False Alarm Ratio ($\text{FAR}$) $\le 25\%$.

- [ ] **Task 3.5: Spatio-Temporal Track Forecasting Model**
  - **Target File:** `src/models/train_track.py`
  - **Description:** Train Bi-directional LSTM with attention over $+6\text{h}, +12\text{h}, +24\text{h}, +48\text{h}$ coordinate increments with $500\,\text{hPa}$ steering flow integration.
  - **Target Metric:** $+24\text{h}$ Mean Track Error $< 80\,\text{km}$ (exceeding IMD operational target of $100\,\text{km}$).

- [ ] **Task 3.6: MLflow Experiment Tracking & Model Registry**
  - **Target File:** `src/core/model_registry.py`
  - **Description:** Version all model checkpoints, hyperparameters, and confusion matrices in an automated MLflow tracking registry.

---

## Phase 4: PostgreSQL 16 + PostGIS 3.4 Spatial Database Migration

**Objective:** Replace in-memory dictionaries and JSONL mock storage with a production geospatial database cluster.

- [ ] **Task 4.1: PostGIS Database Schemas & Alembic Migrations**
  - **Target Files:** `alembic/versions/*`, `src/core/database.py`
  - **Description:** Implement relational schemas with PostGIS spatial types:
    - `storms` table (UUID, name, basin, genesis timestamp, status).
    - `observations` table (`GEOMETRY(Point, 4326)` storm centers, intensity, pressure, category).
    - `forecast_tracks` table (`GEOMETRY(LineString, 4326)`, lead time, timestamps).
    - `uncertainty_cones` table (`GEOMETRY(Polygon, 4326)` 70% confidence swath).
    - `coastal_districts` table (`GEOMETRY(MultiPolygon, 4326)` district boundaries, population, bathymetry slope).

- [ ] **Task 4.2: High-Performance Spatial Query Engine**
  - **Target File:** `src/risk/spatial_engine.py`
  - **Description:** Implement native PostGIS queries (`ST_Intersects`, `ST_Buffer`, `ST_Distance`) to identify impacted coastal districts and compute high-resolution SLOSH storm surge heights.

---

## Phase 5: Production Model Serving & Low-Latency Runtime

**Objective:** Build an optimized, sub-100ms asynchronous serving layer capable of real-time multi-client operations.

- [ ] **Task 5.1: ONNX Runtime & NVIDIA TensorRT Export**
  - **Target File:** `scripts/export_tensorrt.py`
  - **Description:** Convert PyTorch model checkpoints (`.pt`) into optimized ONNX and TensorRT engine binaries with FP16 precision.
  - **Target Performance:** Sub-50ms forward pass on GPU, sub-150ms on CPU INT8 fallback.

- [ ] **Task 5.2: Asynchronous FastAPI Inference Pipelines**
  - **Target File:** `src/api/main.py`
  - **Description:** Update REST endpoints to use non-blocking async DB connection pools (`asyncpg`), Celery background task delegation, and Redis response caching.

- [ ] **Task 5.3: WebSocket Live Telemetry Feed**
  - **Target File:** `src/api/websocket_feed.py`
  - **Description:** Implement WebSocket streaming `/api/v1/stream/storm/{storm_id}` to push live coordinates, sensor updates, and alerts to connected forecaster dashboards without polling.

---

## Phase 6: Operational Forecaster Workflow & Cryptographic Audit Ledger

**Objective:** Comply with IMD operational directives and legal standards under the Disaster Management Act 2005.

- [ ] **Task 6.1: Human-in-the-Loop Override Interface**
  - **Target File:** `src/api/routers/forecaster.py`
  - **Description:** Endpoint `/api/v1/forecaster/review` supporting certified forecaster overrides of center coordinates $(\Delta\text{lat}, \Delta\text{lon})$ and intensity ($\pm 5 - 10\,\text{kt}$) with mandatory synoptic reasoning field.

- [ ] **Task 6.2: Distributed SHA-256 Tamper-Evident Hash Chaining**
  - **Target File:** `src/core/audit.py`
  - **Description:** Implement continuous cryptographic hash chaining:
    $$\text{Hash}_n = \text{SHA-256}\left(\text{Hash}_{n-1} \parallel \text{Timestamp} \parallel \text{ForecasterID} \parallel \text{Payload} \parallel \text{Signature}\right)$$
  - **Verification:** Verification utility `/api/v1/forecaster/audit/verify` ensuring zero unauthorized alterations to advisory history.

---

## Phase 7: Government Alert Dissemination & External Integrations

**Objective:** Automate distribution of warning advisories to national disaster authorities.

- [ ] **Task 7.1: OASIS Common Alerting Protocol (CAP v1.2) Generator**
  - **Target File:** `src/risk/cap_generator.py`
  - **Description:** Auto-generate validated WMO/OASIS CAP v1.2 XML warning payloads for integration into the NDMA Sachet portal.

- [ ] **Task 7.2: IMD GTS & Alphanumeric Bulletin Exporter**
  - **Target File:** `src/risk/bulletin_generator.py`
  - **Description:** Format cyclone warnings into official WMO Tropical Cyclone Advisory (TCA) and national bulletin text standards.

- [ ] **Task 7.3: SEOC & SMS Broadcast Webhook Engine**
  - **Target File:** `src/risk/webhooks.py`
  - **Description:** Push notifications to State Emergency Operation Centers (Odisha, Andhra Pradesh, West Bengal, Tamil Nadu, Gujarat) and automated bilingual SMS gateways.

---

## Phase 8: High-Availability Deployment & Disaster Recovery

**Objective:** Ensure continuous 24/7 uptime during extreme weather emergencies.

- [ ] **Task 8.1: Container Orchestration (Docker & Kubernetes)**
  - **Target Files:** `k8s/deployment.yaml`, `k8s/services.yaml`, `k8s/ingress.yaml`
  - **Description:** Kubernetes deployment manifests with Horizontal Pod Autoscaling (HPA) for FastAPI workers and GPU Triton servers.

- [ ] **Task 8.2: Distributed S3 Object Store (MinIO)**
  - **Target File:** `docker-compose.prod.yml`
  - **Description:** High-availability MinIO cluster for multi-terabyte raw and processed satellite rasters.

- [ ] **Task 8.3: Active-Passive Multi-Region Failover Architecture**
  - **Target File:** `scripts/dr_failover.py`
  - **Description:** Disaster recovery automated failover between IMD New Delhi (Primary) and IITM/INCOIS Pune/Hyderabad (Secondary DR) with RPO $< 5\text{ min}$ and RTO $< 60\text{ sec}$.

---

## Phase 9: Modernize Frontend to Minimalist Black, White & Blue Design System (AT LAST)

**Objective:** Implement the minimal design specifications defined in [`design.md`](file:///d:/code/sihps70/design.md), transforming the frontend into a clean, tactical mission-control dashboard.

- [x] **Task 9.1: Refactor CSS Design Tokens in `frontend/src/index.css`**
  - **Target File:** `frontend/src/index.css`
  - **Description:** 
    - Replaced existing multi-color variables with the strict **Black, White, and Blue token system**:
      - Backgrounds: Pure Black (`#000000`), Obsidian (`#08090C`), Dark Slate (`#0F1218`).
      - Borders: Hairline subtle gray (`#1F2430`) and focused cobalt (`#1E3A8A`).
      - Text: High-contrast Pure White (`#FFFFFF`) and Cloud White (`#F1F5F9`).
      - Accents: Technical Cobalt (`#1D4ED8`), Electric Blue (`#3B82F6`, `#60A5FA`), Ice Blue (`#BAE6FD`).
    - Purged heavy glowing shadows and rainbow gradients.
    - Standardized font hierarchy (`Inter` for UI, `JetBrains Mono` for coordinates and wind telemetry).

- [x] **Task 9.2: Modernize Top Mission-Control Bar (`Navbar.jsx`)**
  - **Target File:** `frontend/src/components/Navbar.jsx`
  - **Description:** 
    - Applied Obsidian background (`#08090C`) with hairline bottom border (`#1F2430`).
    - Crisp white system title (`CYCLONE AI // MISSION CONTROL`).
    - Monospaced real-time UTC / IST dual clocks.
    - Minimalist status pills with cobalt active indicators.

- [x] **Task 9.3: Refactor Map Component to CartoDB Monochrome (`Map/`)**
  - **Target File:** `frontend/src/components/Map/CycloneMap.jsx`
  - **Description:** 
    - Switched tile layer to CartoDB Dark Matter for distraction-free grayscale geography.
    - Rendered cyclone track in sharp Electric Blue (`#3B82F6`).
    - Uncertainty cone with subtle translucent cobalt fill (`rgba(59, 130, 246, 0.14)`) and sharp hairline boundary.
    - Storm center reticle in dual-ring Pure White and Cobalt.

- [x] **Task 9.4: Modernize Diagnostic Charts (`Intensity/` & `RapidIntensification/`)**
  - **Target Files:** `frontend/src/components/Intensity/IntensityCard.jsx`, `frontend/src/components/RapidIntensification/RICard.jsx`
  - **Description:** 
    - Restyled Recharts components: monochrome dark gridlines (`#334155`), vertical cobalt area gradient, pure white tooltips.
    - Replaced rainbow severity badges with the **Luminance-Ranked Blue-to-White scale**.
    - Displayed wind speeds and pressure values in bold, oversized monospaced typography (`JetBrains Mono`, $30\,\text{px}$).

- [x] **Task 9.5: Clean Modernization of Coastal Risk Matrix (`RiskMatrix/`)**
  - **Target File:** `frontend/src/components/RiskMatrix/RiskMatrix.jsx`
  - **Description:** 
    - Minimalist table styling with hairline dividers.
    - Risk rankings rendered in crisp monospaced labels with subtle blue accents instead of bright red/yellow clutter.

- [x] **Task 9.6: Minimalist Forecaster Review Modal (`ForecasterReview/`)**
  - **Target File:** `frontend/src/components/ForecasterReview/ForecasterReviewModal.jsx`
  - **Description:** 
    - Solid Obsidian modal backdrop (`#08090C`) with 1px border.
    - High-contrast pure white form fields with focused cobalt outlines.
    - Cryptographic SHA-256 seal badge styled with monospace hash display.

- [x] **Task 9.7: High-Contrast Pure White / Jet Black Printable IMD Bulletin (`BulletinViewer/`)**
  - **Target File:** `frontend/src/components/BulletinViewer/BulletinViewer.jsx`
  - **Description:** 
    - Implemented the dual-mode bulletin viewer:
      - Screen preview: Minimalist Slate Card (`#0F1218`).
      - 1-Click Print / PDF view: Formal government Gazette layout in **Pure White (`#FFFFFF`) and Jet Black (`#000000`)**.

- [x] **Task 9.8: End-to-End Visual Verification & WCAG Contrast Audit**
  - **Target:** Production Vite build (`npm run build`) and visual inspection.
  - **Verification:** Ensured all critical text achieves $\ge 7:1$ contrast ratio (WCAG AAA) and verified zero compilation errors.

---

## 🎯 Verification & Sign-Off Checklist

- [x] Core backend architectural modules implemented and verified.
- [x] Phase 9 minimal design system fully implemented across all React frontend components.
- [x] Complete automated test suite (`pytest` with 48/48 tests + `npm run build`) passing with 100% green status.
