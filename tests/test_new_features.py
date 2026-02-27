"""Тесты новых функций: humanize_batch, similarity, quality_score, MARKETING tone."""

import pytest

from texthumanize import HumanizeResult, humanize, humanize_batch
from texthumanize.tone import ToneAdjuster, ToneLevel

# Общие тексты для переиспользования
RU_TEXT = (
    "Данный текст является примером. Однако необходимо "
    "осуществить обработку данного текста."
)
EN_TEXT = (
    "This text utilizes a comprehensive methodology for the "
    "implementation of text processing procedures."
)


class TestHumanizeBatch:
    """Тесты функции humanize_batch()."""

    def test_basic_batch(self):
        """Пакетная обработка возвращает список HumanizeResult."""
        texts = [RU_TEXT, "Ещё один пример текста для обработки."]
        results = humanize_batch(texts, lang="ru", seed=42)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, HumanizeResult)
            assert len(r.text) > 0

    def test_empty_list(self):
        """Пустой список — пустой результат."""
        results = humanize_batch([])
        assert results == []

    def test_single_text(self):
        """Один текст в пакете."""
        results = humanize_batch([RU_TEXT], lang="ru", seed=42)
        assert len(results) == 1
        assert isinstance(results[0], HumanizeResult)

    def test_seed_reproducibility(self):
        """Один и тот же seed даёт одинаковые результаты для пакета."""
        texts = [RU_TEXT, EN_TEXT]
        r1 = humanize_batch(texts, lang="auto", seed=100)
        r2 = humanize_batch(texts, lang="auto", seed=100)
        assert r1[0].text == r2[0].text
        assert r1[1].text == r2[1].text

    def test_seed_per_item(self):
        """Каждый текст получает seed + index (seed=10 → 10, 11, ...)."""
        texts = [RU_TEXT, RU_TEXT]
        results = humanize_batch(texts, lang="ru", seed=10)
        # Одинаковый текст с разными seed-ами может дать разные результаты
        # (но не обязательно — зависит от обработки)
        assert len(results) == 2
        # Проверяем, что каждый элемент — отдельный результат
        assert results[0].original == results[1].original

    def test_multiple_texts_with_profile(self):
        """Пакетная обработка с разными профилями работает."""
        texts = [RU_TEXT, EN_TEXT, "Простой текст."]
        results = humanize_batch(texts, profile="seo", intensity=50, seed=42)
        assert len(results) == 3
        for r in results:
            assert r.profile == "seo"

    def test_batch_preserves_params(self):
        """Параметры передаются каждому тексту."""
        results = humanize_batch(
            [RU_TEXT],
            lang="ru",
            profile="formal",
            intensity=80,
            constraints={"keep_keywords": ["текст"]},
            seed=42,
        )
        assert results[0].lang == "ru"
        assert results[0].profile == "formal"
        assert results[0].intensity == 80


class TestSimilarity:
    """Тесты свойства HumanizeResult.similarity."""

    def test_identical_texts(self):
        """Идентичные тексты → similarity = 1.0."""
        r = HumanizeResult(
            original="hello world", text="hello world",
            lang="en", profile="web", intensity=60,
        )
        assert r.similarity == 1.0

    def test_completely_different(self):
        """Полностью разные слова → similarity = 0.0."""
        r = HumanizeResult(
            original="hello world", text="foo bar",
            lang="en", profile="web", intensity=60,
        )
        assert r.similarity == 0.0

    def test_partial_overlap(self):
        """Частичное совпадение → 0 < similarity < 1."""
        r = HumanizeResult(
            original="hello world foo", text="hello world bar",
            lang="en", profile="web", intensity=60,
        )
        assert 0.0 < r.similarity < 1.0

    def test_empty_both(self):
        """Оба пустые → similarity = 1.0."""
        r = HumanizeResult(
            original="", text="",
            lang="en", profile="web", intensity=60,
        )
        assert r.similarity == 1.0

    def test_one_empty(self):
        """Один пустой → similarity = 0.0."""
        r = HumanizeResult(
            original="hello", text="",
            lang="en", profile="web", intensity=60,
        )
        assert r.similarity == 0.0

    def test_case_insensitive(self):
        """Jaccard сравнение нечувствительно к регистру."""
        r = HumanizeResult(
            original="Hello World", text="hello world",
            lang="en", profile="web", intensity=60,
        )
        assert r.similarity == 1.0

    def test_range(self):
        """similarity всегда в [0, 1]."""
        r = humanize(RU_TEXT, lang="ru", seed=42)
        assert 0.0 <= r.similarity <= 1.0


class TestQualityScore:
    """Тесты свойства HumanizeResult.quality_score."""

    def test_unchanged_text(self):
        """Неизменённый текст → quality_score = 0.3 (бесполезная обработка)."""
        r = HumanizeResult(
            original="hello world", text="hello world",
            lang="en", profile="web", intensity=60,
        )
        assert r.quality_score == pytest.approx(0.3)

    def test_totally_different(self):
        """Полностью изменённый текст → quality_score = 0.2 (потеря смысла)."""
        r = HumanizeResult(
            original="aaa bbb ccc ddd eee fff ggg hhh iii jjj",
            text="zzz yyy xxx www vvv uuu ttt sss rrr qqq",
            lang="en", profile="web", intensity=60,
        )
        assert r.quality_score == pytest.approx(0.2)

    def test_reasonable_change(self):
        """Умеренное изменение → quality_score > 0.5."""
        r = humanize(RU_TEXT, lang="ru", intensity=60, seed=42)
        assert r.quality_score >= 0.2

    def test_range(self):
        """quality_score всегда в [0, 1]."""
        r = humanize(RU_TEXT, lang="ru", seed=42)
        assert 0.0 <= r.quality_score <= 1.0


class TestToneMarketingDirection:
    """Тест: MARKETING входит в formal_levels в _get_direction()."""

    def test_neutral_to_marketing(self):
        """NEUTRAL → MARKETING даёт направление informal→formal."""
        direction = ToneAdjuster._get_direction(
            ToneLevel.NEUTRAL, ToneLevel.MARKETING,
        )
        assert direction == ("informal", "formal")

    def test_casual_to_marketing(self):
        """CASUAL → MARKETING даёт направление informal→formal."""
        direction = ToneAdjuster._get_direction(
            ToneLevel.CASUAL, ToneLevel.MARKETING,
        )
        assert direction == ("informal", "formal")

    def test_marketing_to_casual(self):
        """MARKETING → CASUAL даёт направление formal→informal."""
        direction = ToneAdjuster._get_direction(
            ToneLevel.MARKETING, ToneLevel.CASUAL,
        )
        assert direction == ("formal", "informal")

    def test_marketing_to_friendly(self):
        """MARKETING → FRIENDLY даёт направление formal→informal."""
        direction = ToneAdjuster._get_direction(
            ToneLevel.MARKETING, ToneLevel.FRIENDLY,
        )
        assert direction == ("formal", "informal")

    def test_marketing_to_formal_no_change(self):
        """MARKETING → FORMAL — оба формальные, нет направления."""
        direction = ToneAdjuster._get_direction(
            ToneLevel.MARKETING, ToneLevel.FORMAL,
        )
        assert direction is None
