"""Satellite Data Preprocessing & Quality Assurance Pipeline.

Handles radiometric calibration, channel normalization [0, 1], spatial alignment,
and automated inpainting integration for downstream deep learning models.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F

from src.core.constants import (
    CHANNEL_NORMALIZATION_RANGES,
    DEFAULT_IMAGE_SIZE,
    SATELLITE_CHANNELS,
)
from src.data.autoencoder import InpaintingPipeline


def normalize_channels(
    raw_array: np.ndarray,
    channels: Optional[list] = None,
) -> np.ndarray:
    """Normalize raw multi-channel satellite array into [0.0, 1.0] range.
    
    Args:
        raw_array: (4, H, W) physical values (Kelvin, Albedo)
    Returns:
        (4, H, W) float32 array normalized to [0.0, 1.0]
    """
    if channels is None:
        channels = SATELLITE_CHANNELS

    norm_array = np.zeros_like(raw_array, dtype=np.float32)
    for idx, ch_name in enumerate(channels):
        if ch_name in CHANNEL_NORMALIZATION_RANGES:
            min_val, max_val = CHANNEL_NORMALIZATION_RANGES[ch_name]
            norm_array[idx] = (raw_array[idx] - min_val) / (max_val - min_val)
        else:
            norm_array[idx] = raw_array[idx]

    return np.clip(norm_array, 0.0, 1.0)


def denormalize_channels(
    norm_array: np.ndarray,
    channels: Optional[list] = None,
) -> np.ndarray:
    """Denormalize [0.0, 1.0] array back into original physical units (Kelvin, Albedo)."""
    if channels is None:
        channels = SATELLITE_CHANNELS

    phys_array = np.zeros_like(norm_array, dtype=np.float32)
    for idx, ch_name in enumerate(channels):
        if ch_name in CHANNEL_NORMALIZATION_RANGES:
            min_val, max_val = CHANNEL_NORMALIZATION_RANGES[ch_name]
            phys_array[idx] = norm_array[idx] * (max_val - min_val) + min_val
        else:
            phys_array[idx] = norm_array[idx]

    return phys_array


class SatellitePreprocessor:
    """End-to-end preprocessing pipeline for multi-channel satellite scans."""

    def __init__(
        self,
        target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        inpainter: Optional[InpaintingPipeline] = None,
        max_missing_ratio: float = 0.65,
    ):
        self.target_size = target_size
        self.max_missing_ratio = max_missing_ratio
        self.inpainter = inpainter or InpaintingPipeline()

    def check_quality(
        self,
        raw_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> Dict[str, Union[bool, float, str]]:
        """Validate tensor health: checks shape, NaN/Inf values, and missing ratio."""
        if raw_array.ndim != 3 or raw_array.shape[0] != 4:
            return {
                "is_valid": False,
                "reason": f"Expected shape (4, H, W), got {raw_array.shape}",
                "missing_ratio": 1.0,
            }

        # Check for NaN / Inf
        has_nan = np.isnan(raw_array).any()
        has_inf = np.isinf(raw_array).any()
        if has_nan or has_inf:
            return {
                "is_valid": False,
                "reason": "Corrupt tensor: contains NaN or Inf values",
                "missing_ratio": 1.0,
            }

        # Check missing fraction
        if mask is not None:
            missing_ratio = float(1.0 - (np.sum(mask) / mask.size))
        else:
            missing_ratio = 0.0

        if missing_ratio > self.max_missing_ratio:
            return {
                "is_valid": False,
                "reason": f"Missing pixel ratio {missing_ratio:.2%} exceeds threshold {self.max_missing_ratio:.2%}",
                "missing_ratio": missing_ratio,
            }

        return {
            "is_valid": True,
            "reason": "Clean observation passed quality screening",
            "missing_ratio": missing_ratio,
        }

    def process(
        self,
        raw_array: np.ndarray,
        mask: Optional[np.ndarray] = None,
        inpaint_if_needed: bool = True,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """Clean, normalize, resize, and inpaint raw satellite array into ready-to-infer PyTorch tensor.
        
        Args:
            raw_array: (4, H, W) numpy array of physical measurements
            mask: Optional (4, H, W) binary mask (1=valid, 0=corrupt/missing)
            inpaint_if_needed: Whether to trigger autoencoder on missing patches
        Returns:
            (tensor [4, target_H, target_W], quality_report)
        """
        qa_report = self.check_quality(raw_array, mask)
        if not qa_report["is_valid"]:
            # If invalid due to shape/nan, raise ValueError
            raise ValueError(f"Satellite Quality Screening Failed: {qa_report['reason']}")

        # 1. Normalize physical units to [0, 1]
        norm_array = normalize_channels(raw_array)

        # 2. Convert to torch tensor
        tensor = torch.from_numpy(norm_array).float()
        mask_tensor = torch.from_numpy(mask).float() if mask is not None else None

        # 3. Spatial alignment / resize to uniform (4, 256, 256) if needed
        _, cur_h, cur_w = tensor.shape
        target_h, target_w = self.target_size
        if (cur_h, cur_w) != (target_h, target_w):
            tensor = F.interpolate(
                tensor.unsqueeze(0),
                size=(target_h, target_w),
                mode="bilinear",
                align_corners=False,
            ).squeeze(0)
            if mask_tensor is not None:
                mask_tensor = F.interpolate(
                    mask_tensor.unsqueeze(0),
                    size=(target_h, target_w),
                    mode="nearest",
                ).squeeze(0)

        # 4. Inpaint missing scan lines or sensor patches if present
        was_inpainted = False
        if inpaint_if_needed and mask_tensor is not None and (mask_tensor < 0.5).any():
            tensor = self.inpainter.inpaint(tensor, mask_tensor)
            was_inpainted = True

        qa_report["was_inpainted"] = was_inpainted
        qa_report["final_shape"] = tuple(tensor.shape)

        return tensor, qa_report
