"""PyTorch Convolutional Inpainting Autoencoder for Satellite Imagery.

Lightweight U-Net architecture to reconstruct cloud gaps, scan line dropouts,
and missing sensor patches across 4-channel INSAT-3D observations.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.config import MODELS_DIR, get_device


class DoubleConv(nn.Module):
    """Two consecutive [Conv2d -> BatchNorm -> LeakyReLU] blocks."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class SatelliteInpaintingAutoencoder(nn.Module):
    """Lightweight U-Net Autoencoder for multi-channel satellite patch inpainting.
    
    Accepts (B, 4, H, W) normalized tensor in [0, 1] with missing values set to 0.0,
    along with optional mask (B, 4, H, W).
    """

    def __init__(self, in_channels: int = 4, out_channels: int = 4):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        # Encoder
        self.inc = DoubleConv(in_channels, 32)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(32, 64))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(64, 128))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(128, 256))

        # Decoder with Skip Connections
        self.up1 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(256, 128)

        self.up2 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(128, 64)

        self.up3 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.conv_up3 = DoubleConv(64, 32)

        # Output projection
        self.outc = nn.Sequential(
            nn.Conv2d(32, out_channels, kernel_size=1),
            nn.Sigmoid(),  # Satellite channels normalized to [0, 1]
        )

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Forward pass.
        
        Args:
            x: Input tensor [B, 4, H, W] in [0, 1]
            mask: Binary tensor [B, 4, H, W] where 1 is valid, 0 is missing
        Returns:
            Reconstructed or inpainted tensor [B, 4, H, W]
        """
        # Encoder
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)

        # Decoder with skip connections
        u1 = self.up1(x4)
        if u1.shape != x3.shape:
            u1 = F.interpolate(u1, size=x3.shape[2:], mode="bilinear", align_corners=False)
        d1 = self.conv_up1(torch.cat([u1, x3], dim=1))

        u2 = self.up2(d1)
        if u2.shape != x2.shape:
            u2 = F.interpolate(u2, size=x2.shape[2:], mode="bilinear", align_corners=False)
        d2 = self.conv_up2(torch.cat([u2, x2], dim=1))

        u3 = self.up3(d2)
        if u3.shape != x1.shape:
            u3 = F.interpolate(u3, size=x1.shape[2:], mode="bilinear", align_corners=False)
        d3 = self.conv_up3(torch.cat([u3, x1], dim=1))

        output = self.outc(d3)

        # Inpainting blend: retain uncorrupted input pixels exactly
        if mask is not None:
            return mask * x + (1.0 - mask) * output
        return output


class InpaintingPipeline:
    """Production wrapper for loading and running the inpainting model."""

    def __init__(self, model_path: Optional[Path] = None, device: Optional[str] = None):
        self.device = torch.device(device or get_device())
        self.model = SatelliteInpaintingAutoencoder(in_channels=4, out_channels=4).to(self.device)
        self.model.eval()

        if model_path is not None and model_path.exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)

    def inpaint(self, tensor_normalized: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Inpaint missing masked pixels in a normalized (4, H, W) or (B, 4, H, W) tensor."""
        single_frame = False
        if tensor_normalized.ndim == 3:
            single_frame = True
            tensor_normalized = tensor_normalized.unsqueeze(0)
            if mask is not None and mask.ndim == 3:
                mask = mask.unsqueeze(0)

        tensor_normalized = tensor_normalized.to(self.device)
        if mask is not None:
            mask = mask.to(self.device)

        with torch.no_grad():
            output = self.model(tensor_normalized, mask=mask)

        if single_frame:
            output = output.squeeze(0)
        return output

    def save_weights(self, path: Optional[Path] = None) -> Path:
        """Save autoencoder weights to disk."""
        save_path = path or (MODELS_DIR / "autoencoder_inpainting.pt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        return save_path
