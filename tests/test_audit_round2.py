"""Tests for new audit-round modules: neural_paraphraser, gptzero,
ai_markers, pos_benchmark, and cjk_segmenter enhancements."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

# ═══════════════════════════════════════════════════════════════
#  4.3  Neural Paraphraser
# ═══════════════════════════════════════════════════════════════


class TestNeuralParaphraser:
    """Tests for texthumanize.neural_paraphraser."""

    def test_import(self) -> None:
        from texthumanize.neural_paraphraser import (
            NeuralParaphraser,
            NeuralParaphraseResult,
            Seq2SeqParaphraser,
            neural_paraphrase,
        )
        assert NeuralParaphraser is not None
        assert Seq2SeqParaphraser is not None
        assert NeuralParaphraseResult is not None
        assert callable(neural_paraphrase)

    def test_seq2seq_init(self) -> None:
        from texthumanize.neural_paraphraser import Seq2SeqParaphraser
        model = Seq2SeqParaphraser()
        assert model.embed_dim == 32
        assert model.hidden_dim == 48
        assert model.attn_dim == 32

    def test_seq2seq_encode_decode(self) -> None:
        from texthumanize.neural_paraphraser import (
            Seq2SeqParaphraser,
            _decode_indices,
            _encode_text,
        )
        model = Seq2SeqParaphraser()
        text = "Hello world"
        indices = _encode_text(text)
        assert isinstance(indices, list)
        assert all(isinstance(i, int) for i in indices)
        result_indices = model.generate(indices, max_len=50)
        assert isinstance(result_indices, list)
        decoded = _decode_indices(result_indices)
        assert isinstance(decoded, str)

    def test_neural_paraphraser_paraphrase(self) -> None:
        from texthumanize.neural_paraphraser import NeuralParaphraser
        np = NeuralParaphraser(lang="en")
        result = np.paraphrase("The quick brown fox jumps over the lazy dog.")
        assert result.original == "The quick brown fox jumps over the lazy dog."
        assert isinstance(result.paraphrased, str)
        assert result.confidence >= 0.0
        assert result.method in ("neural", "synonym", "structural", "passthrough", "hybrid")

    def test_neural_paraphrase_convenience(self) -> None:
        from texthumanize.neural_paraphraser import neural_paraphrase
        result = neural_paraphrase("This is a test sentence.")
        assert isinstance(result.paraphrased, str)
        assert result.original == "This is a test sentence."

    def test_neural_paraphraser_russian(self) -> None:
        from texthumanize.neural_paraphraser import NeuralParaphraser
        np = NeuralParaphraser(lang="ru")
        result = np.paraphrase("Быстрая коричневая лиса прыгает через забор.")
        assert isinstance(result.paraphrased, str)

    def test_neural_paraphrase_result_dataclass(self) -> None:
        from texthumanize.neural_paraphraser import NeuralParaphraseResult
        r = NeuralParaphraseResult(
            original="a", paraphrased="b",
            confidence=0.8, method="neural",
            changes=["replaced x"],
        )
        assert r.original == "a"
        assert r.paraphrased == "b"
        assert r.confidence == 0.8
        assert r.method == "neural"
        assert len(r.changes) == 1

    def test_lazy_import(self) -> None:
        import texthumanize
        assert hasattr(texthumanize, "NeuralParaphraser")
        assert hasattr(texthumanize, "neural_paraphrase")


# ═══════════════════════════════════════════════════════════════
#  4.2  GPTZero Client
# ═══════════════════════════════════════════════════════════════


class TestGPTZero:
    """Tests for texthumanize.gptzero."""

    def test_import(self) -> None:
        from texthumanize.gptzero import (
            BatchResult,
            GPTZeroClient,
            GPTZeroResult,
            SentenceResult,
        )
        assert GPTZeroClient is not None
        assert GPTZeroResult is not None
        assert SentenceResult is not None
        assert BatchResult is not None

    def test_client_init_no_key(self) -> None:
        from texthumanize.gptzero import GPTZeroClient
        with mock.patch.dict(os.environ, {}, clear=True):
            # Should not raise — key is optional for construction
            client = GPTZeroClient(api_key="test-key-123")
            assert client.api_key == "test-key-123"

    def test_client_env_key(self) -> None:
        from texthumanize.gptzero import GPTZeroClient
        with mock.patch.dict(os.environ, {"GPTZERO_API_KEY": "env-key-456"}):
            client = GPTZeroClient()
            assert client.api_key == "env-key-456"

    def test_result_properties(self) -> None:
        from texthumanize.gptzero import GPTZeroResult
        r = GPTZeroResult(
            ai_probability=0.9,
            human_probability=0.1,
            mixed_probability=0.0,
            predicted_class="ai",
            sentences=[],
        )
        assert r.is_ai is True
        assert r.is_human is False
        assert r.is_mixed is False

    def test_result_human(self) -> None:
        from texthumanize.gptzero import GPTZeroResult
        r = GPTZeroResult(
            ai_probability=0.1,
            human_probability=0.8,
            mixed_probability=0.1,
            predicted_class="human",
            sentences=[],
        )
        assert r.is_human is True
        assert r.is_ai is False

    def test_sentence_result(self) -> None:
        from texthumanize.gptzero import SentenceResult
        s = SentenceResult(
            text="Hello world.",
            ai_probability=0.5,
            generated_probability=0.4,
            highlight=True,
        )
        assert s.text == "Hello world."
        assert s.ai_probability == 0.5
        assert s.highlight is True

    def test_batch_result(self) -> None:
        from texthumanize.gptzero import BatchResult, GPTZeroResult
        r1 = GPTZeroResult(0.9, 0.1, 0.0, "ai", [])
        r2 = GPTZeroResult(0.1, 0.9, 0.0, "human", [])
        br = BatchResult(results=[r1, r2], total_documents=2, processing_time=0.5)
        assert br.total_documents == 2
        assert len(br.results) == 2

    def test_lazy_import(self) -> None:
        import texthumanize
        assert hasattr(texthumanize, "GPTZeroClient")
        assert hasattr(texthumanize, "GPTZeroResult")


# ═══════════════════════════════════════════════════════════════
#  4.12  AI Markers (JSON externalization)
# ═══════════════════════════════════════════════════════════════


class TestAIMarkers:
    """Tests for texthumanize.ai_markers."""

    def test_import(self) -> None:
        from texthumanize.ai_markers import (
            export_markers_to_json,
            get_available_languages,
            import_markers_from_json,
            load_ai_markers,
            load_all_markers,
            update_markers,
        )
        assert callable(load_ai_markers)
        assert callable(load_all_markers)
        assert callable(export_markers_to_json)
        assert callable(import_markers_from_json)
        assert callable(update_markers)
        assert callable(get_available_languages)

    def test_load_builtin_en(self) -> None:
        from texthumanize.ai_markers import clear_cache, load_ai_markers
        clear_cache()
        markers = load_ai_markers("en")
        assert "adverbs" in markers
        assert "adjectives" in markers
        assert "verbs" in markers
        assert "connectors" in markers
        assert "phrases" in markers
        assert isinstance(markers["adverbs"], set)
        assert "significantly" in markers["adverbs"]

    def test_load_builtin_ru(self) -> None:
        from texthumanize.ai_markers import clear_cache, load_ai_markers
        clear_cache()
        markers = load_ai_markers("ru")
        assert "adverbs" in markers
        assert "значительно" in markers["adverbs"]

    def test_load_builtin_uk(self) -> None:
        from texthumanize.ai_markers import clear_cache, load_ai_markers
        clear_cache()
        markers = load_ai_markers("uk")
        assert "connectors" in markers
        assert "однак" in markers["connectors"]

    def test_load_nonexistent_lang(self) -> None:
        from texthumanize.ai_markers import clear_cache, load_ai_markers
        clear_cache()
        markers = load_ai_markers("zz")
        assert markers == {}

    def test_load_all_markers(self) -> None:
        from texthumanize.ai_markers import clear_cache, load_all_markers
        clear_cache()
        all_m = load_all_markers()
        assert "en" in all_m
        assert "ru" in all_m
        assert "uk" in all_m

    def test_export_and_import(self) -> None:
        from texthumanize.ai_markers import (
            clear_cache,
            export_markers_to_json,
            import_markers_from_json,
        )
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            created = export_markers_to_json(lang="en", output_dir=tmpdir)
            assert len(created) >= 2  # en json + meta json

            # Check file content
            en_path = os.path.join(tmpdir, "ai_markers_en.json")
            assert os.path.exists(en_path)
            with open(en_path) as f:
                data = json.load(f)
            assert "markers" in data
            assert "adverbs" in data["markers"]
            assert data["schema_version"] == "1.0"
            assert data["language"] == "en"

            # Import back
            clear_cache()
            markers = import_markers_from_json(en_path, merge=False)
            assert "adverbs" in markers

    def test_update_markers(self) -> None:
        from texthumanize.ai_markers import clear_cache, update_markers
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkey-patch data dir for test
            import texthumanize.ai_markers as am
            orig_dir = am._DATA_DIR
            am._DATA_DIR = Path(tmpdir)
            try:
                result = update_markers("en", "adverbs", ["superbly"], mode="add")
                assert "superbly" in result["adverbs"]

                # Check JSON file was created
                path = os.path.join(tmpdir, "ai_markers_en.json")
                assert os.path.exists(path)
            finally:
                am._DATA_DIR = orig_dir
                clear_cache()

    def test_get_available_languages(self) -> None:
        from texthumanize.ai_markers import get_available_languages
        langs = get_available_languages()
        assert "en" in langs
        assert "ru" in langs
        assert "uk" in langs

    def test_detectors_use_json_markers(self) -> None:
        """Verify detectors.py now loads markers from ai_markers module."""
        from texthumanize.detectors import _get_ai_words
        words = _get_ai_words()
        assert "en" in words
        assert "adverbs" in words["en"]
        assert isinstance(words["en"]["adverbs"], set)

    def test_lazy_import(self) -> None:
        import texthumanize
        assert hasattr(texthumanize, "load_ai_markers")
        assert hasattr(texthumanize, "export_markers_to_json")


# ═══════════════════════════════════════════════════════════════
#  4.6  POS Tagger Benchmark
# ═══════════════════════════════════════════════════════════════


class TestPOSBenchmark:
    """Tests for texthumanize.pos_benchmark."""

    def test_import(self) -> None:
        from texthumanize.pos_benchmark import (
            BenchmarkReport,
            LangBenchmarkResult,
            POSBenchmarkError,
            assert_accuracy,
            format_report,
            run_benchmark,
        )
        assert callable(run_benchmark)
        assert callable(assert_accuracy)
        assert callable(format_report)
        assert BenchmarkReport is not None
        assert LangBenchmarkResult is not None
        assert POSBenchmarkError is not None

    def test_run_benchmark_all_langs(self) -> None:
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark()
        assert report.overall_total > 0
        assert report.overall_correct > 0
        assert 0.0 <= report.overall_accuracy <= 1.0
        assert "en" in report.results
        assert "ru" in report.results
        assert "uk" in report.results
        assert "de" in report.results

    def test_run_benchmark_single_lang(self) -> None:
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark(languages=["en"])
        assert "en" in report.results
        assert len(report.results) == 1

    def test_english_accuracy_above_80(self) -> None:
        """English should be above 80% on gold corpus."""
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark(languages=["en"])
        assert report.results["en"].accuracy >= 0.80

    def test_overall_accuracy_above_75(self) -> None:
        """Overall accuracy on all languages should be above 75%."""
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark()
        assert report.overall_accuracy >= 0.75

    def test_per_tag_accuracy(self) -> None:
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark(languages=["en"])
        en = report.results["en"]
        assert len(en.per_tag_accuracy) > 0
        # DET and PUNCT should be almost perfect
        if "PUNCT" in en.per_tag_accuracy:
            assert en.per_tag_accuracy["PUNCT"] >= 0.95

    def test_format_report(self) -> None:
        from texthumanize.pos_benchmark import format_report, run_benchmark
        report = run_benchmark(languages=["en"])
        text = format_report(report)
        assert "POS Tagger Benchmark Report" in text
        assert "EN" in text
        assert "Accuracy" in text

    def test_confusions_recorded(self) -> None:
        from texthumanize.pos_benchmark import run_benchmark
        report = run_benchmark(languages=["en"])
        # There will likely be some mismatches
        en = report.results["en"]
        # confusions list should exist even if empty
        assert isinstance(en.confusions, list)

    def test_lazy_import(self) -> None:
        import texthumanize
        assert hasattr(texthumanize, "run_benchmark")
        assert hasattr(texthumanize, "assert_accuracy")


# ═══════════════════════════════════════════════════════════════
#  4.11  CJK Segmenter enhancements
# ═══════════════════════════════════════════════════════════════


class TestCJKEnhancements:
    """Tests for CJK segmenter enhancements (zero-dep justification)."""

    def test_register_external_segmenter(self) -> None:
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter("zh")
        # Register a mock segmenter
        mock_seg = mock.Mock(return_value=["mock", "result"])
        seg.register_external_segmenter("zh", mock_seg)
        result = seg.segment("test")
        mock_seg.assert_called_once_with("test")
        assert result == ["mock", "result"]

    def test_external_segmenter_fallback(self) -> None:
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter("zh")
        # Register a failing segmenter
        def failing_seg(text: str) -> list[str]:
            raise RuntimeError("BOOM")

        seg.register_external_segmenter("zh", failing_seg)
        # Should fall back to built-in without raising
        result = seg.segment("今天天气不错")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_builtin_still_works(self) -> None:
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter("zh")
        result = seg.segment("今天天气不错")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_run_cjk_benchmark(self) -> None:
        from texthumanize.cjk_segmenter import run_cjk_benchmark
        metrics = run_cjk_benchmark()
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "exact_match" in metrics
        # BiMM should be reasonable
        assert metrics["precision"] >= 0.5
        assert metrics["recall"] >= 0.5
        assert metrics["f1"] >= 0.5

    def test_docstring_has_justification(self) -> None:
        import texthumanize.cjk_segmenter as mod
        doc = mod.__doc__ or ""
        assert "Zero-dependency" in doc
        assert "jieba" in doc
        assert "BiMM" in doc

    def test_lazy_import_benchmark(self) -> None:
        import texthumanize
        assert hasattr(texthumanize, "run_cjk_benchmark")
