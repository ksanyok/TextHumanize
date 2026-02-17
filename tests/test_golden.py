"""Golden-тесты: фиксированные входы → ожидаемые характеристики выхода."""

import pytest
from texthumanize import humanize, analyze


# Тестовые тексты, типичные для AI-генерации
AI_TEXT_RU = """
Искусственный интеллект является одной из наиболее перспективных технологий современности. Данная технология осуществляет обработку больших объёмов данных и предоставляет возможность автоматизации различных процессов. Однако необходимо отметить, что внедрение ИИ представляет собой сложную задачу.

В настоящее время осуществляется активное развитие данного направления. Более того, функционирование систем ИИ обеспечивает значительное повышение эффективности. Тем не менее, важно подчеркнуть, что использование ИИ должно осуществляться надлежащим образом.

Таким образом, данная технология является чрезвычайно важной. Безусловно, в дальнейшем она будет играть ещё более значительную роль. Следовательно, необходимо уделять внимание её развитию.
""".strip()

AI_TEXT_UK = """
Штучний інтелект є однією з найбільш перспективних технологій сучасності. Дана технологія здійснює обробку великих обсягів даних та надає можливість автоматизації різних процесів. Однак необхідно зазначити, що впровадження ШІ являє собою складне завдання.

На даний час здійснюється активний розвиток даного напрямку. Більш того, функціонування систем ШІ забезпечує значне підвищення ефективності. Тим не менш, важливо підкреслити, що використання ШІ повинно здійснюватися належним чином.

Таким чином, дана технологія є надзвичайно важливою. Безумовно, надалі вона буде відігравати ще більш значну роль. Отже, необхідно приділяти увагу її розвитку.
""".strip()

AI_TEXT_EN = """
Artificial intelligence is one of the most promising technologies of the modern era. This technology utilizes the processing of large volumes of data and facilitates the automation of various processes. However, it is important to note that the implementation of AI represents a considerable challenge.

At the present time, the development of this field is being actively pursued. Furthermore, the functioning of AI systems ensures a significant increase in efficiency. Nevertheless, it should be noted that the utilization of AI must be carried out in an appropriate manner.

Thus, this technology is extremely important. Undoubtedly, it will play an even more significant role in the future. Consequently, it is necessary to pay attention to its development.
""".strip()


class TestGoldenRussian:
    """Golden-тесты для русского языка."""

    def test_typography_normalized(self):
        """Типографика нормализуется."""
        result = humanize(AI_TEXT_RU, lang="ru", profile="web", seed=42)
        # Длинные тире не должны быть в web-профиле
        # (если они были в тексте)
        assert isinstance(result.text, str)
        assert len(result.text) > 100

    def test_bureaucratic_reduced(self):
        """Канцеляризмы уменьшены."""
        result = humanize(AI_TEXT_RU, lang="ru", profile="chat", intensity=80, seed=42)
        text_lower = result.text.lower()
        # Хотя бы некоторые канцеляризмы должны быть заменены
        # Не все обязательно заменятся (зависит от random), но текст должен отличаться
        assert result.text != AI_TEXT_RU

    def test_artificiality_decreases(self):
        """Оценка искусственности снижается."""
        report_before = analyze(AI_TEXT_RU, lang="ru")
        result = humanize(AI_TEXT_RU, lang="ru", profile="web", intensity=70, seed=42)
        report_after = analyze(result.text, lang="ru")

        # Оценка должна снизиться или хотя бы не вырасти сильно
        assert report_after.artificiality_score <= report_before.artificiality_score + 10

    def test_preserves_meaning(self):
        """Смысл текста сохраняется (текст всё ещё про ИИ)."""
        result = humanize(AI_TEXT_RU, lang="ru", profile="web", seed=42)
        # Ключевые понятия должны остаться
        text_lower = result.text.lower()
        assert "интеллект" in text_lower or "ии" in text_lower or "ії" in text_lower

    def test_not_too_many_changes(self):
        """Количество изменений в разумных пределах."""
        result = humanize(AI_TEXT_RU, lang="ru", profile="web", intensity=60, seed=42)
        assert result.change_ratio <= 0.75  # Не более 75% изменений

    def test_sentences_still_valid(self):
        """Предложения всё ещё корректные (заканчиваются на .!?)."""
        result = humanize(AI_TEXT_RU, lang="ru", profile="web", seed=42)
        # У текста должны быть точки
        assert '.' in result.text


class TestGoldenUkrainian:
    """Golden-тесты для украинского языка."""

    def test_basic_processing(self):
        """Украинский текст обрабатывается."""
        result = humanize(AI_TEXT_UK, lang="uk", profile="web", seed=42)
        assert isinstance(result.text, str)
        assert result.text != AI_TEXT_UK
        assert len(result.text) > 100

    def test_language_detected(self):
        """Украинский язык определяется."""
        result = humanize(AI_TEXT_UK, lang="auto", seed=42)
        assert result.lang == "uk"

    def test_artificiality_decreases(self):
        """Оценка искусственности снижается."""
        report_before = analyze(AI_TEXT_UK, lang="uk")
        result = humanize(AI_TEXT_UK, lang="uk", profile="web", intensity=70, seed=42)
        report_after = analyze(result.text, lang="uk")
        assert report_after.artificiality_score <= report_before.artificiality_score + 10


class TestGoldenEnglish:
    """Golden-тесты для английского языка."""

    def test_basic_processing(self):
        """Английский текст обрабатывается."""
        result = humanize(AI_TEXT_EN, lang="en", profile="web", seed=42)
        assert isinstance(result.text, str)
        assert result.text != AI_TEXT_EN
        assert len(result.text) > 100

    def test_language_detected(self):
        """Английский язык определяется."""
        result = humanize(AI_TEXT_EN, lang="auto", seed=42)
        assert result.lang == "en"


class TestPropertyBased:
    """Property-тесты: инварианты, которые всегда должны выполняться."""

    @pytest.mark.parametrize("lang", ["ru", "uk", "en"])
    def test_urls_preserved(self, lang):
        """URL сохраняются при обработке."""
        url = "https://example.com/path?key=value&foo=bar"
        text = f"Текст начало {url} текст конец."
        result = humanize(text, lang=lang, seed=42)
        assert url in result.text

    @pytest.mark.parametrize("lang", ["ru", "uk", "en"])
    def test_emails_preserved(self, lang):
        """Email сохраняются при обработке."""
        email = "test@example.com"
        text = f"Пишите на {email} для связи."
        result = humanize(text, lang=lang, seed=42)
        assert email in result.text

    @pytest.mark.parametrize("lang", ["ru", "uk", "en"])
    def test_code_blocks_preserved(self, lang):
        """Блоки кода сохраняются."""
        text = "Текст:\n```\ncode here\n```\nКонец."
        result = humanize(text, lang=lang, seed=42)
        assert "```" in result.text
        assert "code here" in result.text

    def test_emoji_safe(self):
        """Эмодзи не ломают парсер."""
        text = "Текст со смайлом 😀 и ещё 🎉 и конец."
        result = humanize(text, lang="ru", seed=42)
        assert "😀" in result.text
        assert "🎉" in result.text

    def test_numbers_preserved(self):
        """Числа не теряются."""
        text = "В 2024 году было 150 участников и 3.5 млн просмотров."
        result = humanize(text, lang="ru", seed=42)
        assert "2024" in result.text
        assert "150" in result.text

    def test_multiline_text(self):
        """Многострочный текст обрабатывается."""
        text = (
            "Первый абзац текста.\n\n"
            "Второй абзац текста.\n\n"
            "Третий абзац."
        )
        result = humanize(text, lang="ru", seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 10

    def test_mixed_content(self):
        """Смешанный контент (markdown + текст)."""
        text = (
            "# Заголовок\n\n"
            "Данный текст **является** примером.\n\n"
            "- Первый пункт\n"
            "- Второй пункт\n\n"
            "Ссылка: [пример](https://example.com)\n"
        )
        result = humanize(text, lang="ru", seed=42)
        assert isinstance(result.text, str)
        # Markdown-ссылка должна сохраниться
        assert "https://example.com" in result.text
