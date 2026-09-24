"""Data Ingestion Module for Satellite Scans and Environmental Archives.

Supports reading compressed .npz archives, mock generator datasets, and metadata manifests.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset

from src.core.schemas import CycloneObservation
from src.data.preprocessing import SatellitePreprocessor


class SatelliteObservationDataset(Dataset):
    """PyTorch Dataset loading preprocessed or synthetic cyclone observation archives."""

    def __init__(
        self,
        npz_files: List[Path],
        preprocessor: Optional[SatellitePreprocessor] = None,
    ):
        self.npz_files = [Path(p) for p in npz_files if Path(p).exists()]
        self.preprocessor = preprocessor or SatellitePreprocessor()

    def __len__(self) -> int:
        return len(self.npz_files)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        file_path = self.npz_files[idx]
        with np.load(file_path, allow_pickle=True) as data:
            raw_channels = data["channels"]
            mask = data["mask"]
            meta_json = str(data["metadata"])

        obs = CycloneObservation.model_validate_json(meta_json)
        tensor, qa_report = self.preprocessor.process(raw_channels, mask=mask)

        return {
            "tensor": tensor,
            "observation": obs,
            "qa_report": qa_report,
            "filepath": str(file_path),
        }


def load_single_archive(npz_path: Union[str, Path]) -> Tuple[torch.Tensor, CycloneObservation]:
    """Convenience function to load and preprocess a single observation archive."""
    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=True) as data:
        raw_channels = data["channels"]
        mask = data["mask"]
        meta_json = str(data["metadata"])

    obs = CycloneObservation.model_validate_json(meta_json)
    preprocessor = SatellitePreprocessor()
    tensor, _ = preprocessor.process(raw_channels, mask=mask)
    return tensor, obs
