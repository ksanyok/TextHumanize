"""The fitted-weights loading mechanism (training/ pipeline output)."""
from __future__ import annotations

import json
from importlib.resources import files

from texthumanize.detectors import AIDetector


def test_shipped_weights_file_is_valid():
    raw = (files("texthumanize") / "detector_weights.json").read_text("utf-8")
    data = json.loads(raw)
    assert data["schema"] == "texthumanize.detector_weights.v1"
    w = data["weights"]
    # Every shipped weight is a known metric with a sane, non-negative value.
    for metric, value in w.items():
        assert metric in AIDetector._WEIGHTS, f"unknown metric {metric}"
        assert isinstance(value, (int, float)) and value >= 0
    assert sum(w.values()) > 0


def test_resolved_weights_cover_all_metrics():
    resolved = AIDetector._load_fitted_weights()
    # Merge keeps every default metric even if the file omits some.
    assert set(resolved) == set(AIDetector._WEIGHTS)
    assert all(v >= 0 for v in resolved.values())


def test_invalid_weights_fall_back_to_defaults(monkeypatch):
    # A broken payload must not throw and must yield the hand-tuned defaults.
    def boom(*a, **k):
        raise ValueError("corrupt")
    monkeypatch.setattr("texthumanize.detectors.json.loads", boom)
    fell_back = AIDetector._load_fitted_weights()
    assert fell_back == dict(AIDetector._WEIGHTS)


def test_detection_unchanged_by_bootstrap_weights():
    # The shipped bootstrap equals the hand-tuned weights, so a detection with
    # the file present must match one forced onto the raw defaults.
    text = ("In today's rapidly evolving digital landscape, it is important to "
            "note that leveraging synergistic solutions can significantly enhance "
            "productivity. Furthermore, organizations must carefully consider the "
            "multifaceted implications of these transformative technologies.")
    AIDetector._fitted_weights_cache = None
    with_file = AIDetector().detect(text, "en").ai_probability
    AIDetector._fitted_weights_cache = dict(AIDetector._WEIGHTS)
    forced = AIDetector().detect(text, "en").ai_probability
    AIDetector._fitted_weights_cache = None
    assert abs(with_file - forced) < 1e-9
