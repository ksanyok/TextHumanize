"""Тесты новых возможностей v0.12.0.

- Защита HTML-блоков и списков
- Защита доменов (bare domains)
- Placeholder safety (без утечек \x00)
- Новые языки: арабский, китайский, японский, корейский, турецкий
- Водяные знаки в пайплайне
- Детекция новых языков
"""

import re

import pytest

from texthumanize import humanize
from texthumanize.lang import get_lang_pack, has_deep_support, LANGUAGES
from texthumanize.lang_detect import detect_language
from texthumanize.pipeline import Pipeline
from texthumanize.segmenter import Segmenter, has_placeholder, is_placeholder_word
from texthumanize.utils import HumanizeOptions
from texthumanize.watermark import WatermarkDetector


# ═══════════════════════════════════════════════════════════════
#  HTML BLOCK & LIST PROTECTION
# ═══════════════════════════════════════════════════════════════

class TestHTMLProtection:
    """Тесты защиты HTML-блоков и списков."""

    def setup_method(self):
        self.segmenter = Segmenter()

    def test_ul_block_protection(self):
        """<ul> блок полностью защищён."""
        text = "Список:\n<ul>\n<li>Один</li>\n<li>Два</li>\n</ul>\nКонец."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<ul>" in restored
        assert "</ul>" in restored
        assert "<li>Один</li>" in restored
        assert "<li>Два</li>" in restored

    def test_ol_block_protection(self):
        """<ol> блок полностью защищён."""
        text = "<ol>\n<li>Первый</li>\n<li>Второй</li>\n</ol>"
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<ol>" in restored
        assert "</ol>" in restored

    def test_table_block_protection(self):
        """<table> блок полностью защищён."""
        html = "<table>\n<tr><td>Ячейка</td></tr>\n</table>"
        text = f"Таблица:\n{html}\nПосле."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<table>" in restored
        assert "</table>" in restored
        assert "<td>Ячейка</td>" in restored

    def test_pre_block_protection(self):
        """<pre> блок полностью защищён."""
        text = "Код:\n<pre>print('hello')</pre>\nОстаток."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<pre>print('hello')</pre>" in restored

    def test_blockquote_protection(self):
        """<blockquote> блок защищён."""
        text = "<blockquote>Цитата автора.</blockquote>"
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<blockquote>Цитата автора.</blockquote>" in restored

    def test_li_item_protection(self):
        """Отдельные <li> элементы защищены."""
        text = "Элемент: <li>Пункт списка</li> далее."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<li>Пункт списка</li>" in restored

    def test_h2_tag_protection(self):
        """<h2> теги защищены."""
        text = "<h2>Заголовок</h2>\nТекст параграфа."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<h2>" in restored
        assert "</h2>" in restored

    def test_nested_html_content(self):
        """Вложенный HTML-контент восстанавливается корректно."""
        text = (
            "Вступление.\n"
            "<ul>\n"
            "<li><strong>Жирный</strong> текст</li>\n"
            "<li>Обычный текст</li>\n"
            "</ul>\n"
            "Заключение."
        )
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "<strong>Жирный</strong>" in restored
        assert "</ul>" in restored


# ═══════════════════════════════════════════════════════════════
#  DOMAIN PROTECTION
# ═══════════════════════════════════════════════════════════════

class TestDomainProtection:
    """Тесты защиты доменных имён."""

    def setup_method(self):
        self.segmenter = Segmenter()

    def test_simple_domain(self):
        """Простой домен site.com защищён."""
        text = "Посетите site.com для получения информации."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "site.com" in restored

    def test_domain_com_ua(self):
        """Домен site.com.ua защищён."""
        text = "Наш сайт travel.com.ua предлагает лучшие туры."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "travel.com.ua" in restored

    def test_domain_kh_ua(self):
        """Домен site.kh.ua защищён."""
        text = "Посетите portal.kh.ua для деталей."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "portal.kh.ua" in restored

    def test_domain_co_uk(self):
        """Домен site.co.uk защищён."""
        text = "See example.co.uk for details."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "example.co.uk" in restored

    def test_domain_io(self):
        """Домен .io защищён."""
        text = "Check out myapp.io for the latest."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "myapp.io" in restored

    def test_domain_dev(self):
        """Домен .dev защищён."""
        text = "Our api.dev docs are here."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "api.dev" in restored

    def test_multiple_domains(self):
        """Несколько доменов в одном тексте."""
        text = "Сайты travel.com.ua и booking.com предлагают туры."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "travel.com.ua" in restored
        assert "booking.com" in restored


# ═══════════════════════════════════════════════════════════════
#  PLACEHOLDER SAFETY
# ═══════════════════════════════════════════════════════════════

class TestPlaceholderSafety:
    """Тесты безопасности плейсхолдеров (без утечки \x00)."""

    def test_no_placeholder_leak_simple(self):
        """Простой текст не содержит плейсхолдер-артефактов."""
        result = humanize(
            "Это текст для обработки. Необходимо проверить качество.",
            lang="ru",
        )
        assert "\x00" not in result.text
        assert "THZ_" not in result.text

    def test_no_placeholder_leak_with_html(self):
        """HTML-контент не вызывает утечки плейсхолдеров."""
        text = (
            "<h2>Заголовок</h2>\n"
            "Первый параграф текста. Это важная информация.\n"
            "<ul>\n<li>Первый пункт</li>\n<li>Второй пункт</li>\n</ul>\n"
            "Заключительный параграф."
        )
        result = humanize(text, lang="ru")
        assert "\x00" not in result.text
        assert "THZ_" not in result.text

    def test_no_placeholder_leak_with_urls(self):
        """URL-содержимое не вызывает утечки плейсхолдеров."""
        text = (
            "Для деталей посетите https://example.com/page?q=test. "
            "Также смотрите http://docs.site.org/guide. "
            "Контакт: admin@example.com."
        )
        result = humanize(text, lang="ru")
        assert "\x00" not in result.text
        assert "THZ_" not in result.text

    def test_no_placeholder_leak_with_code(self):
        """Код не вызывает утечки плейсхолдеров."""
        text = (
            "Установите пакет командой `pip install texthumanize`. "
            "Затем выполните необходимую конфигурацию."
        )
        result = humanize(text, lang="ru")
        assert "\x00" not in result.text
        assert "THZ_" not in result.text

    def test_no_placeholder_leak_with_domains(self):
        """Доменные имена не вызывают утечки плейсхолдеров."""
        text = (
            "Наш сайт travel.com.ua предлагает лучшие туры. "
            "Бронирование на booking.com. Информация на info.kh.ua."
        )
        result = humanize(text, lang="uk")
        assert "\x00" not in result.text
        assert "THZ_" not in result.text

    def test_has_placeholder_function(self):
        """has_placeholder() корректно определяет плейсхолдеры."""
        assert has_placeholder("\x00THZ_HTML_TAG_1\x00")
        assert has_placeholder("text \x00THZ_URL_5\x00 more")
        assert not has_placeholder("normal text without placeholders")
        assert not has_placeholder("")

    def test_is_placeholder_word_function(self):
        """is_placeholder_word() корректно определяет слово-плейсхолдер."""
        assert is_placeholder_word("\x00THZ_HTML_TAG_1\x00")
        assert not is_placeholder_word("normal_word")
        assert not is_placeholder_word("")


# ═══════════════════════════════════════════════════════════════
#  NEW LANGUAGES
# ═══════════════════════════════════════════════════════════════

class TestNewLanguages:
    """Тесты новых языков: ar, zh, ja, ko, tr."""

    def test_all_14_languages_registered(self):
        """Все 14 языков зарегистрированы."""
        expected = {"en", "ru", "uk", "de", "fr", "es", "pl", "pt", "it",
                    "ar", "zh", "ja", "ko", "tr"}
        assert set(LANGUAGES.keys()) == expected

    def test_all_14_have_deep_support(self):
        """Все 14 языков имеют глубокую поддержку."""
        for lang in ("en", "ru", "uk", "de", "fr", "es", "pl", "pt", "it",
                      "ar", "zh", "ja", "ko", "tr"):
            assert has_deep_support(lang), f"{lang} должен иметь глубокую поддержку"

    # ── Arabic ────────────────────────────────────────────────

    def test_arabic_lang_pack(self):
        """Арабский языковой пакет загружается."""
        pack = get_lang_pack("ar")
        assert pack["code"] == "ar"
        assert len(pack["bureaucratic"]) >= 50
        assert len(pack["synonyms"]) >= 50

    def test_arabic_detection(self):
        """Арабский текст детектируется."""
        text = "الذكاء الاصطناعي هو أحد أهم التقنيات في عصرنا الحالي"
        lang = detect_language(text)
        assert lang == "ar"

    def test_arabic_humanize(self):
        """Арабский текст обрабатывается без ошибок."""
        text = "يجب التأكيد على أهمية تنفيذ هذا المشروع. من الضروري اتخاذ الإجراءات اللازمة."
        result = humanize(text, lang="ar")
        assert result.text  # Не пустой результат
        assert "\x00" not in result.text

    # ── Chinese ───────────────────────────────────────────────

    def test_chinese_lang_pack(self):
        """Китайский языковой пакет загружается."""
        pack = get_lang_pack("zh")
        assert pack["code"] == "zh"
        assert len(pack["bureaucratic"]) >= 50
        assert len(pack["synonyms"]) >= 50

    def test_chinese_detection(self):
        """Китайский текст детектируется."""
        text = "人工智能是当今时代最重要的技术之一"
        lang = detect_language(text)
        assert lang == "zh"

    def test_chinese_humanize(self):
        """Китайский текст обрабатывается без ошибок."""
        text = "必须强调实施该项目的重要性。有必要采取相应的措施来确保项目的顺利进行。"
        result = humanize(text, lang="zh")
        assert result.text
        assert "\x00" not in result.text

    # ── Japanese ──────────────────────────────────────────────

    def test_japanese_lang_pack(self):
        """Японский языковой пакет загружается."""
        pack = get_lang_pack("ja")
        assert pack["code"] == "ja"
        assert len(pack["bureaucratic"]) >= 40
        assert len(pack["synonyms"]) >= 40

    def test_japanese_detection(self):
        """Японский текст детектируется."""
        text = "人工知能は現代において最も重要な技術のひとつです"
        lang = detect_language(text)
        assert lang == "ja"

    def test_japanese_humanize(self):
        """Японский текст обрабатывается без ошибок."""
        text = "このプロジェクトの実施の重要性を強調しなければなりません。必要な措置を講じる必要があります。"
        result = humanize(text, lang="ja")
        assert result.text
        assert "\x00" not in result.text

    # ── Korean ────────────────────────────────────────────────

    def test_korean_lang_pack(self):
        """Корейский языковой пакет загружается."""
        pack = get_lang_pack("ko")
        assert pack["code"] == "ko"
        assert len(pack["bureaucratic"]) >= 40
        assert len(pack["synonyms"]) >= 40

    def test_korean_detection(self):
        """Корейский текст детектируется."""
        text = "인공지능은 현대 시대에서 가장 중요한 기술 중 하나입니다"
        lang = detect_language(text)
        assert lang == "ko"

    def test_korean_humanize(self):
        """Корейский текст обрабатывается без ошибок."""
        text = "이 프로젝트의 실행 중요성을 강조해야 합니다. 필요한 조치를 취해야 합니다."
        result = humanize(text, lang="ko")
        assert result.text
        assert "\x00" not in result.text

    # ── Turkish ───────────────────────────────────────────────

    def test_turkish_lang_pack(self):
        """Турецкий языковой пакет загружается."""
        pack = get_lang_pack("tr")
        assert pack["code"] == "tr"
        assert len(pack["bureaucratic"]) >= 40
        assert len(pack["synonyms"]) >= 40

    def test_turkish_detection(self):
        """Турецкий текст детектируется."""
        text = "Yapay zeka günümüzün en önemli teknolojilerinden biridir. Bu gelişme ülkemiz için çok değerlidir."
        lang = detect_language(text)
        assert lang == "tr"

    def test_turkish_humanize(self):
        """Турецкий текст обрабатывается без ошибок."""
        text = "Bu projenin uygulanmasının mühim olduğu vurgulanmalıdır. Lüzumlu tedbirlerin alınması icap etmektedir."
        result = humanize(text, lang="tr")
        assert result.text
        assert "\x00" not in result.text


# ═══════════════════════════════════════════════════════════════
#  WATERMARK PIPELINE INTEGRATION
# ═══════════════════════════════════════════════════════════════

class TestWatermarkPipeline:
    """Тесты интеграции водяных знаков в пайплайн."""

    def test_watermark_stage_in_pipeline(self):
        """Стадия watermark присутствует в STAGE_NAMES."""
        assert "watermark" in Pipeline.STAGE_NAMES
        # Должна быть первой (до segmentation)
        idx_wm = Pipeline.STAGE_NAMES.index("watermark")
        idx_seg = Pipeline.STAGE_NAMES.index("segmentation")
        assert idx_wm < idx_seg

    def test_zero_width_chars_cleaned(self):
        """Zero-width символы удаляются при обработке."""
        # Вставляем zero-width space в текст
        text = "Это\u200bтестовый\u200bтекст для проверки."
        detector = WatermarkDetector(lang="ru")
        report = detector.detect(text)
        assert report.has_watermarks
        assert "zero_width_characters" in report.watermark_types
        assert "\u200b" not in report.cleaned_text

    def test_watermark_cleaning_in_humanize(self):
        """Водяные знаки очищаются при humanize()."""
        text = "Это\u200b очень\u200b важный\u200b текст. Необходимо проверить его качество."
        result = humanize(text, lang="ru")
        assert "\u200b" not in result.text

    def test_homoglyph_detection(self):
        """Гомоглифы обнаруживаются, но кириллица не повреждается."""
        # Текст с fullwidth Latin 'a' (U+FF41) — настоящий гомоглиф
        text = "Test\uff41ble text here."
        detector = WatermarkDetector(lang="en")
        report = detector.detect(text)
        assert report.has_watermarks

    def test_cyrillic_not_corrupted(self):
        """Кириллический текст не повреждается детектором гомоглифов."""
        text = "Немає жодних підстав для цього."
        detector = WatermarkDetector(lang="uk")
        report = detector.detect(text)
        # Чистый кириллический текст не должен считаться watermarked
        cleaned = report.cleaned_text
        assert "Немає" in cleaned or "немає" in cleaned


# ═══════════════════════════════════════════════════════════════
#  LANGUAGE DETECTION FOR NEW LANGUAGES
# ═══════════════════════════════════════════════════════════════

class TestNewLanguageDetection:
    """Тесты детекции новых языков."""

    def test_detect_arabic(self):
        """Арабский определяется по скрипту."""
        assert detect_language("هذا نص عربي للاختبار") == "ar"

    def test_detect_chinese(self):
        """Китайский определяется по иероглифам."""
        assert detect_language("这是一个中文测试文本") == "zh"

    def test_detect_japanese(self):
        """Японский определяется по хирагане/катакане."""
        assert detect_language("これはテストです。日本語のテキストです。") == "ja"

    def test_detect_korean(self):
        """Корейский определяется по хангылю."""
        assert detect_language("이것은 테스트입니다") == "ko"

    def test_detect_turkish(self):
        """Турецкий определяется по маркерным словам."""
        text = "Bu bir test metnidir ve günümüzün önemli gelişmelerini içerir."
        assert detect_language(text) == "tr"

    def test_arabic_not_confused_with_others(self):
        """Арабский не путается с другими языками."""
        text = "الذكاء الاصطناعي هو مستقبل التكنولوجيا"
        assert detect_language(text) == "ar"

    def test_cjk_disambiguation(self):
        """CJK языки различаются корректно."""
        # Чистый китайский (нет хираганы/катаканы/хангыля)
        zh = "人工智能技术发展迅速"
        assert detect_language(zh) == "zh"

        # Японский (содержит хирагану)
        ja = "人工知能はとても重要です"
        assert detect_language(ja) == "ja"

        # Корейский (содержит хангыль)
        ko = "인공지능은 매우 중요합니다"
        assert detect_language(ko) == "ko"


# ═══════════════════════════════════════════════════════════════
#  RESTORE ROBUSTNESS
# ═══════════════════════════════════════════════════════════════

class TestRestoreRobustness:
    """Тесты робустности restore()."""

    def test_restore_exact_match(self):
        """Точное совпадение плейсхолдера восстанавливается."""
        seg = Segmenter()
        text = "Текст https://example.com конец."
        result = seg.segment(text)
        restored = result.restore(result.text)
        assert "https://example.com" in restored
        assert "\x00" not in restored

    def test_restore_with_mixed_content(self):
        """Смешанный контент (URL + HTML + код) восстанавливается."""
        text = (
            "Ссылка: https://example.com, "
            "тег <strong>важно</strong>, "
            "код `print(1)`."
        )
        seg = Segmenter()
        result = seg.segment(text)
        restored = result.restore(result.text)
        assert "https://example.com" in restored
        assert "<strong>" in restored
        assert "`print(1)`" in restored
        assert "\x00" not in restored

    def test_restore_orphan_cleanup(self):
        """Осиротевшие плейсхолдеры очищаются."""
        seg = Segmenter()
        # Сегментируем, затем искусственно оставляем плейсхолдер
        result = seg.segment("Текст https://example.com конец.")
        # Даже если restore не найдёт матч, \x00 не должно быть в output
        text_with_orphan = result.text + " \x00THZ_UNKNOWN_999\x00"
        restored = result.restore(text_with_orphan)
        assert "\x00" not in restored
