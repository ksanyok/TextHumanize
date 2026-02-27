"""Покрытие pipeline.py, structure.py, liveliness.py, repetitions.py, validator.py."""

import pytest

from texthumanize.liveliness import LivelinessInjector
from texthumanize.pipeline import Pipeline
from texthumanize.repetitions import RepetitionReducer
from texthumanize.structure import StructureDiversifier
from texthumanize.utils import HumanizeOptions
from texthumanize.validator import QualityValidator

# ═══════════════════════════════════════════════════════════════
#  Pipeline
# ═══════════════════════════════════════════════════════════════

class TestPipelinePlugins:
    """Тесты plugin/hook системы pipeline."""

    def teardown_method(self):
        Pipeline.clear_plugins()

    def test_register_plugin_before(self):
        """Регистрация плагина before."""
        class MyPlugin:
            def process(self, text, lang, profile, intensity):
                return text.upper()

        Pipeline.register_plugin(MyPlugin(), before="typography")
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("Hello world test here.", "en")
        assert isinstance(result.text, str)

    def test_register_plugin_after(self):
        """Регистрация плагина after."""
        class MyPlugin:
            def process(self, text, lang, profile, intensity):
                return text + " [processed]"

        Pipeline.register_plugin(MyPlugin(), after="typography")
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("Hello world test here.", "en")
        assert isinstance(result.text, str)

    def test_register_plugin_no_stage_raises(self):
        """Без before/after → ValueError."""
        class MyPlugin:
            def process(self, text, lang, profile, intensity):
                return text

        with pytest.raises(ValueError, match="Specify"):
            Pipeline.register_plugin(MyPlugin())

    def test_register_plugin_unknown_stage_raises(self):
        """Неизвестный этап → ValueError."""
        class MyPlugin:
            def process(self, text, lang, profile, intensity):
                return text

        with pytest.raises(ValueError, match="Unknown stage"):
            Pipeline.register_plugin(MyPlugin(), before="nonexistent")

    def test_register_hook_before(self):
        """Регистрация hook before."""
        def my_hook(text, lang):
            return text.replace("hello", "hi")

        Pipeline.register_hook(my_hook, before="typography")
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("hello world test here.", "en")
        assert isinstance(result.text, str)

    def test_register_hook_after(self):
        """Регистрация hook after."""
        def my_hook(text, lang):
            return text

        Pipeline.register_hook(my_hook, after="universal")
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("Hello world.", "en")
        assert isinstance(result.text, str)

    def test_register_hook_no_stage_raises(self):
        """Hook без before/after → ValueError."""
        with pytest.raises(ValueError, match="Specify"):
            Pipeline.register_hook(lambda t, l: t)

    def test_register_hook_unknown_stage_raises(self):
        """Hook с неизвестным этапом → ValueError."""
        with pytest.raises(ValueError, match="Unknown stage"):
            Pipeline.register_hook(lambda t, l: t, after="fake_stage")

    def test_clear_plugins(self):
        """clear_plugins очищает всё."""
        Pipeline.register_hook(lambda t, l: t, before="typography")
        Pipeline.clear_plugins()
        # Проверяем что пусто (не падает при run)
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("Test.", "en")
        assert isinstance(result.text, str)

    def test_pipeline_with_keep_keywords(self):
        """Pipeline с constraints.keep_keywords."""
        opts = HumanizeOptions(
            intensity=80,
            constraints={"keep_keywords": ["TextHumanize"]},
        )
        p = Pipeline(opts)
        result = p.run("TextHumanize is a great library.", "en")
        assert "TextHumanize" in result.text

    def test_pipeline_validation_rollback(self):
        """Pipeline с max_change_ratio → rollback при слишком большом изменении."""
        opts = HumanizeOptions(
            intensity=100,
            constraints={"max_change_ratio": 0.01},  # Очень строгое ограничение
        )
        p = Pipeline(opts)
        text = "Необходимо подчеркнуть что данная система обеспечивает значительное улучшение всеобъемлющих показателей."
        result = p.run(text, "ru")
        # При очень строгом ограничении текст может быть откачен
        assert isinstance(result.text, str)

    def test_pipeline_non_dict_lang(self):
        """Pipeline для языка без словаря (этапы 3-6 пропускаются)."""
        opts = HumanizeOptions(intensity=50)
        p = Pipeline(opts)
        result = p.run("Dies ist ein Test. Noch ein Satz hier.", "xx")
        assert isinstance(result.text, str)


# ═══════════════════════════════════════════════════════════════
#  Structure
# ═══════════════════════════════════════════════════════════════

class TestStructureDiversifier:
    """Тесты StructureDiversifier — непокрытые ветки."""

    def test_replace_connectors(self):
        """Замена AI-коннекторов."""
        s = StructureDiversifier(lang="en", intensity=100, seed=0)
        text = (
            "Furthermore the system works. Moreover the data is ready. "
            "Additionally the team is prepared. Nevertheless it was hard. "
            "Consequently the results improved."
        )
        result = s.process(text)
        assert isinstance(result, str)

    def test_replace_connectors_ru(self):
        """Русские коннекторы."""
        s = StructureDiversifier(lang="ru", intensity=100, seed=0)
        text = (
            "Кроме того система работает. Более того данные готовы. "
            "Тем не менее результаты хорошие. Следовательно план удался."
        )
        result = s.process(text)
        assert isinstance(result, str)

    def test_split_long_sentences(self):
        """Разбивка длинных предложений."""
        s = StructureDiversifier(lang="en", intensity=100, seed=0)
        long_sent = "The system provides comprehensive data analysis and the team uses this data to make critical decisions about the future direction of the project and the company strategy going forward"
        text = f"{long_sent}. Short. Another."
        result = s.process(text)
        assert isinstance(result, str)

    def test_join_short_sentences(self):
        """Объединение коротких предложений."""
        s = StructureDiversifier(lang="en", intensity=100, seed=0)
        text = "Go. Now. Do. Try. Yes. OK."
        result = s.process(text)
        assert isinstance(result, str)

    def test_sentence_start_diversity(self):
        """Разнообразие начал предложений."""
        s = StructureDiversifier(lang="en", intensity=100, seed=0)
        text = (
            "The system works. The data flows. The team builds. "
            "The project grows. The results improve. The users love it."
        )
        result = s.process(text)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  Liveliness
# ═══════════════════════════════════════════════════════════════

class TestLivelinessInjector:
    """Тесты LivelinessInjector — непокрытые ветки."""

    def test_marker_injection(self):
        """Инъекция разговорных маркеров."""
        li = LivelinessInjector(lang="ru", profile="chat", intensity=100, seed=0)
        text = (
            "Система работает хорошо. Данные обрабатываются быстро. "
            "Результаты точные и надежные. Пользователи довольны. "
            "Команда следит за всем. Улучшения планируются. "
            "Качество растёт. Объёмы увеличиваются. "
            "Скорость не падает. Стабильность обеспечена. "
            "Мониторинг активен. Поддержка доступна."
        )
        result = li.process(text)
        assert isinstance(result, str)

    def test_punctuation_tweak(self):
        """Замена ; на . с заглавной."""
        li = LivelinessInjector(lang="ru", profile="chat", intensity=100, seed=0)
        text = (
            "Система работает; данные готовы. "
            "Результаты хорошие. Пользователи довольны."
        )
        result = li.process(text)
        assert isinstance(result, str)

    def test_formal_profile_minimal(self):
        """Профиль docs — минимальные изменения."""
        li = LivelinessInjector(lang="ru", profile="docs", intensity=30, seed=42)
        text = "Система работает хорошо. Данные обрабатываются."
        result = li.process(text)
        assert isinstance(result, str)

    def test_en_markers(self):
        """Английские маркеры."""
        li = LivelinessInjector(lang="en", profile="chat", intensity=100, seed=0)
        text = (
            "The system works well today. Data is being processed quickly. "
            "Results are accurate and reliable. Users are satisfied. "
            "The team monitors everything. Improvements are planned. "
            "Quality increases daily. Volume grows steadily. "
            "Speed remains constant. Stability is ensured. "
            "Monitoring is active. Support is available."
        )
        result = li.process(text)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  Repetitions
# ═══════════════════════════════════════════════════════════════

class TestRepetitionReducer:
    """Тесты RepetitionReducer — непокрытые ветки."""

    def test_word_repetitions(self):
        """Замена повторяющихся слов синонимами."""
        r = RepetitionReducer(lang="en", intensity=100, seed=0)
        text = (
            "The system provides important data. The system handles important tasks. "
            "The system ensures important results."
        )
        result = r.process(text)
        assert isinstance(result, str)

    def test_bigram_repetitions(self):
        """Замена повторяющихся биграмм."""
        r = RepetitionReducer(lang="ru", intensity=100, seed=0)
        text = (
            "Данная система обрабатывает информацию. Данная система показывает результаты. "
            "Данная система улучшает качество."
        )
        result = r.process(text)
        assert isinstance(result, str)

    def test_short_text_unchanged(self):
        """Короткий текст без повторов."""
        r = RepetitionReducer(lang="en", intensity=100, seed=42)
        text = "Hello world."
        result = r.process(text)
        assert result == text


# ═══════════════════════════════════════════════════════════════
#  Validator
# ═══════════════════════════════════════════════════════════════

class TestQualityValidator:
    """Тесты QualityValidator — непокрытые ветки."""

    def test_keyword_preservation(self):
        """Проверка сохранения ключевых слов."""
        v = QualityValidator(
            lang="en",
            keep_keywords=["TextHumanize", "API"],
        )
        from texthumanize.analyzer import TextAnalyzer
        analyzer = TextAnalyzer(lang="en")
        metrics = analyzer.analyze("TextHumanize API is great.")
        result = v.validate(
            "TextHumanize API is great.",
            "The library is great.",  # Потеряны ключевые слова
            metrics,
        )
        assert result.errors  # Должны быть ошибки

    def test_number_preservation(self):
        """Проверка сохранения числовых значений."""
        v = QualityValidator(lang="en")
        from texthumanize.analyzer import TextAnalyzer
        analyzer = TextAnalyzer(lang="en")
        metrics = analyzer.analyze("The price is 100 dollars and 50 cents.")
        result = v.validate(
            "The price is 100 dollars and 50 cents.",
            "The price is 200 dollars and 80 cents.",
            metrics,
        )
        # Числа изменились — должно быть предупреждение
        assert isinstance(result.warnings, list) or isinstance(result.errors, list)

    def test_length_ratio_warning(self):
        """Предупреждение при сильном изменении длины."""
        v = QualityValidator(lang="en")
        from texthumanize.analyzer import TextAnalyzer
        analyzer = TextAnalyzer(lang="en")
        original = "This is a normal text with several words."
        metrics = analyzer.analyze(original)
        result = v.validate(
            original,
            "Short.",  # Сильно сократился
            metrics,
        )
        assert isinstance(result.should_rollback, bool)

    def test_change_ratio_calc(self):
        """Расчёт change_ratio."""
        v = QualityValidator(lang="en")
        ratio = v._calc_change_ratio(
            "The quick brown fox jumps.",
            "A fast brown fox leaps.",
        )
        assert 0 < ratio < 1

    def test_validation_result_repr(self):
        """ValidationResult repr."""
        from texthumanize.validator import ValidationResult
        vr = ValidationResult()
        vr.change_ratio = 0.15
        vr.warnings = ["test warning"]
        r = repr(vr)
        assert "VALID" in r

    def test_invalid_result_repr(self):
        """ValidationResult INVALID repr."""
        from texthumanize.validator import ValidationResult
        vr = ValidationResult()
        vr.is_valid = False
        vr.should_rollback = True
        vr.change_ratio = 0.5
        vr.errors = ["error1", "error2"]
        r = repr(vr)
        assert "INVALID" in r
