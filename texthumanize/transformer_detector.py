"""Transformer-based AI text detector — numpy inference engine.

A mini-transformer encoder that processes raw character sequences and
combines them with 35 handcrafted statistical features for AI text
detection.  Designed for ~1.5M parameters, ~6 MB weights, and fast
CPU inference using numpy.

Architecture
------------
CharTokenizer (256 vocab)
    → Embedding (256 → d_model) + Sinusoidal PE
    → N × TransformerEncoderBlock (pre-norm, GELU FFN)
    → Attention-pooled CLS vector (d_model)
    → Concat with 35 handcrafted features → (d_model + 35)
    → MLP classifier → sigmoid → P(AI)

Configs shipped
~~~~~~~~~~~~~~~
- ``TransformerConfig.small``   — ~370 K params, ~1.5 MB
- ``TransformerConfig.medium``  — ~1.5 M params, ~6 MB  (default)
- ``TransformerConfig.large``   — ~4.8 M params, ~19 MB

Training is done externally (see ``scripts/train_v2_pytorch.py``)
and weights are loaded for inference only.
"""

from __future__ import annotations

import json
import logging
import os
import zlib
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from texthumanize.np_ops import (
    F32,
    attention_pool,
    embedding_lookup,
    he_init,
    layer_norm,
    mlp_forward,
    ones,
    sigmoid,
    sinusoidal_position_encoding,
    transformer_block,
    xavier_init,
    zeros,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Character tokenizer  (256 code-points → index)
# ---------------------------------------------------------------------------

_MAX_CHAR = 256

def char_tokenize(text: str, max_len: int = 1024) -> np.ndarray:
    """Convert text to integer token array (char ordinals, clipped to 255)."""
    codes = [min(ord(c), _MAX_CHAR - 1) for c in text[:max_len]]
    return np.array(codes, dtype=np.int64)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class TransformerConfig:
    """Configuration for the transformer detector."""

    vocab_size: int = _MAX_CHAR
    max_seq_len: int = 1024
    d_model: int = 192
    n_heads: int = 6
    n_layers: int = 3
    d_ff: int = 768
    n_handcrafted: int = 35
    mlp_hidden: list[int] = field(default_factory=lambda: [384, 192])
    dropout: float = 0.0  # inference-only → 0

    @classmethod
    def small(cls) -> TransformerConfig:
        """~370K params, ~1.5 MB."""
        return cls(d_model=128, n_heads=4, n_layers=2, d_ff=512,
                   mlp_hidden=[256, 128])

    @classmethod
    def medium(cls) -> TransformerConfig:
        """~1.5M params, ~6 MB (default)."""
        return cls()

    @classmethod
    def large(cls) -> TransformerConfig:
        """~4.8M params, ~19 MB."""
        return cls(d_model=256, n_heads=8, n_layers=4, d_ff=1024,
                   mlp_hidden=[512, 256])

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    def param_count(self) -> int:
        """Estimated total parameter count."""
        d = self.d_model
        ff = self.d_ff
        V = self.vocab_size
        L = self.n_layers
        # Embedding
        p = V * d
        # Per transformer layer: 4 attention projs + 2LN + FFN + 2LN
        p_per_layer = (
            4 * (d * d + d) +          # Wq, Wk, Wv, Wo + biases
            2 * (2 * d) +              # LN1 gamma+beta
            (d * ff + ff) +            # FFN W1 + b1
            (ff * d + d) +             # FFN W2 + b2
            2 * (2 * d)               # LN2 gamma+beta
        )
        p += L * p_per_layer
        # Attention pool
        p += d
        # Final LN
        p += 2 * d
        # MLP classifier
        prev = d + self.n_handcrafted
        for h in self.mlp_hidden:
            p += prev * h + h
            prev = h
        p += prev * 1 + 1  # output
        return p


# ---------------------------------------------------------------------------
# Model weights container
# ---------------------------------------------------------------------------


@dataclass
class TransformerWeights:
    """All weights for the transformer detector model."""

    # Embedding (vocab_size, d_model)
    embed: F32 = None  # type: ignore[assignment]

    # Per-layer weights  (lists of length n_layers)
    attn_wq: list[F32] = field(default_factory=list)
    attn_wk: list[F32] = field(default_factory=list)
    attn_wv: list[F32] = field(default_factory=list)
    attn_wo: list[F32] = field(default_factory=list)
    attn_bq: list[F32] = field(default_factory=list)
    attn_bk: list[F32] = field(default_factory=list)
    attn_bv: list[F32] = field(default_factory=list)
    attn_bo: list[F32] = field(default_factory=list)
    ln1_g: list[F32] = field(default_factory=list)
    ln1_b: list[F32] = field(default_factory=list)
    ff_w1: list[F32] = field(default_factory=list)
    ff_b1: list[F32] = field(default_factory=list)
    ff_w2: list[F32] = field(default_factory=list)
    ff_b2: list[F32] = field(default_factory=list)
    ln2_g: list[F32] = field(default_factory=list)
    ln2_b: list[F32] = field(default_factory=list)

    # Attention pool
    attn_pool_w: F32 = None  # type: ignore[assignment]

    # Final layer norm
    final_ln_g: F32 = None  # type: ignore[assignment]
    final_ln_b: F32 = None  # type: ignore[assignment]

    # MLP classifier
    mlp_weights: list[F32] = field(default_factory=list)
    mlp_biases: list[F32] = field(default_factory=list)

    def total_params(self) -> int:
        """Count total number of parameters."""
        total = 0
        for name in dir(self):
            val = getattr(self, name)
            if isinstance(val, np.ndarray):
                total += val.size
            elif isinstance(val, list) and val and isinstance(val[0], np.ndarray):
                total += sum(a.size for a in val)
        return total


# ---------------------------------------------------------------------------
# Weight initialization
# ---------------------------------------------------------------------------


def init_weights(cfg: TransformerConfig, seed: int = 42) -> TransformerWeights:
    """Initialize transformer weights with Xavier/He initialization."""
    rng = np.random.default_rng(seed)
    w = TransformerWeights()
    d = cfg.d_model
    ff = cfg.d_ff

    # Embedding
    w.embed = rng.normal(0, 0.02, (cfg.vocab_size, d)).astype(np.float32)

    # Transformer layers
    for _ in range(cfg.n_layers):
        w.attn_wq.append(xavier_init(d, d, rng))
        w.attn_wk.append(xavier_init(d, d, rng))
        w.attn_wv.append(xavier_init(d, d, rng))
        w.attn_wo.append(xavier_init(d, d, rng))
        w.attn_bq.append(zeros(d))
        w.attn_bk.append(zeros(d))
        w.attn_bv.append(zeros(d))
        w.attn_bo.append(zeros(d))
        w.ln1_g.append(ones(d))
        w.ln1_b.append(zeros(d))
        w.ff_w1.append(he_init(d, ff, rng))
        w.ff_b1.append(zeros(ff))
        w.ff_w2.append(xavier_init(ff, d, rng))
        w.ff_b2.append(zeros(d))
        w.ln2_g.append(ones(d))
        w.ln2_b.append(zeros(d))

    # Attention pool
    w.attn_pool_w = rng.normal(0, 0.1, (d,)).astype(np.float32)

    # Final LN
    w.final_ln_g = ones(d)
    w.final_ln_b = zeros(d)

    # MLP classifier
    prev = d + cfg.n_handcrafted
    for h in cfg.mlp_hidden:
        w.mlp_weights.append(he_init(prev, h, rng))
        w.mlp_biases.append(zeros(h))
        prev = h
    # Output layer
    w.mlp_weights.append(xavier_init(prev, 1, rng))
    w.mlp_biases.append(zeros(1))

    return w


# ---------------------------------------------------------------------------
# Forward pass
# ---------------------------------------------------------------------------


def forward(
    text: str,
    features: F32,
    weights: TransformerWeights,
    cfg: TransformerConfig,
) -> float:
    """Full forward pass: text + features → AI probability [0, 1].

    Args:
        text: raw input text string
        features: (35,) numpy array of handcrafted features (normalized)
        weights: model weights
        cfg: model configuration
    Returns:
        float: probability that text is AI-generated
    """
    # Tokenize
    tokens = char_tokenize(text, cfg.max_seq_len)
    seq_len = len(tokens)

    if seq_len == 0:
        return 0.5

    # Embedding + positional encoding
    x = embedding_lookup(tokens, weights.embed)  # (seq, d_model)
    pe = sinusoidal_position_encoding(seq_len, cfg.d_model)
    x = x + pe[:seq_len]

    # Transformer blocks
    for i in range(cfg.n_layers):
        x = transformer_block(
            x,
            weights.attn_wq[i], weights.attn_wk[i],
            weights.attn_wv[i], weights.attn_wo[i],
            weights.attn_bq[i], weights.attn_bk[i],
            weights.attn_bv[i], weights.attn_bo[i],
            weights.ln1_g[i], weights.ln1_b[i],
            weights.ff_w1[i], weights.ff_b1[i],
            weights.ff_w2[i], weights.ff_b2[i],
            weights.ln2_g[i], weights.ln2_b[i],
            cfg.n_heads,
        )

    # Final layer norm
    x = layer_norm(x, weights.final_ln_g, weights.final_ln_b)

    # Attention pooling → CLS vector
    cls_vec = attention_pool(x, weights.attn_pool_w)  # (d_model,)

    # Concatenate with handcrafted features
    combined = np.concatenate([cls_vec, features])  # (d_model + 35,)

    # MLP classifier
    n_mlp = len(weights.mlp_weights)
    activations = ["relu"] * (n_mlp - 1) + ["linear"]
    logit = mlp_forward(combined, weights.mlp_weights, weights.mlp_biases, activations)

    # Sigmoid
    prob = float(sigmoid(logit).item())
    return max(0.0, min(1.0, prob))


# ---------------------------------------------------------------------------
# Weight serialization
# ---------------------------------------------------------------------------


def _compress_json(data: Any) -> bytes:
    """JSON → zlib-compress → raw bytes."""
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return zlib.compress(raw, level=9)


def _decompress_json(blob: bytes) -> Any:
    raw = zlib.decompress(blob)
    return json.loads(raw.decode("utf-8"))


def save_weights(weights: TransformerWeights, cfg: TransformerConfig, path: str) -> int:
    """Save weights to a compressed file.  Returns file size in bytes."""
    data: dict[str, Any] = {"config": {
        "vocab_size": cfg.vocab_size,
        "max_seq_len": cfg.max_seq_len,
        "d_model": cfg.d_model,
        "n_heads": cfg.n_heads,
        "n_layers": cfg.n_layers,
        "d_ff": cfg.d_ff,
        "n_handcrafted": cfg.n_handcrafted,
        "mlp_hidden": cfg.mlp_hidden,
    }}

    def _a2l(a: F32) -> list:
        return a.tolist()

    data["embed"] = _a2l(weights.embed)

    data["layers"] = []
    for i in range(cfg.n_layers):
        layer = {
            "attn_wq": _a2l(weights.attn_wq[i]),
            "attn_wk": _a2l(weights.attn_wk[i]),
            "attn_wv": _a2l(weights.attn_wv[i]),
            "attn_wo": _a2l(weights.attn_wo[i]),
            "attn_bq": _a2l(weights.attn_bq[i]),
            "attn_bk": _a2l(weights.attn_bk[i]),
            "attn_bv": _a2l(weights.attn_bv[i]),
            "attn_bo": _a2l(weights.attn_bo[i]),
            "ln1_g": _a2l(weights.ln1_g[i]),
            "ln1_b": _a2l(weights.ln1_b[i]),
            "ff_w1": _a2l(weights.ff_w1[i]),
            "ff_b1": _a2l(weights.ff_b1[i]),
            "ff_w2": _a2l(weights.ff_w2[i]),
            "ff_b2": _a2l(weights.ff_b2[i]),
            "ln2_g": _a2l(weights.ln2_g[i]),
            "ln2_b": _a2l(weights.ln2_b[i]),
        }
        data["layers"].append(layer)

    data["attn_pool_w"] = _a2l(weights.attn_pool_w)
    data["final_ln_g"] = _a2l(weights.final_ln_g)
    data["final_ln_b"] = _a2l(weights.final_ln_b)
    data["mlp_weights"] = [_a2l(w) for w in weights.mlp_weights]
    data["mlp_biases"] = [_a2l(b) for b in weights.mlp_biases]

    blob = _compress_json(data)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)

    logger.info("Saved transformer weights: %s (%d bytes)", path, len(blob))
    return len(blob)


def load_weights(path: str) -> tuple[TransformerWeights, TransformerConfig]:
    """Load weights from compressed file."""
    with open(path, "rb") as f:
        blob = f.read()

    data = _decompress_json(blob)
    c = data["config"]
    cfg = TransformerConfig(
        vocab_size=c["vocab_size"],
        max_seq_len=c["max_seq_len"],
        d_model=c["d_model"],
        n_heads=c["n_heads"],
        n_layers=c["n_layers"],
        d_ff=c["d_ff"],
        n_handcrafted=c["n_handcrafted"],
        mlp_hidden=c["mlp_hidden"],
    )

    def _l2a(lst: list) -> F32:
        return np.array(lst, dtype=np.float32)

    w = TransformerWeights()
    w.embed = _l2a(data["embed"])

    for layer_data in data["layers"]:
        w.attn_wq.append(_l2a(layer_data["attn_wq"]))
        w.attn_wk.append(_l2a(layer_data["attn_wk"]))
        w.attn_wv.append(_l2a(layer_data["attn_wv"]))
        w.attn_wo.append(_l2a(layer_data["attn_wo"]))
        w.attn_bq.append(_l2a(layer_data["attn_bq"]))
        w.attn_bk.append(_l2a(layer_data["attn_bk"]))
        w.attn_bv.append(_l2a(layer_data["attn_bv"]))
        w.attn_bo.append(_l2a(layer_data["attn_bo"]))
        w.ln1_g.append(_l2a(layer_data["ln1_g"]))
        w.ln1_b.append(_l2a(layer_data["ln1_b"]))
        w.ff_w1.append(_l2a(layer_data["ff_w1"]))
        w.ff_b1.append(_l2a(layer_data["ff_b1"]))
        w.ff_w2.append(_l2a(layer_data["ff_w2"]))
        w.ff_b2.append(_l2a(layer_data["ff_b2"]))
        w.ln2_g.append(_l2a(layer_data["ln2_g"]))
        w.ln2_b.append(_l2a(layer_data["ln2_b"]))

    w.attn_pool_w = _l2a(data["attn_pool_w"])
    w.final_ln_g = _l2a(data["final_ln_g"])
    w.final_ln_b = _l2a(data["final_ln_b"])
    w.mlp_weights = [_l2a(m) for m in data["mlp_weights"]]
    w.mlp_biases = [_l2a(b) for b in data["mlp_biases"]]

    logger.info(
        "Loaded transformer weights: %s (config=%s, params=%d)",
        path, f"{cfg.d_model}d/{cfg.n_layers}L/{cfg.n_heads}H", w.total_params(),
    )
    return w, cfg


# ---------------------------------------------------------------------------
# High-level detector class
# ---------------------------------------------------------------------------


class TransformerDetector:
    """Transformer-based AI text detector (numpy inference).

    Uses a mini-transformer encoder over character tokens combined
    with 35 handcrafted statistical features.

    Weights must be trained externally and loaded via ``load()``.
    If no trained weights are available, falls back to the legacy
    MLP detector (``NeuralAIDetector``).
    """

    _WEIGHTS_NAME = "transformer_detector.weights.zb"

    def __init__(
        self,
        config: Optional[TransformerConfig] = None,
        weights_dir: str = "",
    ) -> None:
        if not weights_dir:
            weights_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "weights"
            )
        self._weights_dir = weights_dir
        self._cfg = config or TransformerConfig.medium()
        self._weights: Optional[TransformerWeights] = None
        self._loaded = False

        # Try to load pre-trained weights
        wpath = os.path.join(weights_dir, self._WEIGHTS_NAME)
        if os.path.isfile(wpath):
            try:
                self._weights, self._cfg = load_weights(wpath)
                self._loaded = True
                logger.info("TransformerDetector: loaded trained weights (%d params)",
                            self._weights.total_params())
            except Exception as e:
                logger.warning("TransformerDetector: failed to load weights: %s", e)
        else:
            logger.info(
                "TransformerDetector: no trained weights at %s — "
                "using random init (train first!)", wpath,
            )
            self._weights = init_weights(self._cfg, seed=42)

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def config(self) -> TransformerConfig:
        return self._cfg

    @property
    def param_count(self) -> int:
        return self._weights.total_params() if self._weights else 0

    def detect(self, text: str, features: F32, lang: str = "en") -> dict[str, Any]:
        """Run detection.

        Args:
            text: raw input text
            features: (35,) normalized feature vector (from extract_features + normalize)
            lang: language hint
        Returns:
            dict with score, verdict, confidence
        """
        if self._weights is None:
            return {"score": 0.5, "verdict": "mixed", "confidence": "low",
                    "model": "transformer_v2_uninit"}

        score = forward(text, features, self._weights, self._cfg)

        # Short text dampening
        n_chars = len(text)
        if n_chars < 200:
            score = 0.5 + (score - 0.5) * (n_chars / 200.0)

        # Verdict
        if score < 0.30:
            verdict = "human"
        elif score <= 0.60:
            verdict = "mixed"
        else:
            verdict = "ai"

        # Confidence
        extremity = abs(score - 0.5) * 2.0
        if n_chars >= 400 and extremity > 0.6:
            confidence = "high"
        elif n_chars >= 200 and extremity > 0.3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "score": round(score, 4),
            "verdict": verdict,
            "confidence": confidence,
            "model": f"transformer_v2_{self._cfg.d_model}d{self._cfg.n_layers}L",
            "param_count": self.param_count,
            "trained": self._loaded,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_DETECTOR: Optional[TransformerDetector] = None


def get_transformer_detector() -> TransformerDetector:
    """Get or create the singleton TransformerDetector."""
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = TransformerDetector()
    return _DETECTOR
