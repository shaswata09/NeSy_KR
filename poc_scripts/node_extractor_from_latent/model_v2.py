"""Node Extractor V2: Residual MLP for multi-label classification from pooled SigLIP embeddings.

Architecture rationale
----------------------
V1 used Query2Label-style cross-attention, which was designed for *spatial* feature maps
where label queries attend to different image regions.  Here the input is a single *pooled*
1152-d SigLIP vector — there is no spatial structure to attend over, so cross-attention
adds memory cost without providing a meaningful inductive bias.

V2 replaces that with a deep residual MLP:

    1. Input projection  : 1152  → hidden_dim   (with LayerNorm + GELU)
    2. Residual blocks   : hidden_dim → hidden_dim  (×num_blocks)
       Each block: Linear → LayerNorm → GELU → Dropout → Linear → Dropout → residual add
    3. Output head       : hidden_dim → vocab_size  (one logit per label)

Why this works better for pooled embeddings
-------------------------------------------
- The pooled SigLIP vector already encodes a rich global scene representation.
  A well-regularised MLP can directly decode multi-label predictions from it.
- No O(vocab_size × d_model) activation tensors: enables large hidden_dim (2048+)
  and batch_size (1024+) on the same GPU that V1 OOM'd at batch=128.
- Residual connections let gradients flow cleanly through deep stacks.
- LayerNorm inside each block stabilises training without BatchNorm's batch-size
  sensitivity.
- Dropout per-block provides strong regularisation for the long-tail label space.

Memory comparison (batch=512, vocab=3453)
-----------------------------------------
  V1 activations  : 512 × 3453 × 256 × 4 bytes × layers  ≈ 7 GB
  V2 activations  : 512 × 2048 × 4 bytes × blocks         ≈ 0.04 GB
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    """Pre-norm residual MLP block: LayerNorm → Linear → GELU → Dropout → Linear → Dropout + skip."""

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


class NodeExtractorMLP(nn.Module):
    """Residual MLP multi-label classifier for node extraction.

    Takes a pooled SigLIP embedding and predicts which vocabulary labels are
    present in the image.

    Args:
        input_dim   : SigLIP pooled embedding dimension (1152 for SO400M)
        vocab_size  : number of output labels
        hidden_dim  : width of the residual MLP backbone
        num_blocks  : number of residual blocks
        expansion   : inner-layer expansion ratio within each block (default 2)
        dropout     : dropout rate inside each block and after the input projection
        input_dropout: dropout applied to the raw input embedding (regularises
                       the frozen SigLIP features and improves generalisation)
    """

    def __init__(
        self,
        input_dim: int = 1152,
        vocab_size: int = 3000,
        hidden_dim: int = 2048,
        num_blocks: int = 6,
        expansion: int = 2,
        dropout: float = 0.1,
        input_dropout: float = 0.0,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim

        # Input projection: map SigLIP 1152-d to hidden_dim with normalisation
        self.input_proj = nn.Sequential(
            nn.Dropout(input_dropout),
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )

        # Residual MLP backbone
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, expansion=expansion, dropout=dropout)
            for _ in range(num_blocks)
        ])

        # Final LayerNorm before classification head (pre-norm style)
        self.head_norm = nn.LayerNorm(hidden_dim)

        # Classification head: hidden_dim → vocab_size
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

        # Zero-init the output head so logits start near 0 (sigmoid ≈ 0.5)
        # This gives a neutral starting point for the ASL loss
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, input_dim] pooled SigLIP image embeddings

        Returns:
            logits: [B, vocab_size] raw logits (apply sigmoid for probabilities)
        """
        x = self.input_proj(x)

        for block in self.blocks:
            x = block(x)

        x = self.head_norm(x)
        return self.head(x)

    def count_parameters(self) -> dict:
        counts = {
            "input_proj" : sum(p.numel() for p in self.input_proj.parameters()),
            "blocks"     : sum(p.numel() for p in self.blocks.parameters()),
            "head_norm"  : sum(p.numel() for p in self.head_norm.parameters()),
            "head"       : sum(p.numel() for p in self.head.parameters()),
        }
        counts["total"] = sum(counts.values())
        return counts
