"""Training pipeline v2 — numpy-accelerated MLP training + data loading.

Supports training the MLP classifier on real data loaded via data_loader.
For the full transformer, use the PyTorch training script
(scripts/train_v2_pytorch.py).

Usage::

    from texthumanize.training_v2 import TrainerV2
    trainer = TrainerV2()
    trainer.load_data("data/training_data.jsonl")
    results = trainer.train(epochs=100, lr=0.001)
    trainer.export("texthumanize/weights")
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

from texthumanize.data_loader import (
    TextSample,
    balance_dataset,
    dataset_stats,
    load_auto,
    train_val_test_split,
)
from texthumanize.neural_detector import extract_features, normalize_features

logger = logging.getLogger(__name__)

F32 = NDArray[np.float32]


# ---------------------------------------------------------------------------
# AdamW optimizer (numpy)
# ---------------------------------------------------------------------------


class AdamW:
    """AdamW optimizer with numpy arrays."""

    def __init__(
        self,
        lr: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
        weight_decay: float = 0.01,
    ) -> None:
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.weight_decay = weight_decay
        self._m: dict[str, F32] = {}
        self._v: dict[str, F32] = {}
        self._t = 0

    def step(self, name: str, param: F32, grad: F32) -> F32:
        """Update parameter with AdamW."""
        self._t += 1
        if name not in self._m:
            self._m[name] = np.zeros_like(param)
            self._v[name] = np.zeros_like(param)

        m = self._m[name]
        v = self._v[name]

        # Weight decay (applied before momentum)
        if self.weight_decay > 0:
            param = param - self.lr * self.weight_decay * param

        # Adam update
        m[:] = self.beta1 * m + (1 - self.beta1) * grad
        v[:] = self.beta2 * v + (1 - self.beta2) * grad ** 2

        m_hat = m / (1 - self.beta1 ** self._t)
        v_hat = v / (1 - self.beta2 ** self._t)

        param = param - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)
        return param


# ---------------------------------------------------------------------------
# Numpy MLP with backprop
# ---------------------------------------------------------------------------


class NumpyMLP:
    """MLP with numpy arrays and backpropagation support."""

    def __init__(
        self,
        layer_sizes: list[int],
        activations: Optional[list[str]] = None,
        seed: int = 42,
    ) -> None:
        self.layer_sizes = layer_sizes
        rng = np.random.default_rng(seed)

        if activations is None:
            activations = ["relu"] * (len(layer_sizes) - 2) + ["linear"]
        self.activations = activations

        # Initialize weights with He init
        self.weights: list[F32] = []
        self.biases: list[F32] = []
        for i in range(len(layer_sizes) - 1):
            fan_in = layer_sizes[i]
            fan_out = layer_sizes[i + 1]
            std = np.sqrt(2.0 / fan_in).astype(np.float32)
            w = rng.normal(0, std, (fan_out, fan_in)).astype(np.float32)
            b = np.zeros(fan_out, dtype=np.float32)
            self.weights.append(w)
            self.biases.append(b)

    @property
    def param_count(self) -> int:
        return sum(w.size + b.size for w, b in zip(self.weights, self.biases))

    def forward(self, x: F32) -> tuple[F32, list[F32]]:
        """Forward pass, returns (output, cached_activations)."""
        cache = [x.copy()]
        for w, b, act in zip(self.weights, self.biases, self.activations):
            x = x @ w.T + b
            if act == "relu":
                x = np.maximum(x, 0)
            elif act == "sigmoid":
                x = 1.0 / (1.0 + np.exp(-np.clip(x, -88, 88)))
            elif act == "tanh":
                x = np.tanh(x)
            # "linear" — no activation
            cache.append(x.copy())
        return x, cache

    def predict_proba(self, x: F32) -> float:
        """Forward pass → sigmoid probability."""
        out, _ = self.forward(x)
        logit = out[0] if out.ndim > 0 else float(out)
        return float(1.0 / (1.0 + math.exp(-max(-88, min(88, logit)))))

    def backward(
        self,
        target: float,
        prob: float,
        cache: list[F32],
        clip_grad: float = 5.0,
    ) -> list[tuple[F32, F32]]:
        """Backward pass for BCE loss. Returns list of (dW, db) per layer."""
        grads: list[tuple[F32, F32]] = []

        # BCE gradient w.r.t. logit
        delta = np.array([prob - target], dtype=np.float32)

        for i in range(len(self.weights) - 1, -1, -1):
            a_in = cache[i]
            a_out = cache[i + 1]

            # Gradient through activation
            if i < len(self.weights) - 1:
                act = self.activations[i]
                if act == "relu":
                    delta = delta * (a_out > 0).astype(np.float32)
                elif act == "sigmoid":
                    delta = delta * a_out * (1 - a_out)
                elif act == "tanh":
                    delta = delta * (1 - a_out ** 2)

            # Weight gradients
            dw = np.outer(delta, a_in)
            db = delta.copy()

            # Clip
            np.clip(dw, -clip_grad, clip_grad, out=dw)
            np.clip(db, -clip_grad, clip_grad, out=db)

            grads.insert(0, (dw, db))

            # Propagate to previous layer
            if i > 0:
                delta = delta @ self.weights[i]

        return grads

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (for export)."""
        return {
            "layer_sizes": self.layer_sizes,
            "activations": self.activations,
            "weights": [w.tolist() for w in self.weights],
            "biases": [b.tolist() for b in self.biases],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NumpyMLP:
        """Deserialize from dict."""
        mlp = cls(d["layer_sizes"], d["activations"])
        mlp.weights = [np.array(w, dtype=np.float32) for w in d["weights"]]
        mlp.biases = [np.array(b, dtype=np.float32) for b in d["biases"]]
        return mlp

    def to_legacy_config(self) -> dict[str, Any]:
        """Convert to legacy FeedForwardNet config format."""
        layers = []
        for w, b, act in zip(self.weights, self.biases, self.activations):
            layers.append({
                "weights": w.tolist(),
                "bias": b.tolist(),
                "activation": act,
                "layer_norm": False,
            })
        return {"name": "detector", "layers": layers}


# ---------------------------------------------------------------------------
# Feature extraction from samples
# ---------------------------------------------------------------------------


def extract_sample_features(
    samples: list[TextSample],
    max_workers: int = 1,
    show_progress: bool = True,
) -> list[tuple[F32, float]]:
    """Extract features from text samples.

    Returns list of (normalized_feature_vector, label).
    """
    data: list[tuple[F32, float]] = []
    total = len(samples)
    errors = 0

    for i, sample in enumerate(samples):
        if show_progress and (i + 1) % 100 == 0:
            logger.info("  Feature extraction: %d/%d (errors=%d)", i + 1, total, errors)

        try:
            raw = extract_features(sample.text, sample.lang)
            norm = normalize_features(raw, lang=sample.lang)
            features = np.array(norm, dtype=np.float32)
            data.append((features, sample.label))
        except Exception:
            errors += 1
            continue

    logger.info("Extracted features: %d/%d (errors=%d)", len(data), total, errors)
    return data


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def _bce_loss(prob: float, target: float) -> float:
    prob = max(1e-7, min(1 - 1e-7, prob))
    return -(target * math.log(prob) + (1 - target) * math.log(1 - prob))


def evaluate(
    mlp: NumpyMLP,
    data: list[tuple[F32, float]],
    threshold: float = 0.5,
) -> dict[str, float]:
    """Evaluate MLP on data."""
    tp = fp = tn = fn = 0
    total_loss = 0.0

    for features, label in data:
        prob = mlp.predict_proba(features)
        total_loss += _bce_loss(prob, label)
        pred = 1 if prob >= threshold else 0
        actual = 1 if label >= 0.5 else 0
        if pred == 1 and actual == 1:
            tp += 1
        elif pred == 1 and actual == 0:
            fp += 1
        elif pred == 0 and actual == 0:
            tn += 1
        else:
            fn += 1

    n = max(len(data), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    return {
        "accuracy": round((tp + tn) / n, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "loss": round(total_loss / n, 4),
    }


# ---------------------------------------------------------------------------
# TrainerV2
# ---------------------------------------------------------------------------


class TrainerV2:
    """V2 training pipeline with numpy acceleration and real data support.

    Supports:
    - Loading data from JSONL/CSV/HC3 files
    - Feature extraction from raw text
    - Training larger MLP architectures
    - Cross-validation
    - Export to legacy format (compatible with existing detector)

    Usage::

        trainer = TrainerV2()
        trainer.load_data("data/training_data.jsonl")
        result = trainer.train(epochs=100)
        trainer.export("texthumanize/weights")
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._samples: list[TextSample] = []
        self._train_data: list[tuple[F32, float]] = []
        self._val_data: list[tuple[F32, float]] = []
        self._test_data: list[tuple[F32, float]] = []
        self._mlp: Optional[NumpyMLP] = None
        self._training_log: list[dict[str, Any]] = []

    def load_data(
        self,
        *paths: str,
        max_samples_per_file: int = 0,
        balance: bool = True,
    ) -> dict[str, Any]:
        """Load training data from one or more files/directories."""
        all_samples: list[TextSample] = []
        for path in paths:
            samples = load_auto(path, max_samples=max_samples_per_file)
            all_samples.extend(samples)
            logger.info("Loaded %d samples from %s", len(samples), path)

        if balance:
            all_samples = balance_dataset(all_samples, seed=self.seed)

        self._samples = all_samples
        stats = dataset_stats(all_samples)
        logger.info("Total dataset: %s", stats)
        return stats

    def add_legacy_data(self, n_samples: int = 5000) -> int:
        """Add synthetic data from legacy training pipeline."""
        from texthumanize.training import TrainingDataGenerator
        gen = TrainingDataGenerator(seed=self.seed)
        data = gen.generate(n_samples)
        # Convert to samples (we don't have text, only features)
        # These will be added directly to train_data after feature extraction
        return len(data)

    def prepare_features(
        self,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
    ) -> dict[str, int]:
        """Extract features and split into train/val/test."""
        if not self._samples:
            raise ValueError("No data loaded. Call load_data() first.")

        train_samples, val_samples, test_samples = train_val_test_split(
            self._samples, val_ratio=val_ratio, test_ratio=test_ratio, seed=self.seed,
        )

        logger.info("Extracting features for train set...")
        self._train_data = extract_sample_features(train_samples)
        logger.info("Extracting features for val set...")
        self._val_data = extract_sample_features(val_samples)
        logger.info("Extracting features for test set...")
        self._test_data = extract_sample_features(test_samples)

        return {
            "train": len(self._train_data),
            "val": len(self._val_data),
            "test": len(self._test_data),
        }

    def train(
        self,
        layer_sizes: Optional[list[int]] = None,
        epochs: int = 100,
        lr: float = 0.001,
        weight_decay: float = 0.01,
        patience: int = 15,
        clip_grad: float = 5.0,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """Train the MLP detector.

        Args:
            layer_sizes: MLP architecture. Default: [35, 256, 128, 64, 1]
            epochs: max training epochs
            lr: learning rate
            weight_decay: AdamW weight decay
            patience: early stopping patience
            clip_grad: gradient clipping value
            verbose: log progress

        Returns:
            dict with training results
        """
        if not self._train_data:
            raise ValueError("No training data. Call prepare_features() first.")

        if layer_sizes is None:
            layer_sizes = [35, 256, 128, 64, 1]

        activations = ["relu"] * (len(layer_sizes) - 2) + ["linear"]
        self._mlp = NumpyMLP(layer_sizes, activations, seed=self.seed)
        optimizer = AdamW(lr=lr, weight_decay=weight_decay)
        self._training_log = []

        best_val_f1 = 0.0
        best_weights: Optional[dict[str, Any]] = None
        patience_counter = 0

        logger.info(
            "Training MLP: %s (%d params), %d train, %d val",
            layer_sizes, self._mlp.param_count,
            len(self._train_data), len(self._val_data),
        )

        t0 = time.time()

        for epoch in range(epochs):
            # Shuffle training data
            rng = random.Random(self.seed + epoch)
            train_data = list(self._train_data)
            rng.shuffle(train_data)

            # Training epoch
            epoch_loss = 0.0
            for features, label in train_data:
                prob, cache = self._mlp.forward(features)
                prob_f = float(1.0 / (1.0 + math.exp(-max(-88, min(88, float(prob[0]))))))
                epoch_loss += _bce_loss(prob_f, label)

                grads = self._mlp.backward(label, prob_f, cache, clip_grad)
                for i, (dw, db) in enumerate(grads):
                    self._mlp.weights[i] = optimizer.step(
                        f"w{i}", self._mlp.weights[i], dw,
                    )
                    self._mlp.biases[i] = optimizer.step(
                        f"b{i}", self._mlp.biases[i], db,
                    )

            avg_loss = epoch_loss / max(len(train_data), 1)

            # Validation
            val_metrics = evaluate(self._mlp, self._val_data)

            log_entry = {
                "epoch": epoch + 1,
                "train_loss": round(avg_loss, 4),
                **val_metrics,
            }
            self._training_log.append(log_entry)

            if verbose and (epoch + 1) % 10 == 0:
                elapsed = time.time() - t0
                logger.info(
                    "Epoch %d/%d — loss=%.4f, val_acc=%.4f, val_f1=%.4f (%.1fs)",
                    epoch + 1, epochs, avg_loss,
                    val_metrics["accuracy"], val_metrics["f1"], elapsed,
                )

            # Early stopping
            if val_metrics["f1"] > best_val_f1:
                best_val_f1 = val_metrics["f1"]
                best_weights = self._mlp.to_dict()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info("Early stopping at epoch %d (best F1=%.4f)",
                                epoch + 1, best_val_f1)
                    break

        # Restore best weights
        if best_weights is not None:
            self._mlp = NumpyMLP.from_dict(best_weights)

        # Final evaluation
        result: dict[str, Any] = {
            "epochs_trained": len(self._training_log),
            "best_val_f1": round(best_val_f1, 4),
            "param_count": self._mlp.param_count,
            "architecture": self._mlp.layer_sizes,
            "time_seconds": round(time.time() - t0, 1),
        }

        if self._test_data:
            test_metrics = evaluate(self._mlp, self._test_data)
            result["test_metrics"] = test_metrics
            logger.info("Test metrics: %s", test_metrics)

        result["training_log"] = self._training_log
        return result

    def export(
        self,
        output_dir: str = "texthumanize/weights",
        legacy_format: bool = True,
    ) -> dict[str, str]:
        """Export trained weights.

        If legacy_format=True, also exports in the original FeedForwardNet
        format so the existing NeuralAIDetector can use the improved weights.
        """
        if self._mlp is None:
            raise ValueError("No trained model. Call train() first.")

        os.makedirs(output_dir, exist_ok=True)
        exported: dict[str, str] = {}

        # Save v2 format (JSON)
        v2_path = os.path.join(output_dir, "detector_v2.json")
        with open(v2_path, "w") as f:
            json.dump(self._mlp.to_dict(), f)
        exported["v2"] = v2_path

        # Save legacy format (compressed)
        if legacy_format:
            from texthumanize.neural_engine import compress_weights
            config = self._mlp.to_legacy_config()
            blob = compress_weights(config)
            legacy_path = os.path.join(output_dir, "detector_weights.json.zb85")
            with open(legacy_path, "w") as f:
                f.write(blob)
            exported["legacy"] = legacy_path
            logger.info("Exported legacy weights: %s (%d bytes)", legacy_path, len(blob))

        logger.info("Exported weights to %s: %s", output_dir, list(exported.keys()))
        return exported

    def cross_validate(
        self,
        n_folds: int = 5,
        layer_sizes: Optional[list[int]] = None,
        epochs: int = 50,
        lr: float = 0.001,
    ) -> dict[str, Any]:
        """K-fold cross-validation."""
        if not self._train_data and not self._val_data:
            raise ValueError("No data available.")

        all_data = list(self._train_data) + list(self._val_data)
        rng = random.Random(self.seed)
        rng.shuffle(all_data)

        fold_size = len(all_data) // n_folds
        fold_results: list[dict[str, float]] = []

        for fold in range(n_folds):
            start = fold * fold_size
            end = start + fold_size if fold < n_folds - 1 else len(all_data)
            val_fold = all_data[start:end]
            train_fold = all_data[:start] + all_data[end:]

            self._train_data = train_fold
            self._val_data = val_fold

            result = self.train(
                layer_sizes=layer_sizes,
                epochs=epochs,
                lr=lr,
                verbose=False,
            )
            fold_metrics = evaluate(self._mlp, val_fold)  # type: ignore[arg-type]
            fold_results.append(fold_metrics)
            logger.info("Fold %d/%d: acc=%.4f, f1=%.4f",
                        fold + 1, n_folds, fold_metrics["accuracy"], fold_metrics["f1"])

        # Average
        avg = {}
        for key in fold_results[0]:
            if isinstance(fold_results[0][key], (int, float)):
                vals = [f[key] for f in fold_results]
                avg[f"avg_{key}"] = round(sum(vals) / len(vals), 4)
                avg[f"std_{key}"] = round(
                    (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) ** 0.5, 4
                )

        return {
            "n_folds": n_folds,
            "fold_results": fold_results,
            **avg,
        }
