#!/usr/bin/env python3
"""PyTorch training script for the Transformer AI detector.

Run locally or on Google Colab (free GPU) for full transformer training.
Exports weights in numpy format compatible with TextHumanize inference.

Usage (local)::

    pip install torch numpy
    python scripts/train_v2_pytorch.py --data data/training_data.jsonl --epochs 50

Usage (Colab)::

    !pip install torch numpy
    !git clone https://github.com/ksanyok/TextHumanize.git
    %cd TextHumanize
    !python scripts/train_v2_pytorch.py --data data/training_data.jsonl --epochs 50

Architecture: Mini-Transformer (1.5M params by default)
    CharTokenizer(256) → Embedding(256→192) + SinPE
    → 3×TransformerBlock(192d, 6 heads, 768 FFN)
    → AttentionPool → 192d
    → Concat(192d + 35 features = 227d)
    → MLP(227→384→192→1) → sigmoid

Training:
    - AdamW optimizer
    - Cosine LR schedule with warmup
    - BCE loss
    - Gradient clipping
    - Early stopping on validation F1
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
import zlib
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("PyTorch is required. Install: pip install torch")
    sys.exit(1)

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class Config:
    vocab_size = 256
    max_seq_len = 1024
    d_model = 192
    n_heads = 6
    n_layers = 3
    d_ff = 768
    n_features = 35
    mlp_hidden = [384, 192]
    dropout = 0.1
    # Training
    batch_size = 32
    epochs = 50
    lr = 3e-4
    weight_decay = 0.01
    warmup_steps = 500
    grad_clip = 1.0
    patience = 10


# ---------------------------------------------------------------------------
# Feature extraction (reuse from texthumanize)
# ---------------------------------------------------------------------------

def extract_features_safe(text: str, lang: str = "en") -> list[float]:
    """Extract 35 features, return zeros on failure."""
    try:
        from texthumanize.neural_detector import extract_features, normalize_features
        raw = extract_features(text, lang)
        return normalize_features(raw, lang=lang)
    except Exception:
        return [0.0] * 35


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class TextDetectorDataset(Dataset):
    """Dataset for AI text detection."""

    def __init__(self, data_path: str, max_samples: int = 0, max_len: int = 1024):
        self.texts: list[str] = []
        self.labels: list[float] = []
        self.langs: list[str] = []
        self.features: list[list[float]] = []
        self.max_len = max_len

        logger.info("Loading data from %s ...", data_path)
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "text" not in obj:
                    continue
                self.texts.append(obj["text"])
                self.labels.append(float(obj.get("label", 0.5)))
                self.langs.append(obj.get("lang", "en"))
                if max_samples > 0 and len(self.texts) >= max_samples:
                    break

        logger.info("Loaded %d samples. Extracting features...", len(self.texts))
        for i, (text, lang) in enumerate(zip(self.texts, self.langs)):
            feat = extract_features_safe(text, lang)
            self.features.append(feat)
            if (i + 1) % 500 == 0:
                logger.info("  Features: %d/%d", i + 1, len(self.texts))

        logger.info("Feature extraction complete.")

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        text = self.texts[idx]
        # Tokenize: char ordinals clipped to 255
        tokens = [min(ord(c), 255) for c in text[:self.max_len]]
        return {
            "tokens": torch.tensor(tokens, dtype=torch.long),
            "features": torch.tensor(self.features[idx], dtype=torch.float32),
            "label": torch.tensor(self.labels[idx], dtype=torch.float32),
        }


def collate_fn(batch: list[dict]) -> dict[str, torch.Tensor]:
    """Pad token sequences to same length."""
    max_len = max(len(b["tokens"]) for b in batch)
    tokens = torch.zeros(len(batch), max_len, dtype=torch.long)
    mask = torch.zeros(len(batch), max_len, dtype=torch.bool)
    features = torch.stack([b["features"] for b in batch])
    labels = torch.stack([b["label"] for b in batch])

    for i, b in enumerate(batch):
        l = len(b["tokens"])
        tokens[i, :l] = b["tokens"]
        mask[i, :l] = True

    return {
        "tokens": tokens,
        "mask": mask,
        "features": features,
        "labels": labels,
    }


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TransformerDetector(nn.Module):
    """Mini-Transformer for AI text detection."""

    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg

        # Embedding
        self.embed = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos_embed = nn.Parameter(
            self._sinusoidal_pe(cfg.max_seq_len, cfg.d_model), requires_grad=False,
        )

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_ff,
            dropout=cfg.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=cfg.n_layers)

        # Attention pool
        self.attn_pool = nn.Linear(cfg.d_model, 1)
        self.final_norm = nn.LayerNorm(cfg.d_model)

        # Classifier MLP
        layers = []
        prev = cfg.d_model + cfg.n_features
        for h in cfg.mlp_hidden:
            layers.extend([nn.Linear(prev, h), nn.ReLU(), nn.Dropout(cfg.dropout)])
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.classifier = nn.Sequential(*layers)

        # Init
        self.apply(self._init_weights)

    @staticmethod
    def _sinusoidal_pe(max_len: int, d_model: int) -> torch.Tensor:
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(max_len, dtype=torch.float).unsqueeze(1)
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div[:d_model // 2 + d_model % 2])
        return pe

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, std=0.02)

    def forward(
        self,
        tokens: torch.Tensor,
        mask: torch.Tensor,
        features: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            tokens: (batch, seq_len) int64
            mask: (batch, seq_len) bool — True for real tokens
            features: (batch, 35) float32
        Returns:
            logits: (batch,) float32
        """
        B, L = tokens.shape

        # Embedding + PE
        x = self.embed(tokens)  # (B, L, d)
        x = x + self.pos_embed[:L].unsqueeze(0)

        # Transformer (need src_key_padding_mask for padded tokens)
        padding_mask = ~mask  # True for padding
        x = self.encoder(x, src_key_padding_mask=padding_mask)

        # Attention pooling
        attn_scores = self.attn_pool(x).squeeze(-1)  # (B, L)
        attn_scores = attn_scores.masked_fill(~mask, float("-inf"))
        attn_weights = torch.softmax(attn_scores, dim=-1)  # (B, L)
        pooled = (attn_weights.unsqueeze(-1) * x).sum(dim=1)  # (B, d)

        pooled = self.final_norm(pooled)

        # Concat with features and classify
        combined = torch.cat([pooled, features], dim=-1)  # (B, d+35)
        logits = self.classifier(combined).squeeze(-1)  # (B,)

        return logits

    @property
    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters())


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_epoch(
    model: TransformerDetector,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    device: torch.device,
    grad_clip: float,
) -> float:
    model.train()
    total_loss = 0.0
    n_batches = 0

    for batch in loader:
        tokens = batch["tokens"].to(device)
        mask = batch["mask"].to(device)
        features = batch["features"].to(device)
        labels = batch["labels"].to(device)

        logits = model(tokens, mask, features)
        loss = F.binary_cross_entropy_with_logits(logits, labels)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def evaluate(
    model: TransformerDetector,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    tp = fp = tn = fn = 0
    total_loss = 0.0
    n_batches = 0

    for batch in loader:
        tokens = batch["tokens"].to(device)
        mask = batch["mask"].to(device)
        features = batch["features"].to(device)
        labels = batch["labels"].to(device)

        logits = model(tokens, mask, features)
        loss = F.binary_cross_entropy_with_logits(logits, labels)
        total_loss += loss.item()
        n_batches += 1

        probs = torch.sigmoid(logits)
        preds = (probs >= 0.5).long()
        actuals = (labels >= 0.5).long()

        tp += ((preds == 1) & (actuals == 1)).sum().item()
        fp += ((preds == 1) & (actuals == 0)).sum().item()
        tn += ((preds == 0) & (actuals == 0)).sum().item()
        fn += ((preds == 0) & (actuals == 1)).sum().item()

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    return {
        "loss": total_loss / max(n_batches, 1),
        "accuracy": (tp + tn) / max(tp + fp + tn + fn, 1),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# ---------------------------------------------------------------------------
# Weight export (PyTorch → numpy format)
# ---------------------------------------------------------------------------


def export_weights(model: TransformerDetector, cfg: Config, path: str) -> int:
    """Export model weights to numpy-compatible compressed format.

    The exported file can be loaded by texthumanize.transformer_detector.load_weights().
    """
    state = model.state_dict()

    def _t2l(key: str) -> list:
        return state[key].cpu().float().numpy().tolist()

    data: dict[str, Any] = {
        "config": {
            "vocab_size": cfg.vocab_size,
            "max_seq_len": cfg.max_seq_len,
            "d_model": cfg.d_model,
            "n_heads": cfg.n_heads,
            "n_layers": cfg.n_layers,
            "d_ff": cfg.d_ff,
            "n_handcrafted": cfg.n_features,
            "mlp_hidden": cfg.mlp_hidden,
        },
        "embed": _t2l("embed.weight"),
        "layers": [],
        "attn_pool_w": _t2l("attn_pool.weight")[0],  # (1, d) → (d,)
        "final_ln_g": _t2l("final_norm.weight"),
        "final_ln_b": _t2l("final_norm.bias"),
    }

    # Extract transformer layers
    for i in range(cfg.n_layers):
        prefix = f"encoder.layers.{i}"
        layer = {
            "attn_wq": _t2l(f"{prefix}.self_attn.in_proj_weight")[:cfg.d_model],
            "attn_wk": _t2l(f"{prefix}.self_attn.in_proj_weight")[cfg.d_model:2*cfg.d_model],
            "attn_wv": _t2l(f"{prefix}.self_attn.in_proj_weight")[2*cfg.d_model:],
            "attn_wo": _t2l(f"{prefix}.self_attn.out_proj.weight"),
            "attn_bq": _t2l(f"{prefix}.self_attn.in_proj_bias")[:cfg.d_model],
            "attn_bk": _t2l(f"{prefix}.self_attn.in_proj_bias")[cfg.d_model:2*cfg.d_model],
            "attn_bv": _t2l(f"{prefix}.self_attn.in_proj_bias")[2*cfg.d_model:],
            "attn_bo": _t2l(f"{prefix}.self_attn.out_proj.bias"),
            "ln1_g": _t2l(f"{prefix}.norm1.weight"),
            "ln1_b": _t2l(f"{prefix}.norm1.bias"),
            "ff_w1": _t2l(f"{prefix}.linear1.weight"),
            "ff_b1": _t2l(f"{prefix}.linear1.bias"),
            "ff_w2": _t2l(f"{prefix}.linear2.weight"),
            "ff_b2": _t2l(f"{prefix}.linear2.bias"),
            "ln2_g": _t2l(f"{prefix}.norm2.weight"),
            "ln2_b": _t2l(f"{prefix}.norm2.bias"),
        }
        data["layers"].append(layer)

    # Extract MLP classifier
    mlp_weights = []
    mlp_biases = []
    for name, param in model.classifier.named_parameters():
        if "weight" in name:
            mlp_weights.append(param.cpu().float().numpy().tolist())
        elif "bias" in name:
            mlp_biases.append(param.cpu().float().numpy().tolist())

    data["mlp_weights"] = mlp_weights
    data["mlp_biases"] = mlp_biases

    # Compress and save
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    blob = zlib.compress(raw, level=9)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)

    size_mb = len(blob) / 1024 / 1024
    logger.info("Exported weights: %s (%.2f MB)", path, size_mb)
    return len(blob)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Transformer AI detector")
    parser.add_argument("--data", required=True, help="Path to training data (JSONL)")
    parser.add_argument("--val-data", default="", help="Path to validation data (JSONL)")
    parser.add_argument("--output", default="texthumanize/weights/transformer_detector.weights.zb",
                        help="Output weights path")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--d-model", type=int, default=192)
    parser.add_argument("--n-layers", type=int, default=3)
    parser.add_argument("--n-heads", type=int, default=6)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    # Config
    cfg = Config()
    cfg.d_model = args.d_model
    cfg.n_layers = args.n_layers
    cfg.n_heads = args.n_heads
    cfg.epochs = args.epochs
    cfg.batch_size = args.batch_size
    cfg.lr = args.lr

    # Device
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    logger.info("Device: %s", device)

    # Data
    train_ds = TextDetectorDataset(args.data, max_samples=args.max_samples)

    if args.val_data:
        val_ds = TextDetectorDataset(args.val_data)
    else:
        # Split 90/10
        n = len(train_ds)
        n_val = max(int(n * 0.1), 1)
        train_ds, val_ds = torch.utils.data.random_split(  # type: ignore[assignment]
            train_ds, [n - n_val, n_val],
            generator=torch.Generator().manual_seed(42),
        )

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True,
                              collate_fn=collate_fn, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                            collate_fn=collate_fn, num_workers=0)

    logger.info("Train: %d, Val: %d", len(train_ds), len(val_ds))

    # Model
    model = TransformerDetector(cfg).to(device)
    logger.info("Model: %d params (%.2f MB)", model.param_count,
                model.param_count * 4 / 1024 / 1024)

    # Optimizer + Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    total_steps = len(train_loader) * cfg.epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)

    # Training loop
    best_f1 = 0.0
    best_state = None
    patience_counter = 0
    t0 = time.time()

    for epoch in range(cfg.epochs):
        train_loss = train_epoch(model, train_loader, optimizer, scheduler, device, cfg.grad_clip)
        val_metrics = evaluate(model, val_loader, device)

        elapsed = time.time() - t0
        logger.info(
            "Epoch %d/%d — train_loss=%.4f, val_acc=%.4f, val_f1=%.4f, lr=%.6f (%.0fs)",
            epoch + 1, cfg.epochs, train_loss,
            val_metrics["accuracy"], val_metrics["f1"],
            scheduler.get_last_lr()[0], elapsed,
        )

        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= cfg.patience:
                logger.info("Early stopping at epoch %d (best F1=%.4f)", epoch + 1, best_f1)
                break

    # Restore best
    if best_state:
        model.load_state_dict(best_state)

    # Final eval
    final = evaluate(model, val_loader, device)
    logger.info("Final val metrics: %s", final)

    # Export
    export_weights(model, cfg, args.output)
    logger.info("Done! Total time: %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
