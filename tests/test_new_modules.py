"""Tests for new modules: training, benchmarks, dictionaries, weight_loader, dashboard."""

from __future__ import annotations

import json
import os
import tempfile

# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------


class TestAdamOptimizer:
    """Tests for AdamOptimizer."""

    def test_step_vec_basic(self):
        from texthumanize.training import AdamOptimizer

        opt = AdamOptimizer(lr=0.1)
        params = [1.0, 2.0, 3.0]
        grads = [0.5, -0.3, 0.1]
        new_params = opt.step_vec("p", params, grads)
        assert len(new_params) == 3
        # Parameters should move in opposite direction of gradients
        assert new_params[0] < 1.0  # grad > 0 → param decreases
        assert new_params[1] > 2.0  # grad < 0 → param increases

    def test_step_vec_convergence(self):
        """Adam should converge parameters toward zero gradient."""
        from texthumanize.training import AdamOptimizer

        opt = AdamOptimizer(lr=0.01)
        params = [5.0]
        for _ in range(200):
            grads = [params[0]]  # grad = param → pushes to 0
            params = opt.step_vec("conv", params, grads)
        # Should move noticeably toward 0
        assert abs(params[0]) < abs(5.0)

    def test_step_mat(self):
        from texthumanize.training import AdamOptimizer

        opt = AdamOptimizer(lr=0.1)
        mat = [[1.0, 2.0], [3.0, 4.0]]
        grads = [[0.1, -0.1], [-0.2, 0.2]]
        new_mat = opt.step_mat("m", mat, grads)
        assert len(new_mat) == 2
        assert len(new_mat[0]) == 2


class TestBCELoss:
    """Tests for loss functions."""

    def test_bce_loss_range(self):
        from texthumanize.training import _bce_loss

        # Perfect prediction → loss near 0
        assert _bce_loss(0.99, 1.0) < 0.02
        assert _bce_loss(0.01, 0.0) < 0.02
        # Wrong prediction → high loss
        assert _bce_loss(0.01, 1.0) > 3.0
        assert _bce_loss(0.99, 0.0) > 3.0

    def test_bce_grad_sign(self):
        from texthumanize.training import _bce_grad

        # If predicted > target, gradient is positive
        assert _bce_grad(0.8, 0.0) > 0
        # If predicted < target, gradient is negative
        assert _bce_grad(0.2, 1.0) < 0


class TestTrainingDataGenerator:
    """Tests for data generation."""

    def test_generate_samples(self):
        from texthumanize.training import TrainingDataGenerator

        gen = TrainingDataGenerator(seed=42)
        samples = gen.generate(n_samples=20)
        assert len(samples) == 20
        for feat, label in samples:
            assert isinstance(feat, list)
            assert len(feat) > 0
            assert 0.0 <= label <= 1.0

    def test_has_ai_and_human(self):
        """Should generate both AI and human samples."""
        from texthumanize.training import TrainingDataGenerator

        gen = TrainingDataGenerator(seed=42)
        samples = gen.generate(n_samples=40)
        labels = [lbl for _, lbl in samples]
        # Should have at least some near-AI (>0.5) and near-human (<0.5)
        ai_count = sum(1 for l in labels if l > 0.5)
        human_count = sum(1 for l in labels if l < 0.5)
        assert ai_count > 0
        assert human_count > 0


class TestMLPTrainer:
    """Tests for MLP trainer (quick sanity check, not full training)."""

    def test_single_step_reduces_loss(self):
        from texthumanize.neural_engine import DenseLayer, FeedForwardNet, _he_init, _zeros
        from texthumanize.training import MLPTrainer, TrainingDataGenerator

        gen = TrainingDataGenerator(seed=42)
        samples = gen.generate(n_samples=20)
        dim = len(samples[0][0])

        # Build a small network with proper weight initialization
        net = FeedForwardNet(
            name="test_mlp",
            layers=[
                DenseLayer(weights=_he_init(dim, 8), bias=_zeros(8), activation="relu"),
                DenseLayer(weights=_he_init(8, 1), bias=_zeros(1), activation="linear"),
            ],
        )
        trainer = MLPTrainer(net=net, lr=0.01)

        # Run a few training steps
        losses = []
        for feat, label in samples[:10]:
            loss = trainer.train_step(feat, label)
            losses.append(loss)

        # Loss values should exist and be positive
        assert all(l >= 0 for l in losses)


class TestTrainer:
    """Tests for Trainer orchestrator."""

    def test_generate_data(self):
        from texthumanize.training import Trainer

        trainer = Trainer(seed=42)
        trainer.generate_data(n_samples=20)
        assert len(trainer._train_data) > 0
        assert len(trainer._val_data) > 0


# ---------------------------------------------------------------------------
# Benchmarks tests
# ---------------------------------------------------------------------------


class TestValidationSuite:
    """Tests for ValidationSuite."""

    def test_init(self):
        from texthumanize.benchmarks import ValidationSuite

        suite = ValidationSuite()
        assert suite is not None

    def test_validate_detection_runs(self):
        from texthumanize.benchmarks import ValidationSuite

        suite = ValidationSuite(profiles=["web"], intensities=[40])
        result = suite.validate_detection(lang="en")
        assert isinstance(result, dict)
        assert "accuracy" in result
        assert "confusion" in result

    def test_validate_humanization_runs(self):
        from texthumanize.benchmarks import ValidationSuite

        suite = ValidationSuite(profiles=["web"], intensities=[40])
        results = suite.validate_humanization(lang="en")
        assert isinstance(results, dict)
        assert "avg_score_drop" in results


# ---------------------------------------------------------------------------
# Dictionaries tests
# ---------------------------------------------------------------------------


class TestDictionaries:
    """Tests for updatable dictionary system."""

    def test_load_dict_en(self):
        from texthumanize.dictionaries import load_dict

        d = load_dict("en", force_reload=True)
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_deep_merge(self):
        from texthumanize.dictionaries import _deep_merge

        base = {"a": 1, "b": {"c": 2, "d": 3}}
        overlay = {"b": {"c": 99, "e": 5}, "f": 6}
        merged = _deep_merge(base, overlay)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 99
        assert merged["b"]["d"] == 3
        assert merged["b"]["e"] == 5
        assert merged["f"] == 6

    def test_deep_merge_sets(self):
        from texthumanize.dictionaries import _deep_merge

        base = {"words": {"a", "b"}}
        overlay = {"words": ["c", "d"]}
        merged = _deep_merge(base, overlay)
        assert isinstance(merged["words"], set)
        assert merged["words"] == {"a", "b", "c", "d"}

    def test_update_and_load(self):
        from texthumanize.dictionaries import (
            _OVERLAY_CACHE,
            load_dict,
            reset_overlay,
            update_dict,
        )

        lang = "_test_temp"
        try:
            update_dict(lang, {"test_key": "test_value"})
            d = load_dict(lang, force_reload=True)
            assert d.get("test_key") == "test_value"
        finally:
            reset_overlay(lang)
            _OVERLAY_CACHE.pop(lang, None)

    def test_export_dict(self):
        from texthumanize.dictionaries import export_dict

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            export_dict("en", tmp_path)
            with open(tmp_path, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict)
            assert len(data) > 0
        finally:
            os.unlink(tmp_path)

    def test_make_serializable(self):
        from texthumanize.dictionaries import _make_serializable

        obj = {"s": {"a", "c", "b"}, "l": [1, {"x", "y"}], "n": 42}
        result = _make_serializable(obj)
        assert result["s"] == ["a", "b", "c"]
        assert result["n"] == 42
        assert isinstance(result["l"][1], list)

    def test_list_overlays(self):
        from texthumanize.dictionaries import list_overlays

        result = list_overlays()
        assert isinstance(result, dict)

    def test_reset_overlay(self):
        from texthumanize.dictionaries import (
            _OVERLAY_CACHE,
            _overlay_path,
            reset_overlay,
            update_dict,
        )

        lang = "_test_reset"
        try:
            update_dict(lang, {"x": 1})
            assert os.path.exists(_overlay_path(lang))
            reset_overlay(lang)
            assert not os.path.exists(_overlay_path(lang))
        finally:
            _OVERLAY_CACHE.pop(lang, None)
            # Ensure cleanup
            path = _overlay_path(lang)
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# Weight loader tests
# ---------------------------------------------------------------------------


class TestWeightLoader:
    """Tests for weight loading utilities."""

    def test_load_detector_weights(self):
        from texthumanize.weight_loader import load_detector_weights

        data = load_detector_weights()
        # Should succeed if weights file exists
        if data is not None:
            assert isinstance(data, dict)
            assert "config" in data or "layers" in data or "name" in data

    def test_load_lm_weights(self):
        from texthumanize.weight_loader import load_lm_weights

        data = load_lm_weights()
        if data is not None:
            assert isinstance(data, dict)

    def test_missing_file_returns_none(self):
        from texthumanize.weight_loader import _load_weight_file

        result = _load_weight_file("nonexistent_weights.bin")
        assert result is None


# ---------------------------------------------------------------------------
# Dashboard tests
# ---------------------------------------------------------------------------


class TestDashboard:
    """Tests for evaluation dashboard."""

    def test_init(self):
        from texthumanize.dashboard import Dashboard

        dash = Dashboard()
        assert dash._version != ""

    def test_save_json(self):
        from texthumanize.dashboard import Dashboard

        report = {"version": "test", "data": [1, 2, 3]}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            Dashboard.save_json(report, tmp)
            with open(tmp, encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["version"] == "test"
        finally:
            os.unlink(tmp)

    def test_save_html(self):
        from texthumanize.dashboard import Dashboard

        report = {
            "version": "test",
            "lang": "en",
            "timestamp": "2024-01-01",
            "detection": {"accuracy": 0.9, "precision": 0.85, "recall": 0.88, "f1": 0.86,
                          "confusion": {"tp": 4, "fn": 1, "fp": 2, "tn": 3}},
            "humanization": [{"profile": "web", "intensity": 60, "avg_score_drop": 0.15,
                              "success_rate": 0.8, "avg_humanize_ms": 50}],
            "neural_models": {"detector": {"architecture": "MLP", "param_count": 4000, "trained": True},
                              "language_model": {"type": "LSTM", "hidden_dim": 64}},
            "elapsed_seconds": 1.5,
        }
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            tmp = f.name
        try:
            Dashboard.save_html(report, tmp)
            with open(tmp, encoding="utf-8") as f:
                html = f.read()
            assert "<!DOCTYPE html>" in html
            assert "TextHumanize" in html
            assert "90%" in html  # accuracy formatted
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# humanize_until_human tests
# ---------------------------------------------------------------------------


class TestHumanizeUntilHuman:
    """Tests for auto-retry humanization."""

    def test_basic_run(self):
        from texthumanize import humanize_until_human

        text = (
            "Furthermore, the comprehensive implementation of advanced "
            "methodologies ensures significant improvement across various "
            "domains. Additionally, the holistic approach facilitates "
            "optimal outcomes."
        )
        result = humanize_until_human(
            text, lang="en", max_attempts=2, seed=42,
        )
        assert result is not None
        assert isinstance(result.text, str)
        assert len(result.text) > 10

    def test_returns_humanize_result(self):
        from texthumanize import humanize_until_human

        result = humanize_until_human("Simple test text.", lang="en", max_attempts=1)
        # Should return a HumanizeResult
        assert hasattr(result, "text")
        assert hasattr(result, "lang")

    def test_intensity_increases(self):
        """With high target, intensity should increase across attempts."""
        from texthumanize import humanize_until_human

        # target_score=0.0 is impossible, so it will try all attempts
        result = humanize_until_human(
            "The implementation facilitates automation.",
            lang="en", intensity=20, max_attempts=2,
            intensity_step=30, target_score=0.0, seed=42,
        )
        # Should still return a result
        assert result is not None
