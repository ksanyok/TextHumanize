"""Валидатор качества — проверка результата после обработки."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from texthumanize.analyzer import TextAnalyzer
from texthumanize.utils import AnalysisReport

logger = logging.getLogger(__name__)

class QualityValidator:
    """Проверяет качество результата после гуманизации.

    - Не удалены ли числа, ссылки, имена
    - Не пропали ли ключевые слова
    - Не превышен ли change_ratio
    - Метрики стали лучше, а не хуже
    - Структура (абзацы/списки) сохранена
    """

    def __init__(
        self,
        lang: str = "ru",
        max_change_ratio: float = 0.4,
        keep_keywords: list[str] | None = None,
    ):
        self.lang = lang
        self.max_change_ratio = max_change_ratio
        self.keep_keywords = keep_keywords or []
        self.analyzer = TextAnalyzer(lang=lang)

    def validate(
        self,
        original: str,
        processed: str,
        metrics_before: AnalysisReport | None = None,
    ) -> ValidationResult:
        """Валидировать результат обработки.

        Args:
            original: Исходный текст.
            processed: Обработанный текст.
            metrics_before: Метрики до обработки.

        Returns:
            ValidationResult с результатами проверки.
        """
        result = ValidationResult()

        # 1. Проверка change_ratio
        change_ratio = self._calc_change_ratio(original, processed)
        result.change_ratio = change_ratio
        if change_ratio > self.max_change_ratio:
            result.warnings.append(
                f"Слишком много изменений: {change_ratio:.1%} > {self.max_change_ratio:.1%}"
            )
            result.should_rollback = True

        # 2. Проверка ключевых слов
        for keyword in self.keep_keywords:
            if keyword.lower() in original.lower() and keyword.lower() not in processed.lower():
                result.errors.append(f"Потеряно ключевое слово: '{keyword}'")
                result.should_rollback = True

        # 3. Проверка числовых значений
        original_numbers = self._extract_numbers(original)
        processed_numbers = self._extract_numbers(processed)
        lost_numbers = original_numbers - processed_numbers
        if lost_numbers:
            result.warnings.append(f"Потеряны числа: {lost_numbers}")

        # 4. Проверка длины (не должна сильно измениться)
        len_ratio = len(processed) / len(original) if original else 1.0
        if len_ratio < 0.5 or len_ratio > 1.5:
            result.warnings.append(
                f"Длина текста сильно изменилась: {len_ratio:.1%}"
            )

        # 5. Проверка сохранения структуры (абзацы/строки)
        self._check_structure_preservation(original, processed, result)

        # 6. Проверка метрик (если есть до-обработка)
        if metrics_before:
            metrics_after = self.analyzer.analyze(processed)
            result.metrics_before = metrics_before
            result.metrics_after = metrics_after

            # Искусственность должна снизиться или не измениться
            diff = metrics_after.artificiality_score - metrics_before.artificiality_score
            if diff > 15:
                # Серьёзное ухудшение — откат
                result.errors.append(
                    f"Искусственность значительно выросла: "
                    f"{metrics_before.artificiality_score:.1f} → "
                    f"{metrics_after.artificiality_score:.1f} (+{diff:.1f})"
                )
                result.should_rollback = True
            elif diff > 5:
                result.warnings.append(
                    "Оценка искусственности увеличилась после обработки"
                )

        result.is_valid = not result.errors and not result.should_rollback
        return result

    def _check_structure_preservation(
        self,
        original: str,
        processed: str,
        result: ValidationResult,
    ) -> None:
        """Проверить, что абзацная/списковая структура сохранена."""
        orig_lines = [ln for ln in original.split('\n') if ln.strip()]
        proc_lines = [ln for ln in processed.split('\n') if ln.strip()]

        # Количество непустых строк не должно уменьшиться более чем на 30%
        if orig_lines and proc_lines:
            ratio = len(proc_lines) / len(orig_lines)
            if ratio < 0.7:
                result.warnings.append(
                    f"Потеряна структура: строк было {len(orig_lines)}, "
                    f"стало {len(proc_lines)}"
                )

        # Количество абзацев (блоков, разделённых пустыми строками)
        orig_paras = len(re.split(r'\n\s*\n', original))
        proc_paras = len(re.split(r'\n\s*\n', processed))
        if orig_paras > 1 and proc_paras < orig_paras:
            result.warnings.append(
                f"Абзацы объединены: было {orig_paras}, стало {proc_paras}"
            )

    def _calc_change_ratio(self, original: str, processed: str) -> float:
        """Вычислить долю изменений (SequenceMatcher-based)."""
        if not original:
            return 0.0
        orig_words = original.split()
        proc_words = processed.split()
        if not orig_words:
            return 0.0
        matcher = SequenceMatcher(None, orig_words, proc_words)
        return min(1.0 - matcher.ratio(), 1.0)

    def _extract_numbers(self, text: str) -> set[str]:
        """Извлечь числовые значения из текста."""
        return set(re.findall(r'\b\d+(?:[.,]\d+)?\b', text))


class ValidationResult:
    """Результат валидации."""

    def __init__(self):
        self.is_valid: bool = True
        self.should_rollback: bool = False
        self.change_ratio: float = 0.0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metrics_before: AnalysisReport | None = None
        self.metrics_after: AnalysisReport | None = None

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"ValidationResult({status}, "
            f"change_ratio={self.change_ratio:.1%}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )
