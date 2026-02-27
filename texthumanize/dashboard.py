"""Evaluation dashboard — generate quality reports in JSON and HTML.

Creates comprehensive evaluation reports covering:
- AI detection accuracy and confusion matrices
- Humanization effectiveness per profile/intensity
- Feature importance analysis
- Historical training metrics

Usage::

    from texthumanize.dashboard import Dashboard
    dash = Dashboard()
    report = dash.generate_report(lang="en")
    dash.save_json(report, "report.json")
    dash.save_html(report, "report.html")
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Dashboard:
    """Generate evaluation reports for TextHumanize quality assessment."""

    def __init__(self) -> None:
        self._version: str = ""
        try:
            from texthumanize import __version__
            self._version = __version__
        except Exception:
            self._version = "unknown"

    def generate_report(
        self,
        lang: str = "en",
        n_samples: int = 6,
        profiles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive evaluation report.

        Args:
            lang: Language code.
            n_samples: Number of evaluation samples.
            profiles: List of profiles to test.

        Returns:
            Structured report dict.
        """
        from texthumanize.benchmarks import ValidationSuite

        profiles = profiles or ["web", "chat", "seo"]
        t0 = time.time()

        suite = ValidationSuite(profiles=profiles, intensities=[40, 60, 80])
        validation = suite.run_all(lang=lang)

        # Neural model info
        neural_info = self._get_neural_info()

        report: dict[str, Any] = {
            "version": self._version,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "lang": lang,
            "detection": validation.get("detection", {}),
            "humanization": validation.get("humanization", []),
            "neural_models": neural_info,
            "elapsed_seconds": round(time.time() - t0, 1),
        }

        return report

    def _get_neural_info(self) -> dict[str, Any]:
        """Collect neural model metadata."""
        info: dict[str, Any] = {}
        try:
            from texthumanize.neural_detector import NeuralAIDetector
            det = NeuralAIDetector()
            info["detector"] = {
                "architecture": det.architecture,
                "param_count": det.param_count,
                "trained": det._trained,
            }
        except Exception:
            info["detector"] = {"status": "unavailable"}

        try:
            from texthumanize.neural_lm import NeuralPerplexity
            lm = NeuralPerplexity()
            info["language_model"] = {
                "type": "char-level LSTM",
                "hidden_dim": lm._hidden_dim,
            }
        except Exception:
            info["language_model"] = {"status": "unavailable"}

        return info

    @staticmethod
    def save_json(report: dict[str, Any], path: str) -> None:
        """Save report as JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Saved JSON report: %s", path)

    @staticmethod
    def save_html(report: dict[str, Any], path: str) -> None:
        """Save report as self-contained HTML dashboard."""
        det = report.get("detection", {})
        confusion = det.get("confusion", {})
        human = report.get("humanization", [])

        # Build HTML
        html_parts: list[str] = []
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TextHumanize Evaluation Report</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #333; background: #f8f9fa; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #34495e; margin-top: 30px; }
.card { background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.metric { display: inline-block; min-width: 120px; margin: 8px 15px; }
.metric-value { font-size: 28px; font-weight: 700; color: #2c3e50; }
.metric-label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f1f3f5; font-weight: 600; }
.good { color: #27ae60; }
.bad { color: #e74c3c; }
.neutral { color: #f39c12; }
.bar { height: 20px; border-radius: 3px; background: #3498db; display: inline-block; }
footer { margin-top: 40px; padding: 20px 0; border-top: 1px solid #ddd; color: #95a5a6; font-size: 12px; }
</style>
</head>
<body>
""")
        html_parts.append(f"""
<h1>TextHumanize Evaluation Report</h1>
<p>Version: {report.get('version', '?')} | Language: {report.get('lang', '?')} | {report.get('timestamp', '')}</p>
""")

        # Detection metrics
        html_parts.append("""
<h2>AI Detection Accuracy</h2>
<div class="card">
""")
        for m in ["accuracy", "precision", "recall", "f1"]:
            val = det.get(m, 0)
            css = "good" if val >= 0.8 else ("neutral" if val >= 0.6 else "bad")
            html_parts.append(f"""
  <div class="metric">
    <div class="metric-value {css}">{val:.0%}</div>
    <div class="metric-label">{m}</div>
  </div>""")

        # Confusion matrix
        html_parts.append("""
  <table style="width: auto; margin-top: 15px;">
    <tr><th></th><th>Predicted AI</th><th>Predicted Human</th></tr>
""")
        html_parts.append(f"""
    <tr><td><strong>Actual AI</strong></td><td>{confusion.get('tp', 0)}</td><td>{confusion.get('fn', 0)}</td></tr>
    <tr><td><strong>Actual Human</strong></td><td>{confusion.get('fp', 0)}</td><td>{confusion.get('tn', 0)}</td></tr>
  </table>
</div>
""")

        # Humanization effectiveness
        html_parts.append("""
<h2>Humanization Effectiveness</h2>
<div class="card">
  <table>
    <tr><th>Profile</th><th>Intensity</th><th>Avg Score Drop</th><th>Success Rate</th><th>Avg Time (ms)</th></tr>
""")
        for h in human:
            drop_css = "good" if h.get("avg_score_drop", 0) > 0.1 else "neutral"
            succ_css = "good" if h.get("success_rate", 0) >= 0.5 else "bad"
            html_parts.append(f"""
    <tr>
      <td>{h.get('profile', '?')}</td>
      <td>{h.get('intensity', '?')}%</td>
      <td class="{drop_css}">{h.get('avg_score_drop', 0):+.3f}</td>
      <td class="{succ_css}">{h.get('success_rate', 0):.0%}</td>
      <td>{h.get('avg_humanize_ms', 0):.0f}</td>
    </tr>""")
        html_parts.append("""
  </table>
</div>
""")

        # Neural model info
        nn = report.get("neural_models", {})
        html_parts.append("""
<h2>Neural Models</h2>
<div class="card">
""")
        det_info = nn.get("detector", {})
        html_parts.append(f"""
  <p><strong>Detector:</strong> {det_info.get('architecture', 'N/A')} |
  Params: {det_info.get('param_count', 'N/A')} |
  Trained: {'Yes' if det_info.get('trained') else 'No'}</p>
""")
        lm_info = nn.get("language_model", {})
        html_parts.append(f"""
  <p><strong>Language Model:</strong> {lm_info.get('type', 'N/A')} |
  Hidden: {lm_info.get('hidden_dim', 'N/A')}</p>
</div>
""")

        html_parts.append(f"""
<footer>
  Generated by TextHumanize v{report.get('version', '?')} in {report.get('elapsed_seconds', 0):.1f}s
</footer>
</body>
</html>
""")

        html = "".join(html_parts)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Saved HTML report: %s (%d bytes)", path, len(html))
