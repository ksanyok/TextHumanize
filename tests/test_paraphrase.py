"""Тесты для перефразирования (paraphrase.py)."""

from texthumanize.paraphrase import Paraphraser, paraphrase_text

SAMPLE_EN = (
    "The company has developed a new approach to solving complex problems. "
    "This method allows us to achieve significant improvements in performance. "
    "Furthermore, the results demonstrate that our strategy is effective."
)

SAMPLE_RU = (
    "Компания разработала новый подход к решению сложных задач. "
    "Данный метод позволяет достичь значительных улучшений в производительности. "
    "Кроме того, результаты демонстрируют эффективность нашей стратегии."
)


class TestParaphraser:
    """Тесты для Paraphraser."""

    def test_paraphrase_returns_result(self):
        from texthumanize.paraphrase import ParaphraseResult
        p = Paraphraser(lang="en", seed=42, intensity=0.5)
        result = p.paraphrase(SAMPLE_EN)
        assert isinstance(result, ParaphraseResult)
        assert isinstance(result.paraphrased, str)
        assert len(result.paraphrased) > 0

    def test_paraphrase_sentence(self):
        p = Paraphraser(lang="en", seed=42)
        sent = "The research demonstrates significant improvements in accuracy."
        result, change_type = p.paraphrase_sentence(sent)
        assert isinstance(result, str)
        assert isinstance(change_type, str)
        assert len(result) > 0

    def test_seed_reproducibility(self):
        p1 = Paraphraser(lang="en", seed=42, intensity=0.8)
        p2 = Paraphraser(lang="en", seed=42, intensity=0.8)
        r1 = p1.paraphrase(SAMPLE_EN)
        r2 = p2.paraphrase(SAMPLE_EN)
        assert r1.paraphrased == r2.paraphrased

    def test_intensity_zero(self):
        """При intensity=0 текст не должен меняться."""
        p = Paraphraser(lang="en", seed=42, intensity=0.0)
        result = p.paraphrase(SAMPLE_EN)
        assert result.paraphrased == SAMPLE_EN

    def test_empty_text(self):
        p = Paraphraser(lang="en", intensity=0.5)
        result = p.paraphrase("")
        assert result.paraphrased == ""

    def test_russian(self):
        p = Paraphraser(lang="ru", seed=42, intensity=0.5)
        result = p.paraphrase(SAMPLE_RU)
        assert isinstance(result.paraphrased, str)
        assert len(result.paraphrased) > 0

    def test_single_sentence(self):
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        result = p.paraphrase("This is a simple test sentence.")
        assert isinstance(result.paraphrased, str)


class TestModuleFunction:
    """Тесты для module-level paraphrase_text."""

    def test_paraphrase_text(self):
        result = paraphrase_text(SAMPLE_EN, lang="en", seed=42)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_paraphrase_text_with_intensity(self):
        result = paraphrase_text(SAMPLE_EN, lang="en", intensity=0.8, seed=42)
        assert isinstance(result, str)
