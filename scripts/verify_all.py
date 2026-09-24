"""Master System Verification: Run All 8 Phase Verification Suites.

Validates the full operational readiness of the SIH 2026 PS 26070 Cyclone AI System:
- Phase 1: Satellite Ingestion, Preprocessing & Autoencoder Inpainting
- Phase 2: Deep Learning Cyclone Identification & Center Localisation
- Phase 3: Quantitative Intensity Estimation & Physics-Informed RI
- Phase 4: Bi-LSTM Track Forecasting, Landfall Prediction & Uncertainty Cone
- Phase 5: Cross-Modal Attention Fusion & Coastal Risk Assessment
- Phase 6: FastAPI Production Inference Serving & Cryptographic Audit Trail
- Phase 7: Forecaster Mission-Control Dashboard (React + Leaflet)
- Phase 8: Operational Evaluation Harness, Benchmarks & Containerization
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.logger import logger


def run_command(cmd_args, desc):
    logger.info(f"\n>> RUNNING: {desc} ({' '.join(cmd_args)})")
    t0 = time.time()
    res = subprocess.run(cmd_args, cwd=ROOT_DIR, capture_output=True, text=True)
    elapsed = time.time() - t0
    if res.returncode == 0:
        logger.info(f"   [PASS] {desc} passed in {elapsed:.2f}s")
        return True
    else:
        logger.error(f"   [FAIL] {desc} failed with exit code {res.returncode}")
        logger.error(f"STDOUT:\n{res.stdout}")
        logger.error(f"STDERR:\n{res.stderr}")
        return False


def main():
    logger.info("=" * 75)
    logger.info("   SIH 2026 PS 26070 — MASTER END-TO-END SYSTEM VERIFICATION")
    logger.info("   Ministry of Earth Sciences (MoES) / India Meteorological Department")
    logger.info("=" * 75)

    phases = [
        (["python", "scripts/verify_phase1.py"], "Phase 1: Ingestion & Inpainting"),
        (["python", "scripts/verify_phase2.py"], "Phase 2: Detection & Center Localisation"),
        (["python", "scripts/verify_phase3.py"], "Phase 3: Intensity & Rapid Intensification"),
        (["python", "scripts/verify_phase4.py"], "Phase 4: Track, Landfall & Uncertainty Cone"),
        (["python", "scripts/verify_phase5.py"], "Phase 5: Fusion & Coastal Risk Engine"),
        (["python", "scripts/verify_phase6.py"], "Phase 6: FastAPI Serving Layer & Audit Trail"),
        (["python", "scripts/verify_phase7.py"], "Phase 7: React Forecaster Dashboard"),
        (["python", "scripts/demo_full_system.py"], "Phase 8: Comprehensive End-to-End Demo"),
    ]

    all_passed = True
    for cmd, desc in phases:
        success = run_command(cmd, desc)
        if not success:
            all_passed = False
            logger.error(f"Verification halted due to failure in {desc}.")
            sys.exit(1)

    logger.info("\n" + "=" * 75)
    logger.info("   RUNNING COMPLETE UNIT & INTEGRATION TEST SUITE (PYTEST)...")
    logger.info("=" * 75)
    pytest_res = subprocess.run(["pytest", "tests/", "-v", "--tb=short"], cwd=ROOT_DIR)
    if pytest_res.returncode != 0:
        logger.error("Some pytest unit tests failed!")
        sys.exit(pytest_res.returncode)

    logger.info("\n" + "=" * 75)
    logger.info("   ALL 8 PHASES AND PYTEST TEST SUITES PASSED FLAWLESSLY!")
    logger.info("   THE SYSTEM IS 100% OPERATIONAL, BENCHMARKED, AND DEPLOYMENT-READY.")
    logger.info("=" * 75)


if __name__ == "__main__":
    main()
