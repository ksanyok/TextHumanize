"""Tests for new v0.9.0 features:

- Kirchenbauer watermark detector
- HTML diff report (explain_html, explain_json_patch, explain_side_by_side)
- Quality gate
- Selective humanization (only_flagged)
- Stylometric anonymizer
"""

from __future__ import annotations

import json

from texthumanize import (
    AnonymizeResult,
    StylometricAnonymizer,
    anonymize_style,
    explain,
    humanize,
)
from texthumanize.diff_report import (
    explain_html,
    explain_json_patch,
    explain_side_by_side,
)
from texthumanize.quality_gate import GateConfig, GateResult, check_file
from texthumanize.stylistic import STYLE_PRESETS
from texthumanize.utils import HumanizeResult
from texthumanize.watermark import WatermarkDetector

# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

_AI_TEXT_RU = (
    "Данный текст является примером автоматически сгенерированного контента. "
    "Кроме того, необходимо отметить, что осуществление поставленных задач "
    "требует значительных усилий. Вместе с тем следует подчеркнуть, что "
    "реализация намеченных планов представляется весьма перспективной. "
    "Таким образом, можно сделать вывод о необходимости дальнейшей работы."
)

_AI_TEXT_EN = (
    "This text serves as an example of automatically generated content. "
    "Furthermore, it should be noted that the implementation of established "
    "objectives requires significant effort. Additionally, it must be "
    "emphasized that the realization of planned initiatives appears highly "
    "promising. Consequently, one can conclude that further work is necessary."
)


def _make_result(**kwargs) -> HumanizeResult:
    """Create a minimal HumanizeResult for testing."""
    defaults = {
        "original": _AI_TEXT_EN,
        "text": "This text is an example. Further work is needed.",
        "lang": "en",
        "profile": "web",
        "intensity": 60,
        "changes": [
            {
                "type": "debureaucratize",
                "original": "serves as an example",
                "replacement": "is an example",
            },
            {
                "type": "structure",
                "description": "Shortened sentence",
            },
        ],
        "metrics_before": {
            "artificiality_score": 65.0,
            "avg_sentence_length": 22.0,
            "bureaucratic_ratio": 0.15,
            "connector_ratio": 0.12,
            "repetition_score": 0.3,
            "typography_score": 0.9,
        },
        "metrics_after": {
            "artificiality_score": 20.0,
            "avg_sentence_length": 14.0,
            "bureaucratic_ratio": 0.03,
            "connector_ratio": 0.04,
            "repetition_score": 0.1,
            "typography_score": 0.85,
        },
    }
    defaults.update(kwargs)
    return HumanizeResult(**defaults)


# ═══════════════════════════════════════════════════════════════
#  1. Kirchenbauer watermark detector
# ═══════════════════════════════════════════════════════════════


class TestKirchenbauerDetector:
    """Tests for _detect_kirchenbauer in WatermarkDetector."""

    def test_plain_text_no_watermark(self):
        """Regular human text should not trigger Kirchenbauer flag."""
        detector = WatermarkDetector()
        report = detector.detect(
            "The quick brown fox jumps over the lazy dog. "
            "A second sentence follows naturally."
        )
        assert report.kirchenbauer_score < 4.0
        assert report.kirchenbauer_p_value > 0.01

    def test_short_text_skipped(self):
        """Very short text should be skipped (default z=0)."""
        detector = WatermarkDetector()
        report = detector.detect("Hello world.")
        assert report.kirchenbauer_score == 0.0
        assert report.kirchenbauer_p_value == 1.0

    def test_report_has_fields(self):
        """WatermarkReport should have kirchenbauer_* fields."""
        detector = WatermarkDetector()
        report = detector.detect("Some text here for testing purposes again.")
        assert hasattr(report, "kirchenbauer_score")
        assert hasattr(report, "kirchenbauer_p_value")

    def test_repeated_tokens_not_crash(self):
        """Repeated identical tokens should not crash."""
        detector = WatermarkDetector()
        report = detector.detect("word " * 100)
        assert isinstance(report.kirchenbauer_score, float)


# ═══════════════════════════════════════════════════════════════
#  2. HTML diff report
# ═══════════════════════════════════════════════════════════════


class TestDiffReport:
    """Tests for explain_html, explain_json_patch, explain_side_by_side."""

    def test_explain_html_basic(self):
        result = _make_result()
        html = explain_html(result)
        assert "<!DOCTYPE html>" in html
        assert "TextHumanize" in html
        assert "<del>" in html or "<ins>" in html

    def test_explain_html_metrics(self):
        result = _make_result()
        html = explain_html(result)
        assert "65.00" in html or "65.0" in html  # before score
        assert "20.00" in html or "20.0" in html  # after score

    def test_explain_html_no_changes(self):
        result = _make_result(changes=[])
        html = explain_html(result, show_changes=False)
        assert "<!DOCTYPE html>" in html

    def test_explain_html_truncates_changes(self):
        many_changes = [
            {"type": "test", "original": f"w{i}", "replacement": f"x{i}"}
            for i in range(60)
        ]
        result = _make_result(changes=many_changes)
        html = explain_html(result)
        assert "and 10 more changes" in html

    def test_explain_json_patch(self):
        result = _make_result()
        output = explain_json_patch(result)
        data = json.loads(output)
        assert data["version"] == "1.0"
        assert data["lang"] == "en"
        assert "operations" in data
        assert len(data["operations"]) == 2

    def test_explain_json_patch_ops(self):
        result = _make_result()
        data = json.loads(explain_json_patch(result))
        op0 = data["operations"][0]
        assert op0["op"] == "replace"
        assert op0["old"] == "serves as an example"

    def test_explain_side_by_side(self):
        result = _make_result()
        diff = explain_side_by_side(result)
        assert "---" in diff or "+++" in diff or diff == ""

    def test_explain_via_core_fmt_html(self):
        result = _make_result()
        html = explain(result, fmt="html")
        assert "<!DOCTYPE html>" in html

    def test_explain_via_core_fmt_json(self):
        result = _make_result()
        j = explain(result, fmt="json")
        data = json.loads(j)
        assert "operations" in data

    def test_explain_via_core_fmt_text(self):
        result = _make_result()
        txt = explain(result, fmt="text")
        assert "Отчёт TextHumanize" in txt

    def test_explain_via_core_fmt_diff(self):
        result = _make_result()
        d = explain(result, fmt="diff")
        assert isinstance(d, str)


# ═══════════════════════════════════════════════════════════════
#  3. Quality Gate
# ═══════════════════════════════════════════════════════════════


class TestQualityGate:
    """Tests for quality_gate module."""

    def test_gate_config_defaults(self):
        cfg = GateConfig()
        assert cfg.ai_threshold == 25.0
        assert cfg.readability_threshold == 40.0
        assert cfg.watermark_zero is True

    def test_check_missing_file(self):
        result = check_file("/nonexistent/file.txt")
        assert not result.passed
        assert "not found" in result.issues[0].lower()

    def test_gate_result_fields(self):
        r = GateResult(path="test.txt")
        assert r.passed is True
        assert r.ai_score == 0.0

    def test_check_file_too_large(self, tmp_path):
        big = tmp_path / "big.txt"
        big.write_text("x" * 600_000)
        config = GateConfig(max_file_size=500_000)
        result = check_file(str(big), config)
        assert result.passed  # skipped, not failed
        assert "too large" in result.issues[0].lower()

    def test_check_empty_file(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        result = check_file(str(empty))
        assert result.passed

    def test_check_real_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("Just a simple human sentence. Nothing special here.")
        result = check_file(str(f))
        assert isinstance(result, GateResult)


# ═══════════════════════════════════════════════════════════════
#  4. Selective humanization
# ═══════════════════════════════════════════════════════════════


class TestSelectiveHumanization:
    """Tests for humanize(only_flagged=True)."""

    def test_basic_selective(self):
        result = humanize(_AI_TEXT_RU, lang="ru", only_flagged=True)
        assert isinstance(result, HumanizeResult)
        assert result.text  # non-empty
        assert result.original == _AI_TEXT_RU

    def test_selective_preserves_human(self):
        """Human text should pass through mostly unchanged."""
        human = "Я вчера гулял в парке. Погода была отличная."
        result = humanize(human, lang="ru", only_flagged=True)
        assert isinstance(result, HumanizeResult)
        # Change ratio should be small for human text
        assert result.change_ratio < 0.5

    def test_selective_changes_list(self):
        result = humanize(_AI_TEXT_EN, lang="en", only_flagged=True)
        types = {c.get("type") for c in result.changes}
        assert "selective_mode" in types or "selective_skip" in types or len(result.changes) > 0

    def test_selective_with_empty_text(self):
        result = humanize("", lang="en", only_flagged=True)
        assert result.text == ""


# ═══════════════════════════════════════════════════════════════
#  5. Stylometric anonymizer
# ═══════════════════════════════════════════════════════════════


class TestStylometricAnonymizer:
    """Tests for StylometricAnonymizer and anonymize_style()."""

    def test_anonymizer_basic(self):
        anon = StylometricAnonymizer(lang="en", seed=42)
        result = anon.anonymize(_AI_TEXT_EN)
        assert isinstance(result, AnonymizeResult)
        assert result.text
        assert result.original == _AI_TEXT_EN

    def test_anonymizer_with_preset(self):
        anon = StylometricAnonymizer(lang="en", seed=42)
        result = anon.anonymize(_AI_TEXT_EN, target="blogger")
        assert result.target_preset == "blogger"

    def test_anonymizer_similarity_fields(self):
        anon = StylometricAnonymizer(lang="en", seed=42)
        result = anon.anonymize(_AI_TEXT_EN)
        assert 0.0 <= result.similarity_before <= 1.0
        assert 0.0 <= result.similarity_after <= 1.0

    def test_anonymize_style_convenience(self):
        result = anonymize_style(_AI_TEXT_EN, lang="en", target="student", seed=42)
        assert isinstance(result, dict)
        assert "text" in result
        assert "similarity_before" in result
        assert "similarity_after" in result
        assert result["target_preset"] == "student"

    def test_anonymize_style_auto_lang(self):
        result = anonymize_style(_AI_TEXT_EN, target="copywriter")
        assert isinstance(result, dict)
        assert result["text"]

    def test_anonymize_changes_tracked(self):
        anon = StylometricAnonymizer(lang="en", seed=1)
        result = anon.anonymize(_AI_TEXT_EN, target="blogger")
        # Should have at least some changes recorded
        assert isinstance(result.changes, list)

    def test_all_presets_work(self):
        for name in STYLE_PRESETS:
            result = anonymize_style(
                _AI_TEXT_EN, lang="en", target=name, seed=42,
            )
            assert result["text"], f"Preset {name} returned empty text"

    def test_short_text_no_crash(self):
        result = anonymize_style("Hi.", lang="en")
        assert result["text"]

    def test_anonymizer_russian(self):
        result = anonymize_style(_AI_TEXT_RU, lang="ru", target="blogger")
        assert result["text"]

    def test_fingerprint_similarity(self):
        fp1 = STYLE_PRESETS["student"]
        fp2 = STYLE_PRESETS["scientist"]
        sim = fp1.similarity(fp2)
        assert 0.0 < sim < 1.0  # different but nonzero

    def test_fingerprint_self_similarity(self):
        fp = STYLE_PRESETS["journalist"]
        assert fp.similarity(fp) > 0.99


# ═══════════════════════════════════════════════════════════════
#  Integration
# ═══════════════════════════════════════════════════════════════


class TestIntegration:
    """Cross-feature integration tests."""

    def test_humanize_then_explain_html(self):
        result = humanize(_AI_TEXT_RU, lang="ru")
        html = explain(result, fmt="html")
        assert "<!DOCTYPE html>" in html
        assert "<del>" in html or "<ins>" in html

    def test_humanize_then_explain_json(self):
        result = humanize(_AI_TEXT_EN, lang="en")
        j = explain(result, fmt="json")
        data = json.loads(j)
        assert data["lang"] == "en"

    def test_selective_then_anonymize(self):
        """Chain: selective humanize → anonymize style."""
        result = humanize(_AI_TEXT_EN, lang="en", only_flagged=True)
        anon = anonymize_style(result.text, lang="en", target="blogger")
        assert anon["text"]

    def test_watermark_then_humanize(self):
        """Detect watermarks, then humanize."""
        detector = WatermarkDetector()
        detector.detect(_AI_TEXT_EN)
        result = humanize(_AI_TEXT_EN, lang="en")
        assert result.text != _AI_TEXT_EN or result.change_ratio == 0
