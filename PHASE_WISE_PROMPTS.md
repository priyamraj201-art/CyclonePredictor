# Master Implementation Roadmap: AI/ML-Based Cyclone Monitoring & Prediction System
**Smart India Hackathon 2026 | Problem Statement ID: 26070**  
**Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)**  
**Project:** Port 5000 - Tropical Cyclone Identification, Intensity, RI, Track & Risk Prediction System

---

## 1. System Architecture & Phase Overview

This roadmap converts the technical solution document into an 8-phase execution plan designed specifically for **Antigravity**. Each phase is self-contained, testable, and builds progressively into the complete production-grade system.

```mermaid
flowchart TD
    subgraph Phase 1: Data Engine
        D1[Raw Satellite INSAT-3D/3DR] --> P1[Preprocessing & Autoencoder Inpainting]
        D2[Reanalysis ERA5 / Ocean] --> P1
        D3[IBTrACS Historical Labels] --> P1
    end

    subgraph Phase 2: Detection & Centre
        P1 --> M1[YOLOv8 / ResNet-18 Cyclone Detection & Centre Localisation]
    end

    subgraph Phase 3: Intensity & RI
        P1 --> M2[CNN+ViT Intensity Estimator (Wind Speed in Knots)]
        P1 --> M3[XGBoost / TabNet Rapid Intensification (RI) Classifier]
        M2 --> X1[Grad-CAM Saliency Maps]
    end

    subgraph Phase 4: Track & Cone
        P1 --> M4[LSTM/GRU Multi-Step Track Forecaster (6h, 12h, 24h, 48h)]
        M4 --> M5[Landfall ETA & Uncertainty Cone Generator]
    end

    subgraph Phase 5: Fusion & Risk
        M1 & M2 & M3 & M5 --> F1[Multimodal Fusion Layer]
        F1 --> R1[Coastal Vulnerability & GIS Risk Assessment Engine]
    end

    subgraph Phase 6 & 7: Production Core & UI
        F1 & R1 --> B1[FastAPI High-Throughput Inference Backend]
        B1 --> S1[SHA-256 Tamper-Evident Audit Trail & Forecaster Review]
        B1 --> UI[React + Leaflet + Chart.js Forecaster Mission-Control Dashboard]
    end

    subgraph Phase 8: Deployment
        B1 & UI --> E1[End-to-End Evaluation Benchmarks & Dockerized Deployment]
    end
```

---

## 2. IMD Domain Reference Guide (Required for AI Implementation)

1. **IMD Cyclone Intensity Classification Table:**
   - **Low Pressure Area (LPA):** $< 17 \text{ knots}$ ($< 31 \text{ km/h}$)
   - **Depression (D):** $17 - 27 \text{ knots}$ ($31 - 49 \text{ km/h}$)
   - **Deep Depression (DD):** $28 - 33 \text{ knots}$ ($50 - 61 \text{ km/h}$)
   - **Cyclonic Storm (CS):** $34 - 47 \text{ knots}$ ($62 - 88 \text{ km/h}$)
   - **Severe Cyclonic Storm (SCS):** $48 - 63 \text{ knots}$ ($89 - 117 \text{ km/h}$)
   - **Very Severe Cyclonic Storm (VSCS):** $64 - 89 \text{ knots}$ ($118 - 166 \text{ km/h}$)
   - **Extremely Severe Cyclonic Storm (ESCS):** $90 - 119 \text{ knots}$ ($167 - 221 \text{ km/h}$)
   - **Super Cyclonic Storm (SuCS):** $\ge 120 \text{ knots}$ ($\ge 222 \text{ km/h}$)

2. **Rapid Intensification (RI) Criterion:**
   - Maximum sustained wind speed increase of $\ge 30 \text{ knots}$ ($\sim 55 \text{ km/h}$) within a $24\text{-hour}$ window.

3. **Geospatial Focus Area:**
   - North Indian Ocean (NIO) Basin: Bay of Bengal ($5^\circ\text{N}-25^\circ\text{N}, 80^\circ\text{E}-100^\circ\text{E}$) and Arabian Sea ($5^\circ\text{N}-25^\circ\text{N}, 50^\circ\text{E}-77.5^\circ\text{E}$).

---

## Phase 1: Repository Architecture, Data Schemas & Multi-Source Ingestion Pipeline

### Antigravity Prompt

```text
Build Phase 1 of the SIH 2026 Cyclone AI System (Port 5000 / Problem 26070).
We need to establish the complete Python project structure, environment configuration, standardized data schemas, synthetic/mock data generators, and preprocessing pipelines for multi-source satellite and meteorological data.

Target Requirements:
1. Directory Structure:
   - data/ (raw, processed, synthetic, cache)
   - src/
     - core/ (config, logging, constants, schemas)
     - data/ (ingestion, preprocessing, autoencoder, mock_generator)
     - models/ (placeholders for downstream modules)
     - api/ (placeholders for FastAPI)
     - utils/ (geospatial, conversions)
   - tests/ (unit and integration tests)

2. Schemas & Domain Models (src/core/schemas.py):
   - CycloneStage (Enum of IMD categories: LPA, D, DD, CS, SCS, VSCS, ESCS, SuCS)
   - SatelliteFrameMeta (timestamp, sensor: INSAT_3D, channels: IR, VIS, WV, PMW, resolution, bounding_box)
   - EnvironmentalFeatures (SST in Celsius, vertical_wind_shear in knots, relative_humidity_700hpa in %, ocean_heat_content in kJ/cm2)
   - BestTrackPoint (timestamp, lat, lon, max_sustained_wind_kt, central_pressure_hpa, imd_category, is_rapid_intensification)
   - CycloneObservation (frame_id, satellite_meta, env_features, best_track_label)

3. Synthetic & Mock Multi-Source Data Generator (src/data/mock_generator.py):
   - Generate realistic synthetic multi-channel satellite arrays:
     - 4 channels: IR (10.8 µm brightness temp 180K-310K), WV (6.7 µm), VIS (0.65 µm albedo 0-1), PMW (89 GHz proxy).
     - Inject synthetic cyclonic spiral vortex structures using mathematical vortex models (Rankine or Holland vortex pattern) centered at a simulated lat/lon in Bay of Bengal/Arabian Sea.
     - Add cloud gaps/missing sensor patches (simulating sensor noise/cloud obstruction).
   - Generate corresponding IBTrACS mock historical trajectories (lat, lon, wind speeds progressing over 48 hours).
   - Generate ERA5 reanalysis tabular tabular environmental features matching storm timestamps.
   - Save output in standardized HDF5/NetCDF or compressed NumPy format (.npz) with metadata JSON.

4. Data Preprocessing & Autoencoder Inpainting Module (src/data/preprocessing.py & src/data/autoencoder.py):
   - Normalization functions for satellite channels (brightness temp to [0, 1]).
   - Resizing and spatial alignment to uniform (4, 256, 256).
   - Convolutional Autoencoder in PyTorch (Conv2d encoder-decoder with skip connections / U-Net lightweight) for masked-patch reconstruction / inpainting of missing satellite scans.
   - Preprocessing pipeline class that accepts raw frame, checks quality, inpaints missing masked pixels, and returns tensor ready for inference.

5. Unit Tests (tests/test_phase1_data.py):
   - Test synthetic data generation and channel bounds.
   - Test autoencoder forward pass with missing masks.
   - Test IMD wind-to-category conversions (knots to km/h and correct IMD classification).
   - Test preprocessing pipeline end-to-end.

Ensure all code contains type hints, docstrings, and a setup verification script 'scripts/verify_phase1.py'.
```

### Prompt Explanation & Antigravity Strategy
- **Why this phase comes first:** Real MOSDAC INSAT-3D HDF5 files and ERA5 NetCDF files are massive and frequently unavailable on local development machines without credentials. Providing a rigorous synthetic generator with real physical constraints (Holland vortex equations, realistic temperature ranges 180K–310K) allows Antigravity to immediately develop and test every single downstream computer vision and sequence model without waiting for multi-gigabyte downloads.
- **Architectural Rationale:** Standardizing the Pydantic schemas (`CycloneObservation`, `EnvironmentalFeatures`, `BestTrackPoint`) ensures all subsequent AI modules adhere to identical data contracts.
- **Verification Rule:** The verification script `verify_phase1.py` validates that 4-channel tensor generation, masked inpainting, and schema parsing execute cleanly with `pytest`.

---

## Phase 2: Cyclone Detection & Storm Centre Localisation Engine

### Antigravity Prompt

```text
Build Phase 2 of the Cyclone AI System: Automated Cyclone Detection, Centre Localisation, and Preliminary Stage Classification.

Target Requirements:
1. Module Path: src/models/detection.py
2. Architecture:
   - Provide a dual-mode backbone:
     a) ResNet-18 / EfficientNet-B0 backbone adapted for 4-channel satellite input (or single IR channel fallback) predicting:
        - Cyclonic Presence Probability (binary classification: cyclonic activity vs clear/ambient cloud).
        - Storm Centre Localisation (continuous regression output: normalised (x, y) coordinates within frame, converted to decimal lat/lon).
        - Preliminary Stage Classifier (multi-class: Low Pressure/Depression, Cyclonic Storm, Severe+).
     b) YOLOv8-compatible adapter interface (wrapper class for Ultralytics YOLOv8 bounding box + center point detection).
3. Physics & Geospatial Coordinate Transform:
   - Map normalized image coordinates (0.0 to 1.0) back to geographic coordinates (Latitude, Longitude) using the satellite frame's bounding box metadata (e.g. Bay of Bengal 5N-25N, 80E-100E).
   - Calculate localisation error in kilometers using the Haversine formula against ground-truth centre coordinates.
4. Dataset & PyTorch Training/Inference Wrapper:
   - Create 'CycloneDetectionDataset' capable of loading synthetic or preprocessed .npz frames with centre (lat, lon) labels.
   - Implement training loop with combined loss:
     Loss = BCE(presence) + SmoothL1(centre_x, centre_y) + CrossEntropy(preliminary_stage).
   - Implement 'CycloneDetector' inference engine with thresholding and fallback handling when no cyclone is detected in the frame.
5. Saliency / Heatmap Generation:
   - Output an attention/energy map indicating the detected circulation center (e.g. centroid of low brightness temperature and highest vorticity).
6. Verification & Tests (tests/test_phase2_detection.py):
   - Test forward pass with tensor shape (B, 4, 256, 256).
   - Test Haversine distance calculator.
   - Verify coordinate projection from pixel space to real-world lat/lon.
   - Execute verification script 'scripts/verify_phase2.py'.
```

### Prompt Explanation & Antigravity Strategy
- **Why this is critical:** Operationally, IMD forecasters first ask: *"Is there an organized circulation? Where is the exact low-pressure center?"* Without locating the center, intensity analysis and track forecasting cannot be initialized.
- **Scientific Foundation:** Tropical cyclones in satellite infrared display characteristic curved convective bands or an eye. The model predicts both the center coordinates and maps them back to geographic Lat/Lon using the satellite projection metadata.
- **Evaluation Metric:** Storm-center localisation error measured in kilometers (via Haversine formula) and detection F1-score.

---

## Phase 3: Intensity Estimation, Rapid Intensification (RI) Classifier & Explainability

### Antigravity Prompt

```text
Build Phase 3 of the Cyclone AI System: Wind Speed Regression (Intensity Estimation), Rapid Intensification (RI) Prediction, and Grad-CAM Explainability.

Target Requirements:
1. Intensity Estimation Model (src/models/intensity.py):
   - CNN + Vision Transformer (ViT) Hybrid or timm backbone (e.g., EfficientNet/ResNet feature extractor followed by Multi-Head Self-Attention).
   - Input: 4-channel normalized satellite patch centered on storm (4, 256, 256).
   - Output:
     - Continuous scalar: Maximum Sustained Wind Speed (knots).
     - Uncertainty estimate: Standard deviation or variance (Monte Carlo Dropout or heteroscedastic loss).
   - Helper function to map predicted knots to IMD Cyclone Intensity Categories (LPA, D, DD, CS, SCS, VSCS, ESCS, SuCS) and Central Pressure (hPa) empirical estimates.

2. Rapid Intensification (RI) Classifier (src/models/rapid_intensification.py):
   - IMD/NHC Definition: Wind speed increase >= 30 knots within 24 hours.
   - Model: Gradient Boosted Decision Tree (XGBoost / LightGBM) + PyTorch MLP / TabNet alternative.
   - Tabular Features: Current wind speed, 12h pressure drop, Sea Surface Temperature (SST), 850-200 hPa Vertical Wind Shear, 700 hPa Relative Humidity, Ocean Heat Content (OHC), Coriolis parameter (lat).
   - Class Imbalance Handling: SMOTE synthetic oversampling or Focal Loss / class-weighted XGBoost (scale_pos_weight).
   - Output: Probability of RI onset [0.0 to 1.0] and binary flag based on operational threshold (e.g., threshold = 0.35 calibrated for high recall/POD).

3. Explainability Engine (src/models/explainability.py):
   - Grad-CAM (Gradient-weighted Class Activation Mapping) implementation for the intensity CNN/ViT backbone.
   - Generate visual saliency heatmaps highlighting the cloud features (deep central convection, eye wall symmetry, outer spiral feeder bands) driving the intensity prediction.
   - Overlay heatmap onto IR satellite frame and output base64-encoded PNG / RGB array for dashboard rendering.

4. Metrics & Evaluation Utilities:
   - Intensity: Mean Absolute Error (MAE in knots), Root Mean Square Error (RMSE in knots).
   - RI: Probability of Detection (POD = Recall), False Alarm Ratio (FAR), Critical Success Index (CSI = TS).
   - Temporal train/test split helper (by storm season/year, preventing intra-storm leakage).

5. Verification Script & Tests (tests/test_phase3_intensity_ri.py & scripts/verify_phase3.py):
   - Verify intensity model outputs valid positive wind speed and correct IMD classification.
   - Verify RI classifier predicts probabilities and handles imbalanced features.
   - Verify Grad-CAM generates non-empty heatmaps matching input dimensions (256, 256).
```

### Prompt Explanation & Antigravity Strategy
- **Why this replaces Dvorak:** The manual Dvorak technique relies on subjective chart matching of eye patterns, curved bands, and central dense overcast (CDO). A CNN+ViT hybrid extracts objective quantitative patterns.
- **Why RI is a separate tabular model:** Rapid intensification is driven primarily by oceanic and atmospheric thermodynamic conditions (warm ocean waters $>26.5^\circ\text{C}$, high upper-ocean heat content, low vertical wind shear $<15-20\text{ kt}$). Feeding these reanalysis parameters into XGBoost with focal loss / scale_pos_weight solves the acute class-imbalance problem (since $<10\%$ of storms undergo RI).
- **Explainability (Grad-CAM):** Essential for meteorologists. Forecasters will not trust a black-box number; showing the Grad-CAM heatmap over the inner core builds immediate trust.

---

## Phase 4: Track Forecasting, Landfall Prediction & Uncertainty Cone Engine

### Antigravity Prompt

```text
Build Phase 4 of the Cyclone AI System: Short-Range Track Forecasting, Landfall Point/ETA Prediction, and Probability Uncertainty Cones.

Target Requirements:
1. Sequential Track Forecasting Model (src/models/track.py):
   - Model: PyTorch Bi-directional LSTM / GRU sequence network.
   - Input: Historical storm trajectory sequence (past 12h to 24h at 6-hour intervals):
     [timestamp, lat, lon, intensity_kt, translation_speed_kmh, heading_deg, central_pressure].
   - Output: Predicted future storm positions at +6h, +12h, +24h, and +48h lead times:
     Predicted points: [(lat_+6, lon_+6), (lat_+12, lon_+12), (lat_+24, lon_+24), (lat_+48, lon_+48)].
   - Coordinate delta formulation: Model predicts (d_lat, d_lon) step increments rather than absolute lat/lon to enforce spatial continuity.

2. Uncertainty Cone & Probability Envelope Generator (src/utils/uncertainty_cone.py):
   - Calculate expanding uncertainty radii based on historical IMD/WMO official forecast errors:
     - 6h cone radius: ~30 km
     - 12h cone radius: ~55 km
     - 24h cone radius: ~100 km
     - 48h cone radius: ~180 km
   - Generate GeoJSON polygon representing the smooth cone of uncertainty along the forecast track.
   - Output both GeoJSON FeatureCollection (for Leaflet map rendering) and raw coordinate lists.

3. Landfall Prediction Engine (src/utils/landfall.py):
   - High-resolution coastal boundary geometry for the North Indian Ocean (Indian coastline, Bangladesh, Myanmar, Sri Lanka, Pakistan).
   - Ray-casting / line-polygon intersection to detect if and where the forecast track crosses the coastline.
   - If intersection detected:
     - Output Landfall Location: (lat, lon, coastal district/state name, e.g. "Puri, Odisha" or "Sunderbans, West Bengal").
     - Output Landfall Estimated Time of Arrival (ETA in UTC and IST).
     - Estimated Intensity at Landfall (wind speed and IMD category).
     - Estimated Landfall Uncertainty Window (+/- 3 to 6 hours).

4. Verification Script & Tests (tests/test_phase4_track.py & scripts/verify_phase4.py):
   - Test LSTM track prediction with a simulated North-West moving Bay of Bengal cyclone.
   - Verify uncertainty cone generates valid, non-self-intersecting GeoJSON polygons.
   - Test landfall detection algorithm against synthetic coastal crossing paths.
```

### Prompt Explanation & Antigravity Strategy
- **Why Track Forecasting Matters:** Emergency evacuation decisions, port warnings, and disaster management (NDRF deployments) depend directly on the 24h/48h landfall coordinates and ETA.
- **Engineering Highlights:**
  - Predicting relative delta movements $(\Delta \text{lat}, \Delta \text{lon})$ rather than absolute coordinates ensures physical plausibility and avoids jumping across continents.
  - The uncertainty cone reflects IMD operational error statistics, providing emergency planners with the standard 70% probability envelope rather than a deceptive single line.
  - GeoJSON polygon output integrates directly into Leaflet.js in the frontend.

---

## Phase 5: Multimodal Fusion & Dynamic Coastal Risk Assessment Engine

### Antigravity Prompt

```text
Build Phase 5 of the Cyclone AI System: Multimodal Feature Fusion, GIS-based Coastal Vulnerability Layer, and Dynamic Multi-Hazard Risk Scoring.

Target Requirements:
1. Multimodal Fusion Engine (src/models/fusion.py):
   - Ingest representations from:
     a) Satellite imagery latent embedding (from Phase 3 CNN/ViT, dimension: 256).
     b) Sequential track & translation dynamics embedding (from Phase 4 LSTM, dimension: 64).
     c) Environmental reanalysis tabular features (SST, shear, OHC, dimension: 32).
   - Cross-Modal Attention Mechanism:
     - Query = Satellite Visual Features; Key & Value = Environmental + Sequential Features.
     - Compute unified multimodal representation vector (dimension: 128).
   - Joint downstream verification: Ensure fused embeddings maintain compatibility with end-to-end multi-task inference.

2. GIS Coastal Vulnerability & Hazard Assessment Engine (src/risk/risk_assessment.py):
   - Coastal Districts Database: Built-in dataset/GeoJSON covering vulnerable Indian coastal districts across Odisha, Andhra Pradesh, Tamil Nadu, West Bengal, Gujarat, Maharashtra, Kerala.
   - Demographic & Infrastructure Data: Population density tier, coastline elevation tier, key infrastructure (ports, power plants, evacuation shelters).
   - Hazard Impact Zone Estimation:
     a) Wind Swath: Gale wind radius (>= 34 kt), Storm wind radius (>= 48 kt), Destructive core (>= 64 kt).
     b) Storm Surge Estimate: Empirical surge height (meters) calculated from maximum wind speed, central pressure deficit ($\Delta P = 1010 - P_{min}$), and shallow bathymetry factor.
     c) Rainfall Hazard: Convective precipitation band classification (Moderate: 7-11 cm/day, Heavy: 12-20 cm/day, Extremely Heavy: >20 cm/day).
   - Dynamic Risk Index (Composite Score 0.0 - 100.0 and Category: LOW, MEDIUM, HIGH, CRITICAL):
     $$Risk = 0.4 \times Hazard(Wind, Surge, Rain) + 0.35 \times Exposure(PopDensity) + 0.25 \times Vulnerability(Elevation, LowLying)$$

3. Automated IMD Alert Bulletin Generator (src/risk/bulletin_generator.py):
   - Generate structured standard meteorological bulletins conforming to IMD format:
     - Header: Cyclone Warning Bulletin No. X
     - Current Location & Intensity
     - 24h/48h Forecast Track & Landfall Timing
     - Expected Damages (Extensive thatched house damage, uprooting of trees, coastal inundation)
     - Action Suggested (Fishermen warning, port signals, evacuation advisories)
   - Export bulletin as structured JSON, plain text, and HTML.

4. Verification Script & Tests (tests/test_phase5_risk.py & scripts/verify_phase5.py):
   - Verify multimodal fusion cross-attention forward pass.
   - Test risk scoring engine against high-population coastal districts (e.g. Kendrapara, Odisha vs low-population zones).
   - Verify bulletin generator outputs complete, formatted text containing all required sections.
```

### Prompt Explanation & Antigravity Strategy
- **Bridging AI with Operational Disaster Relief:** Pure AI outputs (e.g. "wind speed is 85 kt") are insufficient for civil authorities. District collectors and NDRF commanders require actionable risk: *Which districts will face 3-meter surge? Where will gale winds strike first?*
- **Multimodal Fusion:** Fuses visual eye-wall structure with thermodynamic tabular features and forward motion vectors via attention, giving an integrated predictive representation.
- **Automated IMD Bulletins:** Mimics the exact four-stage warning system of the IMD (Pre-Cyclone Watch, Cyclone Alert, Cyclone Warning, Post-Landfall Outlook).

---

## Phase 6: FastAPI Production Inference Backend, Forecaster Trust & Audit Trail

### Antigravity Prompt

```text
Build Phase 6 of the Cyclone AI System: High-Performance FastAPI Serving Layer, Forecaster Review & Override System, and Tamper-Evident SHA-256 Audit Trail.

Target Requirements:
1. FastAPI Application Setup (src/api/main.py):
   - Modular routers:
     - /api/v1/health (health checks, loaded models, GPU/CPU status)
     - /api/v1/detect (cyclone detection & centre localisation)
     - /api/v1/intensity (wind speed, IMD category, Grad-CAM saliency base64)
     - /api/v1/ri (rapid intensification probability & flags)
     - /api/v1/track (track forecast, landfall ETA, uncertainty cone GeoJSON)
     - /api/v1/risk (district risk scores, impact zones, automated bulletin)
     - /api/v1/pipeline/full-run (end-to-end pipeline: raw frame/data -> full analysis payload)
     - /api/v1/forecaster (human-in-the-loop review, approve, override, audit trail)

2. Forecaster Human-in-the-Loop & Trust Layer (src/api/forecaster.py & src/core/audit.py):
   - Forecaster Review Workflow:
     - Status: PENDING_REVIEW -> FORECASTER_APPROVED or FORECASTER_MODIFIED.
     - Forecaster can adjust estimated intensity (+/- 5 kt), shift center coordinates, or amend landfall ETA with mandatory rationale note.
   - Tamper-Evident SHA-256 Audit Trail:
     - Stored in SQLite / JSONL log.
     - Every prediction record contains:
       Record_Hash = SHA-256(timestamp + frame_id + model_version + raw_predictions + forecaster_id + forecaster_corrections + previous_record_hash).
     - Tamper-verification endpoint: /api/v1/forecaster/audit/verify to prove historical records have not been altered.

3. Background Task Runner & Simulation Mode:
   - Provide an automated live playback simulator endpoint: /api/v1/simulation/playback that streams historical storm time-steps (e.g. Cyclone Fani or Amphan) every 5 seconds for demonstration and dashboard visualization.

4. CORS, Error Handling & API Documentation:
   - Full CORS middleware for frontend access.
   - Swagger / OpenAPI documentation with example payloads.
   - Async endpoints with efficient PyTorch eval mode (`torch.no_grad()`).

5. Verification Script & Integration Tests (tests/test_phase6_api.py & scripts/verify_phase6.py):
   - Use FastAPI TestClient to test all endpoints.
   - Verify SHA-256 audit chaining: modify a log entry and ensure verify fails; run standard loop and ensure verify passes.
   - Test forecaster override workflow.
```

### Prompt Explanation & Antigravity Strategy
- **Why Human-in-the-Loop is Mandatory:** Section 4.8 of the solution document emphasizes that AI must assist, not supersede, certified IMD meteorologists. Public warnings carry life-and-death consequences.
- **Cryptographic Audit Trail:** The SHA-256 blockchain-like hash chaining guarantees institutional accountability. If an inquiry arises post-disaster, IMD can verify the exact AI prediction and forecaster sign-off timestamp.
- **Simulation Playback:** A game-changer for live hackathon judging. It allows the team to showcase real-time tracking of historic storms (e.g., Cyclone Fani, Amphan, Biparjoy) on demand.

---

## Phase 7: Forecaster Mission-Control Dashboard (React + Leaflet + Chart.js)

### Antigravity Prompt

```text
Build Phase 7 of the Cyclone AI System: Interactive Forecaster Mission-Control Dashboard in React with Leaflet.js geospatial mapping, intensity trends, Grad-CAM saliency visualization, and Human-in-the-Loop review controls.

Target Requirements:
1. Frontend Architecture:
   - Framework: React (Vite-based) with modern styling (Tailwind CSS, clean glassmorphism dark/light tactical theme suited for meteorological ops centers).
   - Component Directory:
     - src/components/Map/ (Leaflet interactive map with layers: satellite frames, storm track, uncertainty cone, coastal district risk boundaries, landfall markers)
     - src/components/Intensity/ (Chart.js / Recharts intensity time-series, current knots, IMD category badge)
     - src/components/Explainability/ (Grad-CAM heatmap viewer with opacity slider over raw IR satellite imagery)
     - src/components/RapidIntensification/ (RI probability gauge, contributing thermodynamic parameters: SST, shear, humidity)
     - src/components/RiskMatrix/ (District vulnerability table, storm surge alerts, wind hazard levels)
     - src/components/ForecasterReview/ (Interactive review modal: approve button, override inputs for wind/track, reason text field, audit trail status)
     - src/components/BulletinViewer/ (Formatted IMD warning bulletin with copy and print actions)
     - src/components/SimulationControls/ (Play, pause, rewind, step-forward, storm selector dropdown)

2. Key UI Features & Interactivity:
   - Geospatial Map (Leaflet.js):
     - Base tile layers (Dark Matter, Satellite, Topo).
     - Render predicted track polyline with 6h, 12h, 24h, 48h waypoints.
     - Render semi-transparent smooth GeoJSON polygon for Uncertainty Cone.
     - Color-coded coastal district polygons based on Risk Score (Green = Low, Yellow = Med, Orange = High, Red = Critical).
   - Saliency Overlay:
     - Toggle between Raw Satellite IR, Enhanced Water Vapor, and Grad-CAM Attention Heatmap.
   - Forecaster Action Bar:
     - Top bar displaying Current Storm Name, Basin (Bay of Bengal / Arabian Sea), IMD Category badge with pulsing red beacon if Rapid Intensification is flagged.
     - "Submit Official Forecaster Bulletin" button that sends approved prediction to /api/v1/forecaster/approve.

3. API Integration:
   - Axios or fetch client connecting to FastAPI backend (default http://localhost:8000).
   - Fallback to robust mock state if backend is offline, ensuring the dashboard never crashes during presentations.

4. Build & Verification:
   - Ensure clean build (`npm run build`).
   - Create a start script 'scripts/start_frontend.bat' / 'scripts/start_all.py' to launch both backend and frontend simultaneously.
```

### Prompt Explanation & Antigravity Strategy
- **Presentation Excellence:** The dashboard is what the SIH judges, MoES officials, and IMD experts will see and evaluate. It transforms abstract machine learning weights into an operational military-grade disaster monitoring console.
- **Forecaster Usability:** Integrating Grad-CAM heatmaps directly with an opacity slider allows forecasters to verify whether the AI focused on the actual eye wall or stray cirrus clouds.
- **Fail-Safe Demo Mode:** Built-in mock data fallback ensures that even if local networking or backend restarts happen during an evaluation, the dashboard remains completely responsive.

---

## Phase 8: End-to-End Evaluation Harness, Benchmarks & Dockerized Deployment

### Antigravity Prompt

```text
Build Phase 8 of the Cyclone AI System: Comprehensive Evaluation Harness, Official Benchmark Reporter, End-to-End Verification Pipeline, and Docker Containerization.

Target Requirements:
1. Evaluation Harness (src/eval/evaluate_pipeline.py):
   - Compute all performance metrics defined in Section 8 of the Solution Document:
     - Detection: Precision, Recall, F1-Score, Storm-Centre Localisation Error (mean & median in km).
     - Intensity: Mean Absolute Error (MAE) and Root Mean Square Error (RMSE) in knots.
     - Rapid Intensification: Probability of Detection (POD), False Alarm Ratio (FAR), Critical Success Index (CSI).
     - Track: Mean Track Error in km at 24-, 48-, and 72-hour lead times against ground truth IBTrACS trajectories.
   - Enforce temporal train/test split (evaluate strictly on out-of-season holdout storms to guarantee zero data leakage).
   - Output structured evaluation report as JSON and Markdown table ('benchmarks/evaluation_summary.md').

2. Comprehensive End-to-End Demo Script (scripts/demo_full_system.py):
   - Automates the full lifecycle for a test storm (e.g. Simulation of Very Severe Cyclonic Storm):
     1. Ingests raw satellite frames & environmental data.
     2. Inpaints cloud gaps using Autoencoder.
     3. Detects center and preliminary stage.
     4. Predicts intensity (knots) and flags Rapid Intensification.
     5. Projects 48h track and checks for coastal landfall intersection.
     6. Evaluates district-level risk scores and generates official IMD warning bulletin.
     7. Records SHA-256 tamper-evident audit entry.
     8. Prints clear summary to terminal and pushes state to the frontend dashboard.

3. Containerization & Deployment:
   - Dockerfile.backend (Python 3.10/3.11, PyTorch CPU/CUDA, FastAPI).
   - Dockerfile.frontend (Node 18/20, Vite build, Nginx production server).
   - docker-compose.yml orchestrating:
     - backend (port 8000)
     - frontend (port 3000 or 5000)
     - persistent volumes for data, models, and audit logs.
   - README.md with complete installation, quick-start guide, architecture diagrams, and hackathon presentation pitch notes.

4. Final System Verification (scripts/verify_all.py):
   - Single command that runs all unit tests, checks API endpoints, executes the benchmark suite, and confirms system readiness.
```

### Prompt Explanation & Antigravity Strategy
- **Scientific Credibility:** SIH evaluators and IMD scientists demand rigorous evaluation metrics (POD, FAR, CSI, MAE in knots, track error in km). Having an automated evaluation harness with temporal split validation proves the AI isn't overfitting.
- **Turnkey Portability:** With Docker and `verify_all.py`, the entire system can be cloned, spun up, and verified in minutes on any judge's machine or cloud instance.

---

## 3. How to Execute This in Antigravity

To build the entire project seamlessly:
1. Feed the prompts **sequentially** from **Phase 1 to Phase 8**.
2. Run the verification script after each phase (e.g., `python scripts/verify_phase1.py`, `pytest tests/`).
3. For deep autonomous runs, you can trigger Antigravity's `/goal` command on each prompt to let it build, debug, and verify each layer until all tests pass.
4. Once completed, run `python scripts/demo_full_system.py` to watch the complete AI cyclone detection, intensity prediction, track cone, and risk alert system in action.
