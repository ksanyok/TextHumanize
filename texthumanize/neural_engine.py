"""Pure-Python neural network engine — zero external dependencies.

Implements feedforward networks, LSTM cells, and word embeddings using
only Python stdlib (math, struct, zlib, base64). Designed for inference
only — weights are pre-trained offline and shipped as compressed data.

This module powers:
- NeuralDetector: AI text detection via 3-layer MLP
- NeuralLM: Character-level language model for perplexity
- WordVec: Lightweight word embeddings for semantic similarity
- HMMTagger: Hidden Markov Model POS tagger with Viterbi decoding
"""

from __future__ import annotations

import base64
import json
import logging
import math
import struct
import zlib
from collections.abc import Sequence
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Low-level vector/matrix ops (pure Python, no numpy)
# ---------------------------------------------------------------------------

Vec = list[float]
Mat = list[list[float]]


def _dot(a: Vec, b: Vec) -> float:
    """Dot product of two vectors."""
    s = 0.0
    for ai, bi in zip(a, b):
        s += ai * bi
    return s


def _matvec(m: Mat, v: Vec) -> Vec:
    """Matrix-vector multiply: m @ v."""
    return [_dot(row, v) for row in m]


def _matadd(a: Mat, b: Mat) -> Mat:
    """Element-wise matrix addition."""
    return [[ai + bi for ai, bi in zip(ar, br)] for ar, br in zip(a, b)]


def _vecadd(a: Vec, b: Vec) -> Vec:
    """Element-wise vector addition."""
    return [ai + bi for ai, bi in zip(a, b)]


def _vecsub(a: Vec, b: Vec) -> Vec:
    """Element-wise vector subtraction."""
    return [ai - bi for ai, bi in zip(a, b)]


def _vecscale(v: Vec, s: float) -> Vec:
    """Scale a vector by scalar."""
    return [vi * s for vi in v]


def _vecnorm(v: Vec) -> float:
    """L2 norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def _cosine_similarity(a: Vec, b: Vec) -> float:
    """Cosine similarity between two vectors."""
    na = _vecnorm(a)
    nb = _vecnorm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return _dot(a, b) / (na * nb)


def _outer(a: Vec, b: Vec) -> Mat:
    """Outer product: a ⊗ b."""
    return [[ai * bj for bj in b] for ai in a]


def _hadamard(a: Vec, b: Vec) -> Vec:
    """Element-wise multiply."""
    return [ai * bi for ai, bi in zip(a, b)]


# ---------------------------------------------------------------------------
# Activation functions
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def _tanh(x: float) -> float:
    """Hyperbolic tangent."""
    return math.tanh(x)


def _relu(x: float) -> float:
    """Rectified linear unit."""
    return max(0.0, x)


def _gelu(x: float) -> float:
    """Gaussian Error Linear Unit (approximate)."""
    return 0.5 * x * (1.0 + _tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x * x * x)))


def _softmax(v: Vec) -> Vec:
    """Softmax over a vector."""
    m = max(v)
    exps = [math.exp(x - m) for x in v]
    s = sum(exps)
    return [e / s for e in exps]


def _log_softmax(v: Vec) -> Vec:
    """Log-softmax for numerical stability."""
    m = max(v)
    lse = m + math.log(sum(math.exp(x - m) for x in v))
    return [x - lse for x in v]


_ACTIVATIONS: dict[str, Callable[[float], float]] = {
    "sigmoid": _sigmoid,
    "tanh": _tanh,
    "relu": _relu,
    "gelu": _gelu,
    "linear": lambda x: x,
}


def _apply_activation(v: Vec, name: str) -> Vec:
    """Apply activation function element-wise."""
    fn = _ACTIVATIONS[name]
    return [fn(x) for x in v]


# ---------------------------------------------------------------------------
# Layer-norm (simplified, per-vector)
# ---------------------------------------------------------------------------

def _layer_norm(v: Vec, eps: float = 1e-5) -> Vec:
    """Apply layer normalization to a vector."""
    n = len(v)
    mean = sum(v) / n
    var = sum((x - mean) ** 2 for x in v) / n
    std = math.sqrt(var + eps)
    return [(x - mean) / std for x in v]


# ---------------------------------------------------------------------------
# Feedforward Neural Network
# ---------------------------------------------------------------------------

class DenseLayer:
    """A single dense (fully-connected) layer."""

    __slots__ = ("activation", "bias", "use_layer_norm", "weights")

    def __init__(
        self,
        weights: Mat,
        bias: Vec,
        activation: str = "relu",
        use_layer_norm: bool = False,
    ) -> None:
        self.weights = weights
        self.bias = bias
        self.activation = activation
        self.use_layer_norm = use_layer_norm

    def forward(self, x: Vec) -> Vec:
        """Forward pass: W @ x + b, then activation."""
        out = _vecadd(_matvec(self.weights, x), self.bias)
        if self.use_layer_norm:
            out = _layer_norm(out)
        return _apply_activation(out, self.activation)

    @property
    def in_features(self) -> int:
        return len(self.weights[0]) if self.weights else 0

    @property
    def out_features(self) -> int:
        return len(self.weights)


class FeedForwardNet:
    """Multi-layer feedforward neural network.

    Supports arbitrary depth, per-layer activation, dropout (training only),
    and layer normalization.
    """

    __slots__ = ("_name", "layers")

    def __init__(self, layers: list[DenseLayer], name: str = "ffn") -> None:
        self.layers = layers
        self._name = name

    def forward(self, x: Vec) -> Vec:
        """Forward pass through all layers."""
        for layer in self.layers:
            x = layer.forward(x)
        return x

    def predict_proba(self, x: Vec) -> float:
        """Run forward pass and return sigmoid probability (for binary classification)."""
        out = self.forward(x)
        if len(out) == 1:
            return _sigmoid(out[0])
        return _softmax(out)[1]  # probability of class 1

    def predict(self, x: Vec, threshold: float = 0.5) -> int:
        """Run forward pass and return binary prediction."""
        return 1 if self.predict_proba(x) >= threshold else 0

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> FeedForwardNet:
        """Create network from a JSON-serializable config dict.

        Config format:
        {
            "name": "detector",
            "layers": [
                {"weights": [...], "bias": [...], "activation": "relu"},
                ...
            ]
        }
        """
        layers = []
        for lc in config["layers"]:
            layers.append(DenseLayer(
                weights=lc["weights"],
                bias=lc["bias"],
                activation=lc.get("activation", "relu"),
                use_layer_norm=lc.get("layer_norm", False),
            ))
        return cls(layers, name=config.get("name", "ffn"))

    def to_config(self) -> dict[str, Any]:
        """Serialize network to JSON-serializable dict."""
        return {
            "name": self._name,
            "layers": [
                {
                    "weights": layer.weights,
                    "bias": layer.bias,
                    "activation": layer.activation,
                    "layer_norm": layer.use_layer_norm,
                }
                for layer in self.layers
            ],
        }

    @property
    def param_count(self) -> int:
        """Total number of parameters."""
        total = 0
        for layer in self.layers:
            total += len(layer.weights) * len(layer.weights[0]) + len(layer.bias)
        return total


# ---------------------------------------------------------------------------
# LSTM Cell (for language model)
# ---------------------------------------------------------------------------

class LSTMCell:
    """A single LSTM cell for sequential processing.

    Implements: f = σ(Wf·[h,x] + bf)
                i = σ(Wi·[h,x] + bi)
                g = tanh(Wg·[h,x] + bg)
                o = σ(Wo·[h,x] + bo)
                c = f⊙c + i⊙g
                h = o⊙tanh(c)
    """

    __slots__ = (
        "bf",
        "bg",
        "bi",
        "bo",
        "hidden_size",
        "input_size",
        "wf",
        "wg",
        "wi",
        "wo",
    )

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        wf: Mat, bf: Vec,
        wi: Mat, bi: Vec,
        wg: Mat, bg: Vec,
        wo: Mat, bo: Vec,
    ) -> None:
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.wf, self.bf = wf, bf
        self.wi, self.bi = wi, bi
        self.wg, self.bg = wg, bg
        self.wo, self.bo = wo, bo

    def forward(
        self, x: Vec, h_prev: Vec, c_prev: Vec
    ) -> tuple[Vec, Vec]:
        """Single step: returns (h_new, c_new)."""
        combined = h_prev + x  # concatenate [h, x]

        f_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.wf, combined), self.bf)]
        i_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.wi, combined), self.bi)]
        g_gate = [_tanh(v) for v in _vecadd(_matvec(self.wg, combined), self.bg)]
        o_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.wo, combined), self.bo)]

        c_new = _vecadd(_hadamard(f_gate, c_prev), _hadamard(i_gate, g_gate))
        h_new = _hadamard(o_gate, [_tanh(c) for c in c_new])

        return h_new, c_new

    @property
    def param_count(self) -> int:
        combined_size = self.hidden_size + self.input_size
        return 4 * (combined_size * self.hidden_size + self.hidden_size)


# ---------------------------------------------------------------------------
# Weight compression / serialization
# ---------------------------------------------------------------------------

def compress_weights(data: Any) -> str:
    """Compress weights dict to base64 string."""
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return base64.b85encode(compressed).decode("ascii")


def decompress_weights(encoded: str) -> Any:
    """Decompress base64 weights string back to dict."""
    compressed = base64.b85decode(encoded.encode("ascii"))
    raw = zlib.decompress(compressed)
    return json.loads(raw.decode("utf-8"))


def pack_floats(floats: Sequence[float]) -> bytes:
    """Pack a sequence of floats into compact binary format (float16)."""
    return struct.pack(f">{len(floats)}e", *floats)


def unpack_floats(data: bytes, count: int) -> list[float]:
    """Unpack float16 binary data."""
    return list(struct.unpack(f">{count}e", data))


# ---------------------------------------------------------------------------
# Xavier/He initialization (for weight generation)
# ---------------------------------------------------------------------------

def _xavier_init(fan_in: int, fan_out: int, seed: int = 42) -> Mat:
    """Xavier/Glorot uniform initialization."""
    import random
    rng = random.Random(seed)
    limit = math.sqrt(6.0 / (fan_in + fan_out))
    return [[rng.uniform(-limit, limit) for _ in range(fan_in)] for _ in range(fan_out)]


def _he_init(fan_in: int, fan_out: int, seed: int = 42) -> Mat:
    """He initialization for ReLU networks."""
    import random
    rng = random.Random(seed)
    std = math.sqrt(2.0 / fan_in)
    return [[rng.gauss(0, std) for _ in range(fan_in)] for _ in range(fan_out)]


def _zeros(n: int) -> Vec:
    """Zero vector."""
    return [0.0] * n


def build_mlp(
    layer_sizes: list[int],
    activations: Optional[list[str]] = None,
    seed: int = 42,
) -> FeedForwardNet:
    """Build an MLP with He initialization.

    Args:
        layer_sizes: [input, hidden1, hidden2, ..., output]
        activations: per-layer activation (default: relu for hidden, linear for output)
        seed: random seed
    """
    if activations is None:
        activations = ["relu"] * (len(layer_sizes) - 2) + ["linear"]

    layers = []
    for i in range(len(layer_sizes) - 1):
        fan_in = layer_sizes[i]
        fan_out = layer_sizes[i + 1]
        act = activations[i] if i < len(activations) else "linear"
        w = _he_init(fan_in, fan_out, seed=seed + i)
        b = _zeros(fan_out)
        layers.append(DenseLayer(w, b, activation=act))

    return FeedForwardNet(layers, name="mlp")


# ---------------------------------------------------------------------------
# Embedding table
# ---------------------------------------------------------------------------

class EmbeddingTable:
    """Lookup table for word/character embeddings."""

    __slots__ = ("_index", "dim", "vectors", "vocab")

    def __init__(self, vocab: list[str], vectors: Mat) -> None:
        self.vocab = vocab
        self.vectors = vectors
        self.dim = len(vectors[0]) if vectors else 0
        self._index: dict[str, int] = {w: i for i, w in enumerate(vocab)}

    def __getitem__(self, word: str) -> Optional[Vec]:
        idx = self._index.get(word)
        if idx is not None:
            return self.vectors[idx]
        return None

    def get(self, word: str, default: Optional[Vec] = None) -> Optional[Vec]:
        v = self[word]
        return v if v is not None else default

    def sentence_vector(self, words: list[str]) -> Vec:
        """Average word vectors for a sentence (skip unknown words)."""
        vecs = [self.vectors[self._index[w]] for w in words if w in self._index]
        if not vecs:
            return [0.0] * self.dim
        n = len(vecs)
        return [sum(v[d] for v in vecs) / n for d in range(self.dim)]

    def similarity(self, a: str, b: str) -> float:
        """Cosine similarity between two words."""
        va = self[a]
        vb = self[b]
        if va is None or vb is None:
            return 0.0
        return _cosine_similarity(va, vb)

    def sentence_similarity(self, words_a: list[str], words_b: list[str]) -> float:
        """Cosine similarity between average sentence vectors."""
        va = self.sentence_vector(words_a)
        vb = self.sentence_vector(words_b)
        return _cosine_similarity(va, vb)

    @property
    def size(self) -> int:
        return len(self.vocab)


# ---------------------------------------------------------------------------
# HMM with Viterbi decoding
# ---------------------------------------------------------------------------

class HMM:
    """Hidden Markov Model with Viterbi decoding for sequence labeling.

    Used for POS tagging: states = POS tags, observations = words.
    """

    __slots__ = ("_state_idx", "emit_prob", "start_prob", "states", "trans_prob")

    def __init__(
        self,
        states: list[str],
        start_prob: dict[str, float],
        trans_prob: dict[str, dict[str, float]],
        emit_prob: dict[str, dict[str, float]],
    ) -> None:
        self.states = states
        self.start_prob = start_prob
        self.trans_prob = trans_prob
        self.emit_prob = emit_prob
        self._state_idx = {s: i for i, s in enumerate(states)}

    def _emit_log_prob(self, state: str, observation: str) -> float:
        """Log emission probability with add-k smoothing."""
        probs = self.emit_prob.get(state, {})
        p = probs.get(observation, 1e-10)
        return math.log(max(p, 1e-10))

    def _trans_log_prob(self, from_state: str, to_state: str) -> float:
        """Log transition probability with smoothing."""
        probs = self.trans_prob.get(from_state, {})
        p = probs.get(to_state, 1e-10)
        return math.log(max(p, 1e-10))

    def viterbi(self, observations: list[str]) -> list[str]:
        """Viterbi decoding: find most likely state sequence."""
        if not observations:
            return []

        n = len(observations)
        ns = len(self.states)

        # Initialize
        viterbi_mat: list[list[float]] = [[-math.inf] * ns for _ in range(n)]
        backptr: list[list[int]] = [[0] * ns for _ in range(n)]

        for si, s in enumerate(self.states):
            sp = self.start_prob.get(s, 1e-10)
            viterbi_mat[0][si] = math.log(max(sp, 1e-10)) + self._emit_log_prob(s, observations[0])

        # Forward pass
        for t in range(1, n):
            obs = observations[t]
            for sj, s_to in enumerate(self.states):
                best_score = -math.inf
                best_prev = 0
                ep = self._emit_log_prob(s_to, obs)
                for si, s_from in enumerate(self.states):
                    score = viterbi_mat[t - 1][si] + self._trans_log_prob(s_from, s_to) + ep
                    if score > best_score:
                        best_score = score
                        best_prev = si
                viterbi_mat[t][sj] = best_score
                backptr[t][sj] = best_prev

        # Backtrace
        best_last = max(range(ns), key=lambda i: viterbi_mat[n - 1][i])
        path = [best_last]
        for t in range(n - 1, 0, -1):
            path.append(backptr[t][path[-1]])
        path.reverse()

        return [self.states[i] for i in path]

    @property
    def param_count(self) -> int:
        total = len(self.start_prob)
        total += sum(len(v) for v in self.trans_prob.values())
        total += sum(len(v) for v in self.emit_prob.values())
        return total
