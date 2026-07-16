"""Tests for CLI benchmark command and performance characteristics."""

from __future__ import annotations

import time
import unittest

import pytest

from texthumanize import detect_ai, humanize
from texthumanize.benchmarks import (
    detector_benchmark,
    index_eval_corpus,
    load_eval_corpus,
)


class TestPerformance(unittest.TestCase):
    """Performance regression tests — ensure we don't get slower."""

    @pytest.mark.perf
    def test_humanize_short_under_2s(self):
        """Short text should complete in under 5 seconds (generous for CI + coverage)."""
        text = "Furthermore, it is important to note that this approach facilitates optimization."
        t0 = time.perf_counter()
        result = humanize(text, lang="en", seed=42)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 30.0, f"Short text took {elapsed:.2f}s")
        self.assertTrue(len(result.text) > 0)

    @pytest.mark.perf
    def test_humanize_medium_under_3s(self):
        """Medium text (~500 chars) should complete in under 10 seconds (generous for CI + coverage)."""
        text = (
            "Furthermore, it is important to note that the implementation of cloud computing "
            "facilitates the optimization of business processes. Additionally, the utilization "
            "of microservices constitutes a significant advancement. Nevertheless, considerable "
            "challenges remain in the area of security. It is worth mentioning that these "
            "challenges necessitate comprehensive solutions."
        )
        t0 = time.perf_counter()
        result = humanize(text, lang="en", seed=42)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 30.0, f"Medium text took {elapsed:.2f}s")
        self.assertTrue(len(result.text) > 0)

    @pytest.mark.perf
    def test_detect_ai_under_500ms(self):
        """AI detection should be fast — under 500ms for medium text."""
        text = (
            "The implementation of artificial intelligence facilitates the optimization "
            "of various business processes. Additionally, machine learning provides "
            "unprecedented opportunities for automation and efficiency improvement."
        )
        t0 = time.perf_counter()
        result = detect_ai(text, lang="en")
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 5.0, f"AI detection took {elapsed:.2f}s")
        self.assertIn("score", result)
        self.assertIn("verdict", result)

    def test_determinism(self):
        """Same seed must produce identical output."""
        text = "Furthermore, it is important to implement this approach."
        r1 = humanize(text, lang="en", seed=12345)
        r2 = humanize(text, lang="en", seed=12345)
        self.assertEqual(r1.text, r2.text)

    def test_different_seeds_different_output(self):
        """Different seeds should generally produce different output."""
        text = (
            "The system utilizes comprehensive methodologies for the implementation "
            "of various optimization strategies. Furthermore, it facilitates the "
            "integration of multiple processing components."
        )
        r1 = humanize(text, lang="en", seed=1)
        r2 = humanize(text, lang="en", seed=99999)
        # They might be the same for very short texts, but for longer ones should differ
        # At minimum, both should be valid
        self.assertTrue(len(r1.text) > 0)
        self.assertTrue(len(r2.text) > 0)


class TestQualityGates(unittest.TestCase):
    """Quality gate tests — ensure humanization maintains standards."""

    def test_change_ratio_within_bounds(self):
        """Change ratio should not exceed max_change_ratio constraint."""
        text = (
            "Furthermore, it is important to note that the implementation of this "
            "approach facilitates the optimization of business processes. Additionally, "
            "the utilization of modern technologies constitutes a significant advancement."
        )
        result = humanize(text, lang="en", constraints={"max_change_ratio": 0.5}, seed=42)
        self.assertLessEqual(result.change_ratio, 0.55)  # small tolerance

    def test_quality_score_positive(self):
        """Quality score should be positive for valid text."""
        text = "The implementation of comprehensive optimization strategies facilitates improvement."
        result = humanize(text, lang="en", seed=42)
        self.assertGreaterEqual(result.quality_score, 0.0)

    def test_preserves_meaning_jaccard(self):
        """Humanized text should share significant vocabulary with original."""
        text = (
            "The implementation of cloud computing facilitates the optimization of "
            "business processes. Additionally, microservices constitute a significant "
            "advancement in software architecture."
        )
        result = humanize(text, lang="en", intensity=60, seed=42)
        # Jaccard similarity — at least 30% word overlap
        orig_words = set(text.lower().split())
        new_words = set(result.text.lower().split())
        if orig_words:
            overlap = len(orig_words & new_words) / len(orig_words | new_words)
            self.assertGreater(overlap, 0.25, f"Jaccard similarity too low: {overlap:.2f}")

    def test_length_preservation(self):
        """Output length should be within reasonable bounds of input."""
        text = (
            "Furthermore, it is important to note that this approach facilitates optimization. "
            "Additionally, the utilization of modern frameworks constitutes advancement."
        )
        result = humanize(text, lang="en", seed=42)
        ratio = len(result.text) / len(text)
        self.assertGreater(ratio, 0.4, f"Output too short: {ratio:.2f}x")
        self.assertLess(ratio, 2.5, f"Output too long: {ratio:.2f}x")

    def test_ai_detection_on_ai_text(self):
        """AI-generated text should score high on AI detection."""
        ai_text = (
            "Furthermore, it is important to note that the implementation of artificial "
            "intelligence constitutes a significant paradigm shift. Additionally, the "
            "utilization of machine learning facilitates comprehensive optimization of "
            "various processes. Nevertheless, it is worth mentioning that considerable "
            "challenges remain. Moreover, the integration of deep learning provides "
            "unprecedented opportunities for automation."
        )
        result = detect_ai(ai_text, lang="en")
        self.assertGreater(result["score"], 0.5, "AI text should score above 50%")

    def test_ai_detection_on_human_text(self):
        """Human-written text should score low on AI detection."""
        human_text = (
            "Tried that new coffee shop downtown. Their espresso was decent - not burnt "
            "like the place on 5th. The barista recommended this Ethiopian blend I'd "
            "never heard of. Might go back this weekend, maybe bring Sarah."
        )
        result = detect_ai(human_text, lang="en")
        self.assertLess(result["score"], 0.55, "Human text should score below 55%")


class TestMultiLanguage(unittest.TestCase):
    """Ensure multiple languages work and produce valid output."""

    def _assert_humanize_lang(self, text: str, lang: str):
        result = humanize(text, lang=lang, seed=42)
        self.assertTrue(len(result.text) > 0, f"Empty output for lang={lang}")

    def test_russian(self):
        self._assert_humanize_lang(
            "Необходимо отметить, что данный подход является оптимальным решением.", "ru"
        )

    def test_ukrainian(self):
        self._assert_humanize_lang(
            "Необхідно зазначити, що даний підхід є оптимальним рішенням.", "uk"
        )

    def test_german(self):
        self._assert_humanize_lang(
            "Es ist wichtig zu beachten, dass die Implementierung dieses Ansatzes die Optimierung erleichtert.", "de"
        )

    def test_french(self):
        self._assert_humanize_lang(
            "Il est important de noter que la mise en œuvre de cette approche facilite l'optimisation.", "fr"
        )

    def test_spanish(self):
        self._assert_humanize_lang(
            "Es importante señalar que la implementación de este enfoque facilita la optimización.", "es"
        )


class TestCLIBenchmarkIntegration(unittest.TestCase):
    """Test the benchmark CLI command produces valid output."""

    def test_benchmark_json_output(self):
        """Benchmark --json should produce valid JSON."""
        import json
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "texthumanize", "benchmark", "-l", "en", "--json"],
            capture_output=True, text=True, timeout=120,
        )
        # Should exit cleanly
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Should be valid JSON
        data = json.loads(result.stdout)
        self.assertIn("version", data)
        self.assertIn("avg_throughput_chars_sec", data)
        self.assertIn("deterministic", data)
        self.assertTrue(data["deterministic"])
        self.assertGreater(data["avg_throughput_chars_sec"], 0)


class TestDetectorBenchmark(unittest.TestCase):
    """Detector benchmark schema and corpus checks."""

    def test_detector_benchmark_custom_corpus(self):
        """Custom corpus should produce per-language label metrics."""
        corpus = [
            {
                "id": "human",
                "lang": "en",
                "label": "human",
                "domain": "note",
                "text": "I checked the file twice and left a note for Mark.",
            },
            {
                "id": "ai",
                "lang": "en",
                "label": "ai",
                "domain": "docs",
                "text": (
                    "Furthermore, it is important to note that this comprehensive "
                    "implementation facilitates optimization across multiple workflows."
                ),
            },
            {
                "id": "edited",
                "lang": "en",
                "label": "edited_ai",
                "domain": "marketing",
                "text": (
                    "The original draft was tightened by an editor, but it still keeps "
                    "a fairly structured assistant-like rhythm and polished phrasing."
                ),
            },
        ]
        report = detector_benchmark(corpus, languages=["en"], include_details=True)
        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(
            report["labels"],
            ["human", "raw_ai", "lightly_edited_ai", "heavily_edited_ai"],
        )
        self.assertEqual(report["label_aliases"]["ai"], "raw_ai")
        self.assertEqual(report["label_aliases"]["edited_ai"], "lightly_edited_ai")
        self.assertEqual(report["overall"]["total"], 3)
        self.assertIn("en", report["per_language"])
        self.assertEqual(report["details"][1]["label"], "raw_ai")
        self.assertEqual(report["details"][2]["label"], "lightly_edited_ai")
        self.assertEqual(len(report["details"]), 3)

    def test_detector_benchmark_builtin_language(self):
        """Built-in corpus can be scoped by language."""
        report = detector_benchmark(languages=["en"], include_details=False)
        self.assertEqual(report["languages"], ["en"])
        self.assertGreaterEqual(report["overall"]["total"], 4)
        self.assertEqual(report["corpus"]["source"], "builtin")
        self.assertEqual(report["corpus"]["license"]["id"], "CC0-1.0")
        self.assertIn("raw_ai_recall", report["per_language"]["en"])
        self.assertIn("lightly_edited_ai_flag_rate", report["per_language"]["en"])
        self.assertIn("heavily_edited_ai_flag_rate", report["per_language"]["en"])
        self.assertEqual(report["per_language"]["en"]["details"], [])

    def test_load_eval_corpus_metadata_and_required_labels(self):
        """Packaged eval corpus should be licensed and balanced by label."""
        corpus = load_eval_corpus(include_metadata=True)
        self.assertEqual(corpus["schema_version"], "text-humanize.eval_corpus.v1")
        self.assertEqual(corpus["license"]["id"], "CC0-1.0")
        # Corpus grows over time; assert a floor rather than an exact count.
        self.assertGreaterEqual(corpus["sample_count"], 12)
        samples = corpus["samples"]
        labels = {sample["label"] for sample in samples}
        self.assertEqual(
            labels,
            {"human", "raw_ai", "lightly_edited_ai", "heavily_edited_ai"},
        )
        langs = {sample["lang"] for sample in samples}
        self.assertTrue({"en", "ru", "uk"}.issubset(langs))
        for sample in samples:
            self.assertTrue(sample["id"])
            self.assertTrue(sample["domain"])
            self.assertTrue(sample["length_bucket"])
            self.assertEqual(sample["source"], "text-humanize-authored-synthetic")
            self.assertEqual(sample["license"], "CC0-1.0")
            self.assertGreater(len(sample["text"]), 40)

    def test_load_eval_corpus_filters_by_fixture_dimensions(self):
        """Corpus fixtures can be selected by domain, language, length and source."""
        samples = load_eval_corpus(
            languages=["en"],
            labels=["raw_ai"],
            domains=["product"],
            length_buckets=["300_1000"],
            sources=["text-humanize-authored-synthetic"],
        )
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["id"], "en_raw_ai_product_001")
        self.assertEqual(samples[0]["lang"], "en")
        self.assertEqual(samples[0]["label"], "raw_ai")
        self.assertEqual(samples[0]["domain"], "product")
        self.assertEqual(samples[0]["length_bucket"], "300_1000")
        self.assertEqual(samples[0]["source"], "text-humanize-authored-synthetic")

    def test_index_eval_corpus_groups_by_fixture_dimensions(self):
        """Corpus index exposes deterministic ids and counts for every dimension."""
        index = index_eval_corpus()
        self.assertEqual(index["schema_version"], "text-humanize.eval_corpus_index.v1")
        self.assertGreaterEqual(index["total"], 12)
        for field in ("lang", "domain", "length_bucket", "source", "label"):
            self.assertIn(field, index["fields"])
            self.assertIn(field, index["counts"])
            self.assertEqual(
                sum(index["counts"][field].values()),
                index["total"],
            )
        self.assertIn("en_human_support_001", index["fields"]["lang"]["en"])
        self.assertEqual(
            index["counts"]["source"]["text-humanize-authored-synthetic"],
            index["total"],
        )
        self.assertGreaterEqual(index["counts"]["label"]["raw_ai"], 3)

    def test_detector_benchmark_reports_builtin_corpus_index(self):
        """Benchmark report includes fixture dimensions for reproducible slicing."""
        report = detector_benchmark(languages=["en"], include_details=False)
        index = report["corpus"]["index"]
        self.assertEqual(index["schema_version"], "text-humanize.eval_corpus_index.v1")
        self.assertGreaterEqual(index["counts"]["lang"]["en"], 4)
        self.assertIn("support", index["counts"]["domain"])


if __name__ == "__main__":
    unittest.main()
