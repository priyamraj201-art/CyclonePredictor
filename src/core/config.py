"""Application Configuration and Environmental Settings.

Handles path resolutions, compute devices, and OpenMP compatibility for Windows Anaconda.
"""

import os
import sys
from pathlib import Path

# Fix Windows Anaconda OpenMP duplicate library conflict
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Base project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = PROJECT_ROOT / "models_saved"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure essential directories exist
for path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, SYNTHETIC_DATA_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Device Configuration
def get_device():
    """Detect and return optimal compute device (CUDA / MPS / CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.device("cuda")
    except Exception:
        pass
    return "cpu"
