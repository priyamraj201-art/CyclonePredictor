"""Phase 8 Tests: Evaluation Harness, Benchmark Reporting, and Container Configs."""

from pathlib import Path
import pytest
from src.eval.evaluate_pipeline import CycloneEvaluationHarness, BENCHMARKS_DIR

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_docker_and_compose_configs():
    assert (ROOT_DIR / "Dockerfile.backend").exists(), "Dockerfile.backend must exist"
    assert (ROOT_DIR / "Dockerfile.frontend").exists(), "Dockerfile.frontend must exist"
    assert (ROOT_DIR / "docker-compose.yml").exists(), "docker-compose.yml must exist"


def test_evaluation_harness_execution():
    harness = CycloneEvaluationHarness(seed=42)
    # Run on a quick subset of 3 frames to verify metrics computation
    report = harness.evaluate_holdout_dataset(num_samples=3)

    assert "detection" in report
    assert "intensity" in report
    assert "rapid_intensification" in report
    assert "track_forecast" in report

    assert 0.0 <= report["detection"]["f1_score"] <= 1.0
    assert report["intensity"]["mae_knots"] >= 0.0
    assert 0.0 <= report["rapid_intensification"]["critical_success_index_csi"] <= 1.0


def test_benchmark_files_generated():
    json_path = BENCHMARKS_DIR / "evaluation_summary.json"
    md_path = BENCHMARKS_DIR / "evaluation_summary.md"
    assert json_path.exists(), "evaluation_summary.json must exist"
    assert md_path.exists(), "evaluation_summary.md must exist"
