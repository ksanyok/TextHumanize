"""Content Health Score — комплексная оценка качества контента (0-100).

Объединяет несколько метрик в единый балл «здоровья» текста:
    - Читабельность (readability)
    - Грамматика (grammar)
    - Уникальность (uniqueness)
    - AI-детекция (ai_score)
    - Когерентность (coherence)
    - Лексическое разнообразие (vocabulary)

Каждый компонент может быть пропущен, если его нельзя вычислить.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthComponent:
    """Один компонент здоровья контента."""

    name: str
    score: float  # 0-100
    weight: float  # Вес в итоговом балле
    details: str = ""


@dataclass
class ContentHealthReport:
    """Полный отчёт о состоянии контента."""

    score: float  # 0-100, composite
    grade: str  # A+ / A / B / C / D / F
    components: list[HealthComponent] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, float]:
        return {c.name: c.score for c in self.components}


def _grade_from_score(score: float) -> str:
    """Преобразовать числовой балл в буквенную оценку."""
    if score >= 95:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def content_health(
    text: str,
    lang: str = "en",
    *,
    include_ai: bool = True,
    include_grammar: bool = True,
    include_uniqueness: bool = True,
    include_readability: bool = True,
    include_coherence: bool = True,
) -> ContentHealthReport:
    """Вычислить комплексный балл «здоровья» контента.

    Объединяет метрики из нескольких модулей библиотеки
    в единый 0-100 балл с буквенной оценкой.

    Args:
        text: Текст для анализа.
        lang: Код языка.
        include_ai: Включить AI-детекцию.
        include_grammar: Включить грамматическую проверку.
        include_uniqueness: Включить уникальность.
        include_readability: Включить читабельность.
        include_coherence: Включить когерентность.

    Returns:
        ContentHealthReport с подробными компонентами.
    """
    components: list[HealthComponent] = []
    total_weight = 0.0

    # ── Readability ──
    if include_readability:
        try:
            from texthumanize.core import full_readability
            rd = full_readability(text, lang=lang)
            # Map readability to 0-100 (ideal: grade_level 8-12)
            gl = rd.get("grade_level", 10)
            if 8 <= gl <= 12:
                r_score = 100.0
            elif gl < 8:
                r_score = max(50.0, 100.0 - (8 - gl) * 10)
            else:
                r_score = max(30.0, 100.0 - (gl - 12) * 8)

            components.append(HealthComponent(
                name="readability", score=round(r_score, 1),
                weight=0.20, details=f"grade_level={gl}",
            ))
            total_weight += 0.20
        except Exception:
            pass

    # ── Grammar ──
    if include_grammar:
        try:
            from texthumanize.grammar import check_grammar
            gr = check_grammar(text, lang)
            components.append(HealthComponent(
                name="grammar", score=gr.score,
                weight=0.25,
                details=f"{gr.errors} errors, {gr.warnings} warnings",
            ))
            total_weight += 0.25
        except Exception:
            pass

    # ── Uniqueness ──
    if include_uniqueness:
        try:
            from texthumanize.uniqueness import uniqueness_score
            uq = uniqueness_score(text)
            components.append(HealthComponent(
                name="uniqueness", score=uq.score,
                weight=0.20,
                details=f"vocab_richness={uq.vocabulary_richness}",
            ))
            total_weight += 0.20
        except Exception:
            pass

    # ── AI Detection (invert: lower AI = better health) ──
    if include_ai:
        try:
            from texthumanize.core import detect_ai
            ai = detect_ai(text, lang=lang)
            ai_prob = ai.get("ai_probability", 0.5)
            ai_score = (1.0 - ai_prob) * 100
            verdict = ai.get("verdict", "unknown")
            components.append(HealthComponent(
                name="ai_naturalness", score=round(ai_score, 1),
                weight=0.20,
                details=f"verdict={verdict}, ai_prob={ai_prob:.2f}",
            ))
            total_weight += 0.20
        except Exception:
            pass

    # ── Coherence ──
    if include_coherence:
        try:
            from texthumanize.core import analyze_coherence
            coh = analyze_coherence(text, lang=lang)
            coh_score = coh.get("overall_score", 0.7) * 100
            components.append(HealthComponent(
                name="coherence", score=round(coh_score, 1),
                weight=0.15,
                details=f"overall={coh.get('overall_score', 0):.2f}",
            ))
            total_weight += 0.15
        except Exception:
            pass

    # ── Composite ──
    if total_weight > 0:
        # Re-normalize weights
        composite = sum(
            c.score * (c.weight / total_weight)
            for c in components
        )
    else:
        composite = 50.0  # Fallback

    composite = round(min(100.0, max(0.0, composite)), 1)
    grade = _grade_from_score(composite)

    return ContentHealthReport(
        score=composite,
        grade=grade,
        components=components,
    )
