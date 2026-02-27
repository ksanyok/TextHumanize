"""Weight loading utilities for pre-trained models.

Loads compressed weight blobs from the weights/ directory.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from texthumanize.neural_engine import decompress_weights

logger = logging.getLogger(__name__)

_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")


def _load_weight_file(name: str) -> Any | None:
    """Load a compressed weight file from the weights directory."""
    path = os.path.join(_WEIGHTS_DIR, name)
    if not os.path.exists(path):
        logger.debug("Weight file not found: %s", path)
        return None
    try:
        with open(path) as f:
            blob = f.read()
        data = decompress_weights(blob)
        logger.info("Loaded weights from %s (%d bytes)", name, len(blob))
        return data
    except Exception as e:
        logger.warning("Failed to load weights %s: %s", name, e)
        return None


def load_detector_weights() -> Any | None:
    """Load pre-trained MLP detector weights."""
    return _load_weight_file("detector_weights.json.zb85")


def load_lm_weights() -> Any | None:
    """Load pre-trained LSTM language model weights."""
    return _load_weight_file("lm_weights.json.zb85")
