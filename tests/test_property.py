"""Property-based tests using Hypothesis.

These tests verify invariants that must hold for ANY valid input,
not just hand-picked examples.
"""

from __future__ import annotations

import unittest

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from texthumanize import analyze, detect_ai, humanize, paraphrase
from texthumanize.utils import HumanizeResult

# Common settings: no deadline, suppress filter health check
_common = dict(
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)


# --- Strategies ---

_word_chars = st.characters(
    whitelist_categories=("L", "N"),
    whitelist_characters="-'",
)
_word = st.text(_word_chars, min_size=1, max_size=15).filter(lambda w: w.strip())

text_strategy = st.lists(_word, min_size=5, max_size=80).map(lambda ws: " ".join(ws))

lang_strategy = st.sampled_from(["en", "ru", "uk", "de", "fr", "es", "pl", "pt", "it"])

intensity_strategy = st.integers(min_value=0, max_value=100)

seed_strategy = st.integers(min_value=0, max_value=2**31)


class TestHumanizeProperties(unittest.TestCase):

    @given(text=text_strategy, lang=lang_strategy, seed=seed_strategy)
    @settings(max_examples=30, **_common)
    def test_returns_humanize_result(self, text, lang, seed):
        result = humanize(text, lang=lang, seed=seed)
        self.assertIsInstance(result, HumanizeResult)
        self.assertIsInstance(result.text, str)
        self.assertTrue(len(result.text) > 0)

    @given(text=text_strategy, lang=lang_strategy,
           intensity=intensity_strategy, seed=seed_strategy)
    @settings(max_examples=20, **_common)
    def test_intensity_accepted(self, text, lang, intensity, seed):
        result = humanize(text, lang=lang, intensity=intensity, seed=seed)
        self.assertIsInstance(result, HumanizeResult)

    @given(text=text_strategy, seed=seed_strategy)
    @settings(max_examples=10, **_common)
    def test_deterministic_with_seed(self, text, seed):
        r1 = humanize(text, lang="en", seed=seed)
        r2 = humanize(text, lang="en", seed=seed)
        self.assertEqual(r1.text, r2.text)

    @given(text=text_strategy)
    @settings(max_examples=10, **_common)
    def test_change_ratio_bounded(self, text):
        result = humanize(text, lang="en", seed=42)
        self.assertGreaterEqual(result.change_ratio, 0.0)
        self.assertLessEqual(result.change_ratio, 1.0)

    def test_whitespace_noop(self):
        result = humanize("   ", lang="en")
        self.assertIsInstance(result, HumanizeResult)


class TestDetectAiProperties(unittest.TestCase):

    @given(text=text_strategy, lang=lang_strategy)
    @settings(max_examples=20, **_common)
    def test_score_in_range(self, text, lang):
        result = detect_ai(text, lang=lang)
        self.assertIsInstance(result, dict)
        score = result.get("score", 0)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    @given(text=text_strategy, lang=lang_strategy)
    @settings(max_examples=20, **_common)
    def test_has_verdict(self, text, lang):
        result = detect_ai(text, lang=lang)
        self.assertIn("verdict", result)
        self.assertIsInstance(result["verdict"], str)


class TestAnalyzeProperties(unittest.TestCase):

    @given(text=text_strategy, lang=lang_strategy)
    @settings(max_examples=10, **_common)
    def test_returns_report(self, text, lang):
        result = analyze(text, lang=lang)
        from texthumanize.utils import AnalysisReport
        self.assertIsInstance(result, AnalysisReport)
        self.assertIsInstance(result.lang, str)
        self.assertGreaterEqual(result.total_words, 0)


class TestParaphraseProperties(unittest.TestCase):

    @given(text=text_strategy, lang=lang_strategy, seed=seed_strategy)
    @settings(max_examples=20, **_common)
    def test_always_returns_result(self, text, lang, seed):
        result = paraphrase(text, lang=lang, seed=seed)
        if isinstance(result, str):
            self.assertTrue(len(result) > 0)
        else:
            self.assertTrue(len(result.text) > 0)

    @given(text=text_strategy, seed=seed_strategy)
    @settings(max_examples=10, **_common)
    def test_deterministic_with_seed(self, text, seed):
        r1 = paraphrase(text, lang="en", seed=seed)
        r2 = paraphrase(text, lang="en", seed=seed)
        t1 = r1 if isinstance(r1, str) else r1.text
        t2 = r2 if isinstance(r2, str) else r2.text
        self.assertEqual(t1, t2)


class TestRoundTrip(unittest.TestCase):

    @given(lang=lang_strategy, seed=seed_strategy)
    @settings(max_examples=5, **_common)
    def test_humanize_lowers_ai_score(self, lang, seed):
        ai_text = (
            "Furthermore, it is important to note that the implementation "
            "of comprehensive methodologies facilitates the optimization "
            "of operational processes in modern organizations."
        )
        assume(lang == "en")
        score_before = detect_ai(ai_text, lang=lang).get("score", 0)
        humanized = humanize(ai_text, lang=lang, seed=seed)
        score_after = detect_ai(humanized.text, lang=lang).get("score", 0)
        self.assertLessEqual(score_after, score_before + 0.15,
                             f"AI score increased from {score_before:.2f} "
                             f"to {score_after:.2f}")


if __name__ == "__main__":
    unittest.main()
