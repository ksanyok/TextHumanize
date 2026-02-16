"""Пайплайн обработки текста — оркестрация всех этапов."""

from __future__ import annotations

from texthumanize.segmenter import Segmenter
from texthumanize.normalizer import TypographyNormalizer
from texthumanize.decancel import Debureaucratizer
from texthumanize.structure import StructureDiversifier
from texthumanize.repetitions import RepetitionReducer
from texthumanize.liveliness import LivelinessInjector
from texthumanize.universal import UniversalProcessor
from texthumanize.antidetect import AntiDetector
from texthumanize.analyzer import TextAnalyzer
from texthumanize.validator import QualityValidator
from texthumanize.lang import has_deep_support
from texthumanize.utils import HumanizeOptions, HumanizeResult, AnalysisReport


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
    8. Антидетекция (для ВСЕХ языков — КЛЮЧЕВОЙ ЭТАП)
    9. Валидация качества
    10. Восстановление защищённых сегментов
    """

    def __init__(self, options: HumanizeOptions | None = None):
        self.options = options or HumanizeOptions()

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
        normalizer = TypographyNormalizer(
            profile=self.options.profile,
            lang=lang,
        )
        text = normalizer.normalize(text)
        all_changes.extend(normalizer.changes)

        # Этапы 3-6: словарная обработка (только для языков с полным словарём)
        if has_deep_support(lang):
            # 3. Деканцеляризация
            debureaucratizer = Debureaucratizer(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = debureaucratizer.process(text)
            all_changes.extend(debureaucratizer.changes)

            # 4. Разнообразие структуры
            structure = StructureDiversifier(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = structure.process(text)
            all_changes.extend(structure.changes)

            # 5. Уменьшение повторов
            repetitions = RepetitionReducer(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = repetitions.process(text)
            all_changes.extend(repetitions.changes)

            # 6. Инъекция «живости»
            liveliness = LivelinessInjector(
                lang=lang,
                profile=self.options.profile,
                intensity=self.options.intensity,
                seed=self.options.seed,
            )
            text = liveliness.process(text)
            all_changes.extend(liveliness.changes)

        # 7. Универсальная обработка (для ВСЕХ языков)
        universal = UniversalProcessor(
            profile=self.options.profile,
            intensity=self.options.intensity,
            seed=self.options.seed,
        )
        text = universal.process(text)
        all_changes.extend(universal.changes)

        # 8. Антидетекция (КЛЮЧЕВОЙ ЭТАП — для ВСЕХ языков)
        antidetect = AntiDetector(
            lang=lang,
            profile=self.options.profile,
            intensity=self.options.intensity,
            seed=self.options.seed,
        )
        text = antidetect.process(text)
        all_changes.extend(antidetect.changes)

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
