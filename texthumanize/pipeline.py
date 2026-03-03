"""Пайплайн обработки текста — оркестрация всех этапов."""

from __future__ import annotations

import logging
import os
import time
from difflib import SequenceMatcher
from typing import Callable, Protocol

from texthumanize.analyzer import TextAnalyzer
from texthumanize.cjk_segmenter import CJKSegmenter, is_cjk_text
from texthumanize.coherence_repair import CoherenceRepairer
from texthumanize.content_classifier import ContentType
from texthumanize.content_classifier import classify as classify_content
from texthumanize.decancel import Debureaucratizer
from texthumanize.fingerprint_randomizer import FingerprintRandomizer
from texthumanize.grammar_fix import GrammarCorrector
from texthumanize.lang import get_language_tier
from texthumanize.liveliness import LivelinessInjector
from texthumanize.naturalizer import TextNaturalizer
from texthumanize.normalizer import TypographyNormalizer
from texthumanize.paraphraser_ext import SemanticParaphraser
from texthumanize.readability_opt import ReadabilityOptimizer
from texthumanize.repetitions import RepetitionReducer
from texthumanize.segmenter import Segmenter
from texthumanize.sentence_validator import SentenceValidator
from texthumanize.structure import StructureDiversifier
from texthumanize.stylistic import StylisticAnalyzer, StylisticFingerprint
from texthumanize.syntax_rewriter import SyntaxRewriter
from texthumanize.tone_harmonizer import ToneHarmonizer
from texthumanize.universal import UniversalProcessor
from texthumanize.utils import AnalysisReport, HumanizeOptions, HumanizeResult
from texthumanize.validator import QualityValidator
from texthumanize.watermark import WatermarkDetector
from texthumanize.word_lm import WordLanguageModel

logger = logging.getLogger(__name__)

class StagePlugin(Protocol):
    """Protocol for custom pipeline stage plugins."""

    def process(self, text: str, lang: str, profile: str, intensity: int) -> str:
        """Process text and return the modified version."""
        ...

# Тип хука: функция (text, lang) -> text
HookFn = Callable[[str, str], str]

class Pipeline:
    """Оркестратор пайплайна гуманизации текста.

    Этапы обработки:
    0. Очистка водяных знаков (zero-width, homoglyphs, invisible Unicode)
    1. Сегментация (защита кода, URL, email и т.д.)
    2. Нормализация типографики
    3. Деканцеляризация (для языков с полным словарём)
    4. Разнообразие структуры (для языков с полным словарём)
    5. Уменьшение повторов (для языков с полным словарём)
    6. Инъекция «живости» (для языков с полным словарём)
    7. Семантическое перефразирование (синтаксические трансформации)
    8. Гармонизация тона (приведение к стилю профиля)
    9. Универсальная обработка (для ВСЕХ языков)
    10. Натурализация стиля (для ВСЕХ языков — КЛЮЧЕВОЙ ЭТАП)
    11. Оптимизация читаемости (разбивка/объединение предложений)
    12. Грамматическая коррекция (финальная полировка)
    13. Коррекция когерентности (связность абзацев)
    14. Валидация качества
    15. Восстановление защищённых сегментов

    Supports custom plugins that can be inserted before or after
    any built-in stage via register_plugin().
    """

    # Class-level default plugin registry (guarded by _cls_lock)
    _cls_lock = __import__('threading').Lock()
    _class_plugins_before: dict[str, list[StagePlugin]] = {}
    _class_plugins_after: dict[str, list[StagePlugin]] = {}
    _class_hooks_before: dict[str, list[HookFn]] = {}
    _class_hooks_after: dict[str, list[HookFn]] = {}

    STAGE_NAMES = (
        "watermark", "segmentation", "typography", "debureaucratization",
        "structure", "repetitions", "liveliness",
        "paraphrasing", "syntax_rewriting", "tone", "universal", "naturalization",
        "paraphrase_engine", "sentence_restructuring",
        "entropy_injection",
        "readability", "grammar", "coherence",
        "validation", "restore",
    )

    def __init__(self, options: HumanizeOptions | None = None):
        self.options = options or HumanizeOptions()
        # Instance-level copies of class plugins (isolation between instances)
        self._plugins_before = {k: list(v) for k, v in self._class_plugins_before.items()}
        self._plugins_after = {k: list(v) for k, v in self._class_plugins_after.items()}
        self._hooks_before = {k: list(v) for k, v in self._class_hooks_before.items()}
        self._hooks_after = {k: list(v) for k, v in self._class_hooks_after.items()}

    # ─── Plugin API ───────────────────────────────────────────

    @classmethod
    def register_plugin(
        cls,
        plugin: StagePlugin,
        *,
        before: str | None = None,
        after: str | None = None,
    ) -> None:
        """Register a custom pipeline stage plugin.

        Args:
            plugin: Object implementing the StagePlugin protocol (needs a
                    ``process(text, lang, profile, intensity) -> str`` method).
            before: Insert this plugin *before* the named stage.
            after: Insert this plugin *after* the named stage.

        Raises:
            ValueError: If neither ``before`` nor ``after`` is given, or
                        if the stage name is unknown.
        """
        if before is None and after is None:
            raise ValueError("Specify 'before' or 'after' stage name.")
        target = before or after
        if target not in cls.STAGE_NAMES:
            raise ValueError(
                f"Unknown stage: {target}. Valid stages: {cls.STAGE_NAMES}"
            )
        with cls._cls_lock:
            if before:
                cls._class_plugins_before.setdefault(before, []).append(plugin)
            else:
                cls._class_plugins_after.setdefault(after, []).append(plugin)  # type: ignore[arg-type]

    @classmethod
    def register_hook(
        cls,
        hook: HookFn,
        *,
        before: str | None = None,
        after: str | None = None,
    ) -> None:
        """Register a lightweight hook function.

        Args:
            hook: Callable ``(text: str, lang: str) -> str``.
            before: Run the hook *before* the named stage.
            after: Run the hook *after* the named stage.
        """
        if before is None and after is None:
            raise ValueError("Specify 'before' or 'after' stage name.")
        target = before or after
        if target not in cls.STAGE_NAMES:
            raise ValueError(
                f"Unknown stage: {target}. Valid stages: {cls.STAGE_NAMES}"
            )
        if before:
            cls._class_hooks_before.setdefault(before, []).append(hook)
        else:
            cls._class_hooks_after.setdefault(after, []).append(hook)  # type: ignore[arg-type]

    @classmethod
    def clear_plugins(cls) -> None:
        """Remove all registered plugins and hooks."""
        with cls._cls_lock:
            cls._class_plugins_before.clear()
            cls._class_plugins_after.clear()
            cls._class_hooks_before.clear()
            cls._class_hooks_after.clear()

    def _run_plugins(self, stage: str, text: str, lang: str, *, is_before: bool) -> str:
        """Run registered plugins/hooks for a stage."""
        registry = self._plugins_before if is_before else self._plugins_after
        hooks_reg = self._hooks_before if is_before else self._hooks_after

        for plugin in registry.get(stage, []):
            text = plugin.process(
                text, lang, self.options.profile, self.options.intensity
            )
        for hook in hooks_reg.get(stage, []):
            text = hook(text, lang)
        return text

    def _apply_custom_dict(self, text: str) -> tuple[str, list[dict]]:
        """Apply user-supplied custom_dict replacements.

        Supports both ``{"word": "replacement"}`` and
        ``{"word": ["var1", "var2"]}`` formats.  When a list is given,
        a random variant is chosen (respecting the pipeline seed).

        Returns:
            Tuple of (modified text, list of change dicts).
        """
        import random as _rnd
        import re as _re

        changes: list[dict] = []
        rng = _rnd.Random(self.options.seed)
        for pattern, replacement in self.options.custom_dict.items():  # type: ignore[union-attr]
            if isinstance(replacement, list):
                if not replacement:
                    continue
                chosen = rng.choice(replacement)
            else:
                chosen = replacement
            # Whole-word, case-insensitive match
            escaped = _re.escape(pattern)
            regex = _re.compile(rf"\b{escaped}\b", _re.IGNORECASE)
            if regex.search(text):
                text = regex.sub(chosen, text)
                changes.append({
                    "type": "custom_dict",
                    "description": f"custom_dict: «{pattern}» → «{chosen}»",
                })
        return text, changes

    # Maximum allowed time for a single pipeline run (seconds).
    # Can be overridden via TEXTHUMANIZE_TIMEOUT env var (useful for CI with coverage).
    PIPELINE_TIMEOUT: float = float(os.environ.get("TEXTHUMANIZE_TIMEOUT", "30"))

    def run(self, text: str, lang: str) -> HumanizeResult:
        """Запустить пайплайн обработки.

        Args:
            text: Текст для обработки.
            lang: Код языка.

        Returns:
            HumanizeResult с обработанным текстом и метаданными.

        Raises:
            TimeoutError: If processing exceeds PIPELINE_TIMEOUT seconds.
        """

        # Adaptive max_change_ratio: higher intensity allows more changes
        # intensity 30 → 0.42, intensity 50 → 0.50, intensity 80 → 0.62
        _user_max = self.options.constraints.get("max_change_ratio", None)
        if _user_max is not None:
            max_change = _user_max
        else:
            _i = self.options.intensity / 100.0
            max_change = min(0.80, 0.30 + _i * 0.50)
        deadline = time.monotonic() + self.PIPELINE_TIMEOUT

        def _check_deadline() -> None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Pipeline processing exceeded {self.PIPELINE_TIMEOUT}s timeout"
                )

        self._check_deadline = _check_deadline

        result = self._run_pipeline(text, lang, intensity_factor=1.0)
        _check_deadline()

        # Graduated retry: если change_ratio слишком высокий,
        # повторяем с пониженной интенсивностью
        if result.change_ratio > max_change:
            for factor in (0.4, 0.20, 0.10, 0.05):
                _check_deadline()
                retry = self._run_pipeline(text, lang, intensity_factor=factor)
                if retry.change_ratio <= max_change:
                    result = retry
                    break
                if retry.quality_score > result.quality_score:
                    result = retry

        # ── Per-run detection cache ────────────────────────────
        # Avoids recomputing detect_ai() for the same text within a single
        # run() invocation. The regression guard often re-detects text that
        # was already scored in the detector-in-the-loop.
        # Use text itself as key (not hash()) to avoid hash collisions.
        _detect_cache: dict[str, dict] = {}

        def _cached_detect(txt: str, *, lang: str) -> dict:  # type: ignore[type-arg]
            """Detect AI with per-run memoization.

            Uses fast MLP-only detection for the in-the-loop passes
            (~3-5x faster than full detection). Full detection is used
            only for the very first call to get accurate baseline.
            """
            cached = _detect_cache.get(txt)
            if cached is not None:
                return cached
            if len(_detect_cache) == 0:
                # First call: full detection for accurate baseline
                from texthumanize.core import detect_ai as _full_detect
                result_d: dict = _full_detect(txt, lang=lang)  # type: ignore[assignment]
            else:
                # Subsequent calls (in-the-loop): fast MLP-only
                from texthumanize.core import detect_ai_fast as _fast_detect
                result_d = _fast_detect(txt, lang=lang)
            _detect_cache[txt] = result_d
            return result_d

        # ── Detector-in-the-loop ──────────────────────────────
        # After humanization, check if the AI detector still flags
        # the result. If so, run another pass with escalated intensity
        # on the already-processed text to push it further from AI.
        target_ai = self.options.constraints.get("target_ai_score", 0.20)
        max_loops = self.options.constraints.get("max_detection_loops", 5)
        ai_before = result.metrics_before.get("artificiality_score", 0)

        # Also check the full combined detection score on the original text.
        # The heuristic analyzer (artificiality_score) may underestimate AI
        # probability for texts the neural MLP detector catches. Use the
        # higher of the two signals to decide whether to loop.
        _full_before = _cached_detect(text, lang=lang).get("combined_score", 0.0)
        _trigger = ai_before > 40 or _full_before > 0.50

        # Only loop if original text was actually AI-like
        if max_loops > 0 and _trigger:
            best_result = result
            detect_result = _cached_detect(result.text, lang=lang)
            best_score = detect_result.get("combined_score", 1.0)

            for loop_i in range(max_loops):
                _check_deadline()

                if best_score <= target_ai:
                    break  # Successfully humanized below threshold

                # Calculate change from original — scale headroom with intensity
                # to prevent inverse monotonicity (low intensity getting more
                # total change than high intensity via the loop)
                loop_change = self._calc_change_ratio(text, best_result.text)
                # When user explicitly sets max_change_ratio, use tight
                # headroom (5%) to respect their constraint.
                if _user_max is not None:
                    _max_total = max_change + 0.05
                else:
                    _headroom = max(0.10, (self.options.intensity / 100) * 0.25)
                    _max_total = max_change + _headroom

                # If AI score is still very high (>0.60) and the user hasn't
                # set an explicit max_change_ratio, allow much more change —
                # the text NEEDS aggressive editing to evade.
                if best_score > 0.60 and _user_max is None:
                    _max_total = max(0.80, _max_total)

                if loop_change > _max_total:
                    break  # Already changed enough, don't risk quality

                # Targeted escalation: analyze which detector features
                # are still flagging AI, and escalate accordingly.
                # Gentler escalation to avoid over-processing cliff.
                escalation = 1.20 + 0.25 * loop_i  # 1.20×, 1.45×, 1.70×, 1.95×, 2.20×
                esc_intensity = min(95, int(self.options.intensity * escalation))

                # Use detection details to target weak features
                loop_profile = self.options.profile
                detect_details = detect_result.get("details", {})
                neural_score = detect_details.get("neural_score", best_score)

                # If neural score is high, focus on structural transforms
                # by using a higher-intensity profile
                if neural_score > 0.6:
                    esc_intensity = min(esc_intensity + 10, 98)

                loop_opts = HumanizeOptions(
                    lang=self.options.lang,
                    profile=loop_profile,
                    intensity=esc_intensity,
                    preserve=dict(self.options.preserve),
                    constraints={
                        **self.options.constraints,
                        "max_change_ratio": 0.55,  # Per-loop limit (raised)
                    },
                    seed=(self.options.seed or 42) + loop_i + 1,
                )
                loop_pipeline = Pipeline(loop_opts)
                loop_pipeline._check_deadline = _check_deadline

                try:
                    loop_result = loop_pipeline._run_pipeline(
                        best_result.text, lang, intensity_factor=1.0,
                    )
                except (TimeoutError, Exception):
                    break

                # Accept loop result ONLY if it improves full detection score
                detect_result = _cached_detect(loop_result.text, lang=lang)
                loop_score = detect_result.get("combined_score", 1.0)
                if loop_score < best_score:
                    total_change = self._calc_change_ratio(text, loop_result.text)
                    if total_change <= _max_total:
                        best_result = HumanizeResult(
                            original=text,
                            text=loop_result.text,
                            lang=lang,
                            profile=self.options.profile,
                            intensity=self.options.intensity,
                            changes=[*best_result.changes, {"type": "detection_loop", "description": f"Loop {loop_i + 1}: AI " f"{best_score:.0%}→{loop_score:.0%}"}, *loop_result.changes],
                            metrics_before=best_result.metrics_before,
                            metrics_after=loop_result.metrics_after,
                        )
                        best_score = loop_score

            # If user set an explicit max_change_ratio constraint,
            # reject loop results that violate it. Fall back to the
            # pre-loop result which respects the constraint.
            if _user_max is not None:
                loop_change = self._calc_change_ratio(text, best_result.text)
                if loop_change > _user_max + 0.05:
                    # Detection loop overshot the constraint; keep pre-loop
                    pass  # result is still the pre-loop one captured above
                else:
                    result = best_result
            else:
                result = best_result

        # ── LLM-assisted evasion ─────────────────────────────
        # When an OpenAI API key is provided and the AI score is still
        # above the target after local transforms, use the LLM to
        # rewrite the text at sentence level for deeper evasion.
        _api_key = self.options.openai_api_key
        if _api_key:
            try:
                _check_deadline()
                llm_score = _cached_detect(result.text, lang=lang).get(
                    "combined_score", 0.0,
                )
                if llm_score > target_ai:
                    llm_result = self._llm_assisted_rewrite(
                        original=text,
                        current=result,
                        lang=lang,
                        api_key=_api_key,
                        model=self.options.openai_model,
                        target_score=target_ai,
                        max_change=max_change,
                        detect_fn=_cached_detect,
                        check_deadline=_check_deadline,
                    )
                    if llm_result is not None:
                        result = llm_result
            except (TimeoutError, Exception):
                pass  # LLM evasion is advisory, never blocks return

        # ── Regression guard ─────────────────────────────────
        # If humanization made the AI score WORSE (increased), try
        # graduated fallback with decreasing intensity factors.
        # This replaces the old binary 0.05× fallback which was too
        # aggressive and returned near-original (high AI) text.
        try:
            score_after = _cached_detect(result.text, lang=lang).get(
                "combined_score", 0.0,
            )
            # Compare like-for-like: full ensemble before vs. after
            score_before_full = _cached_detect(text, lang=lang).get(
                "combined_score", 0.0,
            )
            if score_after > score_before_full + 0.01:  # Worsened by >1%
                # Graduated fallback: try decreasing intensity factors,
                # keep the best result (lowest AI score)
                best_fallback = result
                best_fb_score = score_after
                for fb_factor in (0.5, 0.3, 0.15, 0.08):
                    _check_deadline()
                    fb_result = self._run_pipeline(
                        text, lang, intensity_factor=fb_factor,
                    )
                    fb_score = _cached_detect(fb_result.text, lang=lang).get(
                        "combined_score", 0.0,
                    )
                    if fb_score < best_fb_score:
                        best_fallback = fb_result
                        best_fb_score = fb_score
                    # If we found something better than original, stop
                    if fb_score <= score_before_full:
                        break
                result = best_fallback
                result.changes.append({
                    "type": "regression_guard",
                    "description": (
                        f"Откат: AI {score_before_full:.0%}→{score_after:.0%} "
                        f"(graduated fallback → {best_fb_score:.0%})"
                    ),
                })
        except Exception:
            pass  # Guard is advisory, never blocks return

        # ── Hard constraint enforcement ────────────────────────
        # If the user set max_change_ratio explicitly, guarantee the final
        # result respects it (within 5% tolerance). Re-run at progressively
        # lower intensity if necessary.
        if _user_max is not None and result.change_ratio > _user_max + 0.05:
            for fb_factor in (0.3, 0.15, 0.08, 0.03):
                _check_deadline()
                fb = self._run_pipeline(text, lang, intensity_factor=fb_factor)
                if fb.change_ratio <= _user_max + 0.05:
                    result = fb
                    break

        # ── Final sentence-level sanitization ─────────────────
        # After all pipeline passes (graduated retry, detection loops,
        # regression guard), clean up any remaining artifacts that
        # were introduced by late passes or cross-pass interactions.
        import re as _re_final
        _final_text = result.text
        #  Double conjunctions: "and and", "и и"
        _final_text = _re_final.sub(
            r'\b(and|but|or|yet|so|и|і|а|але|но|und|oder|aber'
            r'|et|ou|mais|y|o|pero)\s+\1\b',
            r'\1', _final_text, flags=_re_final.IGNORECASE,
        )
        #  Dangling conjunction before punctuation: "and." "and,"
        _final_text = _re_final.sub(
            r',?\s*\b(and|but|or|и|і|а|але|но)\b\s*([.!?;])',
            r'\2', _final_text, flags=_re_final.IGNORECASE,
        )
        #  Conjunction chain residue: ", and, but,"
        _final_text = _re_final.sub(
            r'(?:,\s*\b(?:and|but|or|however|moreover|also)\b\s*){2,}',
            ', ', _final_text, flags=_re_final.IGNORECASE,
        )
        if _final_text != result.text:
            result = HumanizeResult(
                original=result.original,
                text=_final_text,
                lang=result.lang,
                profile=result.profile,
                intensity=result.intensity,
                changes=[*result.changes, {
                    "type": "final_sanitization",
                    "description": "Финальная очистка артефактов",
                }],
                metrics_before=result.metrics_before,
                metrics_after=result.metrics_after,
            )

        return result

    # ── LLM-assisted rewrite helper ─────────────────────────

    _LLM_SYSTEM_PROMPT = (
        "You are a text rewriter. Rewrite the following text to sound "
        "completely natural and human-written in {lang}. "
        "CRITICAL RULES:\n"
        "- Use short, simple words (1-2 syllables preferred)\n"
        "- Vary sentence lengths dramatically: mix very short (3-5 words) "
        "with medium (10-15 words) sentences\n"
        "- Add minor imperfections: contractions, informal transitions, "
        "occasional fragments\n"
        "- Avoid formal/academic vocabulary\n"
        "- Start sentences with different words\n"
        "- Preserve the original meaning\n"
        "Only output the rewritten text, nothing else."
    )

    def _llm_assisted_rewrite(
        self,
        original: str,
        current: HumanizeResult,
        lang: str,
        api_key: str,
        model: str,
        target_score: float,
        max_change: float,
        detect_fn: Callable[..., dict],
        check_deadline: Callable[[], None],
    ) -> HumanizeResult | None:
        """Use OpenAI LLM to rewrite text that local transforms couldn't evade.

        Returns an improved HumanizeResult or None if LLM didn't help.
        """
        from texthumanize.ai_backend import AIBackend

        check_deadline()

        try:
            ai = AIBackend(
                openai_api_key=api_key,
                openai_model=model,
                prefer="openai",
            )
            # Rewrite the already-humanized text for deeper evasion
            rewritten = ai.paraphrase(
                current.text, lang=lang, style=self.options.profile,
            )
        except Exception:
            return None

        if not rewritten or not rewritten.strip():
            return None

        # Also try improve_naturalness for a second variant
        try:
            check_deadline()
            natural = ai.improve_naturalness(current.text, lang=lang)
        except Exception:
            natural = None

        # Evaluate both variants, pick the best
        candidates = [rewritten]
        if natural and natural.strip() and natural != rewritten:
            candidates.append(natural)

        best_text: str | None = None
        pre_score = detect_fn(current.text, lang=lang).get("combined_score", 1.0)
        best_score = pre_score

        for candidate in candidates:
            check_deadline()
            try:
                cand_detect = detect_fn(candidate, lang=lang)
            except Exception:
                continue
            cand_score = cand_detect.get("combined_score", 1.0)
            if cand_score < best_score:
                best_text = candidate
                best_score = cand_score

        if best_text is None:
            return None

        # Build result
        return HumanizeResult(
            original=original,
            text=best_text,
            lang=lang,
            profile=self.options.profile,
            intensity=self.options.intensity,
            changes=[
                *current.changes,
                {
                    "type": "llm_evasion",
                    "description": (
                        f"LLM rewrite ({model}): "
                        f"AI {pre_score:.0%}→{best_score:.0%}"
                    ),
                },
            ],
            metrics_before=current.metrics_before,
            metrics_after=current.metrics_after,
        )

    @staticmethod
    def _calc_change_ratio(original: str, current: str) -> float:
        """Вычислить текущий change_ratio (SequenceMatcher-based)."""
        if not original:
            return 0.0
        orig_words = original.split()
        curr_words = current.split()
        if not orig_words:
            return 0.0
        matcher = SequenceMatcher(None, orig_words, curr_words)
        return min(1.0 - matcher.ratio(), 1.0)

    def _typography_only(
        self,
        text: str,
        lang: str,
        metrics_before: AnalysisReport,
        changes: list[dict],
        *,
        preserve_config: dict | None = None,
    ) -> HumanizeResult:
        """Fast path for already-natural text: only typography normalization.

        Skips all semantic stages to prevent over-processing genuine
        human-written content.
        """
        original = text
        all_changes = list(changes)
        all_changes.append({
            "type": "skip_natural",
            "description": (
                f"Текст уже естественный (AI={metrics_before.artificiality_score:.0f}%). "
                "Применяется только типографика."
            ),
        })

        # Watermark cleaning (even for natural text)
        wm_detector = WatermarkDetector(lang=lang)
        wm_report = wm_detector.detect(text)
        if wm_report.has_watermarks:
            text = wm_report.cleaned_text
            all_changes.append({
                "type": "watermark_cleaning",
                "description": (
                    f"Водяные знаки: {', '.join(wm_report.watermark_types)} "
                    f"(удалено {wm_report.characters_removed} символов)"
                ),
            })

        # Segmentation
        preserve = preserve_config or {}
        segmenter = Segmenter(preserve=preserve)
        segmented = segmenter.segment(text)
        text = segmented.text

        # Typography only
        normalizer = TypographyNormalizer(
            profile=self.options.profile,
            lang=lang,
        )
        text = normalizer.normalize(text)
        all_changes.extend(normalizer.changes)

        # Restore segments
        text = segmented.restore(text)

        # Metrics after
        analyzer = TextAnalyzer(lang=lang)
        metrics_after = analyzer.analyze(text)

        return HumanizeResult(
            original=original,
            text=text,
            lang=lang,
            profile=self.options.profile,
            intensity=self.options.intensity,
            changes=all_changes,
            metrics_before={
                "artificiality_score": metrics_before.artificiality_score,
                "avg_sentence_length": metrics_before.avg_sentence_length,
                "bureaucratic_ratio": metrics_before.bureaucratic_ratio,
                "connector_ratio": metrics_before.connector_ratio,
                "repetition_score": metrics_before.repetition_score,
                "typography_score": metrics_before.typography_score,
                "predictability_score": metrics_before.predictability_score,
                "vocabulary_richness": metrics_before.vocabulary_richness,
            },
            metrics_after={
                "artificiality_score": metrics_after.artificiality_score,
                "avg_sentence_length": metrics_after.avg_sentence_length,
                "bureaucratic_ratio": metrics_after.bureaucratic_ratio,
                "connector_ratio": metrics_after.connector_ratio,
                "repetition_score": metrics_after.repetition_score,
                "typography_score": metrics_after.typography_score,
                "predictability_score": metrics_after.predictability_score,
                "vocabulary_richness": metrics_after.vocabulary_richness,
            },
        )

    def _safe_stage(
        self,
        stage_name: str,
        text: str,
        lang: str,
        fn: Callable[[], tuple[str, list[dict]]],
        stage_timings: dict[str, float],
    ) -> tuple[str, list[dict]]:
        """Execute a pipeline stage with error isolation and profiling.

        If the stage raises an exception, returns the original text
        unchanged and records a skip change.
        """
        t0 = time.perf_counter()
        try:
            new_text, changes = fn()
            stage_timings[stage_name] = time.perf_counter() - t0
            return new_text, changes
        except Exception as exc:
            stage_timings[stage_name] = time.perf_counter() - t0
            logging.getLogger("texthumanize").warning(
                "Stage '%s' failed: %s — skipping", stage_name, exc,
            )
            return text, [{
                "type": "stage_skipped",
                "description": f"Этап «{stage_name}» пропущен из-за ошибки: {exc}",
            }]

    @staticmethod
    def _strip_fragment_chains(text: str, lang: str) -> str:
        """Remove over-dense short-fragment chains injected by multiple stages.

        Handles two types of artifacts:
        1. Consecutive short fragments: "Here's the thing. But why? Actually."
        2. In-sentence garbled chains: ", and, but, however, and..."

        Preserves paragraph boundaries (\\n\\n).
        """
        import re as _re

        # Process each paragraph independently to preserve boundaries.
        paragraphs = text.split('\n\n')
        cleaned_paras: list[str] = []

        for para in paragraphs:
            if not para.strip():
                cleaned_paras.append(para)
                continue

            # Pass 0: Clean garbled conjunction/connector chains within sentences.
            para = _re.sub(
                r'(?:,\s*(?:and|but|or|yet|so|however|granted|moreover|furthermore|also|thus|hence)'
                r'(?:\s*,\s*|\s+)){2,}',
                ', ', para, flags=_re.IGNORECASE,
            )
            # Russian/Ukrainian connector stacking
            para = _re.sub(
                r'(?:,?\s*(?:и|а|но|однако|также|ещё|ще|причём|причому|крім того|кроме того)'
                r'(?:\s*,\s*|\s+)){2,}',
                ', ', para, flags=_re.IGNORECASE,
            )
            # Double conjunctions: "и и", "and and"
            para = _re.sub(r'\b(и|і|and|und|et|y|e)\s+\1\b', r'\1', para, flags=_re.IGNORECASE)

            # Pass 1: Split into sentences and remove consecutive short fragments.
            parts = _re.split(r'(?<=[.!?])\s+(?=[A-ZА-ЯІЇЄҐ])', para)
            if len(parts) < 4:
                cleaned_paras.append(para)
                continue

            def _is_fragment(s: str) -> bool:
                words = s.split()
                return len(words) <= 5 and bool(s.strip())

            # Strip consecutive fragments (keep first in each run)
            cleaned: list[str] = []
            prev_was_fragment = False
            for s in parts:
                if _is_fragment(s):
                    if prev_was_fragment:
                        continue  # skip consecutive fragment
                    prev_was_fragment = True
                else:
                    prev_was_fragment = False
                cleaned.append(s)

            # Enforce max 1 fragment per 5-sentence window
            window = 5
            result: list[str] = []
            frag_count_in_window = 0
            for i, s in enumerate(cleaned):
                if _is_fragment(s):
                    frag_count_in_window += 1
                    if frag_count_in_window > 1:
                        continue  # skip excess fragment in this window
                if i > 0 and i % window == 0:
                    frag_count_in_window = 0
                result.append(s)

            cleaned_paras.append(' '.join(result))

        return '\n\n'.join(cleaned_paras)

    def _run_pipeline(
        self, text: str, lang: str, *, intensity_factor: float = 1.0,
    ) -> HumanizeResult:
        """Выполнить один проход пайплайна.

        Args:
            text: Текст для обработки.
            lang: Код языка.
            intensity_factor: Множитель интенсивности (0-1) для graduated retry.
        """
        original = text
        all_changes: list[dict] = []
        stage_timings: dict[str, float] = {}
        checkpoints: list[tuple[str, str]] = []  # (stage_name, text_after_stage)

        # ── Sentence-level integrity validator ────────────────
        # Catches broken sentences BETWEEN stages (not just at the end).
        # After each major transformation, compares output sentences
        # against their pre-stage versions and reverts broken ones.
        _sv = SentenceValidator(lang=lang)

        # Анализ до обработки
        analyzer = TextAnalyzer(lang=lang)
        metrics_before = analyzer.analyze(text)

        # ── Stage 0: Content type classification ──────────────
        _t0 = time.perf_counter()
        content_profile = classify_content(text, lang=lang)
        stage_timings["content_classify"] = time.perf_counter() - _t0
        all_changes.append({
            "type": "content_classification",
            "description": (
                f"Тип контента: {content_profile.content_type.value} "
                f"(уверенность {content_profile.confidence:.0%})"
            ),
        })

        # ── Адаптивная интенсивность ──────────────────────────
        # Автоматически корректируем intensity на основе artificiality_score:
        # - Высокий AI-скор (>60) → усиливаем обработку
        # - Низкий AI-скор (<25) → мягко ослабляем, но гарантируем не менее
        #   50% от запрошенной intensity (монотонность)
        effective_options = self.options
        ai_score = metrics_before.artificiality_score
        base_intensity = self.options.intensity

        # Применяем graduated retry factor
        base_intensity = max(5, int(base_intensity * intensity_factor))

        # Cap base intensity at 92 to allow strong single-pass processing.
        # The detector-in-the-loop provides additional passes if needed.
        base_intensity = min(base_intensity, 92)

        # Content-type intensity cap — protects sensitive content
        base_intensity = min(base_intensity, content_profile.max_intensity_cap)

        if ai_score >= 70:
            # Сильно «искусственный» текст — aggressive boost
            adjusted = min(95, int(base_intensity * 1.30))
        elif ai_score >= 50:
            # Средне «искусственный» — moderate boost
            adjusted = min(90, int(base_intensity * 1.20))
        elif ai_score <= 5:
            # Полностью «живой» текст — применяем только типографику
            return self._typography_only(
                text, lang, metrics_before, all_changes,
                preserve_config=dict(self.options.preserve),
            )
        elif ai_score <= 10:
            # Почти полностью «живой» текст — минимальная обработка
            adjusted = max(5, int(base_intensity * 0.2))
        elif ai_score <= 15:
            # Почти «живой» текст — сильно ослабляем
            adjusted = max(8, int(base_intensity * 0.35))
        elif ai_score <= 25:
            # Слабо «искусственный» — ослабляем
            adjusted = max(10, int(base_intensity * 0.5))
        else:
            adjusted = base_intensity

        if adjusted != self.options.intensity:
            # Создаём копию опций с адаптированной интенсивностью
            # (either intensity_factor changed it OR ai_score adjustment)
            effective_options = HumanizeOptions(
                lang=self.options.lang,
                profile=self.options.profile,
                intensity=adjusted,
                preserve=dict(self.options.preserve),
                constraints=dict(self.options.constraints),
                seed=self.options.seed,
            )
            all_changes.append({
                "type": "adaptive_intensity",
                "description": (
                    f"Адаптация: AI-скор={ai_score:.0f}%, "
                    f"intensity {base_intensity}→{adjusted}"
                ),
            })

        # 1. Сегментация — защита неизменяемых блоков
        preserve_config = dict(self.options.preserve)

        # ── 0. Очистка водяных знаков ─────────────────────────
        _t0 = time.perf_counter()
        text = self._run_plugins("watermark", text, lang, is_before=True)
        wm_detector = WatermarkDetector(lang=lang)
        wm_report = wm_detector.detect(text)
        if wm_report.has_watermarks:
            text = wm_report.cleaned_text
            all_changes.append({
                "type": "watermark_cleaning",
                "description": (
                    f"Водяные знаки: {', '.join(wm_report.watermark_types)} "
                    f"(удалено {wm_report.characters_removed} символов, "
                    f"уверенность {wm_report.confidence:.0%})"
                ),
            })
        text = self._run_plugins("watermark", text, lang, is_before=False)
        stage_timings["watermark"] = time.perf_counter() - _t0

        # ── Стилистический отпечаток ──────────────────────────
        # Если задан target_style, анализируем текущий стиль
        # и корректируем параметры для приближения к целевому
        style_meta: dict = {}
        target_fp = self.options.target_style
        # Resolve preset name → StylisticFingerprint
        if isinstance(target_fp, str):
            from texthumanize.stylistic import STYLE_PRESETS
            target_fp = STYLE_PRESETS.get(target_fp)
        if target_fp is not None and isinstance(target_fp, StylisticFingerprint):
            style_analyzer = StylisticAnalyzer(lang=lang)
            source_fp = style_analyzer.extract(text)
            style_similarity = source_fp.similarity(target_fp)
            style_meta = {
                "style_similarity_before": round(style_similarity, 3),
                "target_sentence_mean": round(target_fp.sentence_length_mean, 1),
                "source_sentence_mean": round(source_fp.sentence_length_mean, 1),
            }
            all_changes.append({
                "type": "style_matching",
                "description": (
                    f"Стилистическое сходство: {style_similarity:.1%}. "
                    f"Целевая длина предложений: {target_fp.sentence_length_mean:.0f} слов"
                ),
            })
        # Добавляем keep_keywords в protect
        keep_kw = self.options.constraints.get("keep_keywords", [])
        if keep_kw:
            preserve_config.setdefault("keep_keywords", [])
            preserve_config["keep_keywords"] = keep_kw

        _t0 = time.perf_counter()
        segmenter = Segmenter(preserve=preserve_config)
        segmented = segmenter.segment(text)
        text = segmented.text
        stage_timings["segmentation"] = time.perf_counter() - _t0

        # 2. Нормализация типографики
        _t0 = time.perf_counter()
        text = self._run_plugins("typography", text, lang, is_before=True)
        normalizer = TypographyNormalizer(
            profile=self.options.profile,
            lang=lang,
        )
        text = normalizer.normalize(text)
        all_changes.extend(normalizer.changes)
        text = self._run_plugins("typography", text, lang, is_before=False)

        # 2b. Пользовательский словарь замен (custom_dict)
        if self.options.custom_dict:
            text, cd_changes = self._apply_custom_dict(text)
            all_changes.extend(cd_changes)
        stage_timings["typography"] = time.perf_counter() - _t0

        # 2c. CJK pre-segmentation — inject word boundaries for CJK text
        # so downstream word-level stages (regex \b, splits) work correctly.
        _cjk_active = False
        if is_cjk_text(text):
            _t0 = time.perf_counter()
            from texthumanize.cjk_segmenter import detect_cjk_lang
            cjk_lang = detect_cjk_lang(text) or "zh"
            _cjk_seg = CJKSegmenter(lang=cjk_lang)
            _cjk_words = _cjk_seg.segment(text)
            # Only add spaces between CJK tokens (keep existing if mixed)
            cjk_text = " ".join(w for w in _cjk_words if w.strip())
            if cjk_text and cjk_text != text:
                text = cjk_text
                _cjk_active = True
                all_changes.append({
                    "type": "cjk_segmentation",
                    "description": (
                        f"CJK сегментация ({cjk_lang}): "
                        f"разбивка на {len(_cjk_words)} токенов"
                    ),
                })
            stage_timings["cjk_segmentation"] = time.perf_counter() - _t0

        # Этапы 3-6: словарная обработка (Tier 1 + Tier 2 languages)
        # Skip if content is pure code — nothing to debureau/rephrase
        _skip_word_stages = (
            content_profile.content_type == ContentType.CODE
        )
        if (get_language_tier(lang) <= 2 and get_language_tier(lang) > 0
                and not _skip_word_stages):
            # 3. Деканцеляризация
            text = self._run_plugins("debureaucratization", text, lang, is_before=True)
            def _run_debureau() -> tuple[str, list]:
                d = Debureaucratizer(
                    lang=lang,
                    profile=effective_options.profile,
                    intensity=effective_options.intensity,
                    seed=effective_options.seed,
                )
                t = d.process(text)
                return t, d.changes
            text, _ch = self._safe_stage(
                "debureaucratization", text, lang,
                _run_debureau, stage_timings,
            )
            all_changes.extend(_ch)
            checkpoints.append(("debureaucratization", text))
            text = self._run_plugins("debureaucratization", text, lang, is_before=False)

            # 4. Разнообразие структуры
            text = self._run_plugins("structure", text, lang, is_before=True)
            def _run_structure() -> tuple[str, list]:
                s = StructureDiversifier(
                    lang=lang,
                    profile=effective_options.profile,
                    intensity=effective_options.intensity,
                    seed=effective_options.seed,
                )
                t = s.process(text)
                return t, s.changes
            text, _ch = self._safe_stage("structure", text, lang, _run_structure, stage_timings)
            all_changes.extend(_ch)
            checkpoints.append(("structure", text))
            text = self._run_plugins("structure", text, lang, is_before=False)

            # 5. Уменьшение повторов
            text = self._run_plugins("repetitions", text, lang, is_before=True)
            def _run_repetitions() -> tuple[str, list]:
                r = RepetitionReducer(
                    lang=lang,
                    profile=effective_options.profile,
                    intensity=effective_options.intensity,
                    seed=effective_options.seed,
                )
                t = r.process(text)
                return t, r.changes
            text, _ch = self._safe_stage("repetitions", text, lang, _run_repetitions, stage_timings)
            all_changes.extend(_ch)
            checkpoints.append(("repetitions", text))
            text = self._run_plugins("repetitions", text, lang, is_before=False)

            # 6. Инъекция «живости»
            text = self._run_plugins("liveliness", text, lang, is_before=True)
            def _run_liveliness() -> tuple[str, list]:
                li = LivelinessInjector(
                    lang=lang,
                    profile=effective_options.profile,
                    intensity=effective_options.intensity,
                    seed=effective_options.seed,
                )
                t = li.process(text)
                return t, li.changes
            text, _ch = self._safe_stage("liveliness", text, lang, _run_liveliness, stage_timings)
            all_changes.extend(_ch)
            checkpoints.append(("liveliness", text))
            text = self._run_plugins("liveliness", text, lang, is_before=False)

        # 7. Семантическое перефразирование (Tier 1 + Tier 2)
        #    Skipped if content type disallows paraphrasing (e.g. pure code)
        if (get_language_tier(lang) <= 2 and get_language_tier(lang) > 0
                and content_profile.allow_paraphrase):
            text = self._run_plugins("paraphrasing", text, lang, is_before=True)
            def _run_paraphrasing() -> tuple[str, list]:
                p = SemanticParaphraser(
                    lang=lang,
                    intensity=effective_options.intensity / 100.0,
                    seed=effective_options.seed,
                )
                t = p.process(text)
                changes = [
                    {"type": "paraphrasing", "kind": c.kind,
                     "description": f"{c.kind}: {c.original[:60]}… → {c.transformed[:60]}…"}
                    for c in p.changes
                ]
                return t, changes
            text, _ch = self._safe_stage(
                "paraphrasing", text, lang,
                _run_paraphrasing, stage_timings,
            )
            all_changes.extend(_ch)
            checkpoints.append(("paraphrasing", text))
            text = self._run_plugins("paraphrasing", text, lang, is_before=False)

        # 7b. Syntax rewriting (sentence-level structural transforms)
        # Only for Tier 1 languages — SyntaxRewriter has proper grammar
        # rules only for these. Skipped for code/academic/technical content.
        if get_language_tier(lang) <= 2 and get_language_tier(lang) > 0 and content_profile.allow_syntax_rewrite:
            text = self._run_plugins("syntax_rewriting", text, lang, is_before=True)
            def _run_syntax_rewrite() -> tuple[str, list]:
                import re as _re_sr
                sr = SyntaxRewriter(
                    lang=lang,
                    seed=effective_options.seed,
                )
                # Split into paragraphs first to preserve structure
                paragraphs = text.split('\n')
                changed = False
                prob = effective_options.intensity / 100.0
                import random as _rnd_sr
                _sr_rng = _rnd_sr.Random(effective_options.seed)
                result_paras = []
                for para in paragraphs:
                    if not para.strip():
                        result_paras.append(para)
                        continue
                    sents = _re_sr.split(r'(?<=[.!?])\s+', para)
                    rewritten = []
                    for s in sents:
                        if _sr_rng.random() < prob * 0.55:
                            r = sr.rewrite_random(s)
                            if r != s:
                                changed = True
                            rewritten.append(r)
                        else:
                            rewritten.append(s)
                    result_paras.append(' '.join(rewritten))
                t = '\n'.join(result_paras)
                changes = [{"type": "syntax_rewrite", "description": "Syntax rewriting applied"}]
                return (t, changes) if changed else (text, [])
            text, _ch = self._safe_stage(
                "syntax_rewriting", text, lang,
                _run_syntax_rewrite, stage_timings,
            )
            all_changes.extend(_ch)
            checkpoints.append(("syntax_rewriting", text))
            # Sentence-level validation: revert broken sentences
            _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
            text = _sv.validate(_sv_before, text, stage_name="syntax_rewriting")
            text = self._run_plugins("syntax_rewriting", text, lang, is_before=False)

        # 8. Гармонизация тона (для ВСЕХ языков)
        text = self._run_plugins("tone", text, lang, is_before=True)
        def _run_tone() -> tuple[str, list]:
            th = ToneHarmonizer(
                lang=lang,
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = th.process(text)
            return t, th.changes
        text, _ch = self._safe_stage("tone", text, lang, _run_tone, stage_timings)
        all_changes.extend(_ch)
        checkpoints.append(("tone", text))
        text = self._run_plugins("tone", text, lang, is_before=False)

        # 9. Универсальная обработка (для ВСЕХ языков)
        text = self._run_plugins("universal", text, lang, is_before=True)
        def _run_universal() -> tuple[str, list]:
            u = UniversalProcessor(
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = u.process(text)
            return t, u.changes
        text, _ch = self._safe_stage("universal", text, lang, _run_universal, stage_timings)
        all_changes.extend(_ch)
        checkpoints.append(("universal", text))
        text = self._run_plugins("universal", text, lang, is_before=False)

        # 10. Натурализация стиля (КЛЮЧЕВОЙ ЭТАП — для ВСЕХ языков)
        text = self._run_plugins("naturalization", text, lang, is_before=True)
        def _run_naturalization() -> tuple[str, list]:
            n = TextNaturalizer(
                lang=lang,
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = n.process(text)
            return t, n.changes
        text, _ch = self._safe_stage(
            "naturalization", text, lang,
            _run_naturalization, stage_timings,
        )
        all_changes.extend(_ch)
        checkpoints.append(("naturalization", text))
        # Sentence-level validation: revert broken sentences
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="naturalization")
        text = self._run_plugins("naturalization", text, lang, is_before=False)

        # 10a. Paraphrase engine — structural rewrites (MWE simplification,
        # connector deletion, hedging, perspective rotation, clause embedding).
        text = self._run_plugins("paraphrase_engine", text, lang, is_before=True)
        def _run_paraphrase_engine() -> tuple[str, list]:
            from texthumanize.paraphrase_engine import ParaphraseEngine
            pe = ParaphraseEngine(
                lang=lang,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = pe.transform(text)
            return t, [{"type": "paraphrase_engine", "description": c} for c in pe.changes]
        text, _ch = self._safe_stage(
            "paraphrase_engine", text, lang,
            _run_paraphrase_engine, stage_timings,
        )
        all_changes.extend(_ch)
        checkpoints.append(("paraphrase_engine", text))
        # Sentence-level validation: revert broken sentences
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="paraphrase_engine")
        text = self._run_plugins("paraphrase_engine", text, lang, is_before=False)

        # 10a½. Sentence restructuring — deep structural transforms
        # (contractions, register mixing, length reshaping, discourse markers,
        #  rhetorical questions, cleft/existential transforms).
        text = self._run_plugins("sentence_restructuring", text, lang, is_before=True)
        def _run_restructuring() -> tuple[str, list]:
            from texthumanize.sentence_restructurer import SentenceRestructurer
            sr = SentenceRestructurer(
                lang=lang,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = sr.process(text)
            return t, sr.changes
        text, _ch = self._safe_stage(
            "sentence_restructuring", text, lang,
            _run_restructuring, stage_timings,
        )
        all_changes.extend(_ch)
        checkpoints.append(("sentence_restructuring", text))
        # Sentence-level validation: revert broken sentences
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="sentence_restructuring")
        text = self._run_plugins("sentence_restructuring", text, lang, is_before=False)

        # 10b. Word LM quality gate — advisory perplexity monitoring.
        # Reports perplexity change but does NOT roll back — perplexity
        # values are advisory until language model data is expanded.
        _t0 = time.perf_counter()
        try:
            _wlm = WordLanguageModel(lang=lang)
            _pp_before = _wlm.perplexity(checkpoints[-2][1] if len(checkpoints) >= 2 else original)
            _pp_after = _wlm.perplexity(text)
            if _pp_before > 0 and _pp_after > 0:
                _pp_delta = "↓" if _pp_after < _pp_before else "↑"
                all_changes.append({
                    "type": "quality_gate_advisory",
                    "description": (
                        f"Word LM: перплексия {_pp_before:.1f}→{_pp_after:.1f} ({_pp_delta})"
                    ),
                })
        except Exception:
            pass  # Word LM is advisory, never blocks pipeline
        stage_timings["word_lm_gate"] = time.perf_counter() - _t0

        # 10c. Entropy & burstiness injection (Phase 1 — all languages)
        text = self._run_plugins("entropy_injection", text, lang, is_before=True)
        def _run_entropy() -> tuple[str, list]:
            from texthumanize.entropy_injector import EntropyInjector
            ei = EntropyInjector(
                lang=lang,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
                profile=effective_options.profile,
            )
            t = ei.process(text)
            return t, ei.changes
        text, _ch = self._safe_stage(
            "entropy_injection", text, lang,
            _run_entropy, stage_timings,
        )
        all_changes.extend(_ch)
        checkpoints.append(("entropy_injection", text))
        # Sentence-level validation: revert broken sentences
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="entropy_injection")
        text = self._run_plugins("entropy_injection", text, lang, is_before=False)

        # 10d. Post-injection fragment deduplication
        # Multiple injection stages (burstiness, rhetorical questions,
        # discourse surprise) fire independently, so adjacent short
        # fragments can stack into garbled chains like
        # "Here's the deal: but why? Granted, and, but..."
        # Strip excess: keep at most 1 fragment per 5-sentence window.
        text = self._strip_fragment_chains(text, lang)

        # 11. Оптимизация читаемости (для ВСЕХ языков)
        text = self._run_plugins("readability", text, lang, is_before=True)
        def _run_readability() -> tuple[str, list]:
            ro = ReadabilityOptimizer(
                lang=lang,
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = ro.process(text)
            return t, ro.changes
        text, _ch = self._safe_stage("readability", text, lang, _run_readability, stage_timings)
        all_changes.extend(_ch)
        checkpoints.append(("readability", text))
        text = self._run_plugins("readability", text, lang, is_before=False)

        # 12. Грамматическая коррекция (для ВСЕХ языков — финальная полировка)
        text = self._run_plugins("grammar", text, lang, is_before=True)
        def _run_grammar() -> tuple[str, list]:
            g = GrammarCorrector(
                lang=lang,
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = g.process(text)
            return t, g.changes
        text, _ch = self._safe_stage("grammar", text, lang, _run_grammar, stage_timings)
        all_changes.extend(_ch)
        checkpoints.append(("grammar", text))
        text = self._run_plugins("grammar", text, lang, is_before=False)

        # 12½. Grammar Guard — neural artifact detector + synonym rollback.
        # Catches bad collocations/agreements introduced by upstream stages.
        text = self._run_plugins("grammar_guard", text, lang, is_before=True)
        def _run_grammar_guard() -> tuple[str, list]:
            from texthumanize.grammar_guard import GrammarGuard
            gg = GrammarGuard(lang=lang)
            t = gg.process(text, original)
            return t, gg.result.changes
        text, _ch = self._safe_stage(
            "grammar_guard", text, lang,
            _run_grammar_guard, stage_timings,
        )
        all_changes.extend(_ch)
        checkpoints.append(("grammar_guard", text))
        # Sentence-level validation after grammar guard
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="grammar_guard")
        text = self._run_plugins("grammar_guard", text, lang, is_before=False)

        # 13. Коррекция когерентности (для ВСЕХ языков)
        text = self._run_plugins("coherence", text, lang, is_before=True)
        def _run_coherence() -> tuple[str, list]:
            c = CoherenceRepairer(
                lang=lang,
                profile=effective_options.profile,
                intensity=effective_options.intensity,
                seed=effective_options.seed,
            )
            t = c.process(text)
            return t, c.changes
        text, _ch = self._safe_stage("coherence", text, lang, _run_coherence, stage_timings)
        all_changes.extend(_ch)
        checkpoints.append(("coherence", text))
        # Sentence-level validation after coherence
        _sv_before = checkpoints[-2][1] if len(checkpoints) >= 2 else original
        text = _sv.validate(_sv_before, text, stage_name="coherence")
        text = self._run_plugins("coherence", text, lang, is_before=False)

        # 13a. Final entropy/burstiness re-injection
        # Stages 11-13 (readability, grammar, coherence) can re-uniformize
        # sentence lengths and undo entropy work. This final pass ensures
        # burstiness and statistical diversity are maintained.
        if effective_options.intensity >= 20:
            def _run_entropy_final() -> tuple[str, list]:
                from texthumanize.entropy_injector import EntropyInjector
                ei = EntropyInjector(
                    lang=lang,
                    intensity=min(effective_options.intensity, 50),
                    seed=(effective_options.seed + 7) if effective_options.seed else None,
                    profile=effective_options.profile,
                )
                t = ei.process(text)
                return t, [c for c in ei.changes if "burstiness" in str(c.get("type", ""))]
            text, _ch = self._safe_stage(
                "entropy_final", text, lang,
                _run_entropy_final, stage_timings,
            )
            all_changes.extend(_ch)

        # 13a¼. Final sentence-level cleanup
        # Late stages (readability, grammar, coherence, entropy_final) can
        # re-introduce artifacts that _strip_fragment_chains already cleaned.
        # Apply targeted fixes:
        import re as _re_late
        #  (a) Double conjunctions: "and and", "и и", "but but"
        text = _re_late.sub(
            r'\b(and|but|or|yet|so|и|і|а|але|но|und|oder|aber|et|ou|mais|y|o|pero)\s+\1\b',
            r'\1', text, flags=_re_late.IGNORECASE,
        )
        #  (b) Garbled conjunction chains left over: ", and, but, however, and"
        text = _re_late.sub(
            r'(?:,\s*(?:and|but|or|however|moreover|also|and)\s*){2,}',
            ', ', text, flags=_re_late.IGNORECASE,
        )

        # 13a½. Sentence-level validation summary
        if _sv.total_reverts > 0:
            all_changes.append({
                "type": "sentence_validation",
                "description": (
                    f"Валидация предложений: откачено {_sv.total_reverts} "
                    f"сломанных предложений"
                ),
            })

        # 13b. Anti-fingerprint diversification
        _fp_rand = FingerprintRandomizer(
            seed=effective_options.seed,
            jitter_level=effective_options.intensity / 100.0 * 0.5,
        )
        text = _fp_rand.diversify_output(text)

        # 14. Восстановление защищённых сегментов
        _t0 = time.perf_counter()
        text = segmented.restore(text)
        stage_timings["restore"] = time.perf_counter() - _t0

        # ── Safety: collapse overlapping em-dash asides ──
        import re as _re_dash
        text = _re_dash.sub(r'\u2014\s*\u2014', '\u2014', text)

        # 15. Валидация
        _t0 = time.perf_counter()
        _user_max_v = self.options.constraints.get("max_change_ratio", None)
        if _user_max_v is not None:
            max_change_v = _user_max_v
        else:
            _iv = effective_options.intensity / 100.0
            max_change_v = min(0.70, 0.25 + _iv * 0.40)
        validator = QualityValidator(
            lang=lang,
            max_change_ratio=max_change_v,
            keep_keywords=keep_kw,
        )
        validation = validator.validate(original, text, metrics_before)

        # Откат только при критических ошибках (потеря ключевых слов,
        # резкий рост AI-скора). Слишком высокий change_ratio не вызывает
        # откат — graduated retry обработает это.
        critical_errors = [e for e in validation.errors if "ключевое слово" in e.lower()
                          or "искусственность" in e.lower()]
        if critical_errors:
            # Try partial rollback — remove stages from the end
            for cp_name, cp_text in reversed(checkpoints):
                restored_cp = segmented.restore(cp_text)
                cp_valid = validator.validate(original, restored_cp, metrics_before)
                cp_critical = [e for e in cp_valid.errors if "ключевое слово" in e.lower()
                              or "искусственность" in e.lower()]
                if not cp_critical:
                    text = restored_cp
                    all_changes.append({
                        "type": "partial_rollback",
                        "description": f"Частичный откат до этапа «{cp_name}»",
                    })
                    break
            else:
                # Full rollback if no checkpoint is clean
                text = original
                all_changes = [{
                    "type": "rollback",
                    "description": f"Полный откат: {'; '.join(critical_errors)}",
                }]
        stage_timings["validation"] = time.perf_counter() - _t0

        # Анализ после обработки
        metrics_after = analyzer.analyze(text)

        # Стилистический анализ после обработки (если задан target)
        if target_fp is not None and isinstance(target_fp, StylisticFingerprint):
            style_analyzer_post = StylisticAnalyzer(lang=lang)
            result_fp = style_analyzer_post.extract(text)
            style_meta["style_similarity_after"] = round(
                result_fp.similarity(target_fp), 3,
            )

        return HumanizeResult(
            original=original,
            text=text,
            lang=lang,
            profile=self.options.profile,
            intensity=self.options.intensity,
            changes=all_changes,
            metrics_before={
                "artificiality_score": metrics_before.artificiality_score,
                "avg_sentence_length": metrics_before.avg_sentence_length,
                "bureaucratic_ratio": metrics_before.bureaucratic_ratio,
                "connector_ratio": metrics_before.connector_ratio,
                "repetition_score": metrics_before.repetition_score,
                "typography_score": metrics_before.typography_score,
                "predictability_score": metrics_before.predictability_score,
                "vocabulary_richness": metrics_before.vocabulary_richness,
                "content_type": content_profile.content_type.value,
                "content_confidence": round(content_profile.confidence, 3),
                **style_meta,
            },
            metrics_after={
                "artificiality_score": metrics_after.artificiality_score,
                "avg_sentence_length": metrics_after.avg_sentence_length,
                "bureaucratic_ratio": metrics_after.bureaucratic_ratio,
                "connector_ratio": metrics_after.connector_ratio,
                "repetition_score": metrics_after.repetition_score,
                "typography_score": metrics_after.typography_score,
                "predictability_score": metrics_after.predictability_score,
                "vocabulary_richness": metrics_after.vocabulary_richness,
                "stage_timings": stage_timings,
                "total_time": sum(stage_timings.values()),
            },
        )
