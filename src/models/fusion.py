"""Multimodal Attention Fusion Layer.

Fuses multi-channel satellite visual embeddings (256-d), sequential track dynamics (64-d),
and environmental reanalysis thermodynamics (32-d) via Cross-Modal Attention into a unified 128-d representation.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.config import MODELS_DIR, get_device


class CrossModalAttentionFusion(nn.Module):
    """Cross-Modal Attention mechanism fusing visual, sequential, and thermodynamic features."""

    def __init__(
        self,
        visual_dim: int = 256,
        track_dim: int = 64,
        env_dim: int = 7,
        fusion_dim: int = 128,
        num_heads: int = 4,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.fusion_dim = fusion_dim

        # 1. Modality projection heads into uniform 128-dimensional embedding space
        self.proj_visual = nn.Sequential(
            nn.Linear(visual_dim, fusion_dim),
            nn.LayerNorm(fusion_dim),
            nn.ReLU(inplace=True),
        )

        self.proj_track = nn.Sequential(
            nn.Linear(track_dim, fusion_dim),
            nn.LayerNorm(fusion_dim),
            nn.ReLU(inplace=True),
        )

        self.proj_env = nn.Sequential(
            nn.Linear(env_dim, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, fusion_dim),
            nn.LayerNorm(fusion_dim),
            nn.ReLU(inplace=True),
        )

        # 2. Cross-Modal Attention:
        # Query = Visual Features; Key & Value = Contextual [Track + Environmental] Features
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=fusion_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.norm_fusion = nn.LayerNorm(fusion_dim)

        # Feed-forward post-attention block
        self.ffn = nn.Sequential(
            nn.Linear(fusion_dim, fusion_dim * 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fusion_dim * 2, fusion_dim),
        )
        self.norm_ffn = nn.LayerNorm(fusion_dim)

        # Joint composite hazard score head [0.0, 1.0]
        self.hazard_head = nn.Sequential(
            nn.Linear(fusion_dim, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        visual_feat: torch.Tensor,   # (B, 256)
        track_feat: torch.Tensor,    # (B, 64)
        env_feat: torch.Tensor,      # (B, 7)
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.
        
        Returns:
            fused_representation: (B, 128)
            hazard_score: (B, 1) in [0.0, 1.0]
        """
        # Projected tokens
        v_token = self.proj_visual(visual_feat).unsqueeze(1)  # (B, 1, 128)
        t_token = self.proj_track(track_feat).unsqueeze(1)    # (B, 1, 128)
        e_token = self.proj_env(env_feat).unsqueeze(1)        # (B, 1, 128)

        # Context key/values: (B, 2, 128)
        context_tokens = torch.cat([t_token, e_token], dim=1)

        # Cross attention: Query=Visual, Key=Context, Value=Context
        attn_out, _ = self.cross_attention(v_token, context_tokens, context_tokens)
        fused = self.norm_fusion(v_token + attn_out)

        # FFN refinement
        fused = self.norm_ffn(fused + self.ffn(fused))
        fused_vector = fused.squeeze(1)  # (B, 128)

        hazard_score = self.hazard_head(fused_vector)

        return fused_vector, hazard_score


class MultimodalFusionPipeline:
    """Production wrapper for multimodal cross-attention fusion."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device or get_device())
        self.model = CrossModalAttentionFusion().to(self.device)
        self.model.eval()

        if model_path is not None and Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)

    def fuse(
        self,
        visual_embedding: np.ndarray,
        track_embedding: np.ndarray,
        env_feature_vector: np.ndarray,
    ) -> Dict[str, Any]:
        """Execute multimodal cross-attention fusion."""
        v = torch.tensor(visual_embedding, dtype=torch.float32).reshape(1, -1).to(self.device)
        t = torch.tensor(track_embedding, dtype=torch.float32).reshape(1, -1).to(self.device)
        e = torch.tensor(env_feature_vector, dtype=torch.float32).reshape(1, -1).to(self.device)

        with torch.no_grad():
            fused_rep, hazard_score = self.model(v, t, e)

        return {
            "fused_embedding": fused_rep[0].cpu().numpy(),
            "composite_hazard_index": round(float(hazard_score[0, 0].item()), 4),
            "fused_dimension": fused_rep.shape[-1],
        }

    def save_weights(self, path: Optional[Path] = None) -> Path:
        """Save model weights to disk."""
        save_path = path or (MODELS_DIR / "multimodal_fusion.pt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        return save_path
