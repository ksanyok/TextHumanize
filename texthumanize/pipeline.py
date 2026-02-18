"""Пайплайн обработки текста — оркестрация всех этапов."""

from __future__ import annotations

from typing import Callable, Protocol

from texthumanize.analyzer import TextAnalyzer
from texthumanize.decancel import Debureaucratizer
from texthumanize.lang import has_deep_support
from texthumanize.liveliness import LivelinessInjector
from texthumanize.naturalizer import TextNaturalizer
from texthumanize.normalizer import TypographyNormalizer
from texthumanize.repetitions import RepetitionReducer
from texthumanize.segmenter import Segmenter
from texthumanize.structure import StructureDiversifier
from texthumanize.universal import UniversalProcessor
from texthumanize.utils import HumanizeOptions, HumanizeResult
from texthumanize.validator import QualityValidator


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
    1. Сегментация (защита кода, URL, email и т.д.)
    2. Нормализация типографики
    3. Деканцеляризация (для языков с полным словарём)
    4. Разнообразие структуры (для языков с полным словарём)
    5. Уменьшение повторов (для языков с полным словарём)
    6. Инъекция «живости» (для языков с полным словарём)
    7. Универсальная обработка (для ВСЕХ языков)
    8. Натурализация стиля (для ВСЕХ языков — КЛЮЧЕВОЙ ЭТАП)
    9. Валидация качества
    10. Восстановление защищённых сегментов

    Supports custom plugins that can be inserted before or after
    any built-in stage via register_plugin().
    """

    # Class-level plugin registry (shared across instances)
    _plugins_before: dict[str, list[StagePlugin]] = {}
    _plugins_after: dict[str, list[StagePlugin]] = {}
    _hooks_before: dict[str, list[HookFn]] = {}
    _hooks_after: dict[str, list[HookFn]] = {}

    STAGE_NAMES = (
        "segmentation", "typography", "debureaucratization",
        "structure", "repetitions", "liveliness",
        "universal", "naturalization", "validation", "restore",
    )

    def __init__(self, options: HumanizeOptions | None = None):
        self.options = options or HumanizeOptions()

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
            cls._plugins_before.setdefault(before, []).append(plugin)
        else:
            cls._plugins_after.setdefault(after, []).append(plugin)  # type: ignore[arg-type]

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
            cls._hooks_before.setdefault(before, []).append(hook)
        else:
            cls._hooks_after.setdefault(after, []).append(hook)  # type: ignore[arg-type]

    @classmethod
    def clear_plugins(cls) -> None:
        """Remove all registered plugins and hooks."""
        cls._plugins_before.clear()
        cls._plugins_after.clear()
        cls._hooks_before.clear()
        cls._hooks_after.clear()

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

    def run(self, text: str, lang: str) -> HumanizeResult:
        """Запустить пайплайн обработки.

        Args:
            text: Текст для обработки.
            lang: Код языка.

        Returns:
            HumanizeResult с обработанным текстом и метаданными.
        """
        original = text
        all_changes: list[dict] = []

        # Анализ до обработки
        analyzer = TextAnalyzer(lang=lang)
        metrics_before = analyzer.analyze(text)

        # 1. Сегментация — защита неизменяемых блоков
        preserve_config = dict(self.options.preserve)
        # Добавляем keep_keywords в protect
        keep_kw = self.options.constraints.get("keep_keywords", [])
        if keep_kw:
            preserve_config.setdefault("keep_keywords", [])
            preserve_config["keep_keywords"] = keep_kw

        segmenter = Segmenter(preserve=preserve_config)
        segmented = segmenter.segment(text)
        text = segmented.text

        # 2. Нормализация типографики
        text = self._run_plugins("typography", text, lang, is_before=True)
        normalizer = TypographyNormalizer(
            profile=self.options.profile,
            lang=lang,
        )
        text = normalizer.normalize(text)
        all_changes.extend(normalizer.changes)
        text = self._run_plugins("typography", text, lang, is_before=False)

        # Этапы 3-6: словарная обработка (только для языков с полным словарём)
        if has_deep_support(lang):
            # 3. Деканцеляризация
            text = self._run_plugins("debureaucratization", text, lang, is_before=True)
            debureaucratizer = Debureaucratizer(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = debureaucratizer.process(text)
            all_changes.extend(debureaucratizer.changes)
            text = self._run_plugins("debureaucratization", text, lang, is_before=False)

            # 4. Разнообразие структуры
            text = self._run_plugins("structure", text, lang, is_before=True)
            structure = StructureDiversifier(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = structure.process(text)
            all_changes.extend(structure.changes)
            text = self._run_plugins("structure", text, lang, is_before=False)

            # 5. Уменьшение повторов
            text = self._run_plugins("repetitions", text, lang, is_before=True)
            repetitions = RepetitionReducer(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = repetitions.process(text)
            all_changes.extend(repetitions.changes)
            text = self._run_plugins("repetitions", text, lang, is_before=False)

            # 6. Инъекция «живости»
            text = self._run_plugins("liveliness", text, lang, is_before=True)
            liveliness = LivelinessInjector(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = liveliness.process(text)
            all_changes.extend(liveliness.changes)
            text = self._run_plugins("liveliness", text, lang, is_before=False)

        # 7. Универсальная обработка (для ВСЕХ языков)
        text = self._run_plugins("universal", text, lang, is_before=True)
        universal = UniversalProcessor(
            profile=self.options.profile,
            intensity=self.options.intensity,
            seed=self.options.seed,
        )
        text = universal.process(text)
        all_changes.extend(universal.changes)
        text = self._run_plugins("universal", text, lang, is_before=False)

        # 8. Натурализация стиля (КЛЮЧЕВОЙ ЭТАП — для ВСЕХ языков)
        text = self._run_plugins("naturalization", text, lang, is_before=True)
        naturalizer = TextNaturalizer(
            lang=lang,
            profile=self.options.profile,
            intensity=self.options.intensity,
            seed=self.options.seed,
        )
        text = naturalizer.process(text)
        all_changes.extend(naturalizer.changes)
        text = self._run_plugins("naturalization", text, lang, is_before=False)

        # 9. Восстановление защищённых сегментов
        text = segmented.restore(text)

        # 10. Валидация
        max_change = self.options.constraints.get("max_change_ratio", 0.4)
        validator = QualityValidator(
            lang=lang,
            max_change_ratio=max_change,
            keep_keywords=keep_kw,
        )
        validation = validator.validate(original, text, metrics_before)

        # Если валидация провалилась — откат
        if validation.should_rollback and validation.errors:
            text = original
            all_changes = [{
                "type": "rollback",
                "description": f"Откат: {'; '.join(validation.errors)}",
            }]

        # Анализ после обработки
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
            },
            metrics_after={
                "artificiality_score": metrics_after.artificiality_score,
                "avg_sentence_length": metrics_after.avg_sentence_length,
                "bureaucratic_ratio": metrics_after.bureaucratic_ratio,
                "connector_ratio": metrics_after.connector_ratio,
                "repetition_score": metrics_after.repetition_score,
                "typography_score": metrics_after.typography_score,
            },
        )
