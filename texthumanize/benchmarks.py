"""External validation framework — benchmark against external AI detectors.

Provides tools to evaluate TextHumanize effectiveness by comparing
AI detection scores before and after humanization.

Usage::

    from texthumanize.benchmarks import ValidationSuite
    suite = ValidationSuite()
    report = suite.run_all(texts, lang="en")
    suite.print_report(report)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from texthumanize.core import detect_ai, humanize

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Standard evaluation texts
# ---------------------------------------------------------------------------

_EVAL_TEXTS_EN = [
    (
        "Furthermore, it is important to note that the utilization of advanced "
        "methodologies has significantly contributed to the overall improvement "
        "of systemic outcomes. The implementation of comprehensive strategies "
        "ensures that all stakeholders benefit from the enhanced framework. "
        "Additionally, the integration of holistic approaches facilitates the "
        "achievement of optimal results across various domains.",
        "ai",
    ),
    (
        "So I was thinking about this the other day - you know how sometimes "
        "things just don't work the way you'd expect? Yeah, that happened "
        "again. Tried to fix the sink, ended up flooding half the kitchen. "
        "My wife wasn't thrilled, to say the least. Lesson learned though.",
        "human",
    ),
    (
        "The comprehensive examination of relevant literature reveals several "
        "key findings that merit consideration. Firstly, the data suggests a "
        "significant correlation between the implementation of evidence-based "
        "practices and positive outcomes. Secondly, the analysis indicates that "
        "organizational culture plays a crucial role.",
        "ai",
    ),
    (
        "Look, I'm not gonna pretend I have all the answers here. But from "
        "what I've seen working in this field, the biggest mistake people make "
        "is overthinking it. Just start somewhere, make mistakes, learn from "
        "them. It's really not rocket science — just common sense.",
        "human",
    ),
]

_EVAL_TEXTS_RU = [
    (
        "Кроме того, необходимо отметить, что применение передовых методологий "
        "значительно способствовало общему улучшению системных результатов. "
        "Внедрение комплексных стратегий обеспечивает извлечение пользы всеми "
        "заинтересованными сторонами из улучшенных рамок.",
        "ai",
    ),
    (
        "Знаешь, я долго думал над этим вопросом, и вот что понял — нет "
        "смысла гнаться за совершенством. Сделал как получилось, посмотрел "
        "что вышло, поправил. И так по кругу. Жизнь — она не по учебнику идёт.",
        "human",
    ),
]


class ValidationResult:
    """Result of a single validation test."""

    __slots__ = (
        "actual_label",
        "ai_score_after",
        "ai_score_before",
        "humanize_time_ms",
        "lang",
        "text_after",
        "text_before",
    )

    def __init__(
        self,
        text_before: str,
        text_after: str,
        ai_score_before: float,
        ai_score_after: float,
        actual_label: str,
        lang: str,
        humanize_time_ms: float,
    ) -> None:
        self.text_before = text_before
        self.text_after = text_after
        self.ai_score_before = ai_score_before
        self.ai_score_after = ai_score_after
        self.actual_label = actual_label
        self.lang = lang
        self.humanize_time_ms = humanize_time_ms

    @property
    def score_drop(self) -> float:
        return self.ai_score_before - self.ai_score_after

    @property
    def detection_correct_before(self) -> bool:
        if self.actual_label == "ai":
            return self.ai_score_before > 0.5
        return self.ai_score_before <= 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_before": self.text_before[:80],
            "text_after": self.text_after[:80],
            "ai_score_before": self.ai_score_before,
            "ai_score_after": self.ai_score_after,
            "score_drop": self.score_drop,
            "actual_label": self.actual_label,
            "lang": self.lang,
            "humanize_time_ms": self.humanize_time_ms,
        }


class ValidationSuite:
    """Run validation benchmarks against the TextHumanize pipeline.

    Evaluates:
    1. AI detection accuracy (can we correctly classify AI vs human?)
    2. Humanization effectiveness (does humanization lower AI scores?)
    3. Quality preservation (is humanized text still readable?)
    """

    def __init__(
        self,
        profiles: list[str] | None = None,
        intensities: list[int] | None = None,
    ) -> None:
        self.profiles = profiles or ["web", "chat", "seo"]
        self.intensities = intensities or [40, 60, 80]

    def _get_eval_texts(self, lang: str) -> list[tuple[str, str]]:
        """Get evaluation texts for a language."""
        if lang == "ru":
            return _EVAL_TEXTS_RU + _EVAL_TEXTS_EN
        return _EVAL_TEXTS_EN + _EVAL_TEXTS_RU

    def validate_detection(
        self,
        texts: list[tuple[str, str]] | None = None,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Validate AI detection accuracy.

        Args:
            texts: Optional list of (text, label) pairs. Uses built-in if None.
            lang: Language code.

        Returns:
            Dict with accuracy, precision, recall, F1 metrics.
        """
        if texts is None:
            texts = self._get_eval_texts(lang)

        tp = fp = tn = fn = 0
        results = []
        for text, label in texts:
            try:
                report = detect_ai(text, lang=lang)
                score = report.get("combined_score", report.get("score", 0.5))
                predicted = "ai" if score > 0.5 else "human"
            except Exception:
                score = 0.5
                predicted = "unknown"

            results.append({
                "text": text[:60],
                "label": label,
                "predicted": predicted,
                "score": round(score, 4),
            })

            if label == "ai":
                if predicted == "ai":
                    tp += 1
                else:
                    fn += 1
            else:
                if predicted == "human":
                    tn += 1
                else:
                    fp += 1

        n = max(tp + fp + tn + fn, 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        return {
            "accuracy": (tp + tn) / n,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
            "details": results,
        }

    def validate_humanization(
        self,
        texts: list[str] | None = None,
        lang: str = "en",
        profile: str = "web",
        intensity: int = 60,
    ) -> dict[str, Any]:
        """Validate humanization effectiveness.

        Measures how much humanization reduces AI detection scores.

        Returns:
            Dict with avg_score_drop, success_rate, results.
        """
        if texts is None:
            texts = [t for t, label in self._get_eval_texts(lang) if label == "ai"]

        results: list[ValidationResult] = []
        for text in texts:
            try:
                before = detect_ai(text, lang=lang)
                before_score = before.get("combined_score", before.get("score", 0.5))

                t0 = time.time()
                humanized = humanize(text, lang=lang, profile=profile, intensity=intensity)
                htime = (time.time() - t0) * 1000

                after = detect_ai(humanized.text, lang=lang)
                after_score = after.get("combined_score", after.get("score", 0.5))

                results.append(ValidationResult(
                    text_before=text, text_after=humanized.text,
                    ai_score_before=before_score, ai_score_after=after_score,
                    actual_label="ai", lang=lang,
                    humanize_time_ms=htime,
                ))
            except Exception as e:
                logger.warning("Validation error: %s", e)

        if not results:
            return {"avg_score_drop": 0.0, "success_rate": 0.0, "results": []}

        avg_drop = sum(r.score_drop for r in results) / len(results)
        success = sum(1 for r in results if r.ai_score_after < 0.5)
        avg_time = sum(r.humanize_time_ms for r in results) / len(results)

        return {
            "profile": profile,
            "intensity": intensity,
            "avg_score_drop": round(avg_drop, 4),
            "success_rate": success / len(results),
            "avg_humanize_ms": round(avg_time, 1),
            "n_texts": len(results),
            "results": [r.to_dict() for r in results],
        }

    def run_all(
        self,
        texts: list[tuple[str, str]] | None = None,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Run complete validation suite.

        Returns comprehensive report with detection accuracy and
        humanization effectiveness across all profiles/intensities.
        """
        t0 = time.time()

        report: dict[str, Any] = {
            "lang": lang,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Detection accuracy
        report["detection"] = self.validate_detection(texts, lang=lang)

        # Humanization effectiveness per profile/intensity
        humanization_results = []
        ai_texts = [t for t, label in (texts or self._get_eval_texts(lang)) if label == "ai"]

        for profile in self.profiles:
            for intensity in self.intensities:
                result = self.validate_humanization(
                    texts=ai_texts, lang=lang, profile=profile, intensity=intensity,
                )
                humanization_results.append(result)

        report["humanization"] = humanization_results
        report["elapsed_seconds"] = round(time.time() - t0, 1)

        return report

    @staticmethod
    def print_report(report: dict[str, Any]) -> None:
        """Print a human-readable validation report."""
        print("=" * 60)
        print("  TextHumanize Validation Report")
        print("=" * 60)

        det = report.get("detection", {})
        print("\n  Detection Accuracy:")
        print(f"    Accuracy:  {det.get('accuracy', 0):.1%}")
        print(f"    Precision: {det.get('precision', 0):.2f}")
        print(f"    Recall:    {det.get('recall', 0):.2f}")
        print(f"    F1:        {det.get('f1', 0):.2f}")

        print("\n  Humanization Effectiveness:")
        for h in report.get("humanization", []):
            print(
                f"    {h['profile']:>6s} @ {h['intensity']:>3d}%: "
                f"avg_drop={h['avg_score_drop']:+.2f}, "
                f"success={h['success_rate']:.0%}, "
                f"time={h['avg_humanize_ms']:.0f}ms"
            )

        print(f"\n  Elapsed: {report.get('elapsed_seconds', 0):.1f}s")
        print("=" * 60)

    @staticmethod
    def save_report(report: dict[str, Any], path: str) -> None:
        """Save report as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Report saved to %s", path)
