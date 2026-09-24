"""Cyclone Detection, Storm Centre Localisation & Stage Classification Engine.

Implements:
1. ResNet-18 multi-task architecture adapted for 4-channel INSAT-3D inputs.
2. Multi-head predictions: Cyclonic presence (BCE), center localisation (x, y), and preliminary stage classification.
3. YOLOv8 adapter interface for bounding-box and center extraction.
4. Circulation energy heatmap generator based on brightness temperature gradients and vorticity.
5. High-level CycloneDetector inference pipeline with geospatial coordinate transforms.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import base64
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
import torchvision.models as models

from src.core.config import MODELS_DIR, get_device
from src.core.constants import Basin, CycloneStage, DEFAULT_IMAGE_SIZE
from src.utils.conversions import knots_to_stage
from src.utils.geospatial import haversine_distance_km, pixel_to_latlon, latlon_to_pixel

# Preliminary stage mapping
PRELIMINARY_STAGES = [
    "Low Pressure / Depression",   # LPA, D, DD (< 34 kt)
    "Cyclonic Storm",              # CS (34 - 47 kt)
    "Severe Cyclonic Storm+",      # SCS, VSCS, ESCS, SuCS (>= 48 kt)
]


class CycloneDetectionNetwork(nn.Module):
    """ResNet-18 multi-task backbone for 4-channel (or 1-channel fallback) satellite imagery."""

    def __init__(
        self,
        in_channels: int = 4,
        pretrained: bool = False,
        dropout_rate: float = 0.3,
    ):
        super().__init__()
        self.in_channels = in_channels

        # Load ResNet-18 backbone
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        base_model = models.resnet18(weights=weights)

        # Adapt first convolution for 4 channels (or 1 channel)
        original_conv1 = base_model.conv1
        self.conv1 = nn.Conv2d(
            in_channels,
            original_conv1.out_channels,
            kernel_size=original_conv1.kernel_size,
            stride=original_conv1.stride,
            padding=original_conv1.padding,
            bias=False,
        )
        if in_channels == 4 and pretrained:
            # Initialize 4th channel using mean of existing 3 channels
            with torch.no_grad():
                self.conv1.weight[:, :3, :, :] = original_conv1.weight
                self.conv1.weight[:, 3:, :, :] = original_conv1.weight.mean(dim=1, keepdim=True)
        elif in_channels == 1 and pretrained:
            with torch.no_grad():
                self.conv1.weight[:, :1, :, :] = original_conv1.weight.mean(dim=1, keepdim=True)

        self.bn1 = base_model.bn1
        self.relu = base_model.relu
        self.maxpool = base_model.maxpool

        self.layer1 = base_model.layer1
        self.layer2 = base_model.layer2
        self.layer3 = base_model.layer3
        self.layer4 = base_model.layer4
        self.avgpool = base_model.avgpool

        feature_dim = 512

        # 1. Presence Head: Binary classification (cyclonic circulation vs ambient clouds)
        self.presence_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

        # 2. Centre Localisation Head: Continuous normalized (x, y) coordinates in [0, 1]
        self.centre_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 2),
            nn.Sigmoid(),
        )

        # 3. Preliminary Stage Classifier: 3 categories (Depression, Cyclonic Storm, Severe+)
        self.stage_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, len(PRELIMINARY_STAGES)),
        )

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract 512-dimensional spatial representation from satellite tensor."""
        # Handle fallback for single-channel IR inputs
        if x.shape[1] == 1 and self.in_channels == 4:
            x = x.repeat(1, 4, 1, 1)
        elif x.shape[1] == 4 and self.in_channels == 1:
            x = x[:, :1, :, :]

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        features = torch.flatten(x, 1)
        return features

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass.
        
        Returns:
            Dict containing:
                - 'presence': (B, 1) in [0, 1]
                - 'centre': (B, 2) in [0, 1]
                - 'stage_logits': (B, 3)
                - 'features': (B, 512)
        """
        features = self.extract_features(x)

        presence = self.presence_head(features)
        centre = self.centre_head(features)
        stage_logits = self.stage_head(features)

        return {
            "presence": presence,
            "centre": centre,
            "stage_logits": stage_logits,
            "features": features,
        }


def compute_circulation_energy_map(
    tensor: torch.Tensor,
    predicted_center_norm: Tuple[float, float],
    image_shape: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
) -> np.ndarray:
    """Generate visual energy heatmap highlighting the circulation vortex center.
    
    Combines IR brightness temperature depression, spatial gradients, and model center prior.
    
    Args:
        tensor: (4, H, W) normalized tensor where channel 0 is IR (inverted in norm: high = cold clouds)
        predicted_center_norm: (norm_x, norm_y) in [0, 1]
    Returns:
        (H, W) float32 energy map in [0, 1]
    """
    h, w = image_shape
    # Channel 0 is IR. In normalized space, deep convective clouds have high values
    ir_channel = tensor[0].detach().cpu().numpy()
    if ir_channel.shape != (h, w):
        ir_channel = np.resize(ir_channel, (h, w))

    # Center prior (Gaussian centered at predicted center)
    cx = predicted_center_norm[0] * (w - 1)
    cy = predicted_center_norm[1] * (h - 1)
    y_coords, x_coords = np.ogrid[:h, :w]
    dist_sq = (x_coords - cx) ** 2 + (y_coords - cy) ** 2
    # Standard deviation ~ 30 pixels (approx 120 km)
    sigma = max(15.0, min(h, w) * 0.12)
    gaussian_prior = np.exp(-dist_sq / (2 * (sigma ** 2)))

    # Compute spatial gradient (proxy for cloud vorticity / shear)
    gy, gx = np.gradient(ir_channel)
    gradient_mag = np.sqrt(gx ** 2 + gy ** 2)
    gradient_mag = gradient_mag / (gradient_mag.max() + 1e-6)

    # Composite energy map: 50% Gaussian focus, 30% deep convection, 20% vorticity gradient
    energy = 0.50 * gaussian_prior + 0.30 * ir_channel + 0.20 * gradient_mag
    energy = (energy - energy.min()) / (energy.max() - energy.min() + 1e-6)

    return energy.astype(np.float32)


class YOLOv8Adapter:
    """Compatibility interface matching the Ultralytics YOLOv8 object detection specification.
    
    Provides standardized bounding box extraction, center coordinates, and class confidence.
    """

    def __init__(self, confidence_threshold: float = 0.45):
        self.confidence_threshold = confidence_threshold
        self.has_ultralytics = False
        try:
            import ultralytics
            self.has_ultralytics = True
        except ImportError:
            self.has_ultralytics = False

    def predict_boxes(
        self,
        image_array: np.ndarray,
        center_norm: Optional[Tuple[float, float]] = None,
        confidence: float = 0.85,
        stage_name: str = "Cyclonic Storm",
    ) -> List[Dict[str, Any]]:
        """Extract bounding box and circulation center.
        
        Returns:
            List of detected boxes: [{ 'bbox': [x1, y1, x2, y2], 'center': [cx, cy], 'conf': float, 'class_name': str }]
        """
        h, w = image_array.shape[-2:]
        if center_norm is None:
            center_norm = (0.5, 0.5)

        cx = center_norm[0] * w
        cy = center_norm[1] * h

        # Physical storm envelope typically spans 35% - 50% of the synoptic frame (~400 - 600 km)
        box_w = w * 0.42
        box_h = h * 0.42

        x1 = max(0.0, cx - box_w / 2.0)
        y1 = max(0.0, cy - box_h / 2.0)
        x2 = min(float(w), cx + box_w / 2.0)
        y2 = min(float(h), cy + box_h / 2.0)

        return [{
            "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            "center_pixel": [round(cx, 1), round(cy, 1)],
            "center_norm": [round(center_norm[0], 4), round(center_norm[1], 4)],
            "confidence": round(confidence, 3),
            "class_name": stage_name,
        }]


class CycloneDetectionDataset(Dataset):
    """Dataset for training and validating cyclone presence and center localization."""

    def __init__(
        self,
        observations: List[Tuple[Any, np.ndarray, np.ndarray]],
        image_shape: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    ):
        self.observations = observations
        self.image_shape = image_shape

    def __len__(self) -> int:
        return len(self.observations)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        obs, raw, mask = self.observations[idx]
        h, w = self.image_shape

        # Normalize raw array to [0, 1]
        norm_array = (raw - raw.min()) / (raw.max() - raw.min() + 1e-6)
        tensor = torch.from_numpy(norm_array).float()

        # Presence label (1.0 = storm present)
        presence = 1.0 if obs.best_track.max_sustained_wind_kt >= 17.0 else 0.0

        # Center coordinates
        bbox = obs.satellite_meta.bounding_box
        px, py = latlon_to_pixel(obs.best_track.lat, obs.best_track.lon, self.image_shape, bbox)
        center_x_norm = np.clip(px / (w - 1), 0.0, 1.0)
        center_y_norm = np.clip(py / (h - 1), 0.0, 1.0)

        # Preliminary stage label
        w_kt = obs.best_track.max_sustained_wind_kt
        if w_kt < 34.0:
            stage_idx = 0  # Depression
        elif w_kt < 48.0:
            stage_idx = 1  # Cyclonic Storm
        else:
            stage_idx = 2  # Severe+

        return {
            "tensor": tensor,
            "presence": torch.tensor([presence], dtype=torch.float32),
            "centre": torch.tensor([center_x_norm, center_y_norm], dtype=torch.float32),
            "stage": torch.tensor(stage_idx, dtype=torch.long),
        }


class CycloneDetector:
    """Production inference engine for Cyclone Detection and Storm Centre Localisation."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        presence_threshold: float = 0.50,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device or get_device())
        self.presence_threshold = presence_threshold

        self.model = CycloneDetectionNetwork(in_channels=4, pretrained=False).to(self.device)
        self.model.eval()

        if model_path is not None and Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)

        self.yolo_adapter = YOLOv8Adapter(confidence_threshold=presence_threshold)

    def detect(
        self,
        satellite_tensor: torch.Tensor,
        bounding_box: Tuple[float, float, float, float] = (5.0, 25.0, 80.0, 100.0),
        ground_truth_latlon: Optional[Tuple[float, float]] = None,
    ) -> Dict[str, Any]:
        """Execute automated cyclone detection, center localization, and stage estimation.
        
        Args:
            satellite_tensor: (4, 256, 256) normalized tensor
            bounding_box: (min_lat, max_lat, min_lon, max_lon)
            ground_truth_latlon: Optional (true_lat, true_lon) for error calculation
        Returns:
            Structured diagnostic dictionary
        """
        if satellite_tensor.ndim == 3:
            tensor_batch = satellite_tensor.unsqueeze(0)
        else:
            tensor_batch = satellite_tensor

        tensor_batch = tensor_batch.to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor_batch)

        presence_prob = float(outputs["presence"][0, 0].item())
        centre_norm = (
            float(outputs["centre"][0, 0].item()),
            float(outputs["centre"][0, 1].item()),
        )
        stage_logits = outputs["stage_logits"][0]
        stage_probs = F.softmax(stage_logits, dim=-1).cpu().numpy()
        pred_stage_idx = int(np.argmax(stage_probs))
        pred_stage_name = PRELIMINARY_STAGES[pred_stage_idx]

        is_detected = presence_prob >= self.presence_threshold

        # Map center to pixel and geographic Lat/Lon
        h, w = satellite_tensor.shape[-2:]
        px = centre_norm[0] * (w - 1)
        py = centre_norm[1] * (h - 1)
        pred_lat, pred_lon = pixel_to_latlon(px, py, (h, w), bounding_box)

        # Compute Haversine distance error if ground truth is supplied
        localisation_error_km: Optional[float] = None
        if ground_truth_latlon is not None:
            true_lat, true_lon = ground_truth_latlon
            localisation_error_km = haversine_distance_km(pred_lat, pred_lon, true_lat, true_lon)

        # Generate circulation energy heatmap
        energy_map = compute_circulation_energy_map(
            tensor=satellite_tensor,
            predicted_center_norm=centre_norm,
            image_shape=(h, w),
        )

        # YOLOv8 bounding box format
        boxes = self.yolo_adapter.predict_boxes(
            image_array=satellite_tensor.cpu().numpy(),
            center_norm=centre_norm,
            confidence=presence_prob,
            stage_name=pred_stage_name,
        )

        return {
            "is_cyclone_detected": is_detected,
            "presence_probability": round(presence_prob, 4),
            "preliminary_stage": pred_stage_name,
            "stage_probabilities": {
                stage_name: round(float(prob), 4)
                for stage_name, prob in zip(PRELIMINARY_STAGES, stage_probs)
            },
            "center_normalized": (round(centre_norm[0], 4), round(centre_norm[1], 4)),
            "center_pixel": (round(px, 1), round(py, 1)),
            "center_lat_lon": (round(pred_lat, 4), round(pred_lon, 4)),
            "bounding_box_geo": bounding_box,
            "localisation_error_km": localisation_error_km,
            "yolo_detection": boxes[0] if boxes else None,
            "energy_heatmap": energy_map,
            "latent_features": outputs["features"][0].cpu().numpy(),
        }

    def save_weights(self, path: Optional[Path] = None) -> Path:
        """Save detection model weights to disk."""
        save_path = path or (MODELS_DIR / "detection_resnet18.pt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        return save_path
