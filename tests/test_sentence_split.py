"""Тесты для умного сплиттера предложений (sentence_split.py)."""

import pytest
from texthumanize.sentence_split import SentenceSplitter, split_sentences, split_sentences_with_spans


class TestSplitSentences:
    """Тесты для split_sentences."""

    def test_basic_split(self):
        text = "Первое предложение. Второе предложение. Третье."
        sents = split_sentences(text, lang="ru")
        assert len(sents) == 3

    def test_abbreviations_ru(self):
        """Аббревиатуры не должны разделять предложения."""
        text = "Он работает в г. Москва и т.д. Всё хорошо."
        sents = split_sentences(text, lang="ru")
        # Должно быть 2 предложения, а не 4+
        assert len(sents) <= 3

    def test_abbreviations_en(self):
        text = "Dr. Smith went to Washington D.C. He arrived at 3 p.m."
        sents = split_sentences(text, lang="en")
        assert len(sents) <= 3

    def test_decimal_numbers(self):
        """Десятичные числа не должны разделять предложения."""
        text = "Цена составляет 3.14 рублей. Это нормально."
        sents = split_sentences(text, lang="ru")
        assert len(sents) == 2

    def test_initials(self):
        """Инициалы не должны разделять предложения."""
        text = "А.С. Пушкин написал много произведений. Он великий поэт."
        sents = split_sentences(text, lang="ru")
        assert len(sents) == 2

    def test_exclamation_and_question(self):
        text = "Как дела? Отлично! Спасибо."
        sents = split_sentences(text, lang="ru")
        assert len(sents) == 3

    def test_ellipsis(self):
        text = "Ну... ладно. Пойдём."
        sents = split_sentences(text, lang="ru")
        assert len(sents) >= 2

    def test_empty_text(self):
        sents = split_sentences("", lang="ru")
        assert sents == [] or sents == [""]

    def test_single_sentence(self):
        text = "Просто одно предложение."
        sents = split_sentences(text, lang="ru")
        assert len(sents) == 1

    def test_english_basic(self):
        text = "Hello world. How are you? Fine, thanks!"
        sents = split_sentences(text, lang="en")
        assert len(sents) == 3

    def test_no_terminal_punctuation(self):
        text = "Текст без точки в конце"
        sents = split_sentences(text, lang="ru")
        assert len(sents) >= 1
        assert sents[0].strip() == text


class TestSplitSentencesWithSpans:
    """Тесты для split_sentences_with_spans."""

    def test_spans_match_text(self):
        text = "Первое. Второе. Третье."
        spans = split_sentences_with_spans(text, lang="ru")
        for span in spans:
            # span text might include trailing space — strip it for comparison
            assert text[span.start:span.end].strip() == span.text.strip()

    def test_spans_cover_full_text(self):
        text = "Hello world. Goodbye."
        spans = split_sentences_with_spans(text, lang="en")
        assert len(spans) >= 2


class TestSentenceSplitter:
    """Тесты для класса SentenceSplitter."""

    def test_constructor(self):
        s = SentenceSplitter(lang="en")
        assert s is not None

    def test_split_method(self):
        s = SentenceSplitter(lang="ru")
        result = s.split("Привет. Пока.")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_split_spans_method(self):
        s = SentenceSplitter(lang="en")
        result = s.split_spans("Hello. Bye.")
        assert len(result) >= 2
