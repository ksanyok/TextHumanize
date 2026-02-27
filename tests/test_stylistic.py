"""Тесты стилистического отпечатка (P3.2)."""

from __future__ import annotations

import pytest

from texthumanize.stylistic import StylisticAnalyzer, StylisticFingerprint

# ───────────────────────── Sample texts ─────────────────────

_SHORT_EN = (
    "The cat sat on the mat. It was a sunny day. "
    "Birds were singing in the trees, and children played in the park. "
    "Everything seemed peaceful and calm. "
    "However, dark clouds gathered on the horizon. "
    "Rain was coming soon. The old man sighed."
)

_FORMAL_EN = (
    "The implementation of advanced algorithms necessitates careful "
    "consideration of computational complexity. Furthermore, the "
    "integration of multiple subsystems requires robust interfaces. "
    "Consequently, a systematic approach to software architecture "
    "becomes paramount. It is essential to evaluate performance "
    "metrics comprehensively. The proposed methodology adheres to "
    "established best practices in the field. Moreover, empirical "
    "validation confirms the efficacy of this framework."
)

_CASUAL_EN = (
    "So I went to the store. Got some milk, bread, the usual stuff. "
    "Then I ran into my old friend Mike! We hadn't talked in ages. "
    "He told me about his new job — pretty cool actually. "
    "We decided to grab coffee. Best decision ever. "
    "Turns out he lives nearby now. Small world, right?"
)

_LONG_RU = (
    "Искусственный интеллект стремительно развивается. Нейронные сети "
    "обрабатывают огромные массивы данных. Машинное обучение позволяет "
    "решать сложные задачи автоматически. Однако важно понимать "
    "ограничения этих технологий. Они не заменяют человеческий разум. "
    "Этические вопросы требуют внимательного рассмотрения. Общество "
    "должно контролировать развитие ИИ. Безопасность остаётся "
    "приоритетом номер один."
)


# ──────────────────── StylisticAnalyzer tests ───────────────

class TestStylisticAnalyzer:
    """Tests for StylisticAnalyzer.extract()."""

    def test_extract_basic(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract(_SHORT_EN)
        assert fp.sentence_length_mean > 0
        assert fp.sentence_length_median > 0
        assert fp.sentence_length_std >= 0
        assert fp.commas_per_k >= 0
        assert fp.avg_word_length > 0
        assert 0 <= fp.vocabulary_richness <= 1.0

    def test_extract_empty_text(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract("")
        assert fp.sentence_length_mean == 0.0
        assert fp.avg_word_length == 0.0

    def test_extract_short_text(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract("Short.")
        # < 100 chars => empty fingerprint
        assert fp.sentence_length_mean == 0.0

    def test_formal_vs_casual_style(self):
        sa = StylisticAnalyzer(lang="en")
        formal_fp = sa.extract(_FORMAL_EN)
        casual_fp = sa.extract(_CASUAL_EN)

        # Formal text has longer sentences
        assert formal_fp.sentence_length_mean > casual_fp.sentence_length_mean
        # Formal text has longer words on average
        assert formal_fp.avg_word_length > casual_fp.avg_word_length

    def test_russian_text(self):
        sa = StylisticAnalyzer(lang="ru")
        fp = sa.extract(_LONG_RU)
        assert fp.sentence_length_mean > 0
        assert fp.avg_paragraph_length > 0

    def test_punctuation_detection(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract(_FORMAL_EN)
        # Formal text should have commas
        assert fp.commas_per_k > 0

    def test_question_detection(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract(_CASUAL_EN)
        # Casual text has questions
        assert fp.question_ratio > 0

    def test_exclamation_detection(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract(_CASUAL_EN)
        # Casual text has exclamations
        assert fp.exclamation_ratio > 0

    def test_connector_start(self):
        sa = StylisticAnalyzer(lang="en")
        fp = sa.extract(_FORMAL_EN)
        # Formal text starts sentences with connectors
        assert fp.connector_start_ratio > 0


# ──────────────────── StylisticFingerprint tests ────────────

class TestStylisticFingerprint:
    """Tests for StylisticFingerprint methods."""

    def test_similarity_identical(self):
        sa = StylisticAnalyzer(lang="en")
        fp1 = sa.extract(_SHORT_EN)
        fp2 = sa.extract(_SHORT_EN)
        sim = fp1.similarity(fp2)
        assert sim > 0.99  # identical text => near-perfect similarity

    def test_similarity_different_styles(self):
        sa = StylisticAnalyzer(lang="en")
        fp_formal = sa.extract(_FORMAL_EN)
        fp_casual = sa.extract(_CASUAL_EN)
        sim = fp_formal.similarity(fp_casual)
        # Different styles should be less similar
        assert sim < 0.95

    def test_similarity_range(self):
        fp1 = StylisticFingerprint(
            sentence_length_mean=15.0,
            sentence_length_std=5.0,
            commas_per_k=20.0,
        )
        fp2 = StylisticFingerprint(
            sentence_length_mean=15.0,
            sentence_length_std=5.0,
            commas_per_k=20.0,
        )
        assert fp1.similarity(fp2) > 0.99

    def test_to_vector(self):
        fp = StylisticFingerprint(
            sentence_length_mean=15.0,
            sentence_length_std=5.0,
        )
        vec = fp._to_vector()
        assert len(vec) == 15
        assert all(isinstance(v, float) for v in vec)

    def test_empty_fingerprint_similarity(self):
        fp1 = StylisticFingerprint()
        fp2 = StylisticFingerprint()
        # Both empty → zero vectors
        sim = fp1.similarity(fp2)
        assert sim == 0.0  # norm is 0


# ──────────────────── Pipeline integration tests ────────────

class TestStylisticPipelineIntegration:
    """Tests for target_style in pipeline."""

    def test_target_style_in_options(self):
        from texthumanize.utils import HumanizeOptions
        opts = HumanizeOptions(target_style=None)
        assert opts.target_style is None

    def test_target_style_with_fingerprint(self):
        from texthumanize.utils import HumanizeOptions
        fp = StylisticFingerprint(sentence_length_mean=12.0)
        opts = HumanizeOptions(target_style=fp)
        assert opts.target_style is fp

    def test_pipeline_with_target_style(self):
        from texthumanize import StylisticAnalyzer, humanize

        # Extract a target style from casual text
        sa = StylisticAnalyzer(lang="en")
        target = sa.extract(_CASUAL_EN)

        result = humanize(
            _FORMAL_EN,
            lang="en",
            profile="web",
            intensity=50,
            target_style=target,
        )

        assert result.text != ""
        # Metrics should include style info
        assert "style_similarity_before" in result.metrics_before

    def test_pipeline_without_target_style(self):
        from texthumanize import humanize

        result = humanize(
            "This is a simple test. It should work fine.",
            lang="en",
            profile="web",
            intensity=30,
        )
        # No style_similarity when no target
        assert "style_similarity_before" not in result.metrics_before


# ──────────────────── Cross-language tests ──────────────────

class TestStylisticMultilang:
    """Test stylistic fingerprint across languages."""

    @pytest.mark.parametrize("lang", ["en", "ru", "uk", "de", "fr", "es"])
    def test_extract_lang(self, lang):
        sa = StylisticAnalyzer(lang=lang)
        text = _LONG_RU if lang in ("ru", "uk") else _SHORT_EN
        fp = sa.extract(text)
        assert fp.sentence_length_mean > 0

    def test_different_languages_different_fingerprints(self):
        sa_en = StylisticAnalyzer(lang="en")
        sa_ru = StylisticAnalyzer(lang="ru")
        fp_en = sa_en.extract(_SHORT_EN)
        fp_ru = sa_ru.extract(_LONG_RU)
        # Different languages produce different fingerprints
        assert fp_en.sentence_length_mean != fp_ru.sentence_length_mean
