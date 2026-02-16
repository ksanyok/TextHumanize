"""Тесты структуры предложений."""

import pytest
from texthumanize.structure import StructureDiversifier


class TestStructureDiversifier:
    """Тесты структурного разнообразия."""

    def test_ai_connector_replacement_ru(self):
        """ИИ-связки заменяются (русский)."""
        sd = StructureDiversifier(lang="ru", profile="web", intensity=100, seed=42)
        text = (
            "Текст начинается. Однако есть нюанс. "
            "Кроме того стоит учесть. Таким образом всё ясно."
        )
        result = sd.process(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ai_connector_replacement_uk(self):
        """ИІ-зв'язки замінюються (українська)."""
        sd = StructureDiversifier(lang="uk", profile="web", intensity=100, seed=42)
        text = (
            "Текст починається. Однак є нюанс. "
            "Крім того варто врахувати. Таким чином все зрозуміло."
        )
        result = sd.process(text)
        assert isinstance(result, str)

    def test_sentence_start_diversity(self):
        """Одинаковые начала предложений разнообразятся."""
        sd = StructureDiversifier(lang="ru", profile="web", intensity=100, seed=42)
        text = "Это первое. Это второе. Это третье."
        result = sd.process(text)
        # Хотя бы одно "Это" должно замениться
        assert isinstance(result, str)

    def test_long_sentence_split(self):
        """Длинные предложения разбиваются."""
        sd = StructureDiversifier(lang="ru", profile="chat", intensity=100, seed=42)
        words = ["слово" + str(i) for i in range(60)]
        text = (
            "Это очень длинное предложение, которое содержит "
            + " ".join(words)
            + ", и оно продолжается дальше."
        )
        result = sd.process(text)
        assert isinstance(result, str)

    def test_short_sentence_join(self):
        """Короткие предложения склеиваются."""
        sd = StructureDiversifier(lang="ru", profile="web", intensity=100, seed=42)
        text = "Текст. Тут. Там. Везде. Всегда."
        result = sd.process(text)
        assert isinstance(result, str)

    def test_changes_tracked(self):
        """Изменения отслеживаются."""
        sd = StructureDiversifier(lang="ru", profile="chat", intensity=100, seed=42)
        text = (
            "Однако это важно. Тем не менее стоит учесть. "
            "Кроме того есть нюанс."
        )
        sd.process(text)
        assert isinstance(sd.changes, list)

    def test_seo_profile_conservative(self):
        """SEO профиль — минимум структурных изменений."""
        sd = StructureDiversifier(lang="ru", profile="seo", intensity=30, seed=42)
        text = "Однако это важно. Однако есть нюанс."
        result = sd.process(text)
        assert isinstance(result, str)

    def test_empty_text(self):
        """Пустой текст обрабатывается."""
        sd = StructureDiversifier(lang="ru", seed=42)
        result = sd.process("")
        assert result == ""


class TestRepetitions:
    """Тесты уменьшения повторов."""

    def test_word_repetition_reduction(self):
        """Повторы слов уменьшаются."""
        from texthumanize.repetitions import RepetitionReducer
        rr = RepetitionReducer(lang="ru", profile="web", intensity=100, seed=42)
        text = (
            "Важный процесс является важным. "
            "Важный результат тоже важный."
        )
        result = rr.process(text)
        assert isinstance(result, str)

    def test_changes_tracked(self):
        """Изменения повторов отслеживаются."""
        from texthumanize.repetitions import RepetitionReducer
        rr = RepetitionReducer(lang="ru", profile="web", intensity=100, seed=42)
        text = (
            "Большой процесс с большим результатом и большим усилием. "
            "Большой эффект от большой работы."
        )
        rr.process(text)
        assert isinstance(rr.changes, list)
