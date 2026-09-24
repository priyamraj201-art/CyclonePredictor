"""Step 3 Verification: Live Pipeline Integration — Full End-to-End Inference.

Verifies that RealTimePipeline.run() correctly connects:
  Stage 1  — Intensity Estimator      (wind speed & central pressure)
  Stage 2  — RI Classifier            (24-h RI probability)
  Stage 3  — Bi-LSTM Track Forecaster (+12h, +24h, +36h, +48h)
  Stage 4  — Uncertainty Cone GeoJSON (70% polygon)
  Stage 5  — Coastal Risk Engine      (district risk scores)

Checks:
  1.  Pipeline produces RealTimePipelineOutput (no exceptions)
  2.  Intensity wind speed in physical range [20, 180] kt
  3.  Central pressure in valid range [850, 1010] hPa
  4.  Pressure deficit > 0
  5.  RI probability in [0.0, 1.0]
  6.  RI advisory string non-empty
  7.  Track has exactly 4 waypoints
  8.  All waypoint lats in NIO domain [3, 35] N
  9.  All waypoint lons in NIO domain [45, 115] E
  10. Lead hours are increasing (12, 24, 36, 48)
  11. Uncertainty cone GeoJSON has type=FeatureCollection
  12. Cone GeoJSON has >= 2 features (cone polygon + track line)
  13. Coastal risk list has >= 1 district entry
  14. Each risk entry has composite_risk in [0, 100]
  15. End-to-end inference time < 1.5 seconds (pipeline only, excl. live fetch)

Exit code 0 = PASS | Exit code 1 = FAIL
"""

import sys
import time

sys.path.insert(0, ".")

from src.data.realtime_service import RealTimeAtmosphericService
from src.data.cyclogenesis import CyclogenesisAnalyzer
from src.models.realtime_pipeline import RealTimePipeline, RealTimePipelineOutput

SEPARATOR = "-" * 65
PASS_TAG  = "[PASS]"
FAIL_TAG  = "[FAIL]"
INFO_TAG  = "[INFO]"


def check(cond: bool, label: str, detail: str = "") -> bool:
    tag = PASS_TAG if cond else FAIL_TAG
    suffix = f"  <- {detail}" if detail else ""
    print(f"  {tag}  {label}{suffix}")
    return cond


def main() -> int:
    passed = True

    print(SEPARATOR)
    print("  STEP 3: Live Pipeline Integration -- Verification Suite")
    print(SEPARATOR)

    # ── Live data fetch (Step 2 pre-requisite) ─────────────────────────────
    print(f"\n{INFO_TAG}  Fetching live cyclogenesis report (Bay of Bengal)...")
    t_fetch = time.perf_counter()
    service  = RealTimeAtmosphericService(timeout_seconds=15.0)
    analyzer = CyclogenesisAnalyzer(service, timeout=15.0)
    report   = analyzer.analyze_basin("BAY_OF_BENGAL")
    fetch_elapsed = round(time.perf_counter() - t_fetch, 1)
    print(f"  {INFO_TAG}  Cyclogenesis fetch complete in {fetch_elapsed}s  "
          f"(GPI={report.basin_max_gpi:.3f}, "
          f"threat={report.primary_threat.threat_level})")

    # ── Pipeline inference ─────────────────────────────────────────────────
    print(f"\n{INFO_TAG}  Running RealTimePipeline.run() (CPU inference)...")
    pipeline = RealTimePipeline(device="cpu")

    t_pipe = time.perf_counter()
    try:
        result: RealTimePipelineOutput = pipeline.run(report)
        pipe_elapsed = round(time.perf_counter() - t_pipe, 3)
        exception_raised = False
    except Exception as exc:
        pipe_elapsed = round(time.perf_counter() - t_pipe, 3)
        exception_raised = True
        print(f"  {FAIL_TAG}  Pipeline raised exception: {exc}")
        passed = False

    if exception_raised:
        print(f"\n{SEPARATOR}")
        print(f"  {FAIL_TAG}  STEP 3 FAILED -- pipeline threw an exception.")
        print(SEPARATOR)
        return 1

    # =========================================================================
    # TEST 1: Intensity Stage
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 1: Intensity Estimator output")
    inten = result.intensity
    passed &= check(
        20.0 <= inten.wind_speed_kt <= 180.0,
        f"Wind speed in [20, 180] kt     -> {inten.wind_speed_kt} kt",
    )
    passed &= check(
        850.0 <= inten.central_pressure_hpa <= 1010.0,
        f"Central pressure in [850,1010] -> {inten.central_pressure_hpa} hPa",
    )
    passed &= check(
        inten.pressure_deficit_hpa > 0.0,
        f"Pressure deficit > 0           -> {inten.pressure_deficit_hpa} hPa",
    )
    passed &= check(
        inten.uncertainty_kt >= 0.0,
        f"Uncertainty >= 0               -> {inten.uncertainty_kt} kt",
    )
    passed &= check(
        bool(inten.imd_category),
        f"IMD category set               -> {inten.imd_category}",
    )
    print(f"         wind={inten.wind_speed_kt}kt  ({inten.wind_speed_kmh} km/h)"
          f"  P={inten.central_pressure_hpa}hPa"
          f"  dP={inten.pressure_deficit_hpa}hPa"
          f"  cat={inten.imd_category}")

    # =========================================================================
    # TEST 2: Rapid Intensification Stage
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 2: Rapid Intensification Classifier output")
    ri = result.rapid_intensification
    passed &= check(
        0.0 <= ri.ri_probability <= 1.0,
        f"RI probability in [0, 1]       -> {ri.ri_probability:.4f}",
    )
    passed &= check(
        isinstance(ri.is_ri_flagged, bool),
        f"RI flag is boolean             -> {ri.is_ri_flagged}",
    )
    passed &= check(
        bool(ri.advisory),
        "RI advisory string non-empty",
    )
    print(f"         P(RI)={ri.ri_probability:.3f}  flagged={ri.is_ri_flagged}"
          f"  threshold={ri.operational_threshold}")
    print(f"         favorable_factors: {len(ri.favorable_factors)}"
          f"  inhibiting_factors: {len(ri.inhibiting_factors)}")

    # =========================================================================
    # TEST 3: Bi-LSTM Track Forecast
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 3: Bi-LSTM Track Forecaster (+12h/+24h/+36h/+48h)")
    wpts = result.track_waypoints
    passed &= check(
        len(wpts) == 4,
        f"Track has 4 waypoints          -> {len(wpts)}/4",
    )
    if wpts:
        passed &= check(
            all(3.0 <= w.lat <= 35.0 for w in wpts),
            f"All waypoint lats in [3, 35] N -> "
            f"{[round(w.lat,2) for w in wpts]}",
        )
        passed &= check(
            all(45.0 <= w.lon <= 115.0 for w in wpts),
            f"All waypoint lons in [45,115]E -> "
            f"{[round(w.lon,2) for w in wpts]}",
        )
        passed &= check(
            list(w.lead_hours for w in wpts) == [12, 24, 36, 48],
            f"Lead hours = [12, 24, 36, 48] -> "
            f"{[w.lead_hours for w in wpts]}",
        )
        passed &= check(
            all(w.wind_speed_kt > 0 for w in wpts),
            f"All waypoint winds > 0         -> "
            f"{[w.wind_speed_kt for w in wpts]}",
        )
        print(f"         +12h ({wpts[0].lat}N,{wpts[0].lon}E) {wpts[0].wind_speed_kt}kt {wpts[0].imd_category}")
        print(f"         +24h ({wpts[1].lat}N,{wpts[1].lon}E) {wpts[1].wind_speed_kt}kt {wpts[1].imd_category}")
        print(f"         +36h ({wpts[2].lat}N,{wpts[2].lon}E) {wpts[2].wind_speed_kt}kt {wpts[2].imd_category}")
        print(f"         +48h ({wpts[3].lat}N,{wpts[3].lon}E) {wpts[3].wind_speed_kt}kt {wpts[3].imd_category}")

    # =========================================================================
    # TEST 4: Uncertainty Cone GeoJSON
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 4: 70%% Uncertainty Cone GeoJSON")
    cone = result.uncertainty_cone_geojson
    passed &= check(
        cone.get("type") == "FeatureCollection",
        f"GeoJSON type=FeatureCollection -> {cone.get('type')}",
    )
    features = cone.get("features", [])
    passed &= check(
        len(features) >= 2,
        f"GeoJSON >= 2 features          -> {len(features)} features",
    )
    cone_feat = next((f for f in features if
                      f.get("properties", {}).get("type") == "uncertainty_cone"), None)
    passed &= check(
        cone_feat is not None,
        "Cone polygon feature present",
    )
    if cone_feat:
        coords = cone_feat.get("geometry", {}).get("coordinates", [[]])
        passed &= check(
            len(coords[0]) >= 6,
            f"Cone polygon >= 6 vertices     -> {len(coords[0])} vertices",
        )

    # =========================================================================
    # TEST 5: Coastal Risk Engine
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 5: Coastal Risk Assessment")
    risk = result.coastal_risk
    passed &= check(
        len(risk) >= 1,
        f"At least 1 district assessed   -> {len(risk)} districts",
    )
    if risk:
        passed &= check(
            all(0.0 <= d.get("composite_risk", -1) <= 100.0 for d in risk),
            "All composite_risk in [0, 100]",
        )
        top = risk[0]
        print(f"         Top risk: {top.get('district')}, {top.get('state')}"
              f"  score={top.get('composite_risk')}  cat={top.get('risk_category')}")
        print(f"         Wind={top.get('local_wind_kt')}kt"
              f"  Surge={top.get('surge_height_m')}m"
              f"  Rain={top.get('rainfall_cm_24h')}cm")

    # =========================================================================
    # TEST 6: Timing & Metadata
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 6: Pipeline timing & metadata")
    passed &= check(
        pipe_elapsed < 1.5,
        f"Pipeline time < 1.5s           -> {pipe_elapsed}s  (excl. live fetch)",
    )
    passed &= check(
        bool(result.pipeline_version),
        f"Pipeline version set           -> {result.pipeline_version}",
    )
    passed &= check(
        result.basin == "BAY_OF_BENGAL",
        f"Basin correct                  -> {result.basin}",
    )
    passed &= check(
        isinstance(result.is_active_cyclone, bool),
        f"is_active_cyclone is bool      -> {result.is_active_cyclone}",
    )
    passed &= check(
        isinstance(result.requires_immediate_advisory, bool),
        f"requires_immediate_advisory    -> {result.requires_immediate_advisory}",
    )

    # ── Cleanup & verdict ─────────────────────────────────────────────────
    analyzer.close()
    service.close()
    pipeline.close()

    print(f"\n{SEPARATOR}")
    if passed:
        print(f"  {PASS_TAG}  STEP 3 COMPLETE -- Live Pipeline Integration is VERIFIED.")
        print(f"         Intensity: {result.intensity.wind_speed_kt}kt"
              f"  {result.intensity.imd_category}")
        print(f"         RI: P={result.rapid_intensification.ri_probability:.3f}"
              f"  flagged={result.rapid_intensification.is_ri_flagged}")
        print(f"         Track: +48h -> ({result.track_waypoints[-1].lat}N,"
              f" {result.track_waypoints[-1].lon}E)")
        print(f"         Coastal districts assessed: {len(result.coastal_risk)}")
        print(f"         Pipeline elapsed: {pipe_elapsed}s  |"
              f"  Total (incl. live fetch): {round(pipe_elapsed + fetch_elapsed, 1)}s")
        print(f"         Scan time: {result.run_timestamp_utc}")
    else:
        print(f"  {FAIL_TAG}  STEP 3 FAILED -- fix the issues above before Step 4.")
    print(SEPARATOR)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
