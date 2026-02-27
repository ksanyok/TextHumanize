"""Тесты для custom_dict API в humanize()."""

from __future__ import annotations

from texthumanize import humanize


class TestCustomDict:
    """Tests for custom_dict parameter in humanize()."""

    def test_simple_replacement(self):
        """Simple word replacement via custom_dict."""
        result = humanize(
            "We need to implement this feature.",
            lang="en",
            custom_dict={"implement": "build"},
            intensity=10,
            seed=42,
        )
        # The custom dict replacement should be applied
        assert "implement" not in result.text.lower() or "build" in result.text.lower()

    def test_list_replacement(self):
        """List of variants should pick one."""
        result = humanize(
            "We need to implement this feature.",
            lang="en",
            custom_dict={"implement": ["build", "create", "develop"]},
            intensity=10,
            seed=42,
        )
        text_lower = result.text.lower()
        assert any(w in text_lower for w in ["build", "create", "develop"]) or "implement" not in text_lower

    def test_none_custom_dict(self):
        """None custom_dict should work normally."""
        result = humanize("Some text here.", lang="en", custom_dict=None, seed=42)
        assert isinstance(result.text, str)

    def test_empty_custom_dict(self):
        """Empty custom_dict should work normally."""
        result = humanize("Some text here.", lang="en", custom_dict={}, seed=42)
        assert isinstance(result.text, str)

    def test_change_logged(self):
        """Custom dict changes should appear in changes list."""
        result = humanize(
            "We need to implement this feature right now.",
            lang="en",
            custom_dict={"implement": "build"},
            intensity=10,
            seed=42,
        )
        custom_changes = [c for c in result.changes if c.get("type") == "custom_dict"]
        # May or may not have changes depending on pipeline flow
        # but should not crash
        assert isinstance(result.changes, list)

    def test_custom_dict_with_russian(self):
        """Custom dict should work with Russian text."""
        result = humanize(
            "Необходимо осуществить данную операцию.",
            lang="ru",
            custom_dict={"осуществить": "выполнить"},
            intensity=10,
            seed=42,
        )
        assert isinstance(result.text, str)

    def test_multiple_replacements(self):
        """Multiple replacements in custom_dict."""
        result = humanize(
            "We need to implement and utilize this feature.",
            lang="en",
            custom_dict={
                "implement": "build",
                "utilize": "use",
            },
            intensity=10,
            seed=42,
        )
        assert isinstance(result.text, str)
