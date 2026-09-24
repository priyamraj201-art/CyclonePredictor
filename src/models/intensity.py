"""Intensity Estimation Model: Wind Speed Regression with Heteroscedastic Uncertainty.

Combines deep convolutional feature extraction with Multi-Head Self-Attention to predict
maximum sustained wind speed (knots), central pressure deficit (hPa), and predictive uncertainty.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.config import MODELS_DIR, get_device
from src.core.constants import CycloneStage
from src.utils.conversions import knots_to_stage, estimate_central_pressure


class ResidualBlock(nn.Module):
    """Conv-BatchNorm-LeakyReLU Residual Block with optional downsampling."""

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.LeakyReLU(0.1, inplace=True)
        self.conv2 = nn.Conv2d(
            out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return self.relu(out)


class IntensityEstimationNetwork(nn.Module):
    """CNN + Multi-Head Self-Attention Hybrid for Cyclone Intensity Estimation."""

    def __init__(
        self,
        in_channels: int = 4,
        embed_dim: int = 256,
        num_heads: int = 4,
        dropout_rate: float = 0.2,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.embed_dim = embed_dim

        # Initial feature stem: (B, 4, 256, 256) -> (B, 64, 128, 128)
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1, inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # (B, 64, 64, 64)
        )

        # Residual stages
        self.stage1 = ResidualBlock(64, 128, stride=2)   # (B, 128, 32, 32)
        self.stage2 = ResidualBlock(128, 256, stride=2)  # (B, 256, 16, 16) - Target layer for Grad-CAM
        self.stage3 = ResidualBlock(256, embed_dim, stride=1)  # (B, 256, 16, 16)

        # Multi-Head Self-Attention over 16x16 = 256 spatial tokens
        self.norm_attn = nn.LayerNorm(embed_dim)
        self.self_attention = nn.MultiheadAttention(
            embed_dim=embed_dim, num_heads=num_heads, dropout=dropout_rate, batch_first=True
        )

        # Global average pool
        self.global_pool = nn.AdaptiveAvgPool2d(1)

        # Regression head: predicts wind speed mean and log-variance for uncertainty
        self.regressor = nn.Sequential(
            nn.Linear(embed_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 2),  # [wind_speed_mean, log_variance]
        )

    def extract_conv_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract spatial feature maps before attention (used for Grad-CAM)."""
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        return x

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass.
        
        Returns:
            (wind_speed_kt, uncertainty_std, visual_embedding)
        """
        # Handle single-channel IR input fallback
        if x.shape[1] == 1 and self.in_channels == 4:
            x = x.repeat(1, 4, 1, 1)

        # 1. Spatial convolutional features (B, 256, 16, 16)
        conv_feat = self.extract_conv_features(x)
        b, c, h, w = conv_feat.shape

        # 2. Self-attention over spatial patches
        # Reshape to (B, H*W, C) = (B, 256, 256)
        tokens = conv_feat.flatten(2).permute(0, 2, 1)
        tokens_norm = self.norm_attn(tokens)
        attn_out, _ = self.self_attention(tokens_norm, tokens_norm, tokens_norm)
        tokens_refined = tokens + attn_out

        # Reshape back to spatial (B, C, H, W)
        spatial_refined = tokens_refined.permute(0, 2, 1).reshape(b, c, h, w)

        # 3. Global pooling to visual embedding vector (B, 256)
        visual_embedding = self.global_pool(spatial_refined).flatten(1)

        # 4. Regression output
        pred = self.regressor(visual_embedding)
        wind_speed_mean = F.relu(pred[:, 0])  # Wind speed >= 0
        log_var = pred[:, 1]
        uncertainty_std = torch.exp(0.5 * torch.clamp(log_var, -4.0, 4.0))

        return wind_speed_mean, uncertainty_std, visual_embedding


class IntensityEstimator:
    """Production inference wrapper for Intensity Estimation."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device or get_device())
        self.model = IntensityEstimationNetwork(in_channels=4).to(self.device)
        self.model.eval()

        if model_path is not None and Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)

    def estimate(
        self,
        satellite_tensor: torch.Tensor,
        calibration_bias_kt: float = 0.0,
    ) -> Dict[str, Any]:
        """Estimate maximum sustained wind speed and empirical central pressure.
        
        Args:
            satellite_tensor: (4, 256, 256) normalized tensor
            calibration_bias_kt: optional manual calibration offset
        Returns:
            Structured prediction dictionary
        """
        if satellite_tensor.ndim == 3:
            tensor_batch = satellite_tensor.unsqueeze(0)
        else:
            tensor_batch = satellite_tensor

        tensor_batch = tensor_batch.to(self.device)

        with torch.no_grad():
            wind_mean, unc_std, visual_emb = self.model(tensor_batch)

        wind_kt = float(wind_mean[0].item()) + calibration_bias_kt
        wind_kt = max(10.0, min(180.0, wind_kt))  # Physical storm bounds
        wind_kt = round(wind_kt, 1)

        uncertainty_kt = round(float(unc_std[0].item()), 2)
        wind_kmh = round(wind_kt * 1.852, 1)

        stage = knots_to_stage(wind_kt)
        central_pressure = estimate_central_pressure(wind_kt)
        pressure_deficit = round(1010.0 - central_pressure, 1)

        return {
            "wind_speed_kt": wind_kt,
            "wind_speed_kmh": wind_kmh,
            "uncertainty_kt": uncertainty_kt,
            "imd_category": stage.value,
            "central_pressure_hpa": central_pressure,
            "pressure_deficit_hpa": pressure_deficit,
            "visual_embedding": visual_emb[0].cpu().numpy(),
        }

    def save_weights(self, path: Optional[Path] = None) -> Path:
        """Save model weights to disk."""
        save_path = path or (MODELS_DIR / "intensity_estimator.pt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        return save_path
