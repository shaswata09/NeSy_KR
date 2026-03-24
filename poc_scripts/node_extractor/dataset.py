"""Dataset and vocabulary for the node extractor.

Loads the merged VG+GQA JSONL, builds a normalized node vocabulary,
and provides a PyTorch Dataset that returns (embedding, multi_hot_target).
"""

import json
import os
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset, Sampler

from .utils import normalize_label


# ---------------------------------------------------------------------------
# Node Vocabulary
# ---------------------------------------------------------------------------


class NodeVocabulary:
    """Maps normalized node labels to indices for multi-label classification.

    Build from a JSONL file, persist to JSON, reload for inference.
    """

    def __init__(self):
        self.label_to_idx: dict[str, int] = {}
        self.idx_to_label: dict[int, str] = {}
        self.label_counts: dict[str, int] = {}

    @property
    def size(self) -> int:
        return len(self.label_to_idx)

    def build(self, jsonl_path: str, min_freq: int = 50) -> "NodeVocabulary":
        """Build vocabulary from a JSONL dataset file.

        Args:
            jsonl_path: path to the merged JSONL (one entry per line)
            min_freq: minimum label frequency to include in vocabulary
        """
        counter = Counter()
        n_images = 0

        print(f"Building vocabulary from {jsonl_path}...")
        with open(jsonl_path) as f:
            for line in f:
                entry = json.loads(line)
                for node in entry["groundTruth"]["nodes"]:
                    label = normalize_label(node["label"])
                    counter[label] += 1
                n_images += 1

        # Filter by frequency
        filtered = {label: count for label, count in counter.items() if count >= min_freq}
        sorted_labels = sorted(filtered.keys(), key=lambda x: -filtered[x])

        self.label_to_idx = {label: idx for idx, label in enumerate(sorted_labels)}
        self.idx_to_label = {idx: label for label, idx in self.label_to_idx.items()}
        self.label_counts = {label: filtered[label] for label in sorted_labels}

        print(f"  Images scanned: {n_images:,}")
        print(f"  Raw unique labels: {len(counter):,}")
        print(f"  After normalization + min_freq={min_freq}: {self.size:,} labels")
        print(f"  Top 20: {sorted_labels[:20]}")
        print(f"  Coverage: {sum(filtered.values()) / sum(counter.values()) * 100:.1f}% "
              f"of all label occurrences")

        return self

    def encode(self, node_labels: list[str]) -> torch.Tensor:
        """Encode a list of node labels to a multi-hot binary vector.

        Args:
            node_labels: raw label strings from the dataset

        Returns:
            float tensor of shape (vocab_size,)
        """
        target = torch.zeros(self.size, dtype=torch.float32)
        for label in node_labels:
            normalized = normalize_label(label)
            if normalized in self.label_to_idx:
                target[self.label_to_idx[normalized]] = 1.0
        return target

    def decode(self, multi_hot: torch.Tensor, threshold: float = 0.5) -> list[str]:
        """Decode a multi-hot or probability vector to label strings.

        Args:
            multi_hot: tensor of shape (vocab_size,), probabilities or binary
            threshold: decision threshold

        Returns:
            list of (label, score) tuples, sorted by score descending
        """
        indices = (multi_hot >= threshold).nonzero(as_tuple=True)[0]
        results = []
        for idx in indices:
            label = self.idx_to_label[idx.item()]
            score = multi_hot[idx].item()
            results.append((label, score))
        return sorted(results, key=lambda x: -x[1])

    def save(self, path: str):
        """Save vocabulary to JSON."""
        data = {
            "label_to_idx": self.label_to_idx,
            "label_counts": self.label_counts,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Vocabulary saved to {path} ({self.size} labels)")

    def load(self, path: str) -> "NodeVocabulary":
        """Load vocabulary from JSON."""
        with open(path) as f:
            data = json.load(f)
        self.label_to_idx = data["label_to_idx"]
        self.idx_to_label = {int(idx): label for label, idx in self.label_to_idx.items()}
        self.label_counts = data.get("label_counts", {})
        print(f"Vocabulary loaded from {path} ({self.size} labels)")
        return self


# ---------------------------------------------------------------------------
# Embedding Cache Builder
# ---------------------------------------------------------------------------


def build_embedding_cache(
    jsonl_path: str,
    cache_path: str,
    siglip_model,
    siglip_processor,
    device: str = "cuda",
    batch_size: int = 32,
):
    """Pre-extract SigLIP image embeddings for all images and save to HDF5.

    Supports **incremental caching**: if the HDF5 file already exists, only
    images that have not yet been extracted are processed.  Each image is
    keyed by its unique ``id`` field from the JSONL, so the positional
    mapping (JSONL row i ↔ HDF5 row i) is always consistent.

    Args:
        jsonl_path: path to the merged JSONL file
        cache_path: output HDF5 file path
        siglip_model: loaded SigLIP model (on device, eval mode)
        siglip_processor: SigLIP processor for images
        device: torch device
        batch_size: images per batch
    """
    from PIL import Image as PILImage
    from tqdm.auto import tqdm
    import requests
    import io

    # ── 1. Load all entries and build the authoritative ID list ────────
    entries = []
    with open(jsonl_path) as f:
        for line in f:
            entries.append(json.loads(line))

    n_total = len(entries)
    embedding_dim = siglip_model.config.vision_config.hidden_size
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)

    # ── 2. Open or create the HDF5 cache ──────────────────────────────
    is_resume = os.path.exists(cache_path)
    if is_resume:
        hf = h5py.File(cache_path, "a")  # append mode

        # Validate that the existing cache matches the current JSONL order
        existing_ids = [hf["image_ids"][i].decode() if isinstance(hf["image_ids"][i], bytes)
                        else hf["image_ids"][i] for i in range(hf["image_ids"].shape[0])]

        # Check if the JSONL has grown or changed
        if len(existing_ids) != n_total:
            print(f"  Cache size mismatch ({len(existing_ids)} vs {n_total}). Rebuilding...")
            hf.close()
            os.remove(cache_path)
            is_resume = False

    if not is_resume:
        hf = h5py.File(cache_path, "w")
        hf.create_dataset(
            "embeddings",
            shape=(n_total, embedding_dim),
            dtype="float16",
            chunks=(min(1000, n_total), embedding_dim),
        )
        hf.create_dataset(
            "image_ids",
            shape=(n_total,),
            dtype=h5py.special_dtype(vlen=str),
        )
        # Boolean mask: True = embedding has been extracted for this row
        hf.create_dataset(
            "extracted",
            shape=(n_total,),
            dtype=bool,
            data=np.zeros(n_total, dtype=bool),
        )
        # Write image IDs upfront so the ID↔row mapping is locked in
        for i, entry in enumerate(entries):
            hf["image_ids"][i] = entry.get("id", str(i))
        hf.attrs["embedding_dim"] = embedding_dim
        hf.attrs["total"] = n_total
        hf.flush()

    emb_ds = hf["embeddings"]
    id_ds = hf["image_ids"]
    extracted_ds = hf["extracted"]

    # ── 3. Determine which rows still need extraction ─────────────────
    already_done = np.array(extracted_ds, dtype=bool)
    todo_indices = [i for i in range(n_total) if not already_done[i]]
    n_skip = n_total - len(todo_indices)

    if n_skip > 0:
        print(f"Resuming: {n_skip:,} already cached, {len(todo_indices):,} remaining")
    else:
        print(f"Building embedding cache for {n_total:,} entries -> {cache_path}")

    if len(todo_indices) == 0:
        hf.attrs["failed"] = int(hf.attrs.get("failed", 0))
        hf.close()
        print("All embeddings already cached. Nothing to do.")
        return

    # ── 4. Verify ID consistency for every row we are about to write ──
    for i in todo_indices[:10]:  # spot-check first 10
        stored_id = id_ds[i].decode() if isinstance(id_ds[i], bytes) else id_ds[i]
        expected_id = entries[i].get("id", str(i))
        assert stored_id == expected_id, (
            f"ID mismatch at row {i}: cache has '{stored_id}', "
            f"JSONL has '{expected_id}'. Delete the cache and rebuild."
        )

    # ── 5. Extract embeddings with batching + tqdm ────────────────────
    batch_images = []
    batch_indices = []
    failed = int(hf.attrs.get("failed", 0))

    pbar = tqdm(
        todo_indices,
        desc="Extracting embeddings",
        unit="img",
        dynamic_ncols=True,
    )

    for i in pbar:
        entry = entries[i]
        image = None

        # Try local path (GQA)
        if entry.get("image_path"):
            p = Path(entry["image_path"])
            if p.exists():
                try:
                    image = PILImage.open(p).convert("RGB")
                except Exception:
                    pass

        # Try remote URL (VG)
        if image is None and entry.get("image_url"):
            try:
                resp = requests.get(entry["image_url"], timeout=10)
                resp.raise_for_status()
                image = PILImage.open(io.BytesIO(resp.content)).convert("RGB")
            except Exception:
                pass

        if image is None:
            failed += 1
            emb_ds[i] = np.zeros(embedding_dim, dtype=np.float16)
            extracted_ds[i] = True
            pbar.set_postfix(failed=failed)
            continue

        batch_images.append(image)
        batch_indices.append(i)

        # Process batch when full or at the end
        if len(batch_images) >= batch_size:
            _flush_batch(
                batch_images, batch_indices, emb_ds, extracted_ds,
                siglip_model, siglip_processor, device, embedding_dim,
            )
            batch_images = []
            batch_indices = []

        pbar.set_postfix(failed=failed)

    # Flush remaining images in the last partial batch
    if batch_images:
        _flush_batch(
            batch_images, batch_indices, emb_ds, extracted_ds,
            siglip_model, siglip_processor, device, embedding_dim,
        )

    hf.attrs["failed"] = failed
    hf.flush()
    hf.close()

    print(f"Done! {n_total:,} entries, {failed} failed. Saved to {cache_path}")


def _flush_batch(
    batch_images, batch_indices, emb_ds, extracted_ds,
    siglip_model, siglip_processor, device, embedding_dim,
):
    """Run SigLIP on a batch of images and write embeddings to HDF5."""
    inputs = siglip_processor(images=batch_images, return_tensors="pt", padding=True)
    pixel_values = inputs["pixel_values"].to(device=device, dtype=siglip_model.dtype)

    with torch.no_grad():
        vision_out = siglip_model.vision_model(pixel_values=pixel_values)
        features = vision_out.pooler_output
        features = features / features.norm(dim=-1, keepdim=True)
        features = features.float().cpu().numpy().astype(np.float16)

    for j, bi in enumerate(batch_indices):
        emb_ds[bi] = features[j]
        extracted_ds[bi] = True


# ---------------------------------------------------------------------------
# PyTorch Dataset
# ---------------------------------------------------------------------------


class NodeDataset(Dataset):
    """Dataset for node extractor training.

    Loads pre-extracted SigLIP embeddings from HDF5 and multi-hot targets from JSONL.
    """

    def __init__(self, jsonl_path: str, vocab: NodeVocabulary, embedding_cache_path: str):
        """
        Args:
            jsonl_path: path to merged JSONL file
            vocab: NodeVocabulary instance
            embedding_cache_path: path to HDF5 file with pre-extracted embeddings
        """
        self.vocab = vocab
        self.embedding_cache_path = embedding_cache_path

        # Load all targets from JSONL (only labels, not full entries)
        print(f"Loading targets from {jsonl_path}...")
        self.targets = []
        self.image_ids = []
        with open(jsonl_path) as f:
            for line in f:
                entry = json.loads(line)
                labels = [node["label"] for node in entry["groundTruth"]["nodes"]]
                self.targets.append(vocab.encode(labels))
                self.image_ids.append(entry.get("id", ""))

        # Open HDF5 (kept open for __getitem__)
        self.hf = h5py.File(embedding_cache_path, "r")
        self.embeddings = self.hf["embeddings"]

        assert len(self.targets) == self.embeddings.shape[0], (
            f"Mismatch: {len(self.targets)} JSONL entries vs "
            f"{self.embeddings.shape[0]} embeddings in HDF5"
        )

        # Verify ID consistency (spot-check first, middle, last entries)
        if "image_ids" in self.hf:
            check_indices = [0, len(self.image_ids) // 2, len(self.image_ids) - 1]
            for ci in check_indices:
                stored = self.hf["image_ids"][ci]
                stored = stored.decode() if isinstance(stored, bytes) else stored
                assert stored == self.image_ids[ci], (
                    f"ID mismatch at row {ci}: cache='{stored}', "
                    f"JSONL='{self.image_ids[ci]}'. Delete cache and re-extract."
                )

        # Stats
        all_targets = torch.stack(self.targets)
        pos_per_sample = all_targets.sum(dim=1)
        pos_per_class = all_targets.sum(dim=0)
        print(f"  Samples: {len(self.targets):,}")
        print(f"  Vocab size: {vocab.size}")
        print(f"  Avg labels per sample: {pos_per_sample.mean():.1f}")
        print(f"  Classes with >0 samples: {(pos_per_class > 0).sum().item()}")

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        embedding = torch.from_numpy(self.embeddings[idx].astype(np.float32))
        target = self.targets[idx]
        return embedding, target

    def close(self):
        """Close the HDF5 file."""
        if hasattr(self, "hf") and self.hf:
            self.hf.close()

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# Repeat Factor Sampler (RFS)
# ---------------------------------------------------------------------------


class RepeatFactorSampler(Sampler):
    """Repeat Factor Sampling for long-tail multi-label classification.

    From: Gupta et al., "LVIS: A Dataset for Large Vocabulary Instance
    Segmentation", CVPR 2019.

    Each image is assigned a repeat factor based on the frequency of its
    rarest label.  Images containing rare labels are oversampled so that
    every class is seen roughly ``threshold`` times per epoch.

    Args:
        dataset: a NodeDataset whose ``.targets`` are multi-hot tensors
        vocab: NodeVocabulary (provides ``label_counts``)
        threshold: target frequency (``t`` in the paper).
            Labels with frequency < threshold get oversampled.
            A good default is the *median* class frequency.
        seed: random seed for shuffling within each epoch
    """

    def __init__(
        self,
        dataset: NodeDataset,
        vocab: NodeVocabulary,
        threshold: float | None = None,
        seed: int = 42,
    ):
        super().__init__()
        self.dataset = dataset
        self.seed = seed
        self.epoch = 0

        # ── 1. Per-class image frequency (fraction of images containing class) ──
        n = len(dataset)
        targets = torch.stack(dataset.targets)            # [N, V]
        class_image_count = targets.sum(dim=0).float()    # [V]
        class_freq = class_image_count / n                # [V]

        # Default threshold: median class frequency
        if threshold is None:
            nonzero = class_freq[class_freq > 0]
            threshold = float(nonzero.median()) if len(nonzero) > 0 else 1.0

        # ── 2. Per-class repeat factor: r_c = max(1, sqrt(t / f_c)) ───────────
        class_rf = torch.ones(vocab.size)
        for c in range(vocab.size):
            fc = class_freq[c].item()
            if fc > 0 and fc < threshold:
                class_rf[c] = max(1.0, (threshold / fc) ** 0.5)

        # ── 3. Per-image repeat factor: r_i = max over its labels ─────────────
        #   For each image, take the maximum class repeat factor among its
        #   positive labels.  Split into integer + fractional part.
        image_rf = torch.ones(n)
        for i in range(n):
            pos = targets[i].nonzero(as_tuple=True)[0]
            if len(pos) > 0:
                image_rf[i] = class_rf[pos].max().item()

        self._int_part = image_rf.long()                  # floor
        self._frac_part = image_rf - self._int_part.float()

        # ── Stats ──────────────────────────────────────────────────────────────
        total_after = int(self._int_part.sum()) + int((self._frac_part > 0).sum())
        max_rf = image_rf.max().item()
        n_oversampled = int((image_rf > 1).sum())

        print(f"  RepeatFactorSampler:")
        print(f"    threshold (t)      : {threshold:.6f}")
        print(f"    images oversampled : {n_oversampled:,} / {n:,} "
              f"({n_oversampled / n * 100:.1f}%)")
        print(f"    max repeat factor  : {max_rf:.2f}")
        print(f"    effective epoch size: ~{total_after:,} (was {n:,}, "
              f"{total_after / n:.2f}x)")

    def _get_indices(self, generator: torch.Generator) -> list[int]:
        """Build the repeated index list for one epoch."""
        indices = []
        for i in range(len(self.dataset)):
            # Integer part: always include this many copies
            indices.extend([i] * int(self._int_part[i]))
            # Fractional part: include one extra copy with probability = frac
            if torch.rand(1, generator=generator).item() < self._frac_part[i]:
                indices.append(i)
        return indices

    def __iter__(self):
        g = torch.Generator()
        g.manual_seed(self.seed + self.epoch)
        indices = self._get_indices(g)
        # Shuffle
        rand_perm = torch.randperm(len(indices), generator=g).tolist()
        return iter([indices[j] for j in rand_perm])

    def __len__(self):
        """Expected length (integer parts + expected fractional draws)."""
        return int(self._int_part.sum()) + int((self._frac_part > 0).sum())

    def set_epoch(self, epoch: int):
        """Set the epoch (changes the random seed for shuffling)."""
        self.epoch = epoch
