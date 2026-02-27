"""Тесты для морфологического движка (morphology.py)."""

from texthumanize.morphology import MorphologyEngine, get_morphology


class TestMorphologyRU:
    """Тесты для русского языка."""

    def setup_method(self):
        self.morph = get_morphology("ru")

    def test_lemmatize_adjective(self):
        """Лемматизация прилагательных."""
        assert self.morph.lemmatize("красивого") == "красивый"
        assert self.morph.lemmatize("красивая") == "красивый"
        assert self.morph.lemmatize("красивые") == "красивый"

    def test_lemmatize_noun(self):
        """Лемматизация существительных — хотя бы не ломается."""
        result = self.morph.lemmatize("домов")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lemmatize_verb(self):
        """Лемматизация глаголов."""
        result = self.morph.lemmatize("делает")
        assert isinstance(result, str)

    def test_generate_forms(self):
        """Генерация форм прилагательного."""
        forms = self.morph.generate_forms("красивый")
        assert isinstance(forms, list)
        assert len(forms) > 1
        assert "красивый" in forms

    def test_detect_pos_adjective(self):
        """Определение части речи прилагательного."""
        pos = self.morph.detect_pos("красивый")
        assert pos == "adj"

    def test_is_same_lemma(self):
        """Проверка общей леммы."""
        assert self.morph.is_same_lemma("красивого", "красивая")

    def test_find_synonym_form(self):
        """Нахождение формы синонима, согласованной с оригиналом."""
        result = self.morph.find_synonym_form("красивого", "прекрасный")
        assert isinstance(result, str)
        # Должен вернуть косвенную форму
        assert result != ""

    def test_lemmatize_unknown_word(self):
        """Неизвестное слово возвращается как есть."""
        result = self.morph.lemmatize("абвгдеёж")
        assert isinstance(result, str)


class TestMorphologyEN:
    """Тесты для английского языка."""

    def setup_method(self):
        self.morph = get_morphology("en")

    def test_lemmatize_verb_ed(self):
        assert self.morph.lemmatize("played") == "play"

    def test_lemmatize_verb_ing(self):
        assert self.morph.lemmatize("playing") == "play"

    def test_lemmatize_verb_s(self):
        assert self.morph.lemmatize("plays") == "play"

    def test_lemmatize_irregular_verb(self):
        result = self.morph.lemmatize("went")
        assert result == "go"

    def test_lemmatize_noun_plural(self):
        result = self.morph.lemmatize("houses")
        assert result == "house"

    def test_detect_pos(self):
        pos = self.morph.detect_pos("quickly")
        assert pos == "adv"

    def test_generate_forms_verb(self):
        forms = self.morph.generate_forms("play")
        assert isinstance(forms, list)
        assert len(forms) > 0


class TestMorphologyUK:
    """Тесты для украинского языка."""

    def setup_method(self):
        self.morph = get_morphology("uk")

    def test_lemmatize_adjective(self):
        result = self.morph.lemmatize("гарного")
        assert isinstance(result, str)

    def test_detect_pos(self):
        pos = self.morph.detect_pos("гарний")
        assert pos == "adj"


class TestGetMorphology:
    """Тесты для фабричной функции."""

    def test_singleton(self):
        """get_morphology должна кэшировать экземпляры."""
        m1 = get_morphology("ru")
        m2 = get_morphology("ru")
        assert m1 is m2

    def test_different_langs(self):
        m_ru = get_morphology("ru")
        m_en = get_morphology("en")
        assert m_ru is not m_en

    def test_unknown_lang(self):
        """Неизвестный язык — не должен падать."""
        m = get_morphology("xx")
        assert isinstance(m, MorphologyEngine)
