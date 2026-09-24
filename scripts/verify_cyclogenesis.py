"""Step 2 Verification: Real-Time Cyclogenesis GPI & Low-Pressure Scanner.

Verifies:
  1. GPI score is a valid non-negative float at every grid point
  2. Genesis probability is within [0.0, 1.0] at every grid point
  3. Candidate vortex coordinates (lat, lon) lie within the NIO domain
  4. Basin max GPI >= 0  and  mean GPI >= 0
  5. At least 15 grid points computed successfully for Bay of Bengal
  6. Primary threat has a valid threat level string
  7. Analysis completes within 120 seconds (includes all HTTP fetches)

Exit code 0 = PASS | Exit code 1 = FAIL
"""

import sys
import time

sys.path.insert(0, ".")

from src.data.realtime_service import RealTimeAtmosphericService
from src.data.cyclogenesis import (
    CyclogenesisAnalyzer,
    SST_THRESHOLD_C,
    SHEAR_THRESHOLD_KT,
    RH700_THRESHOLD_PCT,
)

SEPARATOR = "-" * 65
PASS_TAG  = "[PASS]"
FAIL_TAG  = "[FAIL]"
INFO_TAG  = "[INFO]"

VALID_THREAT_LEVELS = {"NONE", "LOW", "MODERATE", "HIGH", "EXTREME"}

# NIO domain bounds for coordinate validity checks
BOB_LAT_MIN, BOB_LAT_MAX = 5.0,  23.0
BOB_LON_MIN, BOB_LON_MAX = 79.0, 96.0
AS_LAT_MIN,  AS_LAT_MAX  = 5.0,  26.0
AS_LON_MIN,  AS_LON_MAX  = 60.0, 76.0


def check(cond: bool, label: str, detail: str = "") -> bool:
    tag = PASS_TAG if cond else FAIL_TAG
    suffix = f"  <- {detail}" if detail else ""
    print(f"  {tag}  {label}{suffix}")
    return cond


def main() -> int:
    passed = True

    print(SEPARATOR)
    print("  STEP 2: Cyclogenesis GPI Scanner -- Verification Suite")
    print(SEPARATOR)

    service  = RealTimeAtmosphericService(timeout_seconds=15.0)
    analyzer = CyclogenesisAnalyzer(service, timeout=15.0)

    # =========================================================================
    # TEST 1: Bay of Bengal full analysis
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 1: Bay of Bengal -- GPI analysis (20 grid points)")
    t0 = time.perf_counter()
    bob = analyzer.analyze_basin("BAY_OF_BENGAL")
    elapsed = time.perf_counter() - t0

    passed &= check(
        len(bob.grid_gpi_points) >= 15,
        f"Grid points computed       -> {len(bob.grid_gpi_points)}/20  (min 15)",
    )
    passed &= check(
        all(p.gpi_score >= 0.0 for p in bob.grid_gpi_points),
        "All GPI scores >= 0",
    )
    passed &= check(
        all(0.0 <= p.genesis_probability <= 1.0 for p in bob.grid_gpi_points),
        "All genesis probabilities in [0, 1]",
    )
    passed &= check(
        bob.basin_max_gpi >= 0.0,
        f"Basin max GPI              -> {bob.basin_max_gpi:.6f}",
    )
    passed &= check(
        bob.basin_mean_gpi >= 0.0,
        f"Basin mean GPI             -> {bob.basin_mean_gpi:.6f}",
    )
    passed &= check(
        bob.primary_threat is not None,
        "Primary threat object present",
    )
    passed &= check(
        bob.primary_threat.threat_level in VALID_THREAT_LEVELS,
        f"Threat level valid         -> {bob.primary_threat.threat_level}",
    )
    passed &= check(
        BOB_LAT_MIN <= bob.primary_threat.center_lat <= BOB_LAT_MAX,
        f"Vortex lat in BoB domain   -> {bob.primary_threat.center_lat} N",
    )
    passed &= check(
        BOB_LON_MIN <= bob.primary_threat.center_lon <= BOB_LON_MAX,
        f"Vortex lon in BoB domain   -> {bob.primary_threat.center_lon} E",
    )
    passed &= check(
        0.0 <= bob.primary_threat.genesis_probability <= 1.0,
        f"Genesis probability        -> {bob.primary_threat.genesis_probability:.4f}",
    )
    passed &= check(
        elapsed < 120.0,
        f"BoB analysis time          -> {elapsed:.1f}s  (limit: 120s)",
    )

    # =========================================================================
    # TEST 2: GPI component sanity (physics check)
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 2: GPI physics sanity checks")

    # Sample the point with max GPI for per-field inspection
    if bob.grid_gpi_points:
        best = max(bob.grid_gpi_points, key=lambda p: p.gpi_score)
        passed &= check(
            best.absolute_vorticity_s1 >= 0.0,
            f"Absolute vorticity >= 0    -> {best.absolute_vorticity_s1:.2e} s^-1",
        )
        passed &= check(
            best.mpi_kt >= 0.0,
            f"MPI >= 0                   -> {best.mpi_kt:.1f} kt",
        )
        passed &= check(
            best.sst_c > 20.0,
            f"SST physically plausible   -> {best.sst_c} degC",
        )
        passed &= check(
            best.shear_kt >= 0.0,
            f"Shear >= 0                 -> {best.shear_kt} kt",
        )
        passed &= check(
            0.0 <= best.rh700_pct <= 100.0,
            f"RH700 in [0, 100]%%         -> {best.rh700_pct} %%",
        )
        print(f"\n  {INFO_TAG}  Max-GPI cell: ({best.lat}N, {best.lon}E)")
        print(f"          GPI={best.gpi_score:.6f}  P={best.genesis_probability:.4f}"
              f"  Threat={bob.primary_threat.threat_level}")
        print(f"          SST={best.sst_c}C  Shear={best.shear_kt}kt"
              f"  RH={best.rh700_pct}%%  MPI={best.mpi_kt}kt")
        print(f"          eta={best.absolute_vorticity_s1:.2e} s^-1"
              f"  zeta={best.relative_vorticity_s1:.2e} s^-1")
        print(f"          u850={best.u850_ms} m/s  v850={best.v850_ms} m/s")
        fav_count = sum(1 for p in bob.grid_gpi_points if p.cyclogenesis_favorable)
        print(f"          Favorable points (all 3 thresholds): {fav_count}/20")

    # =========================================================================
    # TEST 3: Arabian Sea quick check
    # =========================================================================
    print(f"\n{INFO_TAG}  Test 3: Arabian Sea -- quick GPI scan")
    t0 = time.perf_counter()
    ars = analyzer.analyze_basin("ARABIAN_SEA")
    elapsed = time.perf_counter() - t0

    passed &= check(
        len(ars.grid_gpi_points) >= 12,
        f"AS grid points computed    -> {len(ars.grid_gpi_points)}/16  (min 12)",
    )
    passed &= check(
        all(p.gpi_score >= 0.0 for p in ars.grid_gpi_points),
        "All AS GPI scores >= 0",
    )
    passed &= check(
        ars.primary_threat.threat_level in VALID_THREAT_LEVELS,
        f"AS threat level valid      -> {ars.primary_threat.threat_level}",
    )
    passed &= check(
        elapsed < 120.0,
        f"AS analysis time           -> {elapsed:.1f}s  (limit: 120s)",
    )

    # =========================================================================
    # Cleanup & final verdict
    # =========================================================================
    analyzer.close()
    service.close()

    print(f"\n{SEPARATOR}")
    if passed:
        print(f"  {PASS_TAG}  STEP 2 COMPLETE -- Cyclogenesis GPI Scanner is LIVE.")
        print(f"         BoB max GPI={bob.basin_max_gpi:.4f}"
              f"  threat={bob.primary_threat.threat_level}"
              f"  P={bob.primary_threat.genesis_probability:.4f}")
        print(f"         Vortex candidate: ({bob.primary_threat.center_lat}N,"
              f" {bob.primary_threat.center_lon}E)")
        print(f"         AS  max GPI={ars.basin_max_gpi:.4f}"
              f"  threat={ars.primary_threat.threat_level}")
        print(f"         Scan time: {bob.timestamp_utc}")
    else:
        print(f"  {FAIL_TAG}  STEP 2 FAILED -- fix the issues above before Step 3.")
    print(SEPARATOR)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
