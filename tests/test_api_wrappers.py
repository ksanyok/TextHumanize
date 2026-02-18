"""Tests for core.py API wrapper functions (detect_ai, paraphrase, tone, etc.)."""

import pytest
from texthumanize.core import (
    detect_ai,
    detect_ai_batch,
    paraphrase,
    analyze_tone,
    adjust_tone,
    detect_watermarks,
    clean_watermarks,
    spin,
    spin_variants,
    analyze_coherence,
    full_readability,
    humanize,
    humanize_chunked,
    analyze,
    explain,
)


# ── detect_ai ─────────────────────────────────────────────────

class TestDetectAI:
    def test_returns_dict(self):
        r = detect_ai("This is a test text for detection.", lang="en")
        assert isinstance(r, dict)
        assert "score" in r
        assert "verdict" in r
        assert "confidence" in r
        assert "metrics" in r
        assert "explanations" in r

    def test_score_range(self):
        r = detect_ai("Machine generated content often exhibits patterns.", lang="en")
        assert 0.0 <= r["score"] <= 1.0
        assert 0.0 <= r["confidence"] <= 1.0

    def test_verdict_values(self):
        r = detect_ai("Some sample text here for analysis.", lang="en")
        assert r["verdict"] in ("human", "mixed", "ai", "unknown")

    def test_metrics_12_keys(self):
        r = detect_ai("Text with enough words for analysis.", lang="en")
        metrics = r["metrics"]
        expected = {
            "entropy", "burstiness", "vocabulary", "zipf",
            "stylometry", "ai_patterns", "punctuation", "coherence",
            "grammar_perfection", "opening_diversity",
            "readability_consistency", "rhythm",
        }
        assert set(metrics.keys()) == expected

    def test_auto_lang(self):
        r = detect_ai("Этот текст на русском языке для тестирования.", lang="auto")
        assert r["lang"] == "ru"

    def test_short_text(self):
        r = detect_ai("Short.", lang="en")
        assert isinstance(r["score"], float)


class TestDetectAIBatch:
    def test_batch_returns_list(self):
        texts = ["First text.", "Second text.", "Third text."]
        results = detect_ai_batch(texts, lang="en")
        assert isinstance(results, list)
        assert len(results) == 3

    def test_batch_each_is_dict(self):
        texts = ["Hello world.", "Another text."]
        results = detect_ai_batch(texts, lang="en")
        for r in results:
            assert "score" in r
            assert "verdict" in r

    def test_empty_batch(self):
        results = detect_ai_batch([], lang="en")
        assert results == []


# ── paraphrase ────────────────────────────────────────────────

class TestParaphrase:
    def test_returns_string(self):
        r = paraphrase("This is a simple sentence.", lang="en")
        assert isinstance(r, str)
        assert len(r) > 0

    def test_with_intensity(self):
        r = paraphrase("The quick brown fox jumps over the lazy dog.", lang="en", intensity=0.8)
        assert isinstance(r, str)

    def test_with_seed(self):
        r1 = paraphrase("Furthermore, it is important to note this.", lang="en", seed=42)
        r2 = paraphrase("Furthermore, it is important to note this.", lang="en", seed=42)
        assert r1 == r2

    def test_auto_lang(self):
        r = paraphrase("Данный текст является примером.", lang="auto")
        assert isinstance(r, str)


# ── analyze_tone ──────────────────────────────────────────────

class TestAnalyzeTone:
    def test_returns_dict(self):
        r = analyze_tone("This is a formal document.", lang="en")
        assert isinstance(r, dict)
        assert "primary_tone" in r
        assert "formality" in r
        assert "confidence" in r

    def test_formality_range(self):
        r = analyze_tone("Shall we proceed with the implementation?", lang="en")
        assert 0.0 <= r["formality"] <= 1.0

    def test_auto_lang(self):
        r = analyze_tone("Давайте обсудим этот вопрос.", lang="auto")
        assert isinstance(r["primary_tone"], str)


class TestAdjustTone:
    def test_returns_string(self):
        r = adjust_tone("This is some text.", target="casual", lang="en")
        assert isinstance(r, str)

    def test_formal_target(self):
        r = adjust_tone("Hey, this is cool stuff!", target="formal", lang="en")
        assert isinstance(r, str)

    def test_auto_lang(self):
        r = adjust_tone("Необходимо осуществить обработку.", target="casual", lang="auto")
        assert isinstance(r, str)


# ── detect_watermarks ────────────────────────────────────────

class TestDetectWatermarks:
    def test_clean_text(self):
        r = detect_watermarks("Clean text without watermarks.", lang="en")
        assert isinstance(r, dict)
        assert "has_watermarks" in r
        assert "watermark_types" in r

    def test_with_zero_width(self):
        text = "Text\u200bwith\u200bhidden\u200bchars"
        r = detect_watermarks(text, lang="en")
        assert r["has_watermarks"] is True

    def test_cleaned_text_field(self):
        text = "Water\u200bmark"
        r = detect_watermarks(text, lang="en")
        assert "cleaned_text" in r

    def test_auto_lang(self):
        r = detect_watermarks("Some text to check.", lang="auto")
        assert isinstance(r, dict)


class TestCleanWatermarks:
    def test_removes_zero_width(self):
        r = clean_watermarks("Te\u200bst\u200b text", lang="en")
        assert "\u200b" not in r

    def test_clean_text_unchanged(self):
        r = clean_watermarks("Normal text.", lang="en")
        assert "Normal" in r

    def test_auto_lang(self):
        r = clean_watermarks("Текст\u200bс\u200bводяными знаками.", lang="auto")
        assert isinstance(r, str)


# ── spin ──────────────────────────────────────────────────────

class TestSpin:
    def test_returns_string(self):
        r = spin("The system provides important data.", lang="en")
        assert isinstance(r, str)
        assert len(r) > 0

    def test_with_seed(self):
        r1 = spin("Important information here.", lang="en", seed=42)
        r2 = spin("Important information here.", lang="en", seed=42)
        assert r1 == r2

    def test_auto_lang(self):
        r = spin("Система предоставляет данные.", lang="auto")
        assert isinstance(r, str)


class TestSpinVariants:
    def test_returns_list(self):
        r = spin_variants("The system works well.", count=3, lang="en")
        assert isinstance(r, list)
        assert len(r) >= 1

    def test_variants_are_strings(self):
        r = spin_variants("Important data.", count=2, lang="en")
        for v in r:
            assert isinstance(v, str)

    def test_auto_lang(self):
        r = spin_variants("Текст для проверки.", count=2, lang="auto")
        assert isinstance(r, list)


# ── analyze_coherence ─────────────────────────────────────────

class TestAnalyzeCoherence:
    def test_returns_dict(self):
        text = "First paragraph.\n\nSecond paragraph."
        r = analyze_coherence(text, lang="en")
        assert isinstance(r, dict)
        assert "overall" in r
        assert "lexical_cohesion" in r
        assert "transition_score" in r
        assert "topic_consistency" in r

    def test_score_ranges(self):
        text = "Some text. Another sentence.\n\nNew paragraph here."
        r = analyze_coherence(text, lang="en")
        assert 0.0 <= r["overall"] <= 1.0

    def test_auto_lang(self):
        text = "Первый абзац.\n\nВторой абзац."
        r = analyze_coherence(text, lang="auto")
        assert isinstance(r, dict)


# ── full_readability ──────────────────────────────────────────

class TestFullReadability:
    def test_returns_dict(self):
        r = full_readability("This is a text with several sentences. It should work.", lang="en")
        assert isinstance(r, dict)

    def test_auto_lang(self):
        r = full_readability("Этот текст на русском для анализа.", lang="auto")
        assert isinstance(r, dict)


# ── humanize edge cases ──────────────────────────────────────

class TestHumanizeEdgeCases:
    def test_empty_string(self):
        r = humanize("")
        assert r.text == ""

    def test_whitespace_only(self):
        r = humanize("   ")
        assert r.text == "   "

    def test_none_text(self):
        # None is falsy, should return empty result
        r = humanize(None)
        assert r.text is None

    def test_auto_lang_en(self):
        r = humanize("This is an English text.", lang="auto")
        assert r.lang == "en"

    def test_auto_lang_ru(self):
        r = humanize("Это текст на русском языке.", lang="auto")
        assert r.lang == "ru"

    def test_with_seed(self):
        r1 = humanize("Text for processing.", lang="en", seed=42)
        r2 = humanize("Text for processing.", lang="en", seed=42)
        assert r1.text == r2.text

    def test_with_preserve(self):
        r = humanize("Check https://example.com link.", lang="en",
                      preserve={"urls": True, "brand_terms": ["Check"]})
        assert isinstance(r.text, str)

    def test_with_constraints(self):
        r = humanize("Important text here.", lang="en",
                      constraints={"max_change_ratio": 0.1, "keep_keywords": ["Important"]})
        assert isinstance(r.text, str)


# ── humanize_chunked ──────────────────────────────────────────

class TestHumanizeChunked:
    def test_small_text_uses_regular(self):
        r = humanize_chunked("Small text.", chunk_size=5000, lang="en")
        assert isinstance(r.text, str)

    def test_empty_text(self):
        r = humanize_chunked("", lang="en")
        assert r.text == ""

    def test_large_text(self):
        # Create a text larger than chunk_size
        large = ("This is a paragraph with several sentences. " * 10 + "\n\n") * 20
        r = humanize_chunked(large, chunk_size=500, lang="en")
        assert isinstance(r.text, str)
        assert len(r.text) > 0


# ── analyze ───────────────────────────────────────────────────

class TestAnalyzeWrapper:
    def test_empty_text(self):
        r = analyze("", lang="en")
        assert r.lang == "en"

    def test_whitespace_only(self):
        r = analyze("   ", lang="en")
        assert r.lang == "en"

    def test_auto_lang(self):
        r = analyze("This is some English text for analysis.", lang="auto")
        assert r.lang == "en"


# ── explain ───────────────────────────────────────────────────

class TestExplainWrapper:
    def test_basic_explain(self):
        result = humanize("Furthermore, it is important to note this fact.", lang="en")
        report = explain(result)
        assert isinstance(report, str)
        assert "TextHumanize" in report

    def test_no_changes(self):
        result = humanize("ok", lang="en")
        report = explain(result)
        assert "нет" in report.lower() or "TextHumanize" in report
