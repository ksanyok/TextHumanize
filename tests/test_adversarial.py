"""Adversarial tests — robustness against evasion and edge cases.

Tests that the detection and humanization pipeline handles adversarial
inputs gracefully: obfuscated text, unusual formatting, multi-language
mixing, Unicode tricks, emoji injection, etc.

Run: pytest tests/test_adversarial.py -v
"""

from __future__ import annotations

import pytest

from texthumanize import detect_ai, humanize


class TestAdversarialDetection:
    """Tests for robustness of AI detection under adversarial conditions."""

    def test_homoglyph_substitution(self) -> None:
        """Text with Cyrillic lookalikes for Latin chars."""
        # 'а' (Cyrillic) instead of 'a' (Latin) in some words
        text = (
            "Furthermore, it is importаnt to note that the comprehensive "
            "implementаtion of this methodology demonstrаtes significant "
            "optimizаtion. Additionally, the robust framework facilitates "
            "seаmless integration."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert "combined_score" in result
        # Should still detect as somewhat AI-like (homoglyphs shouldn't fool it)
        assert result["combined_score"] > 0.2

    def test_zero_width_chars(self) -> None:
        """Text with zero-width Unicode characters inserted."""
        text = (
            "Furthermore\u200B, it is important\u200B to note that\u200B "
            "the comprehensive\u200B implementation demonstrates\u200B "
            "significant optimization\u200B."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_excessive_whitespace(self) -> None:
        """Text with unusual whitespace patterns."""
        text = (
            "Furthermore,   it  is   important   to  note  that   the "
            "comprehensive   implementation   demonstrates   significant "
            "optimization.   Additionally,   the   robust   framework "
            "facilitates   seamless   integration."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_all_caps(self) -> None:
        """ALL CAPS text."""
        text = (
            "FURTHERMORE, IT IS IMPORTANT TO NOTE THAT THE COMPREHENSIVE "
            "IMPLEMENTATION OF THIS METHODOLOGY DEMONSTRATES SIGNIFICANT "
            "OPTIMIZATION. ADDITIONALLY, THE ROBUST FRAMEWORK FACILITATES "
            "SEAMLESS INTEGRATION."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        # Should still work
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_mixed_language(self) -> None:
        """Text mixing English and Russian."""
        text = (
            "This technology является одной из most promising. "
            "Она utilizes processing of большие объёмы данных "
            "and facilitates automation различных процессов."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_emoji_heavy(self) -> None:
        """Text heavily laden with emoji."""
        text = (
            "Furthermore 🌟, it is important 📝 to note 🔍 that "
            "the comprehensive 🎯 implementation 🚀 demonstrates "
            "significant 💡 optimization ✨. Additionally 🌈, "
            "the robust 💪 framework 🏗️ facilitates seamless 🔗 "
            "integration 🎉."
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_single_very_long_sentence(self) -> None:
        """One extremely long sentence (no periods)."""
        text = (
            "the cat sat on the mat and the dog barked at the cat "
            "while the bird flew over the house and the fish swam "
            "in the pond near the garden where the flowers bloomed "
            "under the warm sun that shone brightly across the sky "
            "which was clear and blue with no clouds in sight and "
            "everything seemed peaceful and calm in the quiet village "
            "where people lived simple lives full of joy and happiness"
        )
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_only_numbers(self) -> None:
        """Text that is mostly numbers."""
        text = "123 456 789 012 345 678 901 234 567 890"
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)

    def test_empty_string(self) -> None:
        """Empty string should not crash."""
        result = detect_ai("", lang="en")
        assert isinstance(result, dict)
        assert result["combined_score"] == 0.0 or result["verdict"] == "human"

    def test_single_word(self) -> None:
        """Single word should not crash."""
        result = detect_ai("Hello", lang="en")
        assert isinstance(result, dict)

    def test_newlines_only(self) -> None:
        """Text of only newlines."""
        result = detect_ai("\n\n\n\n\n", lang="en")
        assert isinstance(result, dict)

    def test_repeated_sentence(self) -> None:
        """Same sentence repeated many times (common evasion trick)."""
        text = "This is fine. " * 50
        result = detect_ai(text, lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["combined_score"] <= 1.0


class TestAdversarialHumanize:
    """Tests for robustness of humanize() under adversarial inputs."""

    def test_html_entities(self) -> None:
        """Text with HTML entities."""
        text = "This &amp; that are important. Furthermore, it&#39;s essential to implement."
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 5

    def test_markdown_heavy(self) -> None:
        """Heavy markdown formatting."""
        text = (
            "# Title\n\n"
            "**Bold text** and *italic text* with `code`.\n\n"
            "1. First item\n"
            "2. Second item\n"
            "3. Third item\n\n"
            "---\n\n"
            "> Blockquote with **emphasis**.\n\n"
            "```python\nprint('hello')\n```"
        )
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)
        # Code block should be preserved
        assert "print('hello')" in result.text

    def test_very_short_text(self) -> None:
        """Very short text (1-2 words)."""
        result = humanize("Hi!", lang="en", seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) >= 1

    def test_unicode_math(self) -> None:
        """Text with mathematical Unicode symbols."""
        text = "The formula is: α² + β² = γ². Furthermore, ∑(i=1..n) = n(n+1)/2."
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)

    def test_rtl_text(self) -> None:
        """Text with RTL characters (Arabic)."""
        text = "This is مرحبا a mixed text with العربية some Arabic."
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)

    def test_huge_paragraph(self) -> None:
        """Single very large paragraph (~5000 chars)."""
        sentence = "The system processes data efficiently and produces optimal results. "
        text = sentence * 80  # ~5600 chars
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 100

    def test_tab_indentation(self) -> None:
        """Text with unusual tab indentation."""
        text = "\tFirst paragraph.\n\t\tSecond paragraph.\n\t\t\tThird paragraph."
        result = humanize(text, lang="en", seed=42)
        assert isinstance(result.text, str)


class TestAdversarialNeuralDetector:
    """Tests for robustness of neural detector components."""

    def test_neural_detector_empty(self) -> None:
        """Neural detector handles empty text."""
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect("", lang="en")
        assert isinstance(result, dict)
        assert "score" in result

    def test_neural_detector_short(self) -> None:
        """Neural detector handles very short text."""
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect("Hi", lang="en")
        assert isinstance(result, dict)
        assert 0.0 <= result["score"] <= 1.0

    def test_neural_lm_empty(self) -> None:
        """Neural LM handles empty text."""
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        ppl = nlm.perplexity("")
        assert isinstance(ppl, float)
        assert ppl > 0

    def test_neural_lm_short(self) -> None:
        """Neural LM handles very short text."""
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        ppl = nlm.perplexity("Hi")
        assert isinstance(ppl, float)
        assert ppl > 0

    def test_word_vec_empty(self) -> None:
        """WordVec handles empty text."""
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        sim = wv.sentence_similarity("", "")
        assert isinstance(sim, float)

    def test_word_vec_unicode(self) -> None:
        """WordVec handles Unicode text."""
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        sim = wv.sentence_similarity("Привет мир", "Hello world")
        assert isinstance(sim, float)
        assert -1.0 <= sim <= 1.0

    def test_hmm_tagger_empty(self) -> None:
        """HMM tagger handles empty text."""
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("")
        assert tags == []

    def test_hmm_tagger_punctuation_only(self) -> None:
        """HMM tagger handles punctuation-only text."""
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("... !!! ???")
        assert all(tag == "PUNCT" for _, tag in tags)
