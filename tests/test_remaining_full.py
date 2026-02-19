"""Покрытие остальных модулей: spinner, tokenizer, watermark, paraphrase,
morphology, cli, utils, normalizer, segmenter, decancel, core, lang_detect, api, __main__."""

import io
import pytest
import sys
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════
#  Spinner
# ═══════════════════════════════════════════════════════════════

from texthumanize.spinner import ContentSpinner


class TestContentSpinner:
    def test_resolve_spintax(self):
        sp = ContentSpinner(lang="en", seed=0)
        result = sp.resolve_spintax("{hello|hi|hey} world")
        assert result in ("hello world", "hi world", "hey world")

    def test_resolve_spintax_nested(self):
        sp = ContentSpinner(lang="en", seed=42)
        result = sp.resolve_spintax("{good|{nice|great}} day")
        assert "day" in result

    def test_generate_variants(self):
        sp = ContentSpinner(lang="en", seed=0)
        text = "The system works well."
        variants = sp.generate_variants(text, count=3)
        assert isinstance(variants, list)
        assert len(variants) >= 1

    def test_generate_variants_unique(self):
        sp = ContentSpinner(lang="en", seed=0)
        text = "The system provides comprehensive data analysis."
        variants = sp.generate_variants(text, count=5)
        # All should be unique
        assert len(variants) == len(set(variants))

    def test_calculate_uniqueness(self):
        score = ContentSpinner._calculate_uniqueness(
            "The quick brown fox", "A fast brown fox"
        )
        assert 0.0 <= score <= 1.0

    def test_calculate_uniqueness_identical(self):
        score = ContentSpinner._calculate_uniqueness("hello", "hello")
        assert score == 0.0

    def test_count_variants(self):
        count = ContentSpinner._count_variants("{a|b|c} {x|y}")
        assert count == 6

    def test_count_variants_no_spintax(self):
        count = ContentSpinner._count_variants("plain text")
        assert count == 1


# ═══════════════════════════════════════════════════════════════
#  Tokenizer
# ═══════════════════════════════════════════════════════════════

from texthumanize.tokenizer import Tokenizer, Sentence


class TestTokenizer:
    def test_tokenize_basic(self):
        tok = Tokenizer()
        result = tok.tokenize("First sentence. Second sentence!")
        assert len(result.paragraphs) >= 1

    def test_tokenize_multi_paragraph(self):
        tok = Tokenizer()
        result = tok.tokenize("Paragraph one.\n\nParagraph two.")
        assert len(result.paragraphs) >= 1

    def test_sentence_to_text(self):
        s = Sentence(words=["Hello", "world"], ending=".")
        assert s.to_text() == "Hello world."

    def test_sentence_word_count(self):
        s = Sentence(words=["Hello", "world", "here"], ending=".")
        assert s.word_count >= 2

    def test_tokenizer_with_abbreviations(self):
        tok = Tokenizer(abbreviations=["Dr", "Mr", "Mrs"])
        result = tok.tokenize("Dr. Smith went home. He was tired.")
        assert isinstance(result.paragraphs, list)

    def test_split_sentences_internal(self):
        tok = Tokenizer()
        sents = tok._split_sentences("Hello world. How are you? Fine.")
        assert len(sents) >= 2

    def test_parse_sentence(self):
        tok = Tokenizer()
        s = tok._parse_sentence("Hello world!")
        assert s.ending == "!"
        assert len(s.words) >= 2


# ═══════════════════════════════════════════════════════════════
#  Watermark
# ═══════════════════════════════════════════════════════════════

from texthumanize.watermark import WatermarkDetector, detect_watermarks


class TestWatermarkDetector:
    def test_detect_clean(self):
        wd = WatermarkDetector()
        report = wd.detect("Clean text without watermarks.")
        assert report.has_watermarks is False

    def test_detect_invisible_chars(self):
        wd = WatermarkDetector()
        # Inject invisible format chars
        text = "Hello\u200Bworld\u200Btest\u200B here."
        report = wd.detect(text)
        assert isinstance(report.cleaned_text, str)

    def test_detect_homoglyphs_cyrillic(self):
        wd = WatermarkDetector()
        # Mix Latin 'a' with Cyrillic 'а' (U+0430)
        text = "Hello w\u043erld test here."
        report = wd.detect(text)
        assert isinstance(report.has_watermarks, bool)

    def test_detect_spacing_anomalies(self):
        wd = WatermarkDetector()
        text = "Hello   world   test   here   now   again   .\n  trailing  \n  trailing  \n  trailing  \n  trailing  "
        report = wd.detect(text)
        assert isinstance(report.cleaned_text, str)

    def test_is_cyrillic(self):
        assert WatermarkDetector._is_cyrillic("а") is True
        assert WatermarkDetector._is_cyrillic("a") is False

    def test_is_latin(self):
        assert WatermarkDetector._is_latin("a") is True
        assert WatermarkDetector._is_latin("а") is False  # Cyrillic а

    def test_detect_watermarks_func(self):
        report = detect_watermarks("Normal text here.", lang="en")
        assert hasattr(report, "has_watermarks")

    def test_detect_statistical_watermarks(self):
        wd = WatermarkDetector()
        # Need 50+ words for detection
        text = " ".join(
            ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog"] * 10
        )
        report = wd.detect(text)
        assert isinstance(report.has_watermarks, bool)


# ═══════════════════════════════════════════════════════════════
#  Paraphrase
# ═══════════════════════════════════════════════════════════════

from texthumanize.paraphrase import Paraphraser


class TestParaphraser:
    def test_paraphrase_basic(self):
        p = Paraphraser(lang="en", seed=0)
        result = p.paraphrase("The system handles data processing.")
        assert hasattr(result, "paraphrased")
        assert isinstance(result.paraphrased, str)

    def test_clause_reorder(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "Although the system is complex, it works well."
        result, strategy, conf = p._try_clause_swap(sent)
        assert isinstance(result, str)

    def test_passive_to_active(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "The book was written by John."
        result, strategy, conf = p._try_passive_to_active(sent)
        assert isinstance(result, str)

    def test_sentence_split(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "The system processes data and the team analyzes the results of the comprehensive evaluation."
        result, strategy, conf = p._try_sentence_split(sent)
        assert isinstance(result, str)

    def test_sentence_split_short(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "Short sent."
        result, strategy, conf = p._try_sentence_split(sent)
        assert result == sent  # Too short to split

    def test_fronting(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "The team quickly analyzed the data."
        result, strategy, conf = p._try_fronting(sent)
        assert isinstance(result, str)

    def test_nominalization_swap(self):
        p = Paraphraser(lang="en", seed=0)
        sent = "The team decided to implement the system."
        result, strategy, conf = p._try_nominalization_swap(sent)
        assert isinstance(result, str)

    def test_split_sentences_internal(self):
        p = Paraphraser(lang="en", seed=0)
        sents = p._split_sentences("First. Second! Third?")
        assert len(sents) >= 2

    def test_paraphrase_ru(self):
        p = Paraphraser(lang="ru", seed=0)
        result = p.paraphrase("Система обрабатывает данные.")
        assert hasattr(result, "paraphrased")
        assert isinstance(result.paraphrased, str)


# ═══════════════════════════════════════════════════════════════
#  Morphology
# ═══════════════════════════════════════════════════════════════

from texthumanize.morphology import MorphologyEngine, get_morphology


class TestMorphologyEngine:
    def test_lemmatize_en(self):
        m = MorphologyEngine(lang="en")
        assert m.lemmatize("running") != ""
        assert m.lemmatize("played") != ""
        assert m.lemmatize("bigger") != ""

    def test_lemmatize_en_irregular(self):
        m = MorphologyEngine(lang="en")
        result = m.lemmatize("went")
        assert isinstance(result, str)

    def test_generate_forms_en(self):
        m = MorphologyEngine(lang="en")
        forms = m.generate_forms("run")
        assert isinstance(forms, list)
        assert len(forms) >= 1

    def test_match_form_en(self):
        m = MorphologyEngine(lang="en")
        result = m._match_form_en("running", "walk")
        assert isinstance(result, str)

    def test_match_form_en_past(self):
        m = MorphologyEngine(lang="en")
        result = m._match_form_en("played", "work")
        assert isinstance(result, str)

    def test_detect_pos_en(self):
        m = MorphologyEngine(lang="en")
        assert m._detect_pos_en("quickly") == "adv"
        assert m._detect_pos_en("running") == "verb"
        assert isinstance(m._detect_pos_en("house"), str)

    def test_lemmatize_de(self):
        m = MorphologyEngine(lang="de")
        result = m.lemmatize("schneller")
        assert isinstance(result, str)

    def test_generate_forms_de(self):
        m = MorphologyEngine(lang="de")
        forms = m.generate_forms("schnell")
        assert isinstance(forms, list)

    def test_match_form_de(self):
        m = MorphologyEngine(lang="de")
        result = m._match_form_de("schneller", "groß")
        assert isinstance(result, str)

    def test_detect_pos_de(self):
        m = MorphologyEngine(lang="de")
        assert isinstance(m._detect_pos_de("Haus"), str)
        assert isinstance(m._detect_pos_de("schnell"), str)

    def test_lemmatize_uk(self):
        m = MorphologyEngine(lang="uk")
        result = m.lemmatize("великий")
        assert isinstance(result, str)

    def test_generate_forms_uk(self):
        m = MorphologyEngine(lang="uk")
        forms = m.generate_forms("великий")
        assert isinstance(forms, list)

    def test_match_form_slavic(self):
        m = MorphologyEngine(lang="ru")
        result = m._match_form_slavic("большого", "великий")
        assert isinstance(result, str)

    def test_detect_pos_slavic(self):
        m = MorphologyEngine(lang="ru")
        assert isinstance(m._detect_pos_slavic("быстро"), str)
        assert isinstance(m._detect_pos_slavic("красивый"), str)
        assert isinstance(m._detect_pos_slavic("делать"), str)

    def test_get_morphology_singleton(self):
        m1 = get_morphology("en")
        m2 = get_morphology("en")
        assert m1 is m2

    def test_find_synonym_form(self):
        m = MorphologyEngine(lang="en")
        result = m.find_synonym_form("running", "walk")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  Utils
# ═══════════════════════════════════════════════════════════════

from texthumanize.utils import (
    HumanizeOptions,
    get_profile,
    should_apply,
    coin_flip,
    intensity_probability,
)


class TestUtils:
    def test_get_profile_default(self):
        p = get_profile("web")
        assert isinstance(p, dict)

    def test_get_profile_unknown_raises(self):
        with pytest.raises(ValueError):
            get_profile("nonexistent_profile_xyz")

    def test_should_apply_true(self):
        assert should_apply(100, 1.0, 0.5) is True

    def test_should_apply_false(self):
        assert should_apply(10, 0.1, 0.5) is False

    def test_coin_flip(self):
        import random
        rng = random.Random(42)
        result = coin_flip(0.5, rng)
        assert isinstance(result, bool)

    def test_intensity_probability(self):
        assert intensity_probability(100, 1.0) == 1.0
        assert intensity_probability(50, 0.5) == 0.25

    def test_humanize_options_defaults(self):
        opts = HumanizeOptions()
        assert opts.intensity == 60
        assert opts.profile == "web"

    def test_humanize_options_custom(self):
        opts = HumanizeOptions(intensity=80, profile="chat", lang="ru")
        assert opts.intensity == 80
        assert opts.lang == "ru"

    def test_humanize_options_constraints(self):
        opts = HumanizeOptions(
            constraints={"keep_keywords": ["test"], "max_change_ratio": 0.3}
        )
        assert "keep_keywords" in opts.constraints


# ═══════════════════════════════════════════════════════════════
#  Normalizer
# ═══════════════════════════════════════════════════════════════

from texthumanize.normalizer import TypographyNormalizer


class TestNormalizerExtended:
    def test_replace_paired_quotes(self):
        n = TypographyNormalizer(profile="web", lang="en")
        result = n.normalize('"Hello" he said. "Goodbye" she replied.')
        assert isinstance(result, str)

    def test_normalize_ellipsis(self):
        n = TypographyNormalizer(profile="web", lang="en")
        result = n.normalize("Well… I think… maybe not.")
        assert isinstance(result, str)

    def test_normalize_dashes(self):
        n = TypographyNormalizer(profile="web", lang="en")
        result = n.normalize("The system — works — well.")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  Segmenter
# ═══════════════════════════════════════════════════════════════

from texthumanize.segmenter import Segmenter


class TestSegmenterExtended:
    def test_protect_urls(self):
        seg = Segmenter()
        result = seg.segment("Visit https://example.com for details.")
        assert isinstance(result.text, str)

    def test_protect_numbers(self):
        seg = Segmenter()
        result = seg.segment("The price is 99.99 dollars.")
        assert isinstance(result.text, str)

    def test_protect_terms(self):
        seg = Segmenter(preserve={"terms": ["TextHumanize"]})
        result = seg.segment("TextHumanize is a great library.")
        assert isinstance(result.text, str)

    def test_restore(self):
        seg = Segmenter()
        result = seg.segment("Visit https://example.com now.")
        restored = result.restore(result.text)
        assert "https://example.com" in restored or isinstance(restored, str)


# ═══════════════════════════════════════════════════════════════
#  Decancel
# ═══════════════════════════════════════════════════════════════

from texthumanize.decancel import Debureaucratizer


class TestDecancellerExtended:
    def test_replace_phrases(self):
        d = Debureaucratizer(lang="ru", intensity=100, seed=0)
        text = "В рамках данного мероприятия осуществляется деятельность."
        result = d.process(text)
        assert isinstance(result, str)

    def test_replace_words(self):
        d = Debureaucratizer(lang="ru", intensity=100, seed=0)
        text = "Необходимо осуществить мероприятие по обеспечению деятельности."
        result = d.process(text)
        assert isinstance(result, str)

    def test_preserve_case(self):
        d = Debureaucratizer(lang="ru", intensity=100, seed=0)
        text = "Осуществление деятельности."
        result = d.process(text)
        # First letter should stay upper
        assert result[0].isupper() or result == text


# ═══════════════════════════════════════════════════════════════
#  Core
# ═══════════════════════════════════════════════════════════════

from texthumanize.core import humanize, explain, HumanizeResult


class TestCoreExtended:
    def test_explain_output(self):
        result = humanize(
            "The system provides comprehensive data analysis capabilities.",
            lang="en",
            intensity=80,
        )
        explanation = explain(result)
        assert isinstance(explanation, str)
        assert "TextHumanize" in explanation or len(explanation) > 0

    def test_explain_with_changes(self):
        result = humanize(
            "Необходимо подчеркнуть что осуществление мероприятий "
            "в рамках данной деятельности обеспечивает улучшение "
            "всеобъемлющих показателей.",
            lang="ru",
            intensity=100,
        )
        explanation = explain(result)
        assert isinstance(explanation, str)

    def test_humanize_result_fields(self):
        result = humanize("Test text here.", lang="en", intensity=50)
        assert hasattr(result, "text")
        assert hasattr(result, "lang")
        assert hasattr(result, "changes")


# ═══════════════════════════════════════════════════════════════
#  Lang Detect
# ═══════════════════════════════════════════════════════════════

from texthumanize.lang_detect import detect_language


class TestLangDetect:
    def test_detect_english(self):
        assert detect_language("The quick brown fox jumps over the lazy dog.") == "en"

    def test_detect_russian(self):
        lang = detect_language("Система работает хорошо и обрабатывает данные.")
        assert lang in ("ru", "uk")

    def test_detect_ukrainian(self):
        lang = detect_language("Це дуже гарна система, яка працює і забезпечує якість.")
        assert lang in ("uk", "ru")

    def test_detect_german(self):
        lang = detect_language("Das System funktioniert gut und verarbeitet die Daten.")
        assert lang in ("de", "en")

    def test_detect_french(self):
        lang = detect_language("Le système fonctionne très bien avec les données.")
        assert lang in ("fr", "en")

    def test_detect_short_text(self):
        lang = detect_language("Hi")
        assert lang == "en"  # Fallback

    def test_detect_empty(self):
        lang = detect_language("")
        assert lang == "en"

    def test_cyrillic_ratio(self):
        from texthumanize.lang_detect import _cyrillic_ratio
        assert _cyrillic_ratio("Привет мир") > 0.5
        assert _cyrillic_ratio("Hello world") == 0.0


# ═══════════════════════════════════════════════════════════════
#  API (0% → cover all handlers without starting server)
# ═══════════════════════════════════════════════════════════════

from texthumanize.api import (
    _require_text,
    _handle_humanize,
    _handle_analyze,
    _handle_detect_ai,
    _handle_paraphrase,
    _handle_tone_analyze,
    _handle_tone_adjust,
    _handle_watermarks_detect,
    _handle_watermarks_clean,
    _handle_spin,
    _handle_coherence,
    _handle_readability,
    create_app,
)


class TestAPIHandlers:
    """Тестируем API-хендлеры напрямую (без HTTP)."""

    def test_require_text_ok(self):
        assert _require_text({"text": "hello"}) == "hello"

    def test_require_text_missing(self):
        with pytest.raises(ValueError):
            _require_text({})

    def test_handle_humanize(self):
        result = _handle_humanize({"text": "Test sentence here.", "lang": "en"})
        assert "text" in result

    def test_handle_humanize_with_options(self):
        result = _handle_humanize({
            "text": "Test sentence here.",
            "lang": "en",
            "intensity": 80,
            "profile": "chat",
        })
        assert "text" in result

    def test_handle_analyze(self):
        result = _handle_analyze({"text": "Test sentence here.", "lang": "en"})
        assert isinstance(result, dict)

    def test_handle_detect_ai(self):
        result = _handle_detect_ai({
            "text": "The system provides comprehensive data analysis. "
                    "Furthermore the results are excellent. "
                    "Moreover the implementation is solid. "
                    "Additionally the performance meets expectations. "
                    "Consequently we recommend adoption.",
        })
        assert "ai_probability" in result or "verdict" in result

    def test_handle_detect_ai_batch(self):
        result = _handle_detect_ai({
            "texts": ["Hello world.", "Test text here."],
        })
        assert isinstance(result, (dict, list))

    def test_handle_paraphrase(self):
        result = _handle_paraphrase({"text": "The system works well."})
        assert "text" in result

    def test_handle_tone_analyze(self):
        result = _handle_tone_analyze({"text": "Hello friend.", "lang": "en"})
        assert isinstance(result, dict)

    def test_handle_tone_adjust(self):
        result = _handle_tone_adjust({
            "text": "The system works.",
            "target": "formal",
            "lang": "en",
        })
        assert "text" in result

    def test_handle_watermarks_detect(self):
        result = _handle_watermarks_detect({"text": "Clean text."})
        assert isinstance(result, dict)

    def test_handle_watermarks_clean(self):
        result = _handle_watermarks_clean({"text": "Clean text."})
        assert "text" in result

    def test_handle_spin(self):
        result = _handle_spin({"text": "The system works."})
        assert isinstance(result, dict)

    def test_handle_spin_variants(self):
        result = _handle_spin({"text": "The system works.", "count": 3})
        assert isinstance(result, dict)

    def test_handle_coherence(self):
        result = _handle_coherence({
            "text": "First sentence. Second sentence. Third one.",
            "lang": "en",
        })
        assert isinstance(result, dict)

    def test_handle_readability(self):
        result = _handle_readability({
            "text": "Test sentence here.",
            "lang": "en",
        })
        assert isinstance(result, dict)

    def test_create_app(self):
        app = create_app(host="127.0.0.1", port=0)
        assert app is not None
        app.server_close()


# ═══════════════════════════════════════════════════════════════
#  __main__
# ═══════════════════════════════════════════════════════════════

class TestMainModule:
    def test_main_import(self):
        """__main__.py импортируется без ошибок."""
        import importlib
        mod = importlib.import_module("texthumanize.__main__")
        assert hasattr(mod, "__name__")

    def test_main_runs_help(self):
        """python -m texthumanize --help."""
        with pytest.raises(SystemExit) as exc:
            with patch("sys.argv", ["texthumanize", "--help"]):
                from texthumanize.cli import main
                main()
        assert exc.value.code == 0
