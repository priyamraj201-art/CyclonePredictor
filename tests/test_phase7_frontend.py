"""Phase 7 Tests: Forecaster Dashboard Components and Production Build."""

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def test_frontend_directory_structure():
    assert FRONTEND_DIR.exists(), "frontend directory must exist"
    assert (FRONTEND_DIR / "package.json").exists(), "package.json must exist"
    assert (FRONTEND_DIR / "src" / "App.jsx").exists(), "App.jsx must exist"
    assert (FRONTEND_DIR / "src" / "index.css").exists(), "index.css must exist"
    assert (FRONTEND_DIR / "src" / "api.js").exists(), "api.js must exist"


def test_components_exist():
    components_dir = FRONTEND_DIR / "src" / "components"
    expected_components = [
        "Navbar.jsx",
        "Map/CycloneMap.jsx",
        "Intensity/IntensityCard.jsx",
        "RapidIntensification/RICard.jsx",
        "Explainability/GradCAMViewer.jsx",
        "RiskMatrix/RiskMatrix.jsx",
        "BulletinViewer/BulletinViewer.jsx",
        "ForecasterReview/ForecasterReviewModal.jsx",
        "SimulationControls/SimulationBar.jsx",
    ]
    for comp in expected_components:
        comp_path = components_dir / comp
        assert comp_path.exists(), f"Component {comp} must exist at {comp_path}"


def test_production_build_artifacts():
    dist_dir = FRONTEND_DIR / "dist"
    assert dist_dir.exists(), "frontend/dist must exist from build"
    assert (dist_dir / "index.html").exists(), "dist/index.html must exist"
    assets = list((dist_dir / "assets").glob("*.js"))
    assert len(assets) > 0, "dist/assets must contain compiled javascript"
