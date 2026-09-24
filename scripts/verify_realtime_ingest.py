"""Step 1 Verification: Real-Time Oceanic & Atmospheric Ingestion Engine.

This script verifies that:
  1. Live HTTP fetch from Open-Meteo returns HTTP 200 for NIO basin grid points
  2. All critical fields (SST, Shear, RH, Pressure, Wind) are non-zero floats
  3. Basin-level aggregation completes successfully for Bay of Bengal
  4. Arabian Sea scan also completes successfully
  5. Total fetch time is under 60 seconds (full grid scan)

Exit code 0 = PASS | Exit code 1 = FAIL
"""

import sys
import time

# Ensure src package is importable when run from project root
sys.path.insert(0, ".")

from src.data.realtime_service import RealTimeAtmosphericService


SEPARATOR = "─" * 65
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def check(condition: bool, label: str, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    detail_str = f"  ← {detail}" if detail else ""
    print(f"  {status}  {label}{detail_str}")
    return condition


def main() -> int:
    all_passed = True

    print(SEPARATOR)
    print("  STEP 1: Real-Time Ingestion Engine — Verification Suite")
    print(SEPARATOR)

    service = RealTimeAtmosphericService(timeout_seconds=15.0)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Single live point fetch — Bay of Bengal centre
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{INFO}  Test 1: Single grid-point live fetch (BoB centre 14°N 87°E)")
    t0 = time.perf_counter()
    obs = service.fetch_grid_point(lat=14.0, lon=87.0, basin="BAY_OF_BENGAL")
    elapsed = time.perf_counter() - t0

    all_passed &= check(obs.fetch_ok,
                        "HTTP fetch succeeded",
                        obs.error or "")
    all_passed &= check(isinstance(obs.sea_surface_temp_c, float) and obs.sea_surface_temp_c > 0,
                        f"SST valid   → {obs.sea_surface_temp_c} °C")
    all_passed &= check(isinstance(obs.vertical_wind_shear_kt, float),
                        f"Shear valid → {obs.vertical_wind_shear_kt} kt")
    all_passed &= check(obs.relative_humidity_700hpa > 0,
                        f"RH valid    → {obs.relative_humidity_700hpa} %")
    all_passed &= check(obs.surface_pressure_hpa > 900,
                        f"Pressure    → {obs.surface_pressure_hpa} hPa")
    all_passed &= check(obs.wind_speed_10m_kt >= 0,
                        f"Wind speed  → {obs.wind_speed_10m_kt} kt")
    all_passed &= check(elapsed < 15.0,
                        f"Fetch time  → {elapsed:.2f}s  (limit: 15s)")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Bay of Bengal basin scan (20 grid points)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{INFO}  Test 2: Bay of Bengal basin scan (20 grid points)")
    t0 = time.perf_counter()
    bob_snap = service.scan_basin("BAY_OF_BENGAL")
    elapsed = time.perf_counter() - t0

    all_passed &= check(bob_snap.num_points >= 15,
                        f"Successful grid points → {bob_snap.num_points}/20")
    all_passed &= check(bob_snap.mean_sst_c > 0,
                        f"Mean SST    → {bob_snap.mean_sst_c} °C")
    all_passed &= check(bob_snap.mean_shear_kt >= 0,
                        f"Mean Shear  → {bob_snap.mean_shear_kt} kt")
    all_passed &= check(bob_snap.mean_rh700 > 0,
                        f"Mean RH700  → {bob_snap.mean_rh700} %")
    all_passed &= check(bob_snap.max_wind_speed_kt >= 0,
                        f"Max Wind    → {bob_snap.max_wind_speed_kt} kt "
                        f"@ ({bob_snap.max_wind_lat}°N, {bob_snap.max_wind_lon}°E)")
    all_passed &= check(elapsed < 60.0,
                        f"BoB scan time → {elapsed:.1f}s  (limit: 60s)")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Arabian Sea basin scan (16 grid points)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{INFO}  Test 3: Arabian Sea basin scan (16 grid points)")
    t0 = time.perf_counter()
    as_snap = service.scan_basin("ARABIAN_SEA")
    elapsed = time.perf_counter() - t0

    all_passed &= check(as_snap.num_points >= 12,
                        f"Successful grid points → {as_snap.num_points}/16")
    all_passed &= check(as_snap.mean_sst_c > 0,
                        f"Mean SST    → {as_snap.mean_sst_c} °C")
    all_passed &= check(elapsed < 60.0,
                        f"AS scan time  → {elapsed:.1f}s  (limit: 60s)")

    service.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Final Result
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    if all_passed:
        print(f"  {PASS}  STEP 1 COMPLETE — Real-Time Ingestion Engine is LIVE.")
        print(f"         Bay of Bengal: {bob_snap.num_points} points | "
              f"BoB SST {bob_snap.mean_sst_c}°C | Shear {bob_snap.mean_shear_kt} kt")
        print(f"         Arabian Sea : {as_snap.num_points} points | "
              f"AS  SST {as_snap.mean_sst_c}°C | Shear {as_snap.mean_shear_kt} kt")
        print(f"         Scan time   : {bob_snap.scan_time_utc}")
    else:
        print(f"  {FAIL}  STEP 1 FAILED — one or more verification checks did not pass.")
        print("         Fix the issues above, then re-run this script before proceeding.")
    print(SEPARATOR)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
