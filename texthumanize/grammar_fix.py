"""Грамматическая коррекция — этап пайплайна.

Исправляет грамматические ошибки, внесённые предыдущими этапами:
- Двойные слова (the the, is is)
- Капитализация начала предложений
- Лишние/отсутствующие пробелы при пунктуации
- Двойные знаки препинания
- Незакрытые скобки/кавычки
- Частые опечатки (9+ языков)
"""

from __future__ import annotations

from texthumanize.grammar import check_grammar, fix_grammar


class GrammarCorrector:
    """Обёртка grammar.py для использования в пайплайне.

    Работает для ВСЕХ языков — правила универсальны + typo-словари
    для en/ru/uk/de/fr/es/it/pl/pt.
    """

    def __init__(
        self,
        lang: str = "en",
        profile: str = "default",
        intensity: int = 50,
        seed: int | None = None,
    ):
        self.lang = lang
        self.profile = profile
        self.intensity = intensity
        self.seed = seed
        self.changes: list[dict] = []

    def process(self, text: str) -> str:
        """Исправить грамматику текста.

        Защищает placeholder-токены от изменений.

        Returns:
            Исправленный текст.
        """
        if not text or not text.strip():
            return text

        # Анализ до исправления
        report_before = check_grammar(text, self.lang)
        if report_before.total == 0:
            return text

        # Исправление
        result = fix_grammar(text, self.lang)

        if result != text:
            report_after = check_grammar(result, self.lang)
            fixed_count = report_before.total - report_after.total
            if fixed_count > 0:
                self.changes.append({
                    "type": "grammar_correction",
                    "description": (
                        f"Грамматика: исправлено {fixed_count} из "
                        f"{report_before.total} проблем "
                        f"(балл {report_before.score:.0f}→{report_after.score:.0f})"
                    ),
                })

        return result
