"""Step 6: Final System Verification — Cyclone AI Real-Time Pipeline.

Runs all per-step verification checks in sequence and emits a consolidated
Pass/Fail report suitable for the SIH 2026 evaluation panel.

Coverage:
  STEP 1  — Live atmospheric ingestion (Open-Meteo API, 13 checks)
  STEP 2  — Cyclogenesis GPI scanner   (20 checks, Emanuel-Nolan 2004)
  STEP 3  — End-to-end pipeline        (22 checks, 5-stage inference)
  STEP 4  — FastAPI real-time API      (13 pytest tests, Swagger verified)
  STEP 5  — Frontend build integrity   (Vite production build, 0 errors)
  BRANCH  — Git commit log             (all 5 feature commits present)

Exit 0 = ALL PASS | Exit 1 = ONE OR MORE FAILURES
"""

import sys
import subprocess
import time
import os

sys.path.insert(0, ".")

SEPARATOR = "=" * 70
THIN      = "-" * 70
PASS_TAG  = "[ PASS ]"
FAIL_TAG  = "[ FAIL ]"
INFO_TAG  = "[ INFO ]"
WARN_TAG  = "[ WARN ]"


def section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def run_sub(label: str, cmd: list, cwd: str = ".") -> tuple[bool, float, str]:
    """Run a subprocess, return (passed, elapsed_s, stdout_snippet)."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=300,
        )
        elapsed = round(time.perf_counter() - t0, 1)
        passed  = result.returncode == 0
        output  = (result.stdout + result.stderr).strip()
        # Return last 12 lines of output as snippet
        snippet = "\n".join(output.splitlines()[-12:]) if output else "(no output)"
        return passed, elapsed, snippet
    except subprocess.TimeoutExpired:
        elapsed = round(time.perf_counter() - t0, 1)
        return False, elapsed, "(timed out after 300s)"
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 1)
        return False, elapsed, f"(subprocess error: {exc})"


def check_git_log() -> tuple[bool, str]:
    """Verify all 5 feature commits exist on feature/realtime-pipeline."""
    result = subprocess.run(
        ["git", "log", "--oneline", "feature/realtime-pipeline", "-20"],
        capture_output=True, text=True, cwd=".",
    )
    log = result.stdout.strip()

    required_steps = [
        "feat(step-1)",
        "feat(step-2)",
        "feat(step-3)",
        "feat(step-4)",
        "feat(step-5)",
    ]
    missing = [s for s in required_steps if s not in log]
    passed  = len(missing) == 0
    detail  = log[:600] if log else "(no git log output)"
    return passed, detail, missing


def main() -> int:
    total_start = time.perf_counter()
    results: list[dict] = []

    print(SEPARATOR)
    print("  CYCLONE AI — FINAL SYSTEM VERIFICATION  (SIH 2026 PS 26070)")
    print("  Ministry of Earth Sciences / IMD Real-Time Pipeline")
    print(SEPARATOR)
    print(f"\n  {INFO_TAG}  Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"  {INFO_TAG}  Python: {sys.version.split()[0]}  |  CWD: {os.getcwd()}")

    # =========================================================================
    # STEP 1: Real-Time Ingestion
    # =========================================================================
    section("STEP 1/5 — Real-Time Atmospheric Ingestion Service")
    passed, elapsed, snippet = run_sub(
        "Step 1 ingestion", ["python", "scripts/verify_realtime_ingest.py"]
    )
    print(snippet)
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"\n  {tag}  Step 1 completed in {elapsed}s")
    results.append({"step": 1, "name": "Ingestion", "passed": passed, "elapsed": elapsed})

    # =========================================================================
    # STEP 2: Cyclogenesis GPI Scanner
    # =========================================================================
    section("STEP 2/5 — Cyclogenesis GPI Scanner (Emanuel-Nolan 2004)")
    passed, elapsed, snippet = run_sub(
        "Step 2 cyclogenesis", ["python", "scripts/verify_cyclogenesis.py"]
    )
    print(snippet)
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"\n  {tag}  Step 2 completed in {elapsed}s")
    results.append({"step": 2, "name": "GPI Scanner", "passed": passed, "elapsed": elapsed})

    # =========================================================================
    # STEP 3: Live Pipeline Integration
    # =========================================================================
    section("STEP 3/5 — Live Pipeline Integration (5-Stage Inference)")
    passed, elapsed, snippet = run_sub(
        "Step 3 pipeline", ["python", "scripts/verify_realtime_pipeline.py"]
    )
    print(snippet)
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"\n  {tag}  Step 3 completed in {elapsed}s")
    results.append({"step": 3, "name": "Pipeline", "passed": passed, "elapsed": elapsed})

    # =========================================================================
    # STEP 4: FastAPI Real-Time Endpoints
    # =========================================================================
    section("STEP 4/5 — FastAPI Real-Time Endpoints (pytest)")
    passed, elapsed, snippet = run_sub(
        "Step 4 API", [
            "python", "-m", "pytest", "tests/test_realtime_api.py",
            "-v", "--tb=short", "-q"
        ]
    )
    print(snippet)
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"\n  {tag}  Step 4 completed in {elapsed}s")
    results.append({"step": 4, "name": "FastAPI Endpoints", "passed": passed, "elapsed": elapsed})

    # =========================================================================
    # STEP 5: Frontend Build
    # =========================================================================
    section("STEP 5/5 — Frontend Vite Production Build")
    # On Windows, npm must be invoked as npm.cmd via the shell
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    passed, elapsed, snippet = run_sub(
        "Step 5 build",
        [npm_cmd, "run", "build"],
        cwd="frontend",
    )
    print(snippet)
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"\n  {tag}  Step 5 completed in {elapsed}s")
    results.append({"step": 5, "name": "Frontend Build", "passed": passed, "elapsed": elapsed})

    # =========================================================================
    # BRANCH: Git commit log verification
    # =========================================================================
    section("BRANCH — Git Commit Log (feature/realtime-pipeline)")
    git_ok, git_log, missing = check_git_log()
    print(git_log)
    if missing:
        print(f"\n  {FAIL_TAG}  Missing commits: {missing}")
    else:
        print(f"\n  {PASS_TAG}  All 5 step commits present on feature/realtime-pipeline")
    results.append({"step": "git", "name": "Branch Commits", "passed": git_ok, "elapsed": 0})

    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    total_elapsed = round(time.perf_counter() - total_start, 1)
    all_passed    = all(r["passed"] for r in results)

    print(f"\n{SEPARATOR}")
    print("  FINAL SYSTEM VERIFICATION REPORT")
    print(SEPARATOR)
    print(f"  {'STEP':<6} {'NAME':<22} {'STATUS':<10} {'TIME'}")
    print(f"  {THIN[:66]}")
    for r in results:
        step = str(r["step"])
        tag  = PASS_TAG if r["passed"] else FAIL_TAG
        t    = f"{r['elapsed']}s" if r["elapsed"] else "—"
        print(f"  {step:<6} {r['name']:<22} {tag:<12} {t}")

    print(f"\n  Total checks: {len(results)} / {len(results)} evaluated")
    passed_count = sum(1 for r in results if r["passed"])
    print(f"  Passed: {passed_count}  |  Failed: {len(results) - passed_count}")
    print(f"  Wall time: {total_elapsed}s")
    print(SEPARATOR)

    if all_passed:
        print("""
  ██████╗  █████╗ ███████╗███████╗    ██╗
  ██╔══██╗██╔══██╗██╔════╝██╔════╝    ██║
  ██████╔╝███████║███████╗███████╗    ██║
  ██╔═══╝ ██╔══██║╚════██║╚════██║   ╚═╝
  ██║     ██║  ██║███████║███████║    ██╗
  ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝

  ALL STEPS VERIFIED — READY FOR PR MERGE & RELEASE
  feature/realtime-pipeline -> master
        """)
    else:
        failed = [r["name"] for r in results if not r["passed"]]
        print(f"\n  {FAIL_TAG}  SYSTEM VERIFICATION FAILED — fix: {', '.join(failed)}")

    print(SEPARATOR)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
