"""Tests for cli.py — command-line interface."""

import json
import sys
from unittest.mock import patch

import pytest

from texthumanize.cli import main


def run_cli(*args):
    """Run CLI main() with given args, return exit code or None."""
    with patch.object(sys, 'argv', ['texthumanize', *list(args)]):
        return main()


class TestCLIVersion:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            run_cli('--version')
        assert exc.value.code == 0
        out = capsys.readouterr().out
        import texthumanize
        assert texthumanize.__version__ in out


class TestCLIHumanize:
    def test_process_file(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, it is important to note this fact.")
        run_cli(str(infile), '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_file_output(self, tmp_path):
        infile = tmp_path / "input.txt"
        outfile = tmp_path / "output.txt"
        infile.write_text("Text to process here.")
        run_cli(str(infile), '-o', str(outfile), '-l', 'en')
        assert outfile.exists()
        assert len(outfile.read_text()) > 0

    def test_process_with_profile(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Text for chat processing.")
        run_cli(str(infile), '-p', 'chat', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_intensity(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Text with intensity setting.")
        run_cli(str(infile), '-i', '80', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_seed(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Text with seed for reproducibility.")
        run_cli(str(infile), '--seed', '42', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_keep(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Important API text.")
        run_cli(str(infile), '--keep', 'API', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_brand(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("TextHumanize is great.")
        run_cli(str(infile), '--brand', 'TextHumanize', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_minimal(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, it is important to utilize this method.")
        run_cli(str(infile), '--minimal', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_process_with_intent_profile(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("This product update helps support teams move faster.")
        run_cli(str(infile), '-p', 'product_description', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_fail_under_quality_passes(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, it is important to utilize this method.")
        run_cli(str(infile), '-l', 'en', '--fail-under-quality', '0')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    @pytest.mark.perf
    def test_fail_under_quality_exits(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("hello world")
        with pytest.raises(SystemExit) as exc:
            run_cli(str(infile), '-l', 'en', '--fail-under-quality', '0.99')
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "quality_score" in err


class TestCLIAnalyze:
    def test_analyze_mode(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Text to analyze for naturalness metrics.")
        run_cli(str(infile), '--analyze', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "artificiality_score" in data
        assert "lang" in data

    def test_analyze_json_structure(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Another text for detailed analysis.")
        run_cli(str(infile), '--analyze', '-l', 'en')
        data = json.loads(capsys.readouterr().out)
        assert "total_words" in data
        assert "avg_sentence_length" in data


class TestCLIExplain:
    def test_explain_mode(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, it is important to utilize this methodology.")
        run_cli(str(infile), '--explain', '-l', 'en')
        err = capsys.readouterr().err
        assert "TextHumanize" in err


class TestCLIDetectAI:
    def test_detect_ai(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Text for AI detection analysis.")
        run_cli(str(infile), '--detect-ai', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "score" in data
        assert "verdict" in data

    def test_explain_subcommand(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, it is important to utilize this method.")
        run_cli('explain', str(infile), '--json', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["schema_version"] == "text-humanize.ai_explain.v1"
        assert "highlighted_spans" in data

    def test_detector_benchmark_subcommand(self, capsys):
        run_cli('detector-benchmark', '--langs', 'en', '--json')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["schema_version"] == "1.0"
        assert data["languages"] == ["en"]
        assert data["labels"] == [
            "human",
            "raw_ai",
            "lightly_edited_ai",
            "heavily_edited_ai",
        ]
        assert data["corpus"]["license"]["id"] == "CC0-1.0"
        assert data["overall"]["total"] >= 4

    def test_detector_benchmark_text_output_uses_new_labels(self, capsys):
        run_cli('detector-benchmark', '--langs', 'en')
        out = capsys.readouterr().out
        assert "raw_ai_avg" in out
        assert "light_edit_flag" in out
        assert "heavy_edit_flag" in out


class TestCLIParaphrase:
    def test_paraphrase(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("This is a simple sentence to paraphrase.")
        run_cli(str(infile), '--paraphrase', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0


class TestCLITone:
    def test_tone_analyze(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("This formal document requires analysis.")
        run_cli(str(infile), '--tone-analyze', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "primary_tone" in data

    def test_tone_adjust(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("The implementation facilitates optimization.")
        run_cli(str(infile), '--tone', 'casual', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0


class TestCLIWatermarks:
    def test_watermarks_clean(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Clean text without watermarks.")
        run_cli(str(infile), '--watermarks', '-l', 'en')
        err = capsys.readouterr().err
        assert "не обнаружены" in err or "Водяные" in err

    def test_watermarks_with_zwc(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Te\u200bxt\u200b with water\u200bmarks.")
        run_cli(str(infile), '--watermarks', '-l', 'en')
        capsys.readouterr()
        # Should output cleaned text or info

    def test_watermark_report_flag(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Te\u200bst with watermark.")
        run_cli(str(infile), '--watermark-report', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["schema_version"] == "text-humanize.watermark_report.v1"

    def test_watermark_subcommand(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Te\u200bst with watermark.")
        run_cli('watermark', str(infile), '--json', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "highlighted_spans" in data


class TestCLIAudit:
    def test_audit_flag(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, Te\u200bst data is important.")
        run_cli(str(infile), '--audit', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["schema_version"] == "text-humanize.audit_report.v1"

    def test_audit_subcommand(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Furthermore, Te\u200bst data is important.")
        run_cli('audit', str(infile), '--json', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "ai" in data
        assert "watermark" in data


class TestCLIBenchmarkGate:
    def test_benchmark_fail_under_quality_json(self, capsys):
        with pytest.raises(SystemExit) as exc:
            run_cli('benchmark', '-l', 'en', '--json', '--fail-under-quality', '1')
        assert exc.value.code == 2
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["quality_gate_passed"] is False
        assert "avg_quality_score" in captured.err


class TestCLISpin:
    def test_spin(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("The system provides important data.")
        run_cli(str(infile), '--spin', '-l', 'en')
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_variants(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("Important text here.")
        run_cli(str(infile), '--variants', '3', '-l', 'en')
        out = capsys.readouterr().out
        assert "Вариант" in out


class TestCLICoherence:
    def test_coherence(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("First paragraph.\n\nSecond paragraph.")
        run_cli(str(infile), '--coherence', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "overall" in data


class TestCLIReadability:
    def test_readability(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        infile.write_text("This text is used to test readability analysis tools.")
        run_cli(str(infile), '--readability', '-l', 'en')
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, dict)


class TestCLIErrors:
    def test_missing_file(self):
        with pytest.raises(SystemExit):
            run_cli("/nonexistent/file.txt")

    def test_report_save(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        reportfile = tmp_path / "report.json"
        infile.write_text("Text to process and report.")
        run_cli(str(infile), '--report', str(reportfile), '-l', 'en')
        assert reportfile.exists()
        data = json.loads(reportfile.read_text())
        assert "change_ratio" in data
        assert data["schema_version"] == "text-humanize.change_report.v1"
        assert "before" in data
        assert "after" in data
        assert "highlighted_spans" in data
        assert "timings" in data
        assert "warnings" in data

    def test_html_report_save(self, tmp_path, capsys):
        infile = tmp_path / "input.txt"
        reportfile = tmp_path / "report.html"
        infile.write_text("Furthermore, it is important to utilize this method.")
        run_cli(str(infile), '--report', str(reportfile), '-l', 'en')
        assert reportfile.exists()
        html = reportfile.read_text()
        assert "<!DOCTYPE html>" in html
        assert "Before / After" in html
        assert "Highlighted Spans" in html


class TestCLIStdin:
    def test_stdin_input(self, capsys):
        with patch.object(sys, 'stdin', __class__=type(sys.stdin)):
            import io
            with patch('sys.stdin', io.StringIO("Text from stdin.")):
                run_cli('-', '-l', 'en')
                out = capsys.readouterr().out
                assert len(out.strip()) > 0
