"""Node Extractor V3: Q2L cross-attention over real SigLIP spatial patch tokens.

Architecture
------------
This is the correct application of Query2Label (Q2L)-style cross-attention.

V1 used a *pooled* 1152-d vector split into 16 artificial tokens — there was no
real spatial structure for the label queries to attend over.

V3 feeds the model *real* spatial tokens: 729 patch embeddings (27×27 grid) from
SigLIP SO400M's vision transformer (no CLS token — all 729 are spatial), each 1152-d.
Now each label query can genuinely
attend to the spatial region of the image most relevant to its category:
  - "sky"   → attends to upper patches
  - "road"  → attends to lower patches
  - "person" → attends to wherever a human silhouette activates patches

Pipeline:
  1. Project 729 patch tokens from 1152-d → d_model  (shared linear)
  2. Add 2-D positional encoding (27×27 learnable grid)
  3. Self-attention between patch tokens (optional, 1 layer)
     — lets context propagate across patches before label queries arrive
  4. N cross-attention layers:
     - label queries [V, d_model] attend to patch tokens [729, d_model]
     - each query aggregates evidence across the full spatial field
  5. Per-query linear head → logit

Memory vs V1
------------
V1 cross-attention at d_model=256:
  [B, 3453, 256] × 2 layers ≈ 7 GB at batch=128

V3 cross-attention at d_model=512:
  [B, 3453, 512] still large, BUT now the KV side carries real signal.
  Recommended batch_size=32-64 with AMP; the quality gain justifies the cost.

  To keep VRAM manageable: use d_model=256 or 384 if needed.
"""

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Positional Encoding for 27×27 patch grid
# ---------------------------------------------------------------------------

class PatchPositionalEncoding(nn.Module):
    """Learnable 2-D positional encoding for a grid of patches.

    Adds separate row and column embeddings, then sums them.
    This is simpler and more memory-efficient than a flat 729-entry table
    while still encoding full 2-D position.

    Args:
        grid_size : number of patches per side (27 for SigLIP SO400M at 384px)
        d_model   : model hidden dimension
    """

    def __init__(self, grid_size: int = 27, d_model: int = 512):
        super().__init__()
        self.grid_size = grid_size
        self.row_emb   = nn.Embedding(grid_size, d_model)
        self.col_emb   = nn.Embedding(grid_size, d_model)
        self._init()

    def _init(self):
        nn.init.trunc_normal_(self.row_emb.weight, std=0.02)
        nn.init.trunc_normal_(self.col_emb.weight, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, 729, d_model]
        Returns:
            x + positional encoding: [B, 729, d_model]
        """
        G   = self.grid_size
        device = x.device
        rows = torch.arange(G, device=device).unsqueeze(1).expand(G, G).reshape(-1)  # (729,)
        cols = torch.arange(G, device=device).unsqueeze(0).expand(G, G).reshape(-1)  # (729,)
        pos  = self.row_emb(rows) + self.col_emb(cols)   # (729, d_model)
        return x + pos.unsqueeze(0)                       # broadcast over batch


# ---------------------------------------------------------------------------
# Cross-Attention Block (same as V1 but used correctly now)
# ---------------------------------------------------------------------------

class CrossAttentionBlock(nn.Module):
    """Pre-norm cross-attention: label queries attend to patch tokens."""

    def __init__(self, d_model: int, num_heads: int, ffn_dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm_q    = nn.LayerNorm(d_model)
        self.norm_kv   = nn.LayerNorm(d_model)
        self.cross_attn = nn.MultiheadAttention(
            d_model, num_heads, dropout=dropout, batch_first=True,
        )
        self.norm_ffn  = nn.LayerNorm(d_model)
        self.ffn       = nn.Sequential(
            nn.Linear(d_model, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, d_model),
            nn.Dropout(dropout),
        )
        self.dropout   = nn.Dropout(dropout)

    def forward(self, queries: torch.Tensor, kv: torch.Tensor) -> torch.Tensor:
        """
        Args:
            queries : [B, V, d_model]   — one query per label
            kv      : [B, 729, d_model] — patch tokens (key + value)
        Returns:
            updated queries: [B, V, d_model]
        """
        # Cross-attention with pre-norm
        q   = self.norm_q(queries)
        k   = self.norm_kv(kv)
        out, _ = self.cross_attn(q, k, k)
        queries = queries + self.dropout(out)

        # Feed-forward with pre-norm
        queries = queries + self.ffn(self.norm_ffn(queries))
        return queries


# ---------------------------------------------------------------------------
# Optional: self-attention on patch tokens before label queries arrive
# ---------------------------------------------------------------------------

class PatchSelfAttentionBlock(nn.Module):
    """One self-attention layer over patch tokens for context propagation."""

    def __init__(self, d_model: int, num_heads: int, ffn_dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn  = nn.MultiheadAttention(
            d_model, num_heads, dropout=dropout, batch_first=True,
        )
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn   = nn.Sequential(
            nn.Linear(d_model, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, d_model),
            nn.Dropout(dropout),
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_norm     = self.norm1(x)
        out, _     = self.attn(x_norm, x_norm, x_norm)
        x          = x + self.dropout(out)
        x          = x + self.ffn(self.norm2(x))
        return x


# ---------------------------------------------------------------------------
# V3 Model
# ---------------------------------------------------------------------------

class NodeExtractorV3(nn.Module):
    """Q2L-style multi-label classifier over 729 SigLIP spatial patch tokens.

    Args:
        patch_dim       : SigLIP patch token dimension (1152 for SO400M)
        vocab_size      : number of output labels
        d_model         : internal transformer dimension
        num_heads       : attention heads
        num_cross_layers: number of cross-attention layers
        ffn_dim         : FFN inner dimension
        grid_size       : sqrt(num_patches), 27 for SO400M@384
        num_patch_self_attn_layers: self-attention layers on patches before
                          label queries. 0 = skip (faster); 1 recommended.
        dropout         : dropout rate
    """

    def __init__(
        self,
        patch_dim: int = 1152,
        vocab_size: int = 3000,
        d_model: int = 512,
        num_heads: int = 8,
        num_cross_layers: int = 2,
        ffn_dim: int = 1024,
        grid_size: int = 27,
        num_patch_self_attn_layers: int = 1,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.patch_dim   = patch_dim
        self.vocab_size  = vocab_size
        self.d_model     = d_model
        self.num_patches = grid_size * grid_size

        # Project patch tokens: 1152 → d_model
        self.patch_proj = nn.Sequential(
            nn.Linear(patch_dim, d_model),
            nn.LayerNorm(d_model),
        )

        # Learnable 2-D positional encoding for the patch grid
        self.pos_enc = PatchPositionalEncoding(grid_size, d_model)

        # Self-attention over patch tokens (context propagation)
        self.patch_self_attn = nn.ModuleList([
            PatchSelfAttentionBlock(d_model, num_heads, ffn_dim, dropout)
            for _ in range(num_patch_self_attn_layers)
        ])

        # Learned label queries — one per vocabulary entry
        self.label_queries = nn.Parameter(
            torch.randn(1, vocab_size, d_model) * 0.02
        )

        # Cross-attention layers
        self.cross_attn_layers = nn.ModuleList([
            CrossAttentionBlock(d_model, num_heads, ffn_dim, dropout)
            for _ in range(num_cross_layers)
        ])

        # Final norm + per-query classifier
        self.out_norm   = nn.LayerNorm(d_model)
        self.classifier = nn.Linear(d_model, 1, bias=True)

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
        # Zero-init classifier so all logits start at 0 (sigmoid = 0.5)
        nn.init.zeros_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, patches: torch.Tensor) -> torch.Tensor:
        """
        Args:
            patches: [B, 729, 1152]  SigLIP spatial patch tokens

        Returns:
            logits: [B, vocab_size]  raw logits (sigmoid for probabilities)
        """
        B = patches.size(0)

        # 1. Project + positional encoding: [B, 729, d_model]
        kv = self.patch_proj(patches)
        kv = self.pos_enc(kv)

        # 2. Patch self-attention (context propagation)
        for layer in self.patch_self_attn:
            kv = layer(kv)

        # 3. Label queries cross-attend to patch tokens
        queries = self.label_queries.expand(B, -1, -1)   # [B, V, d_model]
        for layer in self.cross_attn_layers:
            queries = layer(queries, kv)

        # 4. Classify: [B, V, d_model] → [B, V]
        queries = self.out_norm(queries)
        logits  = self.classifier(queries).squeeze(-1)
        return logits

    def count_parameters(self) -> dict:
        counts = {
            "patch_proj"        : sum(p.numel() for p in self.patch_proj.parameters()),
            "pos_enc"           : sum(p.numel() for p in self.pos_enc.parameters()),
            "patch_self_attn"   : sum(p.numel() for p in self.patch_self_attn.parameters()),
            "label_queries"     : self.label_queries.numel(),
            "cross_attn_layers" : sum(p.numel() for p in self.cross_attn_layers.parameters()),
            "classifier"        : sum(p.numel() for p in self.classifier.parameters()),
        }
        counts["total"] = sum(counts.values())
        return counts
