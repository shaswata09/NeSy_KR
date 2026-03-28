"""Node Extractor V4: Residual MLP over pooled SigLIP patch tokens.

Architecture rationale
----------------------
V3 used Q2L cross-attention over 729 spatial patch tokens — powerful but
memory-expensive due to O(vocab_size × d_model) label-query activations.

V4 replaces cross-attention with an MLP, exactly mirroring V2's approach
but operating on *patch-token features* instead of the pooled CLS embedding:

    1. Attention pooling : (B, 729, 1152) → (B, 1152)
       Learnable query attends over all 729 patches, producing a single
       weighted-average vector. This is strictly richer than SigLIP's
       built-in mean-pool because the weights are task-specific.
    2. Input projection  : 1152 → hidden_dim  (LayerNorm + GELU)
    3. Residual blocks   : hidden_dim → hidden_dim  (×num_blocks)
    4. Output head       : hidden_dim → vocab_size

Why V4 when V2 already uses pooled embeddings?
-----------------------------------------------
V2's input is SigLIP's *pre-computed* pooler_output — a fixed global average.
V4's input comes from 729 *pre-normalised* patch tokens stored in the same
HDF5 cache as V3.  The learnable attention-pool lets the model discover which
spatial regions matter most for multi-label prediction, then the residual MLP
decodes from that richer representation.

In short:
  V2 = fixed pool → MLP
  V4 = learnable pool over patches → MLP   (same MLP, better input)

Memory comparison (batch=128, vocab=3453)
-----------------------------------------
  V3 activations : 128 × 3453 × 256 × 4 bytes × layers ≈ 3.5 GB
  V4 activations : 128 × 2048 × 4 bytes × blocks        ≈ 0.01 GB
"""

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Attention Pooling: (B, 729, D) → (B, D)
# ---------------------------------------------------------------------------

class AttentionPooling(nn.Module):
    """Single-head attention pooling over patch tokens.

    A learnable query vector attends to all 729 patch tokens and produces
    a single weighted-sum vector.  This is equivalent to a single-head
    cross-attention with one query, but much cheaper to compute.

    Args:
        dim : patch token dimension (1152)
    """

    def __init__(self, dim: int):
        super().__init__()
        self.query = nn.Parameter(torch.randn(1, 1, dim) * 0.02)
        self.scale = dim ** -0.5

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, N, D]  patch tokens
        Returns:
            pooled: [B, D]
        """
        # attn weights: [B, 1, N]
        attn = (self.query * self.scale) @ x.transpose(-2, -1)
        attn = attn.softmax(dim=-1)
        # weighted sum: [B, 1, D] → [B, D]
        return (attn @ x).squeeze(1)


# ---------------------------------------------------------------------------
# Residual Block (same as V2)
# ---------------------------------------------------------------------------

class ResidualBlock(nn.Module):
    """Pre-norm residual MLP block."""

    def __init__(self, dim: int, expansion: int = 2, dropout: float = 0.1):
        super().__init__()
        inner = dim * expansion
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, inner)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(inner, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.drop2(x)
        return x + residual


# ---------------------------------------------------------------------------
# V4 Model
# ---------------------------------------------------------------------------

class NodeExtractorV4(nn.Module):
    """Attention-pooled patch tokens → Residual MLP multi-label classifier.

    Takes 729 SigLIP spatial patch tokens, pools them via learnable attention,
    then decodes multi-label predictions through a deep residual MLP.

    Args:
        patch_dim     : SigLIP patch token dimension (1152 for SO400M)
        vocab_size    : number of output labels
        hidden_dim    : width of the residual MLP backbone
        num_blocks    : number of residual blocks
        expansion     : inner-layer expansion ratio within each block
        dropout       : dropout rate inside each block
        input_dropout : dropout applied after attention pooling
        pool_mode     : "attention" (learnable) or "mean" (simple average)
    """

    def __init__(
        self,
        patch_dim: int = 1152,
        vocab_size: int = 3000,
        hidden_dim: int = 2048,
        num_blocks: int = 6,
        expansion: int = 2,
        dropout: float = 0.1,
        input_dropout: float = 0.05,
        pool_mode: str = "attention",
    ):
        super().__init__()
        self.patch_dim = patch_dim
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.pool_mode = pool_mode

        # Pooling: (B, 729, 1152) → (B, 1152)
        if pool_mode == "attention":
            self.pool = AttentionPooling(patch_dim)
        else:
            self.pool = None  # mean pooling, no parameters

        # Input projection: 1152 → hidden_dim
        self.input_proj = nn.Sequential(
            nn.Dropout(input_dropout),
            nn.Linear(patch_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )

        # Residual MLP backbone
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, expansion=expansion, dropout=dropout)
            for _ in range(num_blocks)
        ])

        # Final norm + classification head
        self.head_norm = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, vocab_size)

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
        # Zero-init output head: logits start at 0, sigmoid ≈ 0.5
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, patches: torch.Tensor) -> torch.Tensor:
        """
        Args:
            patches: [B, 729, 1152] SigLIP spatial patch tokens

        Returns:
            logits: [B, vocab_size] raw logits (apply sigmoid for probabilities)
        """
        # Pool: (B, 729, 1152) → (B, 1152)
        if self.pool is not None:
            x = self.pool(patches)
        else:
            x = patches.mean(dim=1)

        # MLP: (B, 1152) → (B, hidden_dim) → ... → (B, vocab_size)
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        x = self.head_norm(x)
        return self.head(x)

    def count_parameters(self) -> dict:
        counts = {
            "pool"       : sum(p.numel() for p in self.pool.parameters()) if self.pool else 0,
            "input_proj" : sum(p.numel() for p in self.input_proj.parameters()),
            "blocks"     : sum(p.numel() for p in self.blocks.parameters()),
            "head_norm"  : sum(p.numel() for p in self.head_norm.parameters()),
            "head"       : sum(p.numel() for p in self.head.parameters()),
        }
        counts["total"] = sum(counts.values())
        return counts
