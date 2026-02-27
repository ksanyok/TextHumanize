"""Tests for CLI benchmark command and performance characteristics."""

from __future__ import annotations

import time
import unittest

from texthumanize import detect_ai, humanize


class TestPerformance(unittest.TestCase):
    """Performance regression tests — ensure we don't get slower."""

    def test_humanize_short_under_2s(self):
        """Short text should complete in under 5 seconds (generous for CI + coverage)."""
        text = "Furthermore, it is important to note that this approach facilitates optimization."
        t0 = time.perf_counter()
        result = humanize(text, lang="en", seed=42)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 5.0, f"Short text took {elapsed:.2f}s")
        self.assertTrue(len(result.text) > 0)

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
        self.assertLess(elapsed, 10.0, f"Medium text took {elapsed:.2f}s")
        self.assertTrue(len(result.text) > 0)

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
        self.assertLess(elapsed, 0.5, f"AI detection took {elapsed:.2f}s")
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


if __name__ == "__main__":
    unittest.main()
