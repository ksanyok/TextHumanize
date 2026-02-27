"""Тесты нормализации типографики."""

from texthumanize.normalizer import TypographyNormalizer


class TestTypographyNormalizer:
    """Тесты нормализатора типографики."""

    def test_em_dash_to_short_web(self):
        """Длинное тире → короткое тире (web)."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("Текст — продолжение")
        assert "–" in result or "-" in result
        assert "—" not in result

    def test_em_dash_to_hyphen_chat(self):
        """Длинное тире → дефис (chat)."""
        norm = TypographyNormalizer(profile="chat")
        result = norm.normalize("Текст — продолжение")
        assert "-" in result

    def test_em_dash_stays_formal(self):
        """Длинное тире остаётся в formal профиле."""
        norm = TypographyNormalizer(profile="formal")
        result = norm.normalize("Текст — продолжение")
        assert "—" in result

    def test_quotes_to_simple_web(self):
        """Кавычки «» → "" (web)."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize('Слово «пример» конец')
        assert '«' not in result
        assert '»' not in result
        assert '"' in result

    def test_quotes_stay_formal(self):
        """Кавычки остаются «» в formal."""
        norm = TypographyNormalizer(profile="formal")
        result = norm.normalize('Слово «пример» конец')
        assert '«' in result
        assert '»' in result

    def test_ellipsis_to_dots_web(self):
        """Многоточие … → ... (web)."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("Текст продолжается…")
        assert "..." in result
        assert "…" not in result

    def test_ellipsis_stays_formal(self):
        """Многоточие остаётся … в formal."""
        norm = TypographyNormalizer(profile="formal")
        result = norm.normalize("Текст...")
        assert "…" in result

    def test_nbsp_removal(self):
        """Неразрывные пробелы убираются (web)."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("Текст\u00A0продолжение")
        assert "\u00A0" not in result
        assert " " in result

    def test_multiple_spaces(self):
        """Множественные пробелы → одинарный."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("Текст    продолжение")
        assert "    " not in result

    def test_space_before_punctuation(self):
        """Пробел перед знаком убирается."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("Текст , продолжение .")
        assert " ," not in result
        assert " ." not in result

    def test_empty_text(self):
        """Пустой текст не вызывает ошибку."""
        norm = TypographyNormalizer(profile="web")
        result = norm.normalize("")
        assert result == ""

    def test_no_changes_for_plain_text(self):
        """Простой текст без типографики не меняется сильно."""
        norm = TypographyNormalizer(profile="web")
        text = "Простой текст без спецсимволов."
        result = norm.normalize(text)
        assert result == text
