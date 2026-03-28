"""Dataset for V3 node extractor — stores and loads 729 SigLIP patch tokens.

Key differences from V1/V2 (pooled 1152-d):
  - Each image is stored as (729, 1152) float16 instead of (1152,)
  - HDF5 shape: (N, 729, 1152)  ~1.6 MB/image vs 2.3 KB/image
  - The extractor calls vision_model() and takes last_hidden_state directly —
    SigLIP SO400M has no CLS token, so all 729 tokens are spatial patches
  - NodeDatasetPatched.__getitem__ returns (patches, target)
    where patches is float32 tensor of shape (729, 1152)

Storage estimate for ~193k images (train+val):
  193_000 × 729 × 1152 × 2 bytes ≈ 324 GB
  Make sure /data/merged has enough space before extracting.
"""

import json
import os
from pathlib import Path

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset
from tqdm.auto import tqdm

from node_extractor_from_latent.dataset import NodeVocabulary, RepeatFactorSampler  # reuse vocab + RFS


# ---------------------------------------------------------------------------
# Patch Embedding Cache Builder
# ---------------------------------------------------------------------------

NUM_PATCHES = 729   # SigLIP SO400M at 384px: 27×27 = 729 spatial patches
PATCH_DIM   = 1152  # hidden size of SigLIP SO400M


def build_patch_cache(
    jsonl_path: str,
    cache_path: str,
    siglip_model,
    siglip_processor,
    device: str = "cuda",
    batch_size: int = 16,
):
    """Pre-extract SigLIP patch token sequences and save to HDF5.

    Stores shape (N, 729, 1152) in float16.  Supports incremental caching —
    safe to interrupt and resume.  Image ↔ row mapping is locked by the
    ``image_ids`` dataset written on first run.

    Args:
        jsonl_path    : path to the merged JSONL file
        cache_path    : output HDF5 path (e.g. train_embeddings_patched.h5)
        siglip_model  : loaded SigLIP AutoModel (eval, on device)
        siglip_processor : SigLIP AutoProcessor
        device        : torch device string
        batch_size    : images per GPU batch (keep ≤32 to avoid OOM at 729 tokens)
    """
    import requests, io
    from PIL import Image as PILImage

    # ── 1. Load entries ────────────────────────────────────────────────
    entries = []
    with open(jsonl_path) as f:
        for line in f:
            entries.append(json.loads(line))
    n_total = len(entries)

    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)

    # ── 2. Open or create HDF5 ─────────────────────────────────────────
    is_resume = os.path.exists(cache_path)
    if is_resume:
        try:
            hf = h5py.File(cache_path, "a")
            if "patches" not in hf:
                raise KeyError("patches dataset missing")
            existing_n = hf["patches"].shape[0]
            if existing_n != n_total:
                print(f"  Cache size mismatch ({existing_n} vs {n_total}). Rebuilding...")
                hf.close()
                os.remove(cache_path)
                is_resume = False
        except Exception as e:
            print(f"  Existing cache is invalid ({e}). Rebuilding...")
            try:
                hf.close()
            except Exception:
                pass
            os.remove(cache_path)
            is_resume = False

    if not is_resume:
        hf = h5py.File(cache_path, "w")
        # Main dataset: (N, 729, 1152) — chunked per image for fast random access
        hf.create_dataset(
            "patches",
            shape=(n_total, NUM_PATCHES, PATCH_DIM),
            dtype="float16",
            chunks=(1, NUM_PATCHES, PATCH_DIM),
        )
        hf.create_dataset(
            "image_ids",
            shape=(n_total,),
            dtype=h5py.special_dtype(vlen=str),
        )
        hf.create_dataset(
            "extracted",
            shape=(n_total,),
            dtype=bool,
            data=np.zeros(n_total, dtype=bool),
        )
        # Lock in ID ↔ row mapping immediately
        for i, entry in enumerate(entries):
            hf["image_ids"][i] = entry.get("id", str(i))
        hf.attrs["num_patches"] = NUM_PATCHES
        hf.attrs["patch_dim"]   = PATCH_DIM
        hf.attrs["total"]       = n_total
        hf.flush()
        print(f"Created {cache_path}  ({n_total:,} × {NUM_PATCHES} × {PATCH_DIM})")

    patches_ds   = hf["patches"]
    id_ds        = hf["image_ids"]
    extracted_ds = hf["extracted"]

    # ── 3. Determine remaining work ────────────────────────────────────
    already_done  = np.array(extracted_ds, dtype=bool)
    todo_indices  = [i for i in range(n_total) if not already_done[i]]
    n_skip        = n_total - len(todo_indices)
    if n_skip:
        print(f"Resuming: {n_skip:,} already cached, {len(todo_indices):,} remaining")
    else:
        print(f"Extracting {n_total:,} patch sequences → {cache_path}")

    if not todo_indices:
        hf.attrs["failed"] = int(hf.attrs.get("failed", 0))
        hf.close()
        print("All patches already cached.")
        return

    # Spot-check ID consistency
    for i in todo_indices[:5]:
        stored   = id_ds[i].decode() if isinstance(id_ds[i], bytes) else id_ds[i]
        expected = entries[i].get("id", str(i))
        assert stored == expected, (
            f"ID mismatch at row {i}: cache='{stored}', JSONL='{expected}'. "
            "Delete the cache file and re-run."
        )

    # ── 4. Extract with tqdm ───────────────────────────────────────────
    batch_images, batch_indices = [], []
    failed = int(hf.attrs.get("failed", 0))

    pbar = tqdm(todo_indices, desc="Patch extraction", unit="img", dynamic_ncols=True)

    for i in pbar:
        entry = entries[i]
        image = None

        if entry.get("image_path"):
            p = Path(entry["image_path"])
            if p.exists():
                try:
                    image = PILImage.open(p).convert("RGB")
                except Exception:
                    pass

        if image is None and entry.get("image_url"):
            try:
                resp  = requests.get(entry["image_url"], timeout=10)
                resp.raise_for_status()
                image = PILImage.open(io.BytesIO(resp.content)).convert("RGB")
            except Exception:
                pass

        if image is None:
            failed += 1
            # Write zero placeholder so the row is marked done
            patches_ds[i]   = np.zeros((NUM_PATCHES, PATCH_DIM), dtype=np.float16)
            extracted_ds[i] = True
            pbar.set_postfix(failed=failed)
            continue

        batch_images.append(image)
        batch_indices.append(i)

        if len(batch_images) >= batch_size:
            _flush_patch_batch(batch_images, batch_indices,
                               patches_ds, extracted_ds,
                               siglip_model, siglip_processor, device)
            batch_images, batch_indices = [], []

        pbar.set_postfix(failed=failed)

    if batch_images:
        _flush_patch_batch(batch_images, batch_indices,
                           patches_ds, extracted_ds,
                           siglip_model, siglip_processor, device)

    hf.attrs["failed"] = failed
    hf.flush()
    hf.close()
    print(f"Done! {n_total:,} entries, {failed} failed. Saved to {cache_path}")


def _flush_patch_batch(
    batch_images, batch_indices,
    patches_ds, extracted_ds,
    siglip_model, siglip_processor, device,
):
    """Run SigLIP on a batch, extract patch tokens, write to HDF5."""
    inputs       = siglip_processor(images=batch_images, return_tensors="pt", padding=True)
    pixel_values = inputs["pixel_values"].to(device=device, dtype=siglip_model.dtype)

    with torch.no_grad():
        vision_out = siglip_model.vision_model(
            pixel_values=pixel_values,
            output_hidden_states=False,
        )
        # SigLIP SO400M has NO CLS token — last_hidden_state is already
        # purely spatial patch tokens: (B, 729, 1152)
        patch_tokens = vision_out.last_hidden_state  # (B, 729, 1152)

        # L2-normalise each patch token independently
        patch_tokens = patch_tokens / patch_tokens.norm(dim=-1, keepdim=True).clamp(min=1e-6)
        patch_tokens = patch_tokens.float().cpu().numpy().astype(np.float16)

    for j, bi in enumerate(batch_indices):
        patches_ds[bi]   = patch_tokens[j]   # (729, 1152)
        extracted_ds[bi] = True


# ---------------------------------------------------------------------------
# PyTorch Dataset — patch tokens
# ---------------------------------------------------------------------------

class NodeDatasetPatched(Dataset):
    """Dataset returning (patches, multi_hot_target).

    patches shape : (729, 1152)  float32
    target shape  : (vocab_size,) float32
    """

    def __init__(
        self,
        jsonl_path: str,
        vocab: NodeVocabulary,
        patch_cache_path: str,
    ):
        self.vocab            = vocab
        self.patch_cache_path = patch_cache_path

        print(f"Loading targets from {jsonl_path}...")
        self.targets   = []
        self.image_ids = []
        with open(jsonl_path) as f:
            for line in f:
                entry  = json.loads(line)
                labels = [node["label"] for node in entry["groundTruth"]["nodes"]]
                self.targets.append(vocab.encode(labels))
                self.image_ids.append(entry.get("id", ""))

        self.hf      = h5py.File(patch_cache_path, "r")
        self.patches = self.hf["patches"]   # (N, 729, 1152)

        assert len(self.targets) == self.patches.shape[0], (
            f"Mismatch: {len(self.targets)} JSONL entries vs "
            f"{self.patches.shape[0]} rows in HDF5"
        )
        assert self.patches.shape[1] == NUM_PATCHES, (
            f"Expected {NUM_PATCHES} patches, got {self.patches.shape[1]}"
        )

        # Spot-check ID consistency
        if "image_ids" in self.hf:
            for ci in [0, len(self.image_ids) // 2, len(self.image_ids) - 1]:
                stored = self.hf["image_ids"][ci]
                stored = stored.decode() if isinstance(stored, bytes) else stored
                assert stored == self.image_ids[ci], (
                    f"ID mismatch at row {ci}: cache='{stored}', "
                    f"JSONL='{self.image_ids[ci]}'. Delete cache and re-extract."
                )

        all_t = torch.stack(self.targets)
        print(f"  Samples          : {len(self.targets):,}")
        print(f"  Vocab size       : {vocab.size}")
        print(f"  Avg labels/sample: {all_t.sum(dim=1).mean():.1f}")
        print(f"  Patch shape      : {self.patches.shape[1:]}  (num_patches × patch_dim)")

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        # HDF5 read → numpy (729, 1152) float16 → torch float32
        patches = torch.from_numpy(self.patches[idx].astype(np.float32))
        return patches, self.targets[idx]

    def close(self):
        if hasattr(self, "hf") and self.hf:
            self.hf.close()

    def __del__(self):
        self.close()
