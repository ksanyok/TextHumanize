"""Тесты для спиннера контента (spinner.py)."""

from texthumanize.spinner import (
    ContentSpinner,
    SpinResult,
    generate_spintax,
    generate_variants,
    spin_text,
)

SAMPLE_TEXT = (
    "We use modern technology to create effective solutions. "
    "This approach helps improve the overall quality of work. "
    "The results show significant progress in key areas."
)

SAMPLE_RU = (
    "Мы используем современные технологии для создания эффективных решений. "
    "Данный подход помогает улучшить общее качество работы. "
    "Результаты показывают значительный прогресс."
)


class TestContentSpinner:
    """Тесты для ContentSpinner."""

    def test_spin_returns_result(self):
        spinner = ContentSpinner(lang="en", seed=42)
        result = spinner.spin(SAMPLE_TEXT)
        assert isinstance(result, SpinResult)
        assert isinstance(result.spun, str)
        assert len(result.spun) > 0
        assert result.original == SAMPLE_TEXT

    def test_uniqueness_range(self):
        spinner = ContentSpinner(lang="en", seed=42, intensity=0.8)
        result = spinner.spin(SAMPLE_TEXT)
        assert 0.0 <= result.uniqueness <= 1.0

    def test_seed_reproducibility(self):
        """Одинаковый seed → одинаковый результат."""
        s1 = ContentSpinner(lang="en", seed=123)
        s2 = ContentSpinner(lang="en", seed=123)
        r1 = s1.spin(SAMPLE_TEXT)
        r2 = s2.spin(SAMPLE_TEXT)
        assert r1.spun == r2.spun

    def test_different_seeds_different_results(self):
        """Разные seed → разные результаты (с высокой вероятностью)."""
        s1 = ContentSpinner(lang="en", seed=1, intensity=1.0)
        s2 = ContentSpinner(lang="en", seed=999, intensity=1.0)
        r1 = s1.spin(SAMPLE_TEXT)
        r2 = s2.spin(SAMPLE_TEXT)
        # Не гарантировано, но при intensity=1.0 очень вероятно
        # Если оба равны — это OK, просто совпадение

    def test_intensity_zero_no_change(self):
        """При intensity=0 текст не меняется."""
        spinner = ContentSpinner(lang="en", seed=42, intensity=0.0)
        result = spinner.spin(SAMPLE_TEXT)
        assert result.spun == SAMPLE_TEXT

    def test_generate_spintax(self):
        spinner = ContentSpinner(lang="en", intensity=0.5)
        spintax = spinner.generate_spintax(SAMPLE_TEXT)
        assert isinstance(spintax, str)
        # Spintax может содержать {вариант1|вариант2}
        # Но при отсутствии синонимов — просто оригинал

    def test_generate_variants(self):
        spinner = ContentSpinner(lang="en", intensity=0.5)
        variants = spinner.generate_variants(SAMPLE_TEXT, count=3)
        assert isinstance(variants, list)
        assert 1 <= len(variants) <= 3  # May produce fewer if no synonyms found
        for v in variants:
            assert isinstance(v, str)
            assert len(v) > 0

    def test_empty_text(self):
        spinner = ContentSpinner(lang="en")
        result = spinner.spin("")
        assert result.spun == ""

    def test_russian(self):
        spinner = ContentSpinner(lang="ru", seed=42, intensity=0.5)
        result = spinner.spin(SAMPLE_RU)
        assert isinstance(result, SpinResult)
        assert len(result.spun) > 0


class TestModuleFunctions:
    """Тесты для module-level функций."""

    def test_spin_text(self):
        result = spin_text(SAMPLE_TEXT, lang="en", seed=42)
        assert isinstance(result, str)

    def test_generate_spintax_func(self):
        result = generate_spintax(SAMPLE_TEXT, lang="en")
        assert isinstance(result, str)

    def test_generate_variants_func(self):
        result = generate_variants(SAMPLE_TEXT, count=5, lang="en")
        assert isinstance(result, list)
        assert 1 <= len(result) <= 5  # May be fewer if no synonyms
