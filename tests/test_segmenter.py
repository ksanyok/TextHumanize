"""Тесты сегментатора — защита URL, кода и других элементов."""

import pytest
from texthumanize.segmenter import Segmenter, SegmentedText


class TestSegmenter:
    """Тесты сегментатора."""

    def setup_method(self):
        self.segmenter = Segmenter()

    def test_url_protection(self):
        """URL не изменяются."""
        text = "Смотрите на https://example.com/path?q=1 для деталей."
        result = self.segmenter.segment(text)
        assert "https://example.com/path?q=1" not in result.text
        restored = result.restore(result.text)
        assert "https://example.com/path?q=1" in restored

    def test_email_protection(self):
        """Email не изменяются."""
        text = "Пишите на user@example.com для связи."
        result = self.segmenter.segment(text)
        assert "user@example.com" not in result.text
        restored = result.restore(result.text)
        assert "user@example.com" in restored

    def test_code_block_protection(self):
        """Блоки кода не изменяются."""
        text = "Пример:\n```python\nprint('hello')\n```\nКонец."
        result = self.segmenter.segment(text)
        assert "print('hello')" not in result.text
        restored = result.restore(result.text)
        assert "print('hello')" in restored

    def test_inline_code_protection(self):
        """Inline-код не изменяется."""
        text = "Используйте `npm install` для установки."
        result = self.segmenter.segment(text)
        assert "`npm install`" not in result.text
        restored = result.restore(result.text)
        assert "`npm install`" in restored

    def test_html_tag_protection(self):
        """HTML-теги не изменяются."""
        text = "Текст <strong>важный</strong> конец."
        result = self.segmenter.segment(text)
        assert "<strong>" not in result.text
        restored = result.restore(result.text)
        assert "<strong>" in restored

    def test_hashtag_protection(self):
        """Хэштеги не изменяются."""
        text = "Классный пост #TextHumanize #AI"
        result = self.segmenter.segment(text)
        assert "#TextHumanize" not in result.text
        restored = result.restore(result.text)
        assert "#TextHumanize" in restored

    def test_mention_protection(self):
        """@упоминания не изменяются."""
        text = "Спасибо @user123 за помощь."
        result = self.segmenter.segment(text)
        assert "@user123" not in result.text
        restored = result.restore(result.text)
        assert "@user123" in restored

    def test_markdown_link_protection(self):
        """Markdown-ссылки не изменяются."""
        text = "Смотрите [документацию](https://docs.example.com)."
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "[документацию](https://docs.example.com)" in restored

    def test_brand_term_protection(self):
        """Брендовые термины не изменяются."""
        segmenter = Segmenter(preserve={"brand_terms": ["RankBot AI"]})
        text = "Продукт RankBot AI отлично работает."
        result = segmenter.segment(text)
        assert "RankBot AI" not in result.text
        restored = result.restore(result.text)
        assert "RankBot AI" in restored

    def test_number_protection(self):
        """Числа защищаются при включенной опции."""
        segmenter = Segmenter(preserve={"numbers": True})
        text = "Скидка 25% на товар за 150 руб."
        result = segmenter.segment(text)
        restored = result.restore(result.text)
        assert "25%" in restored
        assert "150" in restored

    def test_multiple_elements(self):
        """Множественные элементы защищаются корректно."""
        text = (
            "Проект на https://github.com, email: dev@test.com, "
            "код: `npm run build`, тег #release."
        )
        result = self.segmenter.segment(text)
        restored = result.restore(result.text)
        assert "https://github.com" in restored
        assert "dev@test.com" in restored
        assert "`npm run build`" in restored
        assert "#release" in restored

    def test_no_protection(self):
        """Без защиты ничего не заменяется."""
        segmenter = Segmenter(preserve={
            "code_blocks": False,
            "urls": False,
            "emails": False,
            "hashtags": False,
            "mentions": False,
            "markdown": False,
            "html": False,
            "numbers": False,
        })
        text = "Текст https://example.com user@test.com"
        result = segmenter.segment(text)
        # URL и email всё ещё в тексте
        assert "https://example.com" in result.text
        assert "user@test.com" in result.text

    def test_empty_text(self):
        """Пустой текст обрабатывается без ошибок."""
        result = self.segmenter.segment("")
        assert result.text == ""
        assert result.segments == []
