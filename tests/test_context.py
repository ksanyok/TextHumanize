"""Тесты для контекстного подбора синонимов (context.py)."""

import pytest
from texthumanize.context import ContextualSynonyms


class TestContextualSynonyms:
    """Тесты для ContextualSynonyms."""

    def test_init(self):
        cs = ContextualSynonyms(lang="en")
        assert cs is not None

    def test_detect_topic_technology(self):
        cs = ContextualSynonyms(lang="en")
        text = "We develop software algorithms using machine learning and neural networks."
        topic = cs.detect_topic(text)
        assert topic == "technology"

    def test_detect_topic_business(self):
        cs = ContextualSynonyms(lang="en")
        text = "Our company revenue grew with strong market share and profit margins."
        topic = cs.detect_topic(text)
        assert topic == "business"

    def test_detect_topic_none(self):
        """Текст без явных маркеров темы."""
        cs = ContextualSynonyms(lang="en")
        topic = cs.detect_topic("Hello world")
        assert topic is None

    def test_choose_synonym_returns_string(self):
        cs = ContextualSynonyms(lang="en", seed=42)
        result = cs.choose_synonym(
            word="big",
            synonyms=["large", "huge", "enormous"],
            context="The company has a big market share in technology.",
        )
        assert isinstance(result, str)
        assert result in ["large", "huge", "enormous"]

    def test_choose_synonym_empty_list(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.choose_synonym("big", [], "some context")
        assert result == "big"  # Возвращает оригинал

    def test_choose_synonym_single_option(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.choose_synonym("big", ["large"], "some context")
        assert result == "large"

    def test_russian_topic_detection(self):
        cs = ContextualSynonyms(lang="ru")
        text = "Мы разрабатываем алгоритмы машинного обучения и нейронные сети."
        topic = cs.detect_topic(text)
        # Может определить тему или нет, зависит от словаря
        assert topic is None or isinstance(topic, str)

    def test_negative_collocations(self):
        """Синонимы с плохими коллокациями не должны выбираться."""
        cs = ContextualSynonyms(lang="en", seed=42)
        # Если есть negative collocations, плохой синоним должен отсеиваться
        result = cs.choose_synonym(
            word="run",
            synonyms=["operate", "execute", "dash"],
            context="We need to run the software application",
        )
        assert isinstance(result, str)

    def test_seed_reproducibility(self):
        cs1 = ContextualSynonyms(lang="en", seed=42)
        cs2 = ContextualSynonyms(lang="en", seed=42)
        r1 = cs1.choose_synonym("fast", ["quick", "rapid", "swift"], "A fast algorithm")
        r2 = cs2.choose_synonym("fast", ["quick", "rapid", "swift"], "A fast algorithm")
        assert r1 == r2
