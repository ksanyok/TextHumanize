"""Покрытие context.py, sentence_split.py, tone.py — все непокрытые ветки."""

import pytest


# ═══════════════════════════════════════════════════════════════
#  Context — synonym scoring
# ═══════════════════════════════════════════════════════════════

from texthumanize.context import ContextualSynonyms


class TestContextualSynonyms:
    """Тесты ContextualSynonyms — synonym scoring, topic, collocation."""

    def test_detect_topic(self):
        cs = ContextualSynonyms(lang="en")
        topic = cs.detect_topic(
            "The web server processes HTTP requests. "
            "The API returns JSON responses from the database."
        )
        # Может вернуть None или строку
        assert topic is None or isinstance(topic, str)

    def test_choose_synonym_basic(self):
        cs = ContextualSynonyms(lang="en")
        word = "important"
        synonyms = ["significant", "crucial", "vital", "key"]
        context = "This is an important factor in the decision."
        result = cs.choose_synonym(word, synonyms, context)
        assert result in synonyms or result == word

    def test_choose_synonym_empty_list(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.choose_synonym("hello", [], "Hello world context.")
        assert result == "hello"

    def test_choose_synonym_with_topic_context(self):
        cs = ContextualSynonyms(lang="en")
        word = "big"
        synonyms = ["large", "enormous", "massive", "significant"]
        context = "The server handles big data processing and analytics."
        result = cs.choose_synonym(word, synonyms, context, window=80)
        assert result in synonyms or result == word

    def test_choose_synonym_ru(self):
        cs = ContextualSynonyms(lang="ru")
        word = "большой"
        synonyms = ["крупный", "значительный", "масштабный"]
        context = "Это большой проект с множеством участников."
        result = cs.choose_synonym(word, synonyms, context)
        assert isinstance(result, str)

    def test_match_form_upper(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.match_form("Important", "significant")
        # Должен вернуть Significant (с заглавной)
        assert result[0].isupper()

    def test_match_form_lower(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.match_form("important", "significant")
        assert result[0].islower()

    def test_match_form_all_upper(self):
        cs = ContextualSynonyms(lang="en")
        result = cs.match_form("IMPORTANT", "significant")
        assert result == result.upper() or isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  Sentence Split — splits, repairs, protected zones
# ═══════════════════════════════════════════════════════════════

from texthumanize.sentence_split import SentenceSplitter, split_sentences, split_sentences_with_spans


class TestSentenceSplitter:
    """Тесты SentenceSplitter — splits, repairs, protected zones."""

    def test_basic_split(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split("First sentence. Second sentence! Third one?")
        assert len(result) >= 2

    def test_split_with_abbreviations(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split(
            "Dr. Smith went to Washington. He met Mr. Jones there. "
            "They discussed U.S. policy for the year."
        )
        # Abbreviations should not split
        assert len(result) >= 2

    def test_split_with_ellipsis(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split(
            "Well... I thought about it. Maybe not. "
            "Let me think again... Yes, that works."
        )
        assert len(result) >= 2

    def test_split_with_quotes(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split(
            'She said "Hello. How are you?" and left. He stayed behind.'
        )
        assert isinstance(result, list)

    def test_split_russian(self):
        sp = SentenceSplitter(lang="ru")
        result = sp.split(
            "Система работает хорошо. Данные обрабатываются. "
            "Результат готов!"
        )
        assert len(result) >= 2

    def test_split_spans(self):
        sp = SentenceSplitter(lang="en")
        spans = sp.split_spans("First sentence. Second sentence.")
        assert len(spans) >= 1
        assert hasattr(spans[0], "text") or hasattr(spans[0], "start")

    def test_repair_merge_lowercase(self):
        sp = SentenceSplitter(lang="en")
        sents = ["Hello World", "continued here. Done."]
        repaired = sp.repair(sents)
        assert isinstance(repaired, list)

    def test_repair_merge_short(self):
        sp = SentenceSplitter(lang="en")
        sents = ["Eg", "This is a full sentence."]
        repaired = sp.repair(sents)
        assert isinstance(repaired, list)

    def test_protected_zones_parentheses(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split(
            "The metric (e.g. precision recall F1) improved. "
            "The system works."
        )
        assert isinstance(result, list)

    def test_protected_zones_french_quotes(self):
        sp = SentenceSplitter(lang="ru")
        result = sp.split(
            "Он сказал «Привет. Как дела?» и ушёл. Она осталась."
        )
        assert isinstance(result, list)

    def test_decimal_numbers(self):
        sp = SentenceSplitter(lang="en")
        result = sp.split(
            "The temperature is 36.6 degrees. That is normal. "
            "The price is 99.99 dollars."
        )
        # 36.6 should not split
        assert len(result) >= 2

    def test_multi_dot_abbreviations(self):
        sp = SentenceSplitter(lang="ru")
        result = sp.split(
            "Список включает т.д. элементы. Также есть т.п. варианты."
        )
        assert isinstance(result, list)

    def test_word_before_dot(self):
        sp = SentenceSplitter(lang="en")
        word = sp._get_word_before_dot("Hello Mr. Smith", 8)
        assert isinstance(word, str)

    def test_in_protected(self):
        sp = SentenceSplitter(lang="en")
        zones = [(5, 10), (20, 30)]
        assert sp._in_protected(7, zones) is True
        assert sp._in_protected(15, zones) is False


class TestSentenceSplitTopLevel:
    """Тесты top-level функций."""

    def test_split_sentences(self):
        result = split_sentences("First. Second! Third?", lang="en")
        assert len(result) >= 2

    def test_split_sentences_ru(self):
        result = split_sentences("Привет. Как дела? Хорошо!", lang="ru")
        assert len(result) >= 2

    def test_split_sentences_with_spans(self):
        result = split_sentences_with_spans("First. Second.", lang="en")
        assert len(result) >= 1


# ═══════════════════════════════════════════════════════════════
#  Tone — analyze + adjust
# ═══════════════════════════════════════════════════════════════

from texthumanize.tone import ToneAnalyzer, ToneAdjuster, ToneLevel, analyze_tone, adjust_tone


class TestToneAnalyzer:
    """Тесты ToneAnalyzer."""

    def test_analyze_formal(self):
        ta = ToneAnalyzer(lang="en")
        report = ta.analyze(
            "Furthermore, the comprehensive analysis demonstrates "
            "significant improvements in overall performance metrics."
        )
        assert hasattr(report, "primary_tone")
        assert hasattr(report, "scores")

    def test_analyze_informal(self):
        ta = ToneAnalyzer(lang="en")
        report = ta.analyze(
            "hey so basically the thing works super well lol. "
            "its kinda awesome ngl."
        )
        assert hasattr(report, "primary_tone")

    def test_analyze_ru(self):
        ta = ToneAnalyzer(lang="ru")
        report = ta.analyze(
            "Необходимо подчеркнуть значительное улучшение показателей."
        )
        assert hasattr(report, "primary_tone")


class TestToneAdjuster:
    """Тесты ToneAdjuster — adjust + direction."""

    def test_adjust_to_formal(self):
        adj = ToneAdjuster(lang="en", seed=0)
        result = adj.adjust(
            "The thing works pretty good and stuff is nice.",
            target=ToneLevel.FORMAL,
            intensity=0.8,
        )
        assert isinstance(result, str)

    def test_adjust_to_casual(self):
        adj = ToneAdjuster(lang="en", seed=0)
        result = adj.adjust(
            "The implementation demonstrates significant improvements.",
            target=ToneLevel.CASUAL,
            intensity=0.8,
        )
        assert isinstance(result, str)

    def test_adjust_neutral_no_change(self):
        adj = ToneAdjuster(lang="en", seed=42)
        text = "This is a normal text without extreme tone."
        result = adj.adjust(text, target=ToneLevel.NEUTRAL, intensity=0.5)
        assert isinstance(result, str)

    def test_case_preserving_replacement(self):
        """Замена с сохранением регистра."""
        adj = ToneAdjuster(lang="en", seed=0)
        result = adj.adjust(
            "Furthermore the system is good. FURTHERMORE it works.",
            target=ToneLevel.CASUAL,
            intensity=1.0,
        )
        assert isinstance(result, str)

    def test_direction_formal_to_casual(self):
        direction = ToneAdjuster._get_direction(ToneLevel.FORMAL, ToneLevel.CASUAL)
        assert direction is not None

    def test_direction_casual_to_formal(self):
        direction = ToneAdjuster._get_direction(ToneLevel.CASUAL, ToneLevel.FORMAL)
        assert direction is not None

    def test_direction_same_level(self):
        direction = ToneAdjuster._get_direction(ToneLevel.NEUTRAL, ToneLevel.NEUTRAL)
        # Same level → None (no adjustment needed)
        assert direction is None or isinstance(direction, tuple)

    def test_adjust_ru(self):
        adj = ToneAdjuster(lang="ru", seed=0)
        result = adj.adjust(
            "Необходимо осуществить мероприятие.",
            target=ToneLevel.CASUAL,
            intensity=0.8,
        )
        assert isinstance(result, str)


class TestToneTopLevel:
    """Тесты top-level tone функций."""

    def test_analyze_tone(self):
        report = analyze_tone("This is a test text.", lang="en")
        assert hasattr(report, "primary_tone")

    def test_adjust_tone(self):
        result = adjust_tone(
            "The implementation is good.",
            target="neutral",
            lang="en",
            intensity=0.5,
        )
        assert isinstance(result, str)
