"""Когерентность текста на уровне абзацев.

Анализирует связность текста: тематические предложения,
длину абзацев, плавность переходов, лексические цепочки.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

@dataclass
class CoherenceReport:
    """Результат анализа когерентности."""

    overall: float = 0.0  # 0..1, чем выше — тем более связный текст
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0
    paragraph_length_cv: float = 0.0  # коэф. вариации длин абзацев
    lexical_cohesion: float = 0.0  # 0..1, лексические цепочки
    transition_score: float = 0.0  # 0..1, качество переходов
    topic_consistency: float = 0.0  # 0..1, тематическая последовательность
    sentence_opening_diversity: float = 0.0  # 0..1
    issues: list[str] = field(default_factory=list)


# Переходные слова/фразы для анализа
_TRANSITIONS = {
    "en": {
        "additive": ["moreover", "furthermore", "additionally", "also", "besides",
                     "in addition", "as well", "not only", "what is more"],
        "adversative": ["however", "nevertheless", "nonetheless", "on the other hand",
                       "in contrast", "although", "despite", "yet", "but", "still",
                       "whereas", "while", "on the contrary"],
        "causal": ["therefore", "consequently", "as a result", "because", "since",
                  "thus", "hence", "accordingly", "due to", "owing to", "for this reason"],
        "sequential": ["first", "second", "third", "finally", "then", "next",
                       "subsequently", "meanwhile", "afterward", "lastly", "initially"],
        "exemplification": ["for example", "for instance", "such as", "namely",
                           "specifically", "in particular", "to illustrate"],
        "summary": ["in conclusion", "to summarize", "in summary", "overall",
                   "in short", "to sum up", "ultimately", "in essence"],
    },
    "ru": {
        "additive": ["кроме того", "помимо этого", "также", "более того",
                    "дополнительно", "вдобавок", "к тому же", "наряду с"],
        "adversative": ["однако", "тем не менее", "несмотря на", "впрочем",
                       "с другой стороны", "вместе с тем", "при этом", "напротив",
                       "хотя", "всё же", "зато"],
        "causal": ["поэтому", "следовательно", "таким образом", "потому что",
                  "вследствие", "в результате", "благодаря", "из-за", "ввиду"],
        "sequential": ["во-первых", "во-вторых", "в-третьих", "далее", "затем",
                       "после этого", "наконец", "в заключение", "сначала"],
        "exemplification": ["например", "в частности", "а именно", "так",
                           "к примеру", "в качестве примера"],
        "summary": ["в итоге", "подводя итог", "в заключение", "резюмируя",
                   "в целом", "в общем", "таким образом"],
    },
    "uk": {
        "additive": ["крім того", "окрім цього", "також", "більше того",
                    "додатково", "до того ж", "на додаток"],
        "adversative": ["однак", "проте", "тим не менш", "незважаючи на",
                       "з іншого боку", "водночас", "натомість", "хоча"],
        "causal": ["тому", "отже", "таким чином", "тому що", "адже",
                  "внаслідок", "завдяки", "через"],
        "sequential": ["по-перше", "по-друге", "по-третє", "далі", "потім",
                       "після цього", "нарешті", "спочатку"],
        "exemplification": ["наприклад", "зокрема", "а саме", "як-от"],
        "summary": ["підсумовуючи", "загалом", "на завершення", "у підсумку"],
    },
}


class CoherenceAnalyzer:
    """Анализатор когерентности текста."""

    def __init__(self, lang: str = "ru"):
        self.lang = lang
        self._transitions = _TRANSITIONS.get(lang, _TRANSITIONS.get("en", {}))
        self._all_transitions: list[str] = []
        for cat_words in self._transitions.values():
            self._all_transitions.extend(cat_words)
        # Сортируем по длине убыванию для greedy matching
        self._all_transitions.sort(key=len, reverse=True)

    def analyze(self, text: str) -> CoherenceReport:
        """Анализировать когерентность текста.

        Args:
            text: Полный текст для анализа.

        Returns:
            CoherenceReport с метриками когерентности.
        """
        report = CoherenceReport()

        paragraphs = self._split_paragraphs(text)
        report.paragraph_count = len(paragraphs)

        if len(paragraphs) < 2:
            report.overall = 0.8  # Одноабзацный текст — не можем оценить
            return report

        # --- 1. Длины абзацев ---
        lengths = [len(p.split()) for p in paragraphs]
        report.avg_paragraph_length = sum(lengths) / len(lengths) if lengths else 0

        if report.avg_paragraph_length > 0:
            std = math.sqrt(
                sum((pl - report.avg_paragraph_length) ** 2 for pl in lengths
                    ) / len(lengths)
            )
            report.paragraph_length_cv = std / report.avg_paragraph_length
        else:
            report.paragraph_length_cv = 0

        # --- 2. Лексическая связность (перекрытие между абзацами) ---
        report.lexical_cohesion = self._lexical_cohesion(paragraphs)

        # --- 3. Переходные слова ---
        report.transition_score = self._transition_quality(paragraphs)

        # --- 4. Тематическая последовательность ---
        report.topic_consistency = self._topic_consistency(paragraphs)

        # --- 5. Разнообразие начала предложений ---
        report.sentence_opening_diversity = self._opening_diversity(text)

        # --- Issues ---
        if report.paragraph_length_cv < 0.15:
            report.issues.append("paragraph_uniform_length")
        if report.paragraph_length_cv > 1.5:
            report.issues.append("paragraph_lengths_very_uneven")
        if report.lexical_cohesion < 0.1:
            report.issues.append("low_lexical_cohesion")
        if report.transition_score < 0.15:
            report.issues.append("few_transitions")
        if report.sentence_opening_diversity < 0.3:
            report.issues.append("repetitive_sentence_openings")
        if any(pl > 200 for pl in lengths):
            report.issues.append("very_long_paragraphs")
        if any(pl < 10 for pl in lengths):
            report.issues.append("very_short_paragraphs")

        # --- Overall score ---
        report.overall = self._compute_overall(report)

        return report

    def suggest_improvements(
        self, text: str, report: CoherenceReport | None = None
    ) -> list[str]:
        """Предложить конкретные улучшения когерентности.

        Returns:
            Список рекомендаций.
        """
        if report is None:
            report = self.analyze(text)

        suggestions: list[str] = []

        if "paragraph_uniform_length" in report.issues:
            suggestions.append(
                "Paragraph lengths are too uniform (CV={:.2f}). "
                "Vary paragraph sizes for more natural reading rhythm.".format(
                    report.paragraph_length_cv
                )
            )

        if "few_transitions" in report.issues:
            cats = list(self._transitions.keys())
            examples = []
            for cat in cats[:3]:
                words = self._transitions[cat]
                if words:
                    examples.append(f"{cat}: {', '.join(words[:3])}")
            suggestions.append(
                "Text lacks transition words. Consider adding: " + "; ".join(examples)
            )

        if "low_lexical_cohesion" in report.issues:
            suggestions.append(
                "Low lexical cohesion between paragraphs. "
                "Reuse key terms or use pronouns to connect ideas."
            )

        if "repetitive_sentence_openings" in report.issues:
            suggestions.append(
                "Many sentences start the same way. "
                "Vary openings: use adverbs, subordinate clauses, inversions."
            )

        if "very_long_paragraphs" in report.issues:
            suggestions.append(
                "Some paragraphs exceed 200 words. "
                "Break them into smaller chunks for readability."
            )

        return suggestions

    # ───────────────────────────────────────────────────────────
    #  PRIVATE
    # ───────────────────────────────────────────────────────────

    def _split_paragraphs(self, text: str) -> list[str]:
        """Разбить текст на абзацы (по двойным переносам или отступам)."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        # Фильтруем пустые
        return [p.strip() for p in paragraphs if p.strip()]

    def _extract_content_words(self, text: str, min_len: int = 4) -> set[str]:
        """Извлечь контентные слова (убираем стоп-слова по длине)."""
        words = re.findall(r'\b\w+\b', text.lower())
        return {w for w in words if len(w) >= min_len}

    def _lexical_cohesion(self, paragraphs: list[str]) -> float:
        """Средний коэффициент лексического перекрытия между соседними абзацами."""
        if len(paragraphs) < 2:
            return 1.0

        overlaps: list[float] = []
        for i in range(len(paragraphs) - 1):
            words_a = self._extract_content_words(paragraphs[i])
            words_b = self._extract_content_words(paragraphs[i + 1])
            if not words_a or not words_b:
                overlaps.append(0.0)
                continue
            intersection = words_a & words_b
            union = words_a | words_b
            # Jaccard index
            overlaps.append(len(intersection) / len(union))

        return sum(overlaps) / len(overlaps) if overlaps else 0.0

    def _transition_quality(self, paragraphs: list[str]) -> float:
        """Оценить качество переходов между абзацами."""
        if len(paragraphs) < 2:
            return 1.0

        transition_count = 0
        categories_used: set[str] = set()

        for para in paragraphs[1:]:  # начиная со второго
            para_lower = para.lower()
            # Проверяем начало абзаца (первые ~100 символов)
            start = para_lower[:min(100, len(para_lower))]

            for cat, words in self._transitions.items():
                for word in words:
                    if word in start:
                        transition_count += 1
                        categories_used.add(cat)
                        break

        # Score = наличие переходов × разнообразие категорий
        presence = min(transition_count / max(len(paragraphs) - 1, 1), 1.0)
        diversity = len(categories_used) / max(len(self._transitions), 1)
        return 0.6 * presence + 0.4 * diversity

    def _topic_consistency(self, paragraphs: list[str]) -> float:
        """Тематическая последовательность: насколько плавно меняются темы."""
        if len(paragraphs) < 3:
            return 0.8

        # Для каждого абзаца строим "профиль" (частотные слова)
        profiles: list[Counter] = []
        for para in paragraphs:
            words = re.findall(r'\b\w+\b', para.lower())
            content = [w for w in words if len(w) >= 4]
            profiles.append(Counter(content))

        # Сравниваем "расстояние" между соседними и через-1 абзацами
        # Плавное изменение = хорошая последовательность
        neighbor_sims: list[float] = []
        skip_sims: list[float] = []

        for i in range(len(profiles) - 1):
            sim = self._cosine_similarity(profiles[i], profiles[i + 1])
            neighbor_sims.append(sim)

        for i in range(len(profiles) - 2):
            sim = self._cosine_similarity(profiles[i], profiles[i + 2])
            skip_sims.append(sim)

        avg_neighbor = sum(neighbor_sims) / len(neighbor_sims) if neighbor_sims else 0
        avg_skip = sum(skip_sims) / len(skip_sims) if skip_sims else 0

        # Соседние абзацы должны быть более похожи, чем через-1
        # Но и общая связность должна быть
        return min(avg_neighbor * 0.7 + avg_skip * 0.3 + 0.2, 1.0)

    @staticmethod
    def _cosine_similarity(a: Counter, b: Counter) -> float:
        """Косинусное сходство двух Counter."""
        if not a or not b:
            return 0.0

        common = set(a.keys()) & set(b.keys())
        dot_product = sum(a[k] * b[k] for k in common)
        mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot_product / (mag_a * mag_b)

    def _opening_diversity(self, text: str) -> float:
        """Разнообразие начал предложений."""
        sentences = split_sentences(text.strip(), lang=self.lang)
        if len(sentences) < 3:
            return 0.8

        # Первое слово каждого предложения
        first_words: list[str] = []
        for s in sentences:
            s = s.strip()
            if s:
                words = s.split()
                if words:
                    first_words.append(words[0].lower())

        if len(first_words) < 3:
            return 0.8

        unique = len(set(first_words))
        total = len(first_words)

        # Type-Token Ratio для первых слов
        return unique / total

    def _compute_overall(self, report: CoherenceReport) -> float:
        """Рассчитать итоговый балл когерентности."""
        scores = [
            report.lexical_cohesion * 0.25,
            report.transition_score * 0.25,
            report.topic_consistency * 0.25,
            report.sentence_opening_diversity * 0.15,
        ]

        # Штраф за слишком однородные/неоднородные абзацы
        cv = report.paragraph_length_cv
        if 0.2 <= cv <= 0.8:
            para_score = 1.0
        elif cv < 0.2:
            para_score = 0.5 + cv * 2.5
        else:
            para_score = max(0, 1.0 - (cv - 0.8) * 0.5)

        scores.append(para_score * 0.10)

        return min(max(sum(scores), 0.0), 1.0)
