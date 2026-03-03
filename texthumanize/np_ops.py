"""NumPy-accelerated neural network operations.

Drop-in replacement for the pure-Python linear algebra in neural_engine.py.
Provides 50-100x speedup for matrix operations, LSTM steps, and
transformer inference.

All functions operate on numpy arrays and are designed for CPU inference.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Type aliases
F32 = NDArray[np.float32]


# ---------------------------------------------------------------------------
# Basic ops
# ---------------------------------------------------------------------------


def linear(x: F32, weight: F32, bias: Optional[F32] = None) -> F32:
    """Linear layer: out = x @ W^T + b.  Works for both 1-D and 2-D x."""
    out = x @ weight.T
    if bias is not None:
        out = out + bias
    return out


def relu(x: F32) -> F32:
    return np.maximum(x, 0.0, dtype=np.float32)


def gelu(x: F32) -> F32:
    return (0.5 * x * (1.0 + np.tanh(
        np.sqrt(2.0 / np.pi) * (x + 0.044715 * x ** 3)
    ))).astype(np.float32)


def sigmoid(x: F32) -> F32:
    return (1.0 / (1.0 + np.exp(-np.clip(x, -88, 88)))).astype(np.float32)


def tanh(x: F32) -> F32:
    return np.tanh(x).astype(np.float32)


def softmax(x: F32, axis: int = -1) -> F32:
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return (e / e.sum(axis=axis, keepdims=True)).astype(np.float32)


def log_softmax(x: F32, axis: int = -1) -> F32:
    m = np.max(x, axis=axis, keepdims=True)
    lse = m + np.log(np.sum(np.exp(x - m), axis=axis, keepdims=True))
    return (x - lse).astype(np.float32)


def layer_norm(x: F32, gamma: F32, beta: F32, eps: float = 1e-5) -> F32:
    """Layer normalization."""
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    xn = (x - mean) / np.sqrt(var + eps)
    return (gamma * xn + beta).astype(np.float32)


def layer_norm_simple(x: F32, eps: float = 1e-5) -> F32:
    """Layer norm without learnable parameters."""
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return ((x - mean) / np.sqrt(var + eps)).astype(np.float32)


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def embedding_lookup(indices: NDArray[np.int64], weight: F32) -> F32:
    """Lookup embeddings for given indices."""
    return weight[indices]


# ---------------------------------------------------------------------------
# Positional encoding
# ---------------------------------------------------------------------------


def sinusoidal_position_encoding(max_len: int, d_model: int) -> F32:
    """Sinusoidal positional encoding (Vaswani et al., 2017)."""
    pe = np.zeros((max_len, d_model), dtype=np.float32)
    position = np.arange(max_len, dtype=np.float32)[:, np.newaxis]
    div_term = np.exp(
        np.arange(0, d_model, 2, dtype=np.float32) * (-math.log(10000.0) / d_model)
    )
    pe[:, 0::2] = np.sin(position * div_term)
    pe[:, 1::2] = np.cos(position * div_term[: d_model // 2 + d_model % 2])
    return pe


# ---------------------------------------------------------------------------
# Multi-Head Attention
# ---------------------------------------------------------------------------


def multi_head_attention(
    x: F32,
    wq: F32, wk: F32, wv: F32, wo: F32,
    bq: F32, bk: F32, bv: F32, bo: F32,
    n_heads: int,
    mask: Optional[F32] = None,
) -> F32:
    """Multi-head self-attention.

    Args:
        x: (seq_len, d_model)
        wq, wk, wv: (d_model, d_model)
        wo: (d_model, d_model)
        n_heads: number of attention heads
        mask: optional (seq_len, seq_len) mask
    Returns:
        (seq_len, d_model)
    """
    seq_len, d_model = x.shape
    head_dim = d_model // n_heads

    Q = linear(x, wq, bq)  # (seq, d_model)
    K = linear(x, wk, bk)
    V = linear(x, wv, bv)

    # Reshape to (n_heads, seq, head_dim)
    Q = Q.reshape(seq_len, n_heads, head_dim).transpose(1, 0, 2)
    K = K.reshape(seq_len, n_heads, head_dim).transpose(1, 0, 2)
    V = V.reshape(seq_len, n_heads, head_dim).transpose(1, 0, 2)

    # Scaled dot-product attention
    scale = np.float32(1.0 / math.sqrt(head_dim))
    scores = (Q @ K.transpose(0, 2, 1)) * scale  # (n_heads, seq, seq)

    if mask is not None:
        scores = scores + mask[np.newaxis, :, :]

    attn = softmax(scores, axis=-1)  # (n_heads, seq, seq)
    context = attn @ V  # (n_heads, seq, head_dim)

    # Concat heads
    context = context.transpose(1, 0, 2).reshape(seq_len, d_model)

    return linear(context, wo, bo)


# ---------------------------------------------------------------------------
# FFN (Feed-Forward Network) block
# ---------------------------------------------------------------------------


def ffn_block(x: F32, w1: F32, b1: F32, w2: F32, b2: F32) -> F32:
    """Position-wise FFN: GELU(x @ W1 + b1) @ W2 + b2."""
    return linear(gelu(linear(x, w1, b1)), w2, b2)


# ---------------------------------------------------------------------------
# Transformer Block
# ---------------------------------------------------------------------------


def transformer_block(
    x: F32,
    # Attention weights
    wq: F32, wk: F32, wv: F32, wo: F32,
    bq: F32, bk: F32, bv: F32, bo: F32,
    # Layer norm 1
    ln1_g: F32, ln1_b: F32,
    # FFN weights
    ff_w1: F32, ff_b1: F32, ff_w2: F32, ff_b2: F32,
    # Layer norm 2
    ln2_g: F32, ln2_b: F32,
    n_heads: int,
    mask: Optional[F32] = None,
) -> F32:
    """Single transformer encoder block (pre-norm)."""
    # Self-attention with residual
    normed = layer_norm(x, ln1_g, ln1_b)
    attn_out = multi_head_attention(normed, wq, wk, wv, wo, bq, bk, bv, bo, n_heads, mask)
    x = x + attn_out

    # FFN with residual
    normed = layer_norm(x, ln2_g, ln2_b)
    ff_out = ffn_block(normed, ff_w1, ff_b1, ff_w2, ff_b2)
    x = x + ff_out

    return x


# ---------------------------------------------------------------------------
# LSTM Cell (numpy-accelerated)
# ---------------------------------------------------------------------------


def lstm_step(
    x: F32,
    h_prev: F32,
    c_prev: F32,
    W_ih: F32,  # (4*hidden, input_size)
    W_hh: F32,  # (4*hidden, hidden_size)
    b_ih: F32,  # (4*hidden,)
    b_hh: F32,  # (4*hidden,)
) -> tuple[F32, F32]:
    """Single LSTM step using fused gate computation.

    W_ih and W_hh stack all 4 gate weights: [Wi, Wf, Wg, Wo]
    """
    gates = x @ W_ih.T + h_prev @ W_hh.T + b_ih + b_hh  # (4*hidden,)
    hidden_size = h_prev.shape[0]

    i_gate = sigmoid(gates[:hidden_size])
    f_gate = sigmoid(gates[hidden_size:2 * hidden_size])
    g_gate = tanh(gates[2 * hidden_size:3 * hidden_size])
    o_gate = sigmoid(gates[3 * hidden_size:])

    c_new = f_gate * c_prev + i_gate * g_gate
    h_new = o_gate * tanh(c_new)

    return h_new, c_new


def lstm_forward(
    x_seq: F32,  # (seq_len, input_size)
    h0: F32,
    c0: F32,
    W_ih: F32,
    W_hh: F32,
    b_ih: F32,
    b_hh: F32,
) -> tuple[F32, F32, F32]:
    """Run LSTM over a sequence. Returns (outputs, h_final, c_final)."""
    seq_len = x_seq.shape[0]
    hidden_size = h0.shape[0]
    outputs = np.empty((seq_len, hidden_size), dtype=np.float32)
    h, c = h0, c0

    for t in range(seq_len):
        h, c = lstm_step(x_seq[t], h, c, W_ih, W_hh, b_ih, b_hh)
        outputs[t] = h

    return outputs, h, c


def bilstm_forward(
    x_seq: F32,
    h0_fwd: F32, c0_fwd: F32,
    W_ih_fwd: F32, W_hh_fwd: F32, b_ih_fwd: F32, b_hh_fwd: F32,
    h0_bwd: F32, c0_bwd: F32,
    W_ih_bwd: F32, W_hh_bwd: F32, b_ih_bwd: F32, b_hh_bwd: F32,
) -> F32:
    """Bidirectional LSTM. Returns concatenated (seq_len, 2*hidden)."""
    fwd_out, _, _ = lstm_forward(x_seq, h0_fwd, c0_fwd, W_ih_fwd, W_hh_fwd, b_ih_fwd, b_hh_fwd)
    bwd_out, _, _ = lstm_forward(
        x_seq[::-1], h0_bwd, c0_bwd, W_ih_bwd, W_hh_bwd, b_ih_bwd, b_hh_bwd,
    )
    return np.concatenate([fwd_out, bwd_out[::-1]], axis=-1)


# ---------------------------------------------------------------------------
# Attention pooling
# ---------------------------------------------------------------------------


def attention_pool(
    h_seq: F32,  # (seq_len, hidden)
    w_attn: F32,  # (hidden,)
) -> F32:
    """Attention-weighted pooling over a sequence."""
    scores = h_seq @ w_attn  # (seq_len,)
    weights = softmax(scores)  # (seq_len,)
    return (weights[:, np.newaxis] * h_seq).sum(axis=0)  # (hidden,)


# ---------------------------------------------------------------------------
# MLP (Multi-Layer Perceptron) — numpy version
# ---------------------------------------------------------------------------


def mlp_forward(
    x: F32,
    weights: list[F32],
    biases: list[F32],
    activations: list[str],
) -> F32:
    """Forward pass through MLP with specified activations."""
    _act_map = {
        "relu": relu,
        "gelu": gelu,
        "sigmoid": sigmoid,
        "tanh": tanh,
        "linear": lambda v: v,
    }
    for w, b, act_name in zip(weights, biases, activations):
        x = linear(x, w, b)
        x = _act_map[act_name](x)
    return x


# ---------------------------------------------------------------------------
# Weight conversion helpers (list ↔ numpy)
# ---------------------------------------------------------------------------


def lists_to_np(data: list[list[float]] | list[float]) -> F32:
    """Convert nested Python lists to numpy float32 array."""
    return np.array(data, dtype=np.float32)


def np_to_lists(arr: F32) -> Any:
    """Convert numpy array back to nested Python lists."""
    return arr.tolist()


# ---------------------------------------------------------------------------
# Weight initialization
# ---------------------------------------------------------------------------


def he_init(fan_in: int, fan_out: int, rng: np.random.Generator) -> F32:
    """He initialization for ReLU networks."""
    std = np.sqrt(np.float32(2.0 / fan_in))
    return rng.normal(0, std, (fan_out, fan_in)).astype(np.float32)


def xavier_init(fan_in: int, fan_out: int, rng: np.random.Generator) -> F32:
    """Xavier/Glorot uniform initialization."""
    limit = np.sqrt(np.float32(6.0 / (fan_in + fan_out)))
    return rng.uniform(-limit, limit, (fan_out, fan_in)).astype(np.float32)


def zeros(n: int) -> F32:
    return np.zeros(n, dtype=np.float32)


def ones(n: int) -> F32:
    return np.ones(n, dtype=np.float32)
