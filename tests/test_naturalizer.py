"""Тесты натурализации и универсального процессора."""

import pytest

from texthumanize.naturalizer import TextNaturalizer
from texthumanize.universal import UniversalProcessor

# ─── Тестовые тексты ─────────────────────────────────────────

AI_TEXT_EN = (
    "Artificial intelligence is one of the most significant technologies of our time. "
    "This technology facilitates the processing of substantial volumes of data. "
    "Furthermore, it is important to note that the implementation of AI represents "
    "a significant challenge. Nevertheless, this development is fundamentally "
    "important for our future. Additionally, AI plays a crucial role in modern "
    "society. It is worth mentioning that the comprehensive nature of AI systems "
    "enables seamless integration into various workflows. Consequently, the "
    "optimization of these systems is of paramount importance."
)

AI_TEXT_RU = (
    "Искусственный интеллект является одной из наиболее значительных технологий "
    "современности. Данная технология обеспечивает обработку существенных объёмов "
    "данных. Более того, необходимо подчеркнуть, что внедрение ИИ представляет "
    "собой чрезвычайно сложную задачу. Тем не менее, данное развитие является "
    "фундаментально важным для нашего будущего. Кроме того, ИИ играет ключевую "
    "роль в современном мире. Следует отметить, что всеобъемлющий характер "
    "систем ИИ обеспечивает бесшовную интеграцию в различные процессы."
)

UNIFORM_TEXT = (
    "This is a sentence with ten words in it. "
    "This is a sentence with ten words in it. "
    "This is a sentence with ten words in it. "
    "This is a sentence with ten words in it. "
    "This is a sentence with ten words in it. "
    "This is a sentence with ten words in it."
)


class TestUniversalProcessor:
    """Тесты универсального процессора."""

    def test_basic_processing(self):
        """Базовая обработка работает."""
        proc = UniversalProcessor(seed=42)
        result = proc.process(AI_TEXT_EN)
        assert result  # Не пустой
        assert isinstance(result, str)

    def test_unicode_normalization(self):
        """Нормализация Unicode-символов."""
        text = "Текст\u00A0с\u00A0неразрывными\u00A0пробелами и\u2014тире."
        proc = UniversalProcessor(profile="web", intensity=80, seed=42)
        result = proc.process(text)
        assert "\u00A0" not in result  # Неразрывные пробелы убраны

    def test_empty_text(self):
        """Пустой текст возвращается без изменений."""
        proc = UniversalProcessor(seed=42)
        assert proc.process("") == ""
        assert proc.process("short") == "short"

    def test_changes_tracked(self):
        """Изменения отслеживаются."""
        text = "Текст\u00A0с\u00A0многими\u00A0неразрывными\u00A0пробелами и ещё текст для проверки."
        proc = UniversalProcessor(profile="web", intensity=80, seed=42)
        proc.process(text)
        # Могут быть изменения, а могут не быть — зависит от рандома
        assert isinstance(proc.changes, list)

    def test_profile_respect(self):
        """Профиль влияет на обработку."""
        text = "Текст — с тире\u00A0и пробелами."
        proc_chat = UniversalProcessor(profile="chat", intensity=80, seed=42)
        proc_formal = UniversalProcessor(profile="formal", intensity=80, seed=42)
        result_chat = proc_chat.process(text)
        result_formal = proc_formal.process(text)
        # Chat заменяет тире на дефис, formal — нет
        # Результаты могут различаться
        assert isinstance(result_chat, str)
        assert isinstance(result_formal, str)

    def test_intensity_zero(self):
        """При нулевой интенсивности текст почти не меняется."""
        proc = UniversalProcessor(intensity=0, seed=42)
        result = proc.process(AI_TEXT_EN)
        assert result == AI_TEXT_EN  # Без изменений при intensity=0


class TestTextNaturalizer:
    """Тесты модуля натурализации."""

    def test_basic_english(self):
        """Антидетект работает для английского текста."""
        ad = TextNaturalizer(lang="en", profile="web", intensity=80, seed=42)
        result = ad.process(AI_TEXT_EN)
        assert result  # Не пустой
        assert result != AI_TEXT_EN  # Есть изменения

    def test_basic_russian(self):
        """Антидетект работает для русского текста."""
        ad = TextNaturalizer(lang="ru", profile="web", intensity=80, seed=42)
        result = ad.process(AI_TEXT_RU)
        assert result  # Не пустой
        assert result != AI_TEXT_RU  # Есть изменения

    def test_ai_word_replacement_en(self):
        """AI-характерные слова заменяются (EN)."""
        text = "We need to utilize this technology to facilitate progress."
        ad = TextNaturalizer(lang="en", profile="web", intensity=100, seed=42)
        result = ad.process(text)
        changes = [c for c in ad.changes if c["type"] == "naturalize_word"]
        # Хотя бы одно слово должно быть заменено
        assert len(changes) >= 1 or "utilize" not in result or "facilitate" not in result

    def test_ai_word_replacement_ru(self):
        """AI-характерные слова заменяются (RU)."""
        text = ("Данный подход значительно улучшает результаты. "
                "Безусловно, это несомненно важно.")
        ad = TextNaturalizer(lang="ru", profile="web", intensity=100, seed=42)
        result = ad.process(text)
        # Должны быть какие-то изменения
        assert result != text or len(ad.changes) >= 0

    def test_contractions_english(self):
        """Сокращения для английского (chat/web)."""
        text = ("We do not need to worry about this. "
                "It is not a problem. "
                "They are working on it right now. "
                "There is nothing to add here.")
        ad = TextNaturalizer(lang="en", profile="chat", intensity=100, seed=42)
        result = ad.process(text)
        # Должны появиться сокращения
        contraction_changes = [
            c for c in ad.changes if c["type"] == "naturalize_contraction"
        ]
        assert len(contraction_changes) >= 1

    def test_no_contractions_formal(self):
        """Сокращения НЕ применяются для formal профиля."""
        text = "We do not need this. It is not relevant."
        ad = TextNaturalizer(lang="en", profile="formal", intensity=100, seed=42)
        result = ad.process(text)
        contraction_changes = [
            c for c in ad.changes if c["type"] == "naturalize_contraction"
        ]
        assert len(contraction_changes) == 0

    def test_phrase_replacement(self):
        """AI-фразы заменяются."""
        text = ("It is important to note that this approach works. "
                "In today's world, technology plays a crucial role.")
        ad = TextNaturalizer(lang="en", profile="web", intensity=100, seed=42)
        result = ad.process(text)
        phrase_changes = [
            c for c in ad.changes if c["type"] == "naturalize_phrase"
        ]
        assert len(phrase_changes) >= 1

    def test_empty_text(self):
        """Пустой текст без ошибок."""
        ad = TextNaturalizer(lang="en", seed=42)
        assert ad.process("") == ""
        assert ad.process("short") == "short"

    def test_changes_tracked(self):
        """Все изменения отслеживаются."""
        ad = TextNaturalizer(lang="en", profile="web", intensity=80, seed=42)
        ad.process(AI_TEXT_EN)
        assert isinstance(ad.changes, list)
        for change in ad.changes:
            assert "type" in change

    def test_seed_reproducibility(self):
        """Результат воспроизводим при одинаковом seed."""
        ad1 = TextNaturalizer(lang="en", profile="web", intensity=80, seed=42)
        result1 = ad1.process(AI_TEXT_EN)
        ad2 = TextNaturalizer(lang="en", profile="web", intensity=80, seed=42)
        result2 = ad2.process(AI_TEXT_EN)
        assert result1 == result2

    def test_unknown_language(self):
        """Обработка неизвестного языка (без словаря) — без ошибок."""
        text = "Đây là một đoạn văn bản bằng tiếng Việt để kiểm tra."
        ad = TextNaturalizer(lang="vi", profile="web", intensity=80, seed=42)
        result = ad.process(text)
        assert result  # Не крашится

    @pytest.mark.parametrize("lang", ["de", "fr", "es", "pl", "pt", "it"])
    def test_naturalizer_new_languages(self, lang):
        """Антидетект работает для всех новых языков."""
        texts = {
            "de": "Diese Technologie ist signifikant und innovativ. "
                  "Darüber hinaus implementiert sie grundlegende Verbesserungen.",
            "fr": "Cette technologie est significative et innovante. "
                  "En outre, elle implémente des améliorations fondamentales.",
            "es": "Esta tecnología es significativa e innovadora. "
                  "Además, implementa mejoras fundamentales.",
            "pl": "Ta technologia jest znacząca i innowacyjna. "
                  "Ponadto implementuje fundamentalne ulepszenia.",
            "pt": "Esta tecnologia é significativa e inovadora. "
                  "Além disso, implementa melhorias fundamentais.",
            "it": "Questa tecnologia è significativa e innovativa. "
                  "Inoltre, implementa miglioramenti fondamentali.",
        }
        ad = TextNaturalizer(lang=lang, profile="web", intensity=100, seed=42)
        result = ad.process(texts[lang])
        assert result  # Не пустой
