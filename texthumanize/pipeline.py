"""Пайплайн обработки текста — оркестрация всех этапов."""

from __future__ import annotations

import time
from difflib import SequenceMatcher
from typing import Callable, Protocol

from texthumanize.analyzer import TextAnalyzer
from texthumanize.cjk_segmenter import CJKSegmenter, is_cjk_text
from texthumanize.coherence_repair import CoherenceRepairer
from texthumanize.decancel import Debureaucratizer
from texthumanize.fingerprint_randomizer import FingerprintRandomizer
from texthumanize.grammar_fix import GrammarCorrector
from texthumanize.lang import has_deep_support
from texthumanize.liveliness import LivelinessInjector
from texthumanize.naturalizer import TextNaturalizer
from texthumanize.normalizer import TypographyNormalizer
from texthumanize.paraphraser_ext import SemanticParaphraser
from texthumanize.readability_opt import ReadabilityOptimizer
from texthumanize.repetitions import RepetitionReducer
from texthumanize.segmenter import Segmenter
from texthumanize.structure import StructureDiversifier
from texthumanize.stylistic import StylisticAnalyzer, StylisticFingerprint
from texthumanize.syntax_rewriter import SyntaxRewriter
from texthumanize.tone_harmonizer import ToneHarmonizer
from texthumanize.universal import UniversalProcessor
from texthumanize.utils import AnalysisReport, HumanizeOptions, HumanizeResult
from texthumanize.validator import QualityValidator
from texthumanize.watermark import WatermarkDetector
from texthumanize.word_lm import WordLanguageModel


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

    # Class-level default plugin registry
    _class_plugins_before: dict[str, list[StagePlugin]] = {}
    _class_plugins_after: dict[str, list[StagePlugin]] = {}
    _class_hooks_before: dict[str, list[HookFn]] = {}
    _class_hooks_after: dict[str, list[HookFn]] = {}

    STAGE_NAMES = (
        "watermark", "segmentation", "typography", "debureaucratization",
        "structure", "repetitions", "liveliness",
        "paraphrasing", "syntax_rewriting", "tone", "universal", "naturalization",
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

    def run(self, text: str, lang: str) -> HumanizeResult:
        """Запустить пайплайн обработки.

        Args:
            text: Текст для обработки.
            lang: Код языка.

        Returns:
            HumanizeResult с обработанным текстом и метаданными.
        """
        max_change = self.options.constraints.get("max_change_ratio", 0.4)

        result = self._run_pipeline(text, lang, intensity_factor=1.0)

        # Graduated retry: если change_ratio слишком высокий,
        # повторяем с пониженной интенсивностью
        if result.change_ratio > max_change:
            for factor in (0.4, 0.15):
                retry = self._run_pipeline(text, lang, intensity_factor=factor)
                if retry.change_ratio <= max_change:
                    return retry
                if retry.quality_score > result.quality_score:
                    result = retry

        return result

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
        metrics_before: "AnalysisReport",
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
        import logging
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

        # Анализ до обработки
        analyzer = TextAnalyzer(lang=lang)
        metrics_before = analyzer.analyze(text)

        # ── Адаптивная интенсивность ──────────────────────────
        # Автоматически корректируем intensity на основе artificiality_score:
        # - Высокий AI-скор (>60) → усиливаем обработку
        # - Низкий AI-скор (<25) → ослабляем, чтобы не портить живой текст
        effective_options = self.options
        ai_score = metrics_before.artificiality_score
        base_intensity = self.options.intensity

        # Применяем graduated retry factor
        base_intensity = max(5, int(base_intensity * intensity_factor))

        if ai_score >= 70:
            # Сильно «искусственный» текст — усиливаем
            adjusted = min(100, int(base_intensity * 1.3))
        elif ai_score >= 50:
            # Средне «искусственный» — немного усиливаем
            adjusted = min(100, int(base_intensity * 1.1))
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

        if adjusted != base_intensity:
            # Создаём копию опций с адаптированной интенсивностью
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

        # Этапы 3-6: словарная обработка (только для языков с полным словарём)
        if has_deep_support(lang):
            # 3. Деканцеляризация
            text = self._run_plugins("debureaucratization", text, lang, is_before=True)
            def _run_debureau():
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
            def _run_structure():
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
            def _run_repetitions():
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
            def _run_liveliness():
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

        # 7. Семантическое перефразирование (для языков с полным словарём)
        if has_deep_support(lang):
            text = self._run_plugins("paraphrasing", text, lang, is_before=True)
            def _run_paraphrasing():
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
        if has_deep_support(lang):
            text = self._run_plugins("syntax_rewriting", text, lang, is_before=True)
            def _run_syntax_rewrite():
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
                        if _sr_rng.random() < prob * 0.3:
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
            text = self._run_plugins("syntax_rewriting", text, lang, is_before=False)

        # 8. Гармонизация тона (для ВСЕХ языков)
        text = self._run_plugins("tone", text, lang, is_before=True)
        def _run_tone():
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
        def _run_universal():
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
        def _run_naturalization():
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
        text = self._run_plugins("naturalization", text, lang, is_before=False)

        # 10b. Word LM quality gate — ensure naturalization didn't make
        # text MORE predictable (lower perplexity = more AI-like).
        # Roll back naturalization if perplexity dropped significantly.
        _t0 = time.perf_counter()
        try:
            _wlm = WordLanguageModel(lang=lang)
            _pp_before = _wlm.perplexity(checkpoints[-2][1] if len(checkpoints) >= 2 else original)
            _pp_after = _wlm.perplexity(text)
            if _pp_before > 0 and _pp_after > 0:
                # If perplexity dropped by >30%, naturalization made text
                # more predictable — partial rollback
                if _pp_after < _pp_before * 0.7:
                    _prev_text = checkpoints[-2][1] if len(checkpoints) >= 2 else original
                    text = _prev_text
                    all_changes.append({
                        "type": "quality_gate_rollback",
                        "description": (
                            f"Word LM: перплексия упала {_pp_before:.1f}→{_pp_after:.1f}, "
                            "откат натурализации"
                        ),
                    })
                else:
                    all_changes.append({
                        "type": "quality_gate_pass",
                        "description": (
                            f"Word LM: перплексия {_pp_before:.1f}→{_pp_after:.1f} (OK)"
                        ),
                    })
        except Exception:
            pass  # Word LM is advisory, never blocks pipeline
        stage_timings["word_lm_gate"] = time.perf_counter() - _t0

        # 11. Оптимизация читаемости (для ВСЕХ языков)
        text = self._run_plugins("readability", text, lang, is_before=True)
        def _run_readability():
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
        def _run_grammar():
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

        # 13. Коррекция когерентности (для ВСЕХ языков)
        text = self._run_plugins("coherence", text, lang, is_before=True)
        def _run_coherence():
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
        text = self._run_plugins("coherence", text, lang, is_before=False)

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

        # 15. Валидация
        _t0 = time.perf_counter()
        max_change = self.options.constraints.get("max_change_ratio", 0.4)
        validator = QualityValidator(
            lang=lang,
            max_change_ratio=max_change,
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
