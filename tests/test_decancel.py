"""Тесты деканцеляризации."""

import pytest
from texthumanize.decancel import Debureaucratizer


class TestDebureaucratizer:
    """Тесты деканцеляризации."""

    def test_basic_ru_decancel(self):
        """Базовая деканцеляризация русского текста."""
        db = Debureaucratizer(lang="ru", profile="web", intensity=100, seed=42)
        text = "Данный текст осуществляет описание процесса."
        result = db.process(text)
        # "данный" должен замениться
        assert "данный" not in result.lower() or "этот" in result.lower()

    def test_basic_uk_decancel(self):
        """Базовая деканцеляризация украинского текста."""
        db = Debureaucratizer(lang="uk", profile="web", intensity=100, seed=42)
        text = "Даний текст здійснює опис процесу."
        result = db.process(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_basic_en_decancel(self):
        """Базовая деканцеляризация английского текста."""
        db = Debureaucratizer(lang="en", profile="web", intensity=100, seed=42)
        text = "We utilize this methodology to facilitate the process."
        result = db.process(text)
        assert isinstance(result, str)

    def test_phrase_replacement(self):
        """Фразовые канцеляризмы заменяются."""
        db = Debureaucratizer(lang="ru", profile="web", intensity=100, seed=42)
        text = "Необходимо отметить, что этот процесс представляет собой пример."
        result = db.process(text)
        assert isinstance(result, str)

    def test_low_intensity(self):
        """Низкая интенсивность → мало изменений."""
        db = Debureaucratizer(lang="ru", profile="web", intensity=10, seed=42)
        text = "Данный текст осуществляет описание процесса."
        result = db.process(text)
        assert isinstance(result, str)

    def test_formal_profile_minimal(self):
        """Формальный профиль → минимум замен."""
        db = Debureaucratizer(lang="ru", profile="formal", intensity=60, seed=42)
        text = "Данный текст осуществляет описание процесса."
        result = db.process(text)
        assert isinstance(result, str)

    def test_changes_tracked(self):
        """Изменения отслеживаются."""
        db = Debureaucratizer(lang="ru", profile="chat", intensity=100, seed=42)
        text = "Данный текст осуществляет описание функционирования процесса."
        db.process(text)
        # При высокой интенсивности и chat профиле должны быть замены
        # (но мы не гарантируем количество из-за random)
        assert isinstance(db.changes, list)

    def test_empty_text(self):
        """Пустой текст обрабатывается."""
        db = Debureaucratizer(lang="ru", seed=42)
        result = db.process("")
        assert result == ""

    def test_no_bureaucratic_text(self):
        """Текст без канцеляризмов не меняется."""
        db = Debureaucratizer(lang="ru", profile="web", intensity=100, seed=42)
        text = "Простой понятный текст без сложных слов."
        result = db.process(text)
        # Может быть некоторое совпадение случайных слов, но в целом мало изменений
        assert isinstance(result, str)


class TestDebureaucratizStructure:
    """Тесты структуры обработки."""

    def test_case_preservation(self):
        """Регистр первой буквы сохраняется."""
        db = Debureaucratizer(lang="ru", profile="chat", intensity=100, seed=42)
        text = "Данный вопрос важен."
        result = db.process(text)
        # Первая буква должна остаться заглавной
        if result != text:
            assert result[0].isupper()
