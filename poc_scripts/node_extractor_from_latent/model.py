"""Node Extractor model: cross-attention transformer for multi-label classification.

Architecture (Query2Label-style):
    1. Project SigLIP embedding (1152-d) to d_model
    2. Learned label queries (one per vocab entry) attend to the projected image feature
    3. Each query outputs a binary logit for its corresponding label
    4. Sigmoid + ASL loss for training; threshold at inference

This mirrors DETR/Q2L: each label query independently decides if its object
category is present by attending to the image representation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossAttentionBlock(nn.Module):
    """Single cross-attention layer: queries attend to image features."""

    def __init__(self, d_model: int, num_heads: int, ffn_dim: int, dropout: float = 0.1):
        super().__init__()
        self.cross_attn = nn.MultiheadAttention(
            d_model, num_heads, dropout=dropout, batch_first=True,
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, d_model),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, queries: torch.Tensor, kv: torch.Tensor) -> torch.Tensor:
        """
        Args:
            queries: [B, num_labels, d_model] — label queries
            kv: [B, S, d_model] — image feature tokens

        Returns:
            updated queries: [B, num_labels, d_model]
        """
        # Cross-attention: queries attend to image features
        attn_out, _ = self.cross_attn(queries, kv, kv)
        queries = self.norm1(queries + self.dropout(attn_out))

        # Feed-forward
        ffn_out = self.ffn(queries)
        queries = self.norm2(queries + ffn_out)

        return queries


class NodeExtractorTransformer(nn.Module):
    """Multi-label classifier using cross-attention label queries.

    Args:
        input_dim: dimension of the input embedding (1152 for SigLIP)
        vocab_size: number of labels in the vocabulary
        d_model: internal model dimension
        num_heads: attention heads per layer
        num_layers: number of cross-attention layers
        ffn_dim: feed-forward hidden dimension
        num_image_tokens: number of tokens to split the projected embedding into
        dropout: dropout rate
    """

    def __init__(
        self,
        input_dim: int = 1152,
        vocab_size: int = 3000,
        d_model: int = 512,
        num_heads: int = 8,
        num_layers: int = 2,
        ffn_dim: int = 1024,
        num_image_tokens: int = 16,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.num_image_tokens = num_image_tokens

        # Project input embedding to a sequence of tokens
        # 1152 -> num_image_tokens * d_model, then reshape to [B, num_image_tokens, d_model]
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, num_image_tokens * d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.input_norm = nn.LayerNorm(d_model)

        # Positional encoding for image tokens
        self.image_pos = nn.Parameter(torch.randn(1, num_image_tokens, d_model) * 0.02)

        # Learned label queries — one per vocabulary entry
        self.label_queries = nn.Parameter(torch.randn(1, vocab_size, d_model) * 0.02)

        # Cross-attention layers
        self.layers = nn.ModuleList([
            CrossAttentionBlock(d_model, num_heads, ffn_dim, dropout)
            for _ in range(num_layers)
        ])

        # Classification head: each query -> single logit
        self.classifier = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.trunc_normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, input_dim] SigLIP image embeddings

        Returns:
            logits: [B, vocab_size] raw logits (apply sigmoid for probabilities)
        """
        B = x.size(0)

        # Project to token sequence: [B, num_image_tokens, d_model]
        kv = self.input_proj(x)
        kv = kv.view(B, self.num_image_tokens, self.d_model)
        kv = self.input_norm(kv)
        kv = kv + self.image_pos

        # Expand label queries for batch: [B, vocab_size, d_model]
        queries = self.label_queries.expand(B, -1, -1)

        # Cross-attention layers
        for layer in self.layers:
            queries = layer(queries, kv)

        # Classify each query: [B, vocab_size, 1] -> [B, vocab_size]
        logits = self.classifier(queries).squeeze(-1)

        return logits

    def count_parameters(self) -> dict:
        """Count parameters by component."""
        counts = {
            "input_proj": sum(p.numel() for p in self.input_proj.parameters()),
            "image_pos": self.image_pos.numel(),
            "label_queries": self.label_queries.numel(),
            "cross_attn_layers": sum(p.numel() for p in self.layers.parameters()),
            "classifier": sum(p.numel() for p in self.classifier.parameters()),
        }
        counts["total"] = sum(counts.values())
        return counts
