"""Grad-CAM Visual Explainability Engine for Tropical Cyclone Intensity.

Computes gradient-weighted class activation maps showing convective cloud features
(eyewall, inner core, spiral bands) driving the neural network's wind speed predictions.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import base64
import io
from typing import Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from src.models.intensity import IntensityEstimationNetwork


class GradCAM:
    """Gradient-weighted Class Activation Mapping (Grad-CAM) for Intensity Networks."""

    def __init__(
        self,
        model: IntensityEstimationNetwork,
        target_layer: Optional[torch.nn.Module] = None,
    ):
        self.model = model
        self.model.eval()
        self.target_layer = target_layer or model.stage3

        self.gradients = None
        self.activations = None

        # Register forward and backward hooks
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        target_size: Tuple[int, int] = (256, 256),
    ) -> np.ndarray:
        """Generate normalized 2D Grad-CAM saliency heatmap in [0.0, 1.0].
        
        Args:
            input_tensor: (1, 4, H, W) or (4, H, W) normalized tensor
        Returns:
            (H, W) float32 numpy array
        """
        if input_tensor.ndim == 3:
            input_tensor = input_tensor.unsqueeze(0)

        input_tensor = input_tensor.clone().requires_grad_(True)
        self.model.zero_grad()

        # Forward pass
        wind_mean, _, _ = self.model(input_tensor)

        # Backward pass with respect to predicted wind speed
        target_score = wind_mean[0]
        target_score.backward(retain_graph=False)

        # Compute importance weights alpha_k via global average pooling of gradients
        # gradients: (1, C, H, W), activations: (1, C, H, W)
        grads = self.gradients[0]       # (C, H, W)
        acts = self.activations[0]      # (C, H, W)

        weights = torch.mean(grads, dim=(1, 2), keepdim=True)  # (C, 1, 1)
        cam = torch.sum(weights * acts, dim=0)                 # (H, W)
        cam = F.relu(cam)                                      # ReLU to focus on positive contributions

        # Upsample to full image size
        cam = cam.unsqueeze(0).unsqueeze(0)                    # (1, 1, H, W)
        cam = F.interpolate(cam, size=target_size, mode="bilinear", align_corners=False)
        cam = cam.squeeze().cpu().numpy()

        # Normalize to [0.0, 1.0]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-6:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        return cam.astype(np.float32)

    def generate_saliency_overlay(
        self,
        input_tensor: torch.Tensor,
        alpha: float = 0.45,
    ) -> Tuple[np.ndarray, str]:
        """Create RGB composite overlay over IR channel and export as Base64 PNG.
        
        Args:
            input_tensor: (4, 256, 256) normalized satellite tensor
            alpha: blending factor for saliency heatmap
        Returns:
            (overlay_rgb [256, 256, 3] uint8, base64_png_data_url)
        """
        if input_tensor.ndim == 4:
            tensor_single = input_tensor[0]
        else:
            tensor_single = input_tensor

        heatmap = self.generate_heatmap(tensor_single)

        # Background is IR channel (Channel 0)
        ir_raw = tensor_single[0].detach().cpu().numpy()
        ir_norm = (ir_raw - ir_raw.min()) / (ir_raw.max() - ir_raw.min() + 1e-6)
        bg_gray = (ir_norm * 255.0).astype(np.uint8)
        bg_rgb = np.stack([bg_gray, bg_gray, bg_gray], axis=-1)

        # Apply custom pseudo-jet colormap for heatmap
        # Blue -> Cyan -> Yellow -> Red
        r = np.clip(1.5 * heatmap - 0.5, 0.0, 1.0) * 255.0
        g = np.clip(1.0 - 2.0 * np.abs(heatmap - 0.5), 0.0, 1.0) * 255.0
        b = np.clip(1.0 - 1.5 * heatmap, 0.0, 1.0) * 255.0
        heat_rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)

        # Blend: mask out very low activations (< 0.15) to preserve clear view of storm
        active_mask = (heatmap > 0.15)[..., np.newaxis]
        composite = bg_rgb.copy()
        composite[active_mask[:, :, 0]] = (
            (1.0 - alpha) * bg_rgb[active_mask[:, :, 0]] + alpha * heat_rgb[active_mask[:, :, 0]]
        ).astype(np.uint8)

        # Convert to Base64 PNG
        pil_img = Image.fromarray(composite)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        base64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        return composite, base64_str
