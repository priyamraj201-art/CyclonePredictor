# Cyclone AI — Minimalist Design System Specification
**Palette: Monochromatic White & Black with Tactical Precision Blue**  
**Interface: IMD / MoES Mission-Control Operations Dashboard**

---

## 1. Design Philosophy: Tactical Minimalism

The Cyclone AI mission-control dashboard is engineered for high-stakes operational environments (meteorologists tracking severe storms during 12-hour shifts). 

### Core Principles
1. **Zero Visual Noise:** Eliminate candy gradients, excessive glowing shadows, and saturated rainbow palettes that cause cognitive fatigue.
2. **High Data Density & Legibility:** Prioritize immediate readability of geospatial coordinates, wind vectors, and landfall timestamps.
3. **Monochromatic Restraint with Blue Precision:** Use deep black, crisp white, and an authoritative blue spectrum to convey hierarchy, status, and telemetry.
4. **Sub-second Recognition:** Critical metrics (e.g., Landfall ETA, Max Sustained Winds, Rapid Intensification probability) must be perceptible in $< 500\,\text{ms}$.

---

## 2. Color Palette System

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THE WHITE • BLACK • BLUE SYSTEM                                │
├──────────────────────────┬──────────────────┬────────────────────────────────────────────────────┤
│ Token Name               │ Hex Code         │ Intended Operational Usage                         │
├──────────────────────────┼──────────────────┼────────────────────────────────────────────────────┤
│ `--surface-black`        │ `#000000`        │ Master viewport canvas, deep contrast base         │
│ `--surface-obsidian`     │ `#08090C`        │ Primary panel background, header bar               │
│ `--surface-slate`        │ `#0F1218`        │ Card background, sidebar container                 │
│ `--surface-elevated`     │ `#161B22`        │ Modal overlays, popovers, dropdown menus           │
│                          │                  │                                                    │
│ `--border-subtle`        │ `#1F2430`        │ Hairline structural grid dividers (1px)            │
│ `--border-blue`          │ `#1E3A8A`        │ Active card borders, focused state                 │
│ `--border-focus`         │ `#3B82F6`        │ Interactive input focus, selected tab border       │
│                          │                  │                                                    │
│ `--accent-navy`          │ `#0A2540`        │ Secondary button backgrounds, badge backgrounds    │
│ `--accent-cobalt`        │ `#1D4ED8`        │ Primary action buttons, active navigation badges   │
│ `--accent-blue`          │ `#3B82F6`        │ Primary brand blue, key metrics, forecast tracks   │
│ `--accent-electric`      │ `#60A5FA`        │ Center eye reticle, uncertainty cone stroke        │
│ `--accent-ice`           │ `#BAE6FD`        │ Maximum intensity highlights, eye temperature      │
│                          │                  │                                                    │
│ `--text-pure-white`      │ `#FFFFFF`        │ Primary headers, critical numerical readouts       │
│ `--text-cloud-white`     │ `#F1F5F9`        │ Primary body labels, active status titles          │
│ `--text-muted-gray`      │ `#94A3B8`        │ Secondary metadata, coordinate units, table headers│
│ `--text-subtle-gray`     │ `#64748B`        │ Timestamps, inactive tabs, disabled state          │
└──────────────────────────┴──────────────────┴────────────────────────────────────────────────────┘
```

### 2.1 Contrast & Accessibility (WCAG 2.2 AAA Compliance)
* Pure White (`#FFFFFF`) on Surface Slate (`#0F1218`): **18.2:1 contrast ratio** (Exceeds AAA requirement of 7:1).
* Electric Blue (`#60A5FA`) on Surface Slate (`#0F1218`): **8.9:1 contrast ratio** (Exceeds AAA requirement).
* Accent Cobalt (`#3B82F6`) on Black (`#000000`): **8.4:1 contrast ratio** (Exceeds AAA requirement).

### 2.2 Severity Scale without Rainbow Clutter
Instead of harsh yellows, purples, and oranges that conflict with map imagery, storm severity is communicated through a **Luminance-Ranked Blue-to-White Scale**:

```
  [LOW / DEPRESSION]          ➔ Muted Blue-Slate     (#64748B)  • Subtle Outline
  [CYCLONIC STORM]            ➔ Sky Blue             (#38BDF8)  • Solid Text
  [SEVERE CYCLONIC STORM]     ➔ High-Impact Blue     (#3B82F6)  • Accent Card
  [VERY SEVERE CYCLONE]       ➔ Electric Cobalt      (#60A5FA)  • High Contrast
  [EXTREMELY SEVERE CYCLONE]  ➔ Crisp Ice Blue       (#BAE6FD)  • High Luminance
  [SUPER CYCLONIC STORM]      ➔ Pure White On Cobalt (#FFFFFF on #1D4ED8) • Inverted Badge
```

---

## 3. Typography & Numerical Formatting

```
Primary Sans:   Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
Telemetry Mono: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace
```

### 3.1 Type Hierarchy Table
| Style Name | Font Family | Weight | Size | Line Height | Usage Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display Header** | Sans | 700 (Bold) | 20px | 24px | `CYCLONE AI // MISSION CONTROL` |
| **Section Title** | Sans | 600 (SemiBold) | 14px | 18px | `STORM INTENSITY ESTIMATION` |
| **Telemetry Hero** | Mono | 700 (Bold) | 32px | 36px | `95.0 KT` / `942 HPA` |
| **Data Metric** | Mono | 600 (SemiBold) | 18px | 22px | `19.42° N, 86.85° E` |
| **Body Text** | Sans | 400 (Regular) | 13px | 18px | `Landfall projected near Puri district, Odisha.` |
| **Micro Caption** | Sans | 500 (Medium) | 11px | 14px | `UPDATED: 2026-09-20 06:00 UTC` |
| **Audit Hash** | Mono | 400 (Regular) | 11px | 14px | `sha256:7f8a91c2e4...` |

---

## 4. Layout Architecture & Grid System

The operations room layout follows a rigid **3-Panel Tactical Command Architecture**:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  HEADER: IMD Insignia | Storm ID | Current Category | Basin | Connection Status | UTC / IST Time        │
├──────────────────────────┬─────────────────────────────────────────────┬───────────────────────────────┤
│  LEFT PANEL (280px)      │  CENTER VIEWPORT (Flexible Flex-1)          │  RIGHT PANEL (340px)          │
│                          │                                             │                               │
│  • Storm Selector        │  • Interactive Leaflet Map                  │  • Intensity & Dvorak Meter   │
│  • Sensor Channels       │    - CartoDB Dark Monochrome Tiles          │  • Rapid Intensification (RI) │
│    [IR] [WV] [VIS] [PMW] │    - Real-Time Electric Blue Track          │  • Coastal Risk & Landfall    │
│  • Inpainting Toggle     │    - Expanding 70% Uncertainty Cone         │  • Forecaster Review Sign-off │
│  • Grad-CAM Heatmap      │    - District Impact Polygon Highlights     │  • 1-Click IMD Bulletin Export│
│  • Historical Simulation │  • Time-series Scrub Slider (0h ➔ 48h)      │  • SHA-256 Audit Status       │
│                          │                                             │                               │
├──────────────────────────┴─────────────────────────────────────────────┴───────────────────────────────┤
│  STATUS FOOTER: System Latency: 42ms | Active Models: ViT + Bi-LSTM | DB Sync: Nominal                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Structural Rules
* **Borders:** Razor-thin `1px solid var(--border-subtle)` (`#1F2430`).
* **Radius:** Consistent `6px` or `8px` corner radius. Avoid pill shapes or bubbly curves.
* **Shadows:** No soft colored drop-shadows. Use an inset highlight or clean `0 1px 3px rgba(0,0,0,0.8)`.
* **Scrollbars:** Ultra-thin $4\,\text{px}$ track in `#08090C`, thumb in `#1E3A8A`.

---

## 5. Component Specifications

### 5.1 Geospatial Map Canvas
* **Base Layer:** CartoDB Dark Matter or Stadia Alidade Smooth Dark (grayscale monochrome coastlines with zero road or commercial label clutter).
* **Storm Center Reticle:** Outer circle $16\,\text{px}$ stroke in `#3B82F6` ($2\,\text{px}$ width), inner dot $4\,\text{px}$ solid `#FFFFFF`.
* **Historical Track:** Solid `#94A3B8` line with small filled dots at past observation points.
* **Forecast Track:** Electric Blue (`#3B82F6`) dashed line (`dashArray: "6, 6"`) with forecast point waypoints (+6h, +12h, +24h, +48h).
* **Uncertainty Cone Polygon:**
  - Fill: `rgba(59, 130, 246, 0.12)` (Translucent cobalt blue).
  - Border: `rgba(96, 165, 250, 0.60)` ($1.5\,\text{px}$ stroke).

### 5.2 Intensity & Gauge Displays
* **Card Container:** Background `#0F1218`, border `1px solid #1F2430`.
* **Numerical Hero:** Value in `#FFFFFF` ($32\,\text{px}$ `JetBrains Mono`), unit in `#94A3B8` ($14\,\text{px}$).
* **Trendline (Recharts):**
  - Gridlines: `#161B22` (subtle dark lines).
  - Area Fill: Vertical gradient from `rgba(59, 130, 246, 0.25)` to `rgba(59, 130, 246, 0.0)`.
  - Line Stroke: `#3B82F6` ($2\,\text{px}$ crisp stroke).
  - Active Tooltip: Background `#08090C`, border `1px solid #3B82F6`, text `#FFFFFF`.

### 5.3 Forecaster Human-in-the-Loop Override Panel
* **Purpose:** Ensure forecaster review is frictionless yet deliberate.
* **Input Fields:** Background `#08090C`, border `1px solid #1F2430`, text `#FFFFFF`, focus border `#3B82F6`.
* **Approve Button:** Solid Accent Cobalt (`#1D4ED8`), text `#FFFFFF`, hover `#2563EB`.
* **Override Button:** Outline `#3B82F6`, background `transparent`, text `#60A5FA`.
* **Audit Seal Badge:** Background `rgba(30, 58, 138, 0.3)`, border `1px solid #1E3A8A`, text `#BAE6FD`, monospace icon with SHA-256 short hash.

### 5.4 Official IMD Bulletin Viewer (Light Mode Print View)
* While the operational dashboard is dark, the **1-Click Printable IMD Warning Bulletin** renders in a pristine **Black & White High-Contrast Document View**:
  - Background: Pure White (`#FFFFFF`).
  - Text: Jet Black (`#000000`).
  - Headings: Deep Navy (`#0A2540`).
  - Tables: Border `#000000` ($1\,\text{px}$ formal government layout matching IMD Gazette format).

---

## 6. Ready-to-Use CSS Variables (`tokens.css`)

Drop this into `frontend/src/index.css` to activate the minimal White, Black, and Blue design system:

```css
:root {
  /* Surface & Background */
  --bg-canvas: #000000;
  --bg-header: #08090c;
  --bg-surface: #0f1218;
  --bg-surface-elevated: #161b22;
  --bg-surface-glass: rgba(15, 18, 24, 0.85);

  /* Hairline Borders */
  --border-subtle: #1f2430;
  --border-active: #1e3a8a;
  --border-focus: #3b82f6;

  /* Tactical Blue Scale */
  --blue-900: #0c2340;
  --blue-800: #1e3a8a;
  --blue-700: #1d4ed8;
  --blue-600: #2563eb;
  --blue-500: #3b82f6;
  --blue-400: #60a5fa;
  --blue-200: #bae6fd;
  --blue-100: #e0f2fe;

  /* Monochromatic White & Grays */
  --text-white: #ffffff;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --text-dim: #334155;

  /* Structural Geometry */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;
}
```
