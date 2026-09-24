# Cyclone AI — Real-World Production Architecture Specification
**Targeting: Ministry of Earth Sciences (MoES) & India Meteorological Department (IMD)**  
**Problem Statement ID: 26070 | Disaster Management**

---

## 1. Executive Summary & Transition Roadmap

This document defines the comprehensive engineering blueprint to transition the **Cyclone AI** prototype from its current mathematically-grounded synthetic simulation into an operational, enterprise-grade meteorological intelligence platform integrated with IMD/MoES infrastructure.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       PROTOTYPE vs. PRODUCTION MATRIX                                  │
├────────────────────────────┬──────────────────────────────────────┬────────────────────────────────────┤
│ Component                  │ Current Prototype State              │ Real-World Target Architecture     │
├────────────────────────────┼──────────────────────────────────────┼────────────────────────────────────┤
│ Satellite Ingestion        │ Synthetic Holland Vortex Arrays      │ Live MOSDAC INSAT-3D/3DR/4A HDF5   │
│ Ocean/Atmospheric Data     │ Synthetic Pydantic Environmental DTO │ ECMWF ERA5 / GFS GRIB2 via CDS API │
│ Ocean Surface Winds        │ Synthetic Scalar Approximations      │ SCATSAT-1 / Oceansat-3 OSCAT HDF5  │
│ Historical Track Grounding │ Hardcoded 5-step dictionaries        │ NOAA IBTrACS & IMD Best Track CSV  │
│ Model Weights              │ Initialized / Untrained Checkpoints  │ PyTorch ViT & Bi-LSTM on 2000-2025 │
│ Geospatial Layer           │ In-Memory Bounding Boxes             │ PostgreSQL 16 + PostGIS 3.4 Cluster│
│ Audit Trail                │ Local JSONL Hash Chaining            │ Distributed Cryptographic Ledger   │
│ Alert Dissemination        │ In-Memory HTML / Text Bulletins      │ WMO CAP XML + IMD GTS / SMS Engine │
└────────────────────────────┴──────────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Real-World Data Ingestion & Calibration Pipeline

```
                                    EXTERNAL SATELLITE & SENSOR FEEDS
  ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
  │   ISRO MOSDAC FTP/API │    │    ECMWF / CDS API    │    │      NOAA IBTrACS     │    │   IMD DWR Radar & AWS │
  │ (INSAT-3D/3DR/4A HDF5)│    │   (ERA5 Reanalysis)   │    │  (Best-Track NIO CSV) │    │  (Doppler / AWS Obs)  │
  └───────────┬───────────┘    └───────────┬───────────┘    └───────────┬───────────┘    └───────────┬───────────┘
              │                            │                            │                            │
              ▼                            ▼                            ▼                            ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                     APACHE AIRFLOW INGESTION DAGS                                            │
  │  • 15-min Polling Loop      • GRIB2 to NetCDF4        • Auto-sync Storm Traj     • NetCDF Radar Grids        │
  │  • MD5 Integrity Validation • 0.25° Lat/Lon Slicing   • Dvorak T-Number Extract  • Coastal Rain Rates        │
  └──────────────────────────────────────────────┬───────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                     OBJECT STORAGE LAYER (MinIO / AWS S3)                                    │
  │  Bucket: /raw-satellite/insat3d/YYYY/MM/DD/hhmm_channel.h5                                                   │
  │  Bucket: /environmental/era5/YYYY/MM/DD/era5_surface_wind_sst.nc                                             │
  └──────────────────────────────────────────────┬───────────────────────────────────────────────────────────────┘
                                                 │ (S3 Event Notification)
                                                 ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                     HIGH-THROUGHPUT PROCESSING (Celery / Redis)                              │
  │  • Radiometric Calibration & Planck Function (Raw Counts ➔ Brightness Temp [K])                             │
  │  • Geospatial Reprojection (Satellite Geostationary Projection ➔ EPSG:4326 Lat/Lon)                         │
  │  • Cloud-Gap & Line-Dropout Inpainting (PyTorch Lightweight U-Net Engine)                                   │
  └──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Satellite Ingestion Specifications (INSAT-3D / 3DR / 4A)
* **Data Source:** ISRO Meteorological and Oceanographic Satellite Data Archival Centre (MOSDAC) via secure SFTP / REST API.
* **Payload Structure:** Hierarchical Data Format 5 (`.h5` / HDF5) comprising:
  1. `TIR1` (Thermal Infrared 1: $10.8\,\mu\text{m}$, resolution $4\,\text{km}$): Deep convective cloud top brightness temperatures ($180\,\text{K} - 310\,\text{K}$).
  2. `TIR2` (Thermal Infrared 2: $12.0\,\mu\text{m}$, resolution $4\,\text{km}$): Split-window differential absorption for low-level moisture.
  3. `WV` (Water Vapor: $6.7\,\mu\text{m}$, resolution $8\,\text{km}$): Upper-tropospheric moisture dynamics and jet-stream shearing.
  4. `MIR` (Middle Infrared: $3.9\,\mu\text{m}$, resolution $4\,\text{km}$): Low-level cloud identification and warm eye detection during night.
  5. `VIS` (Visible: $0.65\,\mu\text{m}$, resolution $1\,\text{km}$): Daytime high-resolution vortex spiral structure and eyewall geometry.
* **Processing Driver (`h5py` + `Rasterio`):**
  - Extract sensor calibration lookup tables (LUT).
  - Apply Planck inversion formula to convert raw detector digital counts into Brightness Temperatures ($T_B$) in Kelvin.
  - Reproject geostationary projection coordinates (`+proj=geos`) to World Geodetic System 1984 (`EPSG:4326`).

### 2.2 Reanalysis & Environmental Ingestion (ECMWF ERA5 & GFS)
* **Parameters Extracted:**
  - Sea Surface Temperature ($\text{SST} \ge 26.5^\circ\text{C}$ threshold for cyclogenesis).
  - Vertical Wind Shear ($\text{VWS} = \| \vec{V}_{200\,\text{hPa}} - \vec{V}_{850\,\text{hPa}} \|$, values $< 15\,\text{kt}$ enable rapid intensification).
  - Relative Humidity at $700\,\text{hPa}$ and $500\,\text{hPa}$ (mid-tropospheric moisture).
  - Ocean Heat Content ($\text{OHC}$ in $\text{kJ/cm}^2$).
  - Low-level relative vorticity at $850\,\text{hPa}$ ($10^{-5}\,\text{s}^{-1}$).

### 2.3 Ocean Vector Winds (SCATSAT-1 & Oceansat-3 OSCAT)
* Scatterometer Level-2B wind vectors ($12.5\,\text{km}$ resolution) across the North Indian Ocean basin to provide unambiguous ground-truth surface circulation centers prior to eye formation.

---

## 3. End-to-End Deep Learning Pipeline Architecture

```
                          PREPROCESSED 4-CHANNEL SATELLITE TENSOR [4, 256, 256]
                                                   │
                ┌──────────────────────────────────┴──────────────────────────────────┐
                │                                                                     │
                ▼                                                                     ▼
┌──────────────────────────────────────┐                            ┌──────────────────────────────────────┐
│        MODULE 1: DETECTION           │                            │        MODULE 2: INTENSITY           │
│  Backbone: ResNet-50 / ConvNeXt-Tiny │                            │  Backbone: ViT-B/16 + Dvorak Head    │
│  Outputs:                            │                            │  Outputs:                            │
│  • Cyclogenesis Probability [0, 1]   │                            │  • Max Sustained Wind (knots)        │
│  • Center Regressor (lat, lon)       │                            │  • Central Pressure (hPa)            │
│  • Bounding Box Anchors              │                            │  • IMD Category Classification       │
│  • Energy Vorticity Map              │                            │  • Grad-CAM Eyewall Saliency         │
└──────────────────┬───────────────────┘                            └──────────────────┬───────────────────┘
                   │                                                                   │
                   │ [Storm Center (lat, lon)]                                         │ [Wind Speed (kt)]
                   └─────────────────────────────────┬─────────────────────────────────┘
                                                     │
                                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             MODULE 3: RAPID INTENSIFICATION (RI) ENGINE                                  │
│  Architecture: Gradient Boosted Trees (XGBoost / LightGBM) + Multi-Layer Perceptron                      │
│  Inputs: Visual ViT Embedding (256-d) + ERA5 Environmental Features (SST, VWS, OHC, RH, Vorticity)       │
│  Threshold: $\Delta V_{\text{max}} \ge 30\,\text{kt}$ over 24 hours                                     │
│  Outputs: RI Probability [0, 1] + SHAP Thermodynamic Feature Attribution                                │
└────────────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            MODULE 4: SPATIO-TEMPORAL TRACK FORECASTING                                   │
│  Architecture: Spatio-Temporal Graph Neural Network (ST-GNN) / Bi-directional LSTM with Attention        │
│  Inputs: Past 24h trajectory sequence + Steering flow vectors ($500\,\text{hPa}$ wind stream)            │
│  Forecast Horizons: +6h, +12h, +18h, +24h, +36h, +48h, +72h                                              │
│  Outputs: Coordinate Steps $(\Delta\text{lat}, \Delta\text{lon})$ + Expanding 70% Uncertainty Cones      │
└────────────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          MODULE 5: COASTAL RISK, SURGE & LANDFALL PREDICTOR                              │
│  Algorithms: High-Precision Vector Ray-Casting + SLOSH (Sea, Lake, and Overland Surges from Hurricanes)  │
│  Spatial Queries: PostGIS 3.4 Spatial Index (`ST_Intersects`, `ST_Buffer`, `ST_DWithin`)                 │
│  Outputs: District Landfall ETA (IST/UTC), Storm Surge Height (meters), Multi-Hazard Vulnerability Index │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Model Training Protocols on Historical NIO Datasets
1. **Dataset Compilation:**
   - 25 years of North Indian Ocean tropical cyclone data (2000–2025): Cyclones *Odisha Super Cyclone (1999)*, *Phailin (2013)*, *Hudhud (2014)*, *Fani (2019)*, *Amphan (2020)*, *Tauktae (2021)*, *Biparjoy (2023)*, *Michaung (2023)*, *Remal (2024)*.
   - Synchronize hourly INSAT-3D/3DR frames with IBTrACS 3-hourly best-track ground truth using cubic spline interpolation.
2. **Loss Functions:**
   - Center Localisation: Smooth L1 + Haversine Geospatial Loss:
     $$\mathcal{L}_{\text{center}} = \frac{1}{N} \sum_{i=1}^N \mathcal{H}\left( (\text{lat}_i, \text{lon}_i)_{\text{pred}}, (\text{lat}_i, \text{lon}_i)_{\text{true}} \right)$$
   - Intensity Estimation: Huber Loss ($\delta = 5.0\,\text{kt}$) + Ordinal IMD Classification Cross-Entropy.
   - Rapid Intensification: Focal Loss ($\gamma = 2.0, \alpha = 0.75$) to handle extreme class imbalance (RI occurs in $< 12\%$ of cyclone forecast cycles).
   - Track Forecasting: Autoregressive Stepwise Mean Squared Error with steering wind regularizer.

---

## 4. Database & Geospatial Architecture (PostgreSQL + PostGIS)

To replace in-memory storage, the operational database must utilize **PostgreSQL 16** with **PostGIS 3.4**:

```sql
-- Schema Definition: Operational Cyclonic Observations & Tracks
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE storms (
    storm_id VARCHAR(32) PRIMARY KEY,
    storm_name VARCHAR(64) NOT NULL,
    basin VARCHAR(16) NOT NULL CHECK (basin IN ('BAY_OF_BENGAL', 'ARABIAN_SEA')),
    genesis_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE observations (
    obs_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storm_id VARCHAR(32) REFERENCES storms(storm_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL, -- Center coordinates
    max_wind_kt REAL NOT NULL,
    central_pressure_hpa REAL NOT NULL,
    imd_category VARCHAR(32) NOT NULL,
    is_rapid_intensification BOOLEAN DEFAULT FALSE,
    satellite_raster_uri TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_obs_geom ON observations USING GIST(geom);
CREATE INDEX idx_obs_timestamp ON observations(timestamp);

-- Spatial Query: Coastal Districts intersecting the 70% Probability Uncertainty Cone
SELECT 
    d.district_name,
    d.state_name,
    d.population_density,
    ST_Distance(d.geom::geography, c.cone_geom::geography) / 1000.0 AS dist_to_cone_km
FROM coastal_districts d, forecast_cones c
WHERE c.forecast_cycle_id = 'FC_20260512_0600'
  AND ST_Intersects(d.geom, c.cone_geom)
ORDER BY dist_to_cone_km ASC;
```

---

## 5. Forecaster Human-in-the-Loop & Cryptographic Audit Trail

In compliance with IMD Operational Directives and the **Disaster Management Act 2005**, automated AI predictions must pass through accredited human forecaster review:

```
  [AI Inference Engine]
            │
            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Preliminary AI Advisory: Center, Intensity, Track, Landfall │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │         DUTY FORECASTER SECURE DASHBOARD REVIEW             │
  │  [APPROVE] ── OR ── [OVERRIDE (Center / Wind / Landfall)]   │
  │  (Mandatory Synoptic Justification Required for Overrides)  │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │        CRYPTOGRAPHIC SHA-256 TAMPER-EVIDENT LEDGER          │
  │  Header: Index, Timestamp, Forecaster ID, Model Version     │
  │  Payload: Raw Predictions + Human Corrections + Notes       │
  │  Hash Chain: H_n = SHA-256( H_{n-1} + Payload + DigitalSig) │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ OFFICIAL DISSEMINATION: WMO CAP XML, IMD GTS, NDMA/SDMA API │
  └─────────────────────────────────────────────────────────────┘
```

---

## 6. Dissemination & Alert Generation Protocol

1. **Common Alerting Protocol (CAP v1.2):**
   - Automated conversion of high-risk district evaluations into standard OASIS CAP XML formats ingested by the National Disaster Management Authority (NDMA) Sachet portal.
2. **Global Telecommunication System (GTS):**
   - Format bulletins into WMO alphanumeric code (TAC) and BUFR format for transmission across Regional Specialized Meteorological Centers (RSMC New Delhi).
3. **Multi-Channel Push Gateways:**
   - Webhooks to State Emergency Operation Centers (SEOC Odisha, West Bengal, AP, Gujarat).
   - Automated generation of bilingual (English & Hindi) SMS/WhatsApp broadcasts for port authorities and fishermen warnings.

---

## 7. High-Availability Infrastructure & Deployment Topology

```
                                      INTERNET / GOVNET
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │    CLOUDFLARE / GOV WAAP & LB    │
                             └────────────────┬─────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │       KUBERNETES INGRESS         │
                             └────────┬────────────────┬────────┘
                                      │                │
            ┌─────────────────────────┴────┐      ┌────┴─────────────────────────┐
            │                              │      │                              │
            ▼                              ▼      ▼                              ▼
┌────────────────────────┐    ┌────────────────────────┐    ┌────────────────────────┐
│  FastAPI Async Workers │    │ Triton Inference Server│    │   Celery Workers       │
│  (REST / WebSocket API)│    │ (PyTorch GPU TensorRT) │    │  (Ingestion / GeoTIFF) │
│  HPA: 3 - 10 Pods      │    │ 2x NVIDIA L4 / A10G    │    │  HPA: 4 - 16 Pods      │
└───────────┬────────────┘    └────────────┬───────────┘    └────────────┬───────────┘
            │                              │                             │
            └──────────────────────────────┼─────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE & PERSISTENCE                                 │
│  • PostgreSQL 16 + PostGIS 3.4 Primary + Read Replica                              │
│  • Redis 7 Cluster (Pub/Sub + Task Broker + Session Cache)                         │
│  • MinIO / Ceph Distributed Object Store (Satellite Rasters)                      │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Failover & Disaster Recovery (DR)
- **Primary Data Center:** New Delhi (IMD Headquarters).
- **Secondary DR Site:** Pune / Hyderabad (IITM / INCOIS).
- **RPO (Recovery Point Objective):** $\le 5\text{ minutes}$ (continuous database streaming replication).
- **RTO (Recovery Time Objective):** $\le 60\text{ seconds}$ (automated DNS health check failover).
- **Offline / Degraded Mode:** If external satellite feeds fail, the system falls back to numerical weather prediction (NWP) GFS grids; if GPU workers fail, fallback to CPU INT8 quantized models.
