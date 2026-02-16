"""Валидатор качества — проверка результата после обработки."""

from __future__ import annotations

import re

from texthumanize.analyzer import TextAnalyzer
from texthumanize.utils import AnalysisReport


class QualityValidator:
    """Проверяет качество результата после гуманизации.

    - Не удалены ли числа, ссылки, имена
    - Не пропали ли ключевые слова
    - Не превышен ли change_ratio
    - Метрики стали лучше, а не хуже
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

        # 5. Проверка метрик (если есть до-обработка)
        if metrics_before:
            metrics_after = self.analyzer.analyze(processed)
            result.metrics_before = metrics_before
            result.metrics_after = metrics_after

            # Искусственность должна снизиться или не измениться
            if metrics_after.artificiality_score > metrics_before.artificiality_score + 5:
                result.warnings.append(
                    "Оценка искусственности увеличилась после обработки"
                )

        result.is_valid = not result.errors and not result.should_rollback
        return result

    def _calc_change_ratio(self, original: str, processed: str) -> float:
        """Вычислить долю изменений."""
        if not original:
            return 0.0

        orig_words = original.split()
        proc_words = processed.split()

        if not orig_words:
            return 0.0

        # Простое сравнение по словам
        max_len = max(len(orig_words), len(proc_words))
        diff = 0
        for i in range(max_len):
            orig = orig_words[i] if i < len(orig_words) else ""
            proc = proc_words[i] if i < len(proc_words) else ""
            if orig != proc:
                diff += 1

        return diff / len(orig_words)

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
