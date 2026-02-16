"""Тесты мультиязычности — новые языковые пакеты и детекция."""

import pytest

from texthumanize import humanize, analyze
from texthumanize.lang import get_lang_pack, has_deep_support, LANGUAGES
from texthumanize.lang_detect import detect_language


# ─── Тексты на новых языках ─────────────────────────────────

GERMAN_TEXT = (
    "Künstliche Intelligenz ist eine der bedeutendsten Technologien unserer Zeit. "
    "Diese Technologie implementiert die Verarbeitung großer Datenmengen und bietet "
    "die Möglichkeit, verschiedene Prozesse zu optimieren. Darüber hinaus muss "
    "betont werden, dass die Einführung von KI eine signifikante Herausforderung "
    "darstellt. Nichtsdestotrotz ist es fundamental wichtig, diese Entwicklung "
    "voranzutreiben."
)

FRENCH_TEXT = (
    "L'intelligence artificielle est l'une des technologies les plus prometteuses "
    "de notre époque. Cette technologie permet d'implémenter le traitement de "
    "grands volumes de données. En outre, il est nécessaire de souligner que "
    "l'introduction de l'IA représente un défi exhaustif. Néanmoins, cette "
    "évolution est fondamentale pour notre avenir."
)

SPANISH_TEXT = (
    "La inteligencia artificial es una de las tecnologías más prometedoras de "
    "nuestra época. Esta tecnología permite implementar el procesamiento de "
    "grandes volúmenes de datos. Además, es fundamental señalar que la "
    "introducción de la IA representa un desafío significativo. Sin embargo, "
    "esta evolución es innovadora para nuestro futuro."
)

POLISH_TEXT = (
    "Sztuczna inteligencja jest jedną z najważniejszych technologii naszych "
    "czasów. Ta technologia umożliwia implementowanie przetwarzania dużych "
    "ilości danych. Ponadto, należy podkreślić, że wdrożenie SI stanowi "
    "fundamentalne wyzwanie. Niemniej jednak, ten rozwój jest innowacyjny "
    "i znacząco wpływa na naszą przyszłość."
)

PORTUGUESE_TEXT = (
    "A inteligência artificial é uma das tecnologias mais promissoras da "
    "nossa época. Esta tecnologia permite implementar o processamento de "
    "grandes volumes de dados. Além disso, é fundamental destacar que "
    "a introdução da IA representa um desafio significativo. No entanto, "
    "esta evolução é inovadora para o nosso futuro."
)

ITALIAN_TEXT = (
    "L'intelligenza artificiale è una delle tecnologie più promettenti della "
    "nostra epoca. Questa tecnologia consente di implementare l'elaborazione "
    "di grandi volumi di dati. Inoltre, è fondamentale sottolineare che "
    "l'introduzione dell'IA rappresenta una sfida significativa. Tuttavia, "
    "questa evoluzione è innovativa per il nostro futuro."
)


class TestLanguageDetection:
    """Тесты определения языка."""

    def test_detect_german(self):
        assert detect_language(GERMAN_TEXT) == "de"

    def test_detect_french(self):
        assert detect_language(FRENCH_TEXT) == "fr"

    def test_detect_spanish(self):
        assert detect_language(SPANISH_TEXT) == "es"

    def test_detect_polish(self):
        assert detect_language(POLISH_TEXT) == "pl"

    def test_detect_portuguese(self):
        assert detect_language(PORTUGUESE_TEXT) == "pt"

    def test_detect_italian(self):
        assert detect_language(ITALIAN_TEXT) == "it"


class TestLanguagePacks:
    """Тесты языковых пакетов."""

    @pytest.mark.parametrize("lang_code", ["de", "fr", "es", "pl", "pt", "it"])
    def test_pack_structure(self, lang_code):
        """Каждый пакет содержит все обязательные поля."""
        pack = get_lang_pack(lang_code)
        required_keys = [
            "code", "name", "trigrams", "stop_words",
            "bureaucratic", "bureaucratic_phrases", "ai_connectors",
            "synonyms", "profile_targets",
        ]
        for key in required_keys:
            assert key in pack, f"Отсутствует ключ '{key}' в пакете {lang_code}"

    @pytest.mark.parametrize("lang_code", ["de", "fr", "es", "pl", "pt", "it"])
    def test_pack_has_data(self, lang_code):
        """Каждый пакет содержит данные (не пустой)."""
        pack = get_lang_pack(lang_code)
        assert len(pack["bureaucratic"]) >= 10
        assert len(pack["ai_connectors"]) >= 8
        assert len(pack["synonyms"]) >= 10

    def test_all_deep_languages(self):
        """Все 9 языков имеют полную поддержку."""
        for lang in ["ru", "uk", "en", "de", "fr", "es", "pl", "pt", "it"]:
            assert has_deep_support(lang), f"{lang} должен иметь полную поддержку"

    def test_unknown_language_returns_empty(self):
        """Неизвестный язык возвращает пустой пакет (без ошибки)."""
        pack = get_lang_pack("zh")
        assert pack["code"] == "zh"
        assert pack["bureaucratic"] == {}

    def test_has_deep_support_unknown(self):
        """Неизвестный язык — нет глубокой поддержки."""
        assert not has_deep_support("zh")
        assert not has_deep_support("ja")


class TestMultilingualProcessing:
    """Тесты обработки текста на разных языках."""

    @pytest.mark.parametrize("text,lang", [
        (GERMAN_TEXT, "de"),
        (FRENCH_TEXT, "fr"),
        (SPANISH_TEXT, "es"),
        (POLISH_TEXT, "pl"),
        (PORTUGUESE_TEXT, "pt"),
        (ITALIAN_TEXT, "it"),
    ])
    def test_humanize_new_languages(self, text, lang):
        """Обработка работает для всех новых языков."""
        result = humanize(text, lang=lang, profile="web", intensity=60, seed=42)
        assert result.text  # Результат не пустой
        assert result.lang == lang
        assert result.text != text or len(text) < 50  # Какие-то изменения

    @pytest.mark.parametrize("text,lang", [
        (GERMAN_TEXT, "de"),
        (FRENCH_TEXT, "fr"),
        (SPANISH_TEXT, "es"),
        (POLISH_TEXT, "pl"),
        (PORTUGUESE_TEXT, "pt"),
        (ITALIAN_TEXT, "it"),
    ])
    def test_analyze_new_languages(self, text, lang):
        """Анализ работает для всех новых языков."""
        report = analyze(text, lang=lang)
        assert report.total_words > 0
        assert report.total_sentences > 0
        assert 0 <= report.artificiality_score <= 100

    @pytest.mark.parametrize("text,lang", [
        (GERMAN_TEXT, "de"),
        (FRENCH_TEXT, "fr"),
        (SPANISH_TEXT, "es"),
        (POLISH_TEXT, "pl"),
        (PORTUGUESE_TEXT, "pt"),
        (ITALIAN_TEXT, "it"),
    ])
    def test_auto_detect_and_process(self, text, lang):
        """Автоопределение + обработка для новых языков."""
        result = humanize(text, lang="auto", profile="web", intensity=60, seed=42)
        assert result.lang == lang
        assert result.text  # Не пустой

    @pytest.mark.parametrize("text,lang", [
        (GERMAN_TEXT, "de"),
        (FRENCH_TEXT, "fr"),
        (SPANISH_TEXT, "es"),
    ])
    def test_artificiality_decreases(self, text, lang):
        """Балл искусственности уменьшается после обработки."""
        result = humanize(text, lang=lang, profile="web", intensity=80, seed=42)
        before = result.metrics_before.get("artificiality_score", 0)
        after = result.metrics_after.get("artificiality_score", 0)
        assert after <= before  # Должен уменьшиться или остаться равным
