"""Utility functions for the node extractor: loss, metrics, label normalization, training helpers."""

import math
import re
from collections import defaultdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score


# ---------------------------------------------------------------------------
# Label Normalization
# ---------------------------------------------------------------------------

# Hand-curated synonym map: maps variants to a canonical form.
# Extend as needed after inspecting the vocabulary.
_SYNONYM_MAP = {
    "trees": "tree", "leaves": "leaf", "bushes": "bush",
    "flowers": "flower", "rocks": "rock", "clouds": "cloud",
    "mountains": "mountain", "buildings": "building", "cars": "car",
    "buses": "bus", "trucks": "truck", "boats": "boat",
    "planes": "plane", "airplane": "plane", "airplanes": "plane",
    "people": "person", "persons": "person", "men": "man",
    "women": "woman", "children": "child", "kids": "child",
    "boys": "boy", "girls": "girl",
    "dogs": "dog", "cats": "cat", "horses": "horse",
    "birds": "bird", "elephants": "elephant", "cows": "cow",
    "sheep": "sheep", "zebras": "zebra", "giraffes": "giraffe",
    "chairs": "chair", "tables": "table", "couches": "couch",
    "beds": "bed", "benches": "bench", "shelves": "shelf",
    "bottles": "bottle", "cups": "cup", "glasses": "glass",
    "plates": "plate", "bowls": "bowl", "forks": "fork",
    "knives": "knife", "spoons": "spoon",
    "books": "book", "phones": "phone", "laptops": "laptop",
    "windows": "window", "doors": "door", "walls": "wall",
    "signs": "sign", "poles": "pole", "lights": "light",
    "lamps": "lamp", "tiles": "tile", "wheels": "wheel",
    "legs": "leg", "arms": "arm", "hands": "hand", "feet": "foot",
    "eyes": "eye", "ears": "ear",
    "pants": "pants", "jeans": "jeans", "shorts": "shorts",
    "shoes": "shoe", "boots": "boot", "sneakers": "sneaker",
    "letters": "letter", "numbers": "number", "words": "word",
    "stripes": "stripe", "spots": "spot", "lines": "line",
    "automobile": "car", "vehicle": "car", "sedan": "car",
    "sofa": "couch", "settee": "couch",
    "tv": "television", "monitor": "television",
    "cellphone": "phone", "cell phone": "phone", "mobile phone": "phone",
    "bike": "bicycle", "motorbike": "motorcycle",
}


def normalize_label(label: str) -> str:
    """Normalize a node label: lowercase, strip, apply synonym map."""
    label = label.lower().strip()
    # Remove trailing/leading articles and whitespace
    label = re.sub(r"\s+", " ", label)
    return _SYNONYM_MAP.get(label, label)


# ---------------------------------------------------------------------------
# Asymmetric Loss (ASL)
# ---------------------------------------------------------------------------


class AsymmetricLoss(nn.Module):
    """Asymmetric Loss for multi-label classification.

    From: Ridnik et al., "Asymmetric Loss For Multi-Label Classification", 2021.

    Args:
        gamma_neg: focusing parameter for negative samples (default 4)
        gamma_pos: focusing parameter for positive samples (default 1)
        clip: probability margin for negative clipping (default 0.05)
        label_smoothing: smooth targets toward 0.5 (default 0.0)
        eps: numerical stability constant
    """

    def __init__(self, gamma_neg=4, gamma_pos=1, clip=0.05,
                 label_smoothing=0.0, eps=1e-8):
        super().__init__()
        self.gamma_neg = gamma_neg
        self.gamma_pos = gamma_pos
        self.clip = clip
        self.label_smoothing = label_smoothing
        self.eps = eps

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: raw logits [B, V] (before sigmoid)
            targets: binary targets [B, V]
        Returns:
            scalar loss
        """
        # Apply label smoothing
        if self.label_smoothing > 0:
            targets = targets * (1 - self.label_smoothing) + (1 - targets) * self.label_smoothing

        # Sigmoid probabilities
        p = torch.sigmoid(logits)
        p_pos = p
        p_neg = 1 - p

        # Asymmetric clipping for negatives
        if self.clip > 0:
            p_neg = (p_neg + self.clip).clamp(max=1.0)

        # Basic cross-entropy components
        loss_pos = targets * torch.log(p_pos.clamp(min=self.eps))
        loss_neg = (1 - targets) * torch.log(p_neg.clamp(min=self.eps))

        # Asymmetric focusing
        if self.gamma_pos > 0:
            loss_pos = loss_pos * ((1 - p_pos) ** self.gamma_pos)
        if self.gamma_neg > 0:
            loss_neg = loss_neg * (p.detach() ** self.gamma_neg)

        loss = -(loss_pos + loss_neg)
        return loss.mean()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(logits: torch.Tensor, targets: torch.Tensor,
                    threshold: float = 0.5) -> dict:
    """Compute multi-label classification metrics.

    Args:
        logits: raw logits [N, V] (before sigmoid)
        targets: binary targets [N, V]
        threshold: decision threshold for binary predictions

    Returns:
        dict with mAP, micro/macro F1, precision, recall
    """
    with torch.no_grad():
        probs = torch.sigmoid(logits).cpu().numpy()
        targets_np = targets.cpu().numpy()
        preds = (probs >= threshold).astype(np.float32)

    metrics = {}

    # Mean Average Precision (the primary multi-label metric)
    # Only compute AP for classes that have at least one positive sample
    has_pos = targets_np.sum(axis=0) > 0
    if has_pos.any():
        metrics["mAP"] = float(average_precision_score(
            targets_np[:, has_pos], probs[:, has_pos], average="micro"
        ))
        per_class_ap = average_precision_score(
            targets_np[:, has_pos], probs[:, has_pos], average=None
        )
        metrics["macro_mAP"] = float(np.mean(per_class_ap))
    else:
        metrics["mAP"] = 0.0
        metrics["macro_mAP"] = 0.0

    # F1, Precision, Recall
    metrics["micro_f1"] = float(f1_score(targets_np, preds, average="micro", zero_division=0))
    metrics["macro_f1"] = float(f1_score(targets_np, preds, average="macro", zero_division=0))
    metrics["micro_precision"] = float(precision_score(targets_np, preds, average="micro", zero_division=0))
    metrics["micro_recall"] = float(recall_score(targets_np, preds, average="micro", zero_division=0))

    # Per-sample stats
    preds_per_sample = preds.sum(axis=1)
    metrics["avg_preds_per_sample"] = float(preds_per_sample.mean())

    return metrics


# ---------------------------------------------------------------------------
# Learning Rate Scheduler: Cosine with Linear Warmup
# ---------------------------------------------------------------------------


class CosineWarmupScheduler(torch.optim.lr_scheduler._LRScheduler):
    """Linear warmup followed by cosine decay."""

    def __init__(self, optimizer, warmup_steps, total_steps, min_lr=1e-7, last_epoch=-1):
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr
        super().__init__(optimizer, last_epoch)

    def get_lr(self):
        step = self.last_epoch
        if step < self.warmup_steps:
            # Linear warmup
            scale = step / max(1, self.warmup_steps)
        else:
            # Cosine decay
            progress = (step - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
            scale = 0.5 * (1.0 + math.cos(math.pi * progress))

        return [
            max(self.min_lr, base_lr * scale)
            for base_lr in self.base_lrs
        ]


# ---------------------------------------------------------------------------
# Early Stopping
# ---------------------------------------------------------------------------


class EarlyStopping:
    """Stop training when a monitored metric stops improving."""

    def __init__(self, patience=10, mode="max", min_delta=1e-4):
        self.patience = patience
        self.mode = mode
        self.min_delta = min_delta
        self.best = None
        self.counter = 0
        self.best_epoch = 0

    def __call__(self, metric, epoch):
        if self.best is None:
            self.best = metric
            self.best_epoch = epoch
            return False

        if self.mode == "max":
            improved = metric > self.best + self.min_delta
        else:
            improved = metric < self.best - self.min_delta

        if improved:
            self.best = metric
            self.best_epoch = epoch
            self.counter = 0
            return False
        else:
            self.counter += 1
            return self.counter >= self.patience
