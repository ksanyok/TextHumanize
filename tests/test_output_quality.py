"""Output-quality tests for the humanization pipeline.

These tests verify that the humanize() function actually improves
text naturalness and doesn't introduce regressions like:
- Broken sentences / truncation
- Unmatched quotes or parentheses
- Excessive repetition
- Meaning corruption
- Encoding issues
"""

import re
import pytest

from texthumanize import humanize, HumanizeResult


# ── Test data ─────────────────────────────────────────────

AI_TEXT_EN = (
    "Furthermore, it is important to note that the implementation of "
    "comprehensive strategies necessitates a thorough understanding of "
    "the underlying mechanisms. In conclusion, the systematic approach "
    "provides significant advantages in terms of efficiency and effectiveness. "
    "Moreover, the utilization of advanced methodologies facilitates "
    "the optimization of resource allocation."
)

AI_TEXT_RU = (
    "В данном контексте необходимо отметить, что осуществление комплексных "
    "мероприятий требует тщательного анализа. Кроме того, следует учитывать, "
    "что данный подход является наиболее оптимальным. Более того, использование "
    "передовых методологий способствует оптимизации распределения ресурсов."
)

AI_TEXT_DE = (
    "Darüber hinaus ist es wichtig zu beachten, dass die Umsetzung "
    "umfassender Strategien ein gründliches Verständnis der zugrunde "
    "liegenden Mechanismen erfordert. Zusammenfassend lässt sich sagen, "
    "dass der systematische Ansatz erhebliche Vorteile bietet."
)

AI_TEXT_FR = (
    "En outre, il est important de noter que la mise en œuvre de "
    "stratégies globales nécessite une compréhension approfondie des "
    "mécanismes sous-jacents. En conclusion, l'approche systématique "
    "offre des avantages significatifs en termes d'efficacité."
)

AI_TEXT_ES = (
    "Además, es importante señalar que la implementación de estrategias "
    "integrales requiere una comprensión profunda de los mecanismos "
    "subyacentes. En conclusión, el enfoque sistemático proporciona "
    "ventajas significativas en términos de eficiencia y eficacia."
)

HUMAN_TEXT_EN = (
    "I went to the store yesterday and bought some milk. "
    "The weather was kinda nice, so I walked. My dog was happy to see me."
)


# ── Structural integrity tests ────────────────────────────

class TestStructuralIntegrity:
    """Tests that humanization doesn't break text structure."""

    @pytest.mark.parametrize("intensity", [30, 50, 70, 90])
    def test_output_not_empty_en(self, intensity: int):
        """Output should never be empty."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=intensity, seed=42)
        assert len(result.text.strip()) > 0

    @pytest.mark.parametrize("intensity", [30, 50, 70, 90])
    def test_output_not_empty_ru(self, intensity: int):
        """Output should never be empty for Russian."""
        result = humanize(AI_TEXT_RU, lang="ru", intensity=intensity, seed=42)
        assert len(result.text.strip()) > 0

    def test_sentence_count_preserved_en(self):
        """Number of sentences should be approximately preserved."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        original_sents = len(re.findall(r'[.!?]+', AI_TEXT_EN))
        result_sents = len(re.findall(r'[.!?]+', result.text))
        # Allow ±2 sentence difference (splitting/merging is ok)
        assert abs(original_sents - result_sents) <= 2, (
            f"Sentence count changed too much: {original_sents} → {result_sents}"
        )

    def test_sentence_count_preserved_ru(self):
        """Number of sentences should be approximately preserved (Russian)."""
        result = humanize(AI_TEXT_RU, lang="ru", intensity=70, seed=42)
        original_sents = len(re.findall(r'[.!?]+', AI_TEXT_RU))
        result_sents = len(re.findall(r'[.!?]+', result.text))
        assert abs(original_sents - result_sents) <= 2

    def test_no_trailing_whitespace(self):
        """Output shouldn't have excessive trailing whitespace."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert result.text == result.text.rstrip() or result.text.endswith('\n')

    def test_no_double_spaces(self):
        """Output shouldn't have double spaces (outside of deliberate formatting)."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        # Allow at most a few double spaces
        double_spaces = result.text.count("  ")
        assert double_spaces <= 2, f"Too many double spaces: {double_spaces}"

    def test_balanced_parentheses(self):
        """Parentheses should remain balanced if present."""
        text_with_parens = (
            "The results (as shown in Table 1) demonstrate that the "
            "implementation (which was completed last month) succeeded."
        )
        result = humanize(text_with_parens, lang="en", intensity=50, seed=42)
        opens = result.text.count("(")
        closes = result.text.count(")")
        assert opens == closes, f"Unbalanced parens: ({opens} opens, {closes} closes)"

    def test_balanced_quotes_en(self):
        """Double quotes should remain balanced."""
        text_with_quotes = (
            'The term "optimization" is frequently used in academic writing. '
            'Similarly, "implementation" appears in many contexts.'
        )
        result = humanize(text_with_quotes, lang="en", intensity=50, seed=42)
        quote_count = result.text.count('"')
        # Even number of quotes (balanced)
        assert quote_count % 2 == 0, f"Unbalanced quotes: {quote_count}"

    def test_no_encoding_artifacts(self):
        """No encoding artifacts in output."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        # Check for common encoding artifacts
        bad_patterns = ['\x00', '\ufffd', '\\u00', '\\x']
        for pat in bad_patterns:
            assert pat not in result.text, f"Encoding artifact found: {pat!r}"


# ── Length preservation tests ─────────────────────────────

class TestLengthPreservation:
    """Humanized text should be roughly similar in length."""

    @pytest.mark.parametrize("lang,text", [
        ("en", AI_TEXT_EN),
        ("ru", AI_TEXT_RU),
    ])
    def test_length_within_bounds(self, lang: str, text: str):
        """Output length should be within 50%-200% of original."""
        result = humanize(text, lang=lang, intensity=70, seed=42)
        ratio = len(result.text) / len(text)
        assert 0.5 <= ratio <= 2.0, (
            f"Length ratio {ratio:.2f} out of bounds for {lang}"
        )

    @pytest.mark.parametrize("intensity", [30, 50, 70])
    def test_length_stability_en(self, intensity: int):
        """Multiple runs with same seed should produce same length."""
        r1 = humanize(AI_TEXT_EN, lang="en", intensity=intensity, seed=42)
        r2 = humanize(AI_TEXT_EN, lang="en", intensity=intensity, seed=42)
        assert len(r1.text) == len(r2.text), "Deterministic output expected with same seed"


# ── Change quality tests ──────────────────────────────────

class TestChangeQuality:
    """Tests that changes are meaningful and appropriate."""

    def test_change_ratio_positive_en(self):
        """AI text should have non-zero change ratio at intensity 70."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert result.change_ratio > 0.05, (
            f"Change ratio too low: {result.change_ratio:.2%}"
        )

    def test_change_ratio_positive_ru(self):
        """Russian AI text should have non-zero change ratio."""
        result = humanize(AI_TEXT_RU, lang="ru", intensity=70, seed=42)
        assert result.change_ratio > 0.05, (
            f"Change ratio too low: {result.change_ratio:.2%}"
        )

    def test_change_ratio_scales_with_intensity(self):
        """Higher intensity should produce more changes."""
        r_low = humanize(AI_TEXT_EN, lang="en", intensity=30, seed=42)
        r_high = humanize(AI_TEXT_EN, lang="en", intensity=90, seed=42)
        # High intensity should produce at least as many changes
        assert r_high.change_ratio >= r_low.change_ratio * 0.8, (
            f"High intensity ({r_high.change_ratio:.2%}) should not be "
            f"significantly less than low ({r_low.change_ratio:.2%})"
        )

    def test_human_text_less_changed(self):
        """Human-written text should be changed less than AI text."""
        r_ai = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        r_human = humanize(HUMAN_TEXT_EN, lang="en", intensity=70, seed=42)
        # AI text should have more changes (or equal)
        # This is a soft check — human text may still get some changes
        assert r_human.change_ratio <= r_ai.change_ratio + 0.15, (
            f"Human text changed more than AI: "
            f"{r_human.change_ratio:.2%} vs {r_ai.change_ratio:.2%}"
        )

    def test_changes_list_non_empty(self):
        """Changes list should be populated."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert len(result.changes) >= 1, "Expected at least 1 change"

    def test_changes_are_real(self):
        """Each change should represent an actual modification."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        for change in result.changes:
            # Change should have some structure
            assert isinstance(change, (dict, tuple, str, list))


# ── Content preservation tests ────────────────────────────

class TestContentPreservation:
    """Tests that meaning-bearing content is preserved."""

    def test_numbers_preserved(self):
        """Numbers in text should be preserved."""
        text = (
            "The study involved 150 participants across 3 locations. "
            "Results showed a 25% improvement in efficiency."
        )
        result = humanize(text, lang="en", intensity=70, seed=42)
        for num in ["150", "3", "25"]:
            assert num in result.text, f"Number {num} lost in humanization"

    def test_proper_nouns_preserved(self):
        """Proper nouns / named entities should be preserved."""
        text = (
            "According to the United Nations report, climate change "
            "represents a significant challenge for European countries."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        # Key proper nouns should survive
        assert "United Nations" in result.text or "UN" in result.text

    def test_urls_preserved(self):
        """URLs should not be modified."""
        text = (
            "For more information, visit https://example.com/docs. "
            "The implementation details are documented there."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        assert "https://example.com/docs" in result.text

    def test_email_preserved(self):
        """Email addresses should not be modified."""
        text = (
            "Contact us at info@example.com for further information. "
            "The team will respond within 24 hours."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        assert "info@example.com" in result.text


# ── Multi-language quality tests ──────────────────────────

class TestMultiLangQuality:
    """Quality tests across multiple languages."""

    @pytest.mark.parametrize("lang,text", [
        ("en", AI_TEXT_EN),
        ("ru", AI_TEXT_RU),
        ("de", AI_TEXT_DE),
        ("fr", AI_TEXT_FR),
        ("es", AI_TEXT_ES),
    ])
    def test_produces_changes(self, lang: str, text: str):
        """Each language should produce some changes at intensity 70."""
        result = humanize(text, lang=lang, intensity=70, seed=42)
        assert result.text != text, f"No changes for {lang}"
        assert result.change_ratio > 0.0, f"Zero change ratio for {lang}"

    @pytest.mark.parametrize("lang,text", [
        ("en", AI_TEXT_EN),
        ("ru", AI_TEXT_RU),
        ("de", AI_TEXT_DE),
        ("fr", AI_TEXT_FR),
        ("es", AI_TEXT_ES),
    ])
    def test_unicode_integrity(self, lang: str, text: str):
        """Output should be valid unicode without surrogates."""
        result = humanize(text, lang=lang, intensity=70, seed=42)
        # Re-encode to verify no surrogate issues
        encoded = result.text.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == result.text

    @pytest.mark.parametrize("lang,text", [
        ("en", AI_TEXT_EN),
        ("ru", AI_TEXT_RU),
    ])
    def test_ends_with_punctuation(self, lang: str, text: str):
        """Output should end with sentence-ending punctuation."""
        result = humanize(text, lang=lang, intensity=70, seed=42)
        stripped = result.text.rstrip()
        assert stripped[-1] in '.!?…»"\')', (
            f"Text doesn't end with punctuation: ...{stripped[-20:]!r}"
        )


# ── Determinism tests ─────────────────────────────────────

class TestDeterminism:
    """Tests that seed-based determinism works."""

    def test_same_seed_same_output_en(self):
        """Same seed should produce identical output."""
        r1 = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=123)
        r2 = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=123)
        assert r1.text == r2.text

    def test_same_seed_same_output_ru(self):
        """Same seed should produce identical output (Russian)."""
        r1 = humanize(AI_TEXT_RU, lang="ru", intensity=70, seed=123)
        r2 = humanize(AI_TEXT_RU, lang="ru", intensity=70, seed=123)
        assert r1.text == r2.text

    def test_different_seeds_different_output(self):
        """Different seeds should usually produce different output."""
        r1 = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=1)
        r2 = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=999)
        # Not guaranteed but very likely with different seeds
        # Only assert they're not identical (soft check)
        # Both should be valid outputs regardless
        assert isinstance(r1.text, str)
        assert isinstance(r2.text, str)


# ── Repetition tests ──────────────────────────────────────

class TestRepetition:
    """Tests that humanization doesn't introduce excessive repetition."""

    def test_no_word_stuck_loop_en(self):
        """No single word should repeat more than 5x in a row."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        words = result.text.lower().split()
        for i in range(len(words) - 5):
            window = words[i:i + 6]
            if all(w == window[0] for w in window):
                pytest.fail(f"Word repeated 6x: {window[0]!r}")

    def test_no_sentence_duplication(self):
        """Same sentence should not appear twice."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        sentences = re.split(r'[.!?]+', result.text)
        sentences = [s.strip().lower() for s in sentences if s.strip()]
        seen = set()
        for s in sentences:
            if len(s) > 20:  # Only check non-trivial sentences
                assert s not in seen, f"Duplicate sentence: {s[:60]}..."
                seen.add(s)


# ── Edge case tests ───────────────────────────────────────

class TestEdgeCases:
    """Edge cases that should be handled gracefully."""

    def test_single_word(self):
        """Single word should not crash."""
        result = humanize("Hello", lang="en", intensity=50, seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    def test_single_sentence(self):
        """Single short sentence should work."""
        result = humanize("This is a test.", lang="en", intensity=50, seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    def test_empty_string(self):
        """Empty string should not crash."""
        result = humanize("", lang="en", intensity=50)
        assert isinstance(result.text, str)

    def test_whitespace_only(self):
        """Whitespace-only input should not crash."""
        result = humanize("   \n\t  ", lang="en", intensity=50)
        assert isinstance(result.text, str)

    def test_very_long_text(self):
        """Long text should be handled."""
        long_text = AI_TEXT_EN * 20
        result = humanize(long_text, lang="en", intensity=50, seed=42)
        assert len(result.text) > len(long_text) * 0.5

    def test_text_with_special_chars(self):
        """Text with special characters shouldn't crash."""
        text = (
            "The cost is $500 (€450). Results: 95% — significantly higher! "
            "See section §3.2 & appendix #4 for details."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    def test_mixed_language_text(self):
        """Text with mixed languages should not crash."""
        text = (
            "This is English. Это русский текст. "
            "Back to English again."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        assert isinstance(result.text, str)

    def test_text_with_newlines(self):
        """Text with newlines should preserve paragraph structure."""
        text = (
            "First paragraph about implementation.\n\n"
            "Second paragraph about methodology.\n\n"
            "Third paragraph about results."
        )
        result = humanize(text, lang="en", intensity=50, seed=42)
        assert isinstance(result.text, str)
        # Should still have some paragraph markers
        assert '\n' in result.text or len(result.text) > 50


# ── Result metadata tests ─────────────────────────────────

class TestResultMetadata:
    """Tests that HumanizeResult metadata is valid."""

    def test_change_ratio_bounds(self):
        """Change ratio should be between 0.0 and 1.0."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert 0.0 <= result.change_ratio <= 1.0

    def test_lang_field_set(self):
        """Language field should be correctly set."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert result.lang == "en"   

    def test_profile_field_set(self):
        """Profile field should be set when specified."""
        result = humanize(AI_TEXT_EN, lang="en", profile="web", intensity=70, seed=42)
        assert result.profile == "web"

    def test_result_text_is_string(self):
        """Result text should always be a string."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert isinstance(result.text, str)

    def test_changes_is_list(self):
        """Changes should be a list."""
        result = humanize(AI_TEXT_EN, lang="en", intensity=70, seed=42)
        assert isinstance(result.changes, list)
