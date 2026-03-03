"""
texthumanize.visualize — Модуль визуализации анализа текста.

Предоставляет Unicode-графики для терминала / plain-text вывода:
- Перплексия по предложениям (кривая + бары)
- AI-detection карта (по предложениям)
- Распределение длин предложений
- Лексическое разнообразие (TTR)
- Энтропия символов
- Сводная дашборд-панель

Все графики работают в любом терминале с UTF-8, без внешних зависимостей.

© 2024-2025 ASH™ / TextHumanize
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "TextVisualizer",
    "VisualizationResult",
    "dashboard",
    "detection_heatmap",
    "entropy_chart",
    "lexical_diversity_chart",
    "perplexity_chart",
    "sentence_length_chart",
]

# ═══════════════════════════════════════════════════════════════
#  UNICODE CHART ELEMENTS
# ═══════════════════════════════════════════════════════════════

_BLOCKS = " ▁▂▃▄▅▆▇█"
_SHADE_BLOCKS = " ░▒▓█"
_HBAR = "━"
_VBAR = "│"
_CORNER_TL = "┌"
_CORNER_TR = "┐"
_CORNER_BL = "└"
_CORNER_BR = "┘"
_TEE_L = "├"
_TEE_R = "┤"
_CROSS = "┼"
_H_DOUBLE = "═"
_V_DOUBLE = "║"

# ── Цветовые маркеры (ANSI, опционально) ──
_COLORS = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def _c(color: str, text: str, use_color: bool = True) -> str:
    """Обернуть текст ANSI-цветом (если включён)."""
    if not use_color:
        return text
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


# ═══════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════

def _split_sentences(text: str) -> list[str]:
    """Базовое разбиение на предложения."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p for p in parts if p.strip()]


def _tokenize(text: str) -> list[str]:
    """Простая токенизация."""
    return re.findall(r'\b\w+\b', text.lower())


def _bar(value: float, max_val: float, width: int = 30) -> str:
    """Горизонтальный прогресс-бар."""
    if max_val <= 0:
        return " " * width
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _sparkline(values: list[float], width: int = 50) -> str:
    """Unicode sparkline (▁▂▃▄▅▆▇█)."""
    if not values:
        return "(нет данных)"
    mn = min(values)
    mx = max(values)
    rng = mx - mn if mx > mn else 1.0
    result = ""
    for v in values[:width]:
        idx = int((v - mn) / rng * (len(_BLOCKS) - 1))
        result += _BLOCKS[idx]
    return result


def _heatmap_char(value: float, low: float = 0.0, high: float = 1.0) -> str:
    """Символ для тепловой карты (0.0→' ', 1.0→'█')."""
    ratio = max(0.0, min(1.0, (value - low) / (high - low) if high > low else 0.0))
    idx = int(ratio * (len(_SHADE_BLOCKS) - 1))
    return _SHADE_BLOCKS[idx]


def _entropy(text: str) -> float:
    """Энтропия Шеннона посимвольно."""
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(text)
    ent = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def _ttr(tokens: list[str]) -> float:
    """Type-Token Ratio."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _word_perplexity(sentence: str) -> float:
    """Простая оценка перплексии на основе inverse word frequency."""
    # Упрощённая формула: чем реже слова — тем выше перплексия
    tokens = _tokenize(sentence)
    if not tokens:
        return 0.0
    # Используем длину слов как прокси для редкости
    total = sum(len(w) ** 1.5 for w in tokens)
    return total / len(tokens) * 100


# ═══════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class VisualizationResult:
    """Результат визуализации."""
    text: str                        # Исходный текст
    chart: str                       # Сгенерированный текстовый график
    data: dict[str, Any] = field(default_factory=dict)  # Числовые данные


# ═══════════════════════════════════════════════════════════════
#  ГРАФИКИ
# ═══════════════════════════════════════════════════════════════

def perplexity_chart(
    text: str,
    *,
    width: int = 50,
    use_color: bool = False,
    lang: str = "en",
    show_values: bool = True,
) -> VisualizationResult:
    """
    Визуализация перплексии по предложениям.

    Показывает Unicode sparkline + числовые значения для каждого предложения.
    Интегрируется с PerplexitySculptor если доступен.
    """
    # Попробуем использовать PerplexitySculptor для реальных значений
    per_sentence_ppls: list[float] = []
    sentences = _split_sentences(text)

    try:
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang=lang)
        analysis = ps.analyze_curve(text)
        per_sent = analysis.get("per_sentence", [])
        if per_sent:
            per_sentence_ppls = [s["perplexity"] for s in per_sent]
            sentences = [s["text"] for s in per_sent]
    except Exception:
        pass

    if not per_sentence_ppls:
        per_sentence_ppls = [_word_perplexity(s) for s in sentences]

    if not per_sentence_ppls:
        return VisualizationResult(text=text, chart="(текст пустой)", data={})

    mn = min(per_sentence_ppls)
    mx = max(per_sentence_ppls)
    mean_ppl = sum(per_sentence_ppls) / len(per_sentence_ppls)
    cv = (
        (sum((p - mean_ppl) ** 2 for p in per_sentence_ppls) / len(per_sentence_ppls)) ** 0.5
        / mean_ppl if mean_ppl > 0 else 0.0
    )

    lines: list[str] = []
    lines.append(f"{'═' * 60}")
    lines.append(f"  ПЕРПЛЕКСИЯ ПО ПРЕДЛОЖЕНИЯМ ({len(sentences)} предл.)")
    lines.append(f"{'═' * 60}")
    lines.append("")
    lines.append(f"  Sparkline: {_sparkline(per_sentence_ppls, width)}")
    lines.append("")

    # Таблица по предложениям
    lines.append(f"  {'#':>3}  {'PPL':>10}  {'Бар':^32}  Текст")
    lines.append(f"  {'─' * 80}")

    for i, (ppl, sent) in enumerate(zip(per_sentence_ppls, sentences)):
        bar = _bar(ppl, mx, 25)
        short = sent[:40] + "…" if len(sent) > 40 else sent

        if use_color:
            if ppl > mean_ppl * 1.5:
                bar = _c("red", bar)
            elif ppl < mean_ppl * 0.5:
                bar = _c("green", bar)
            else:
                bar = _c("yellow", bar)

        if show_values:
            lines.append(f"  {i+1:>3}  {ppl:>10.1f}  {bar}  {short}")
        else:
            lines.append(f"  {i+1:>3}  {'▓' * 10}  {bar}  {short}")

    lines.append("")
    lines.append(f"  Среднее: {mean_ppl:.1f}  |  Мин: {mn:.1f}  |  Макс: {mx:.1f}")
    lines.append(f"  CV (вариация): {cv:.4f}  |  Диапазон: {mx - mn:.1f}")

    # Оценка «человечности» по вариации
    if cv > 0.4:
        verdict = "✓ Человекоподобная вариация"
    elif cv > 0.15:
        verdict = "~ Умеренная вариация"
    else:
        verdict = "✗ Подозрительно ровная (AI-паттерн)"

    lines.append(f"  Вердикт: {verdict}")
    lines.append("")

    chart = "\n".join(lines)
    data = {
        "per_sentence_ppl": per_sentence_ppls,
        "mean": mean_ppl,
        "min": mn,
        "max": mx,
        "cv": cv,
        "sentence_count": len(sentences),
    }

    return VisualizationResult(text=text, chart=chart, data=data)


def detection_heatmap(
    text: str,
    *,
    lang: str = "en",
    width: int = 50,
    use_color: bool = False,
) -> VisualizationResult:
    """
    Тепловая карта AI-detection по предложениям.

    Каждому предложению присваивается score 0.0-1.0 и отображается как
    символ интенсивности. Высокие score = больше AI-характеристик.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return VisualizationResult(text=text, chart="(текст пустой)", data={})

    # Получаем покомпонентные оценки через AIDetector
    scores: list[float] = []
    details_per_sent: list[dict] = []

    try:
        from texthumanize.detectors import AIDetector
        det = AIDetector(lang=lang)
        for sent in sentences:
            r = det.detect(sent, lang=lang)
            scores.append(float(r.ai_probability))
            details_per_sent.append({
                "entropy": float(r.entropy_score),
                "vocabulary": float(r.vocabulary_score),
                "pattern": float(r.pattern_score),
                "rhythm": float(r.rhythm_score),
            })
    except Exception:
        # Fallback: простая эвристика
        for sent in sentences:
            tokens = _tokenize(sent)
            ttr_val = _ttr(tokens)
            avg_len = sum(len(w) for w in tokens) / max(len(tokens), 1)
            # Низкий TTR и длинные слова → скорее AI
            score = min(1.0, max(0.0, (1.0 - ttr_val) * 0.5 + (avg_len / 12) * 0.5))
            scores.append(score)
            details_per_sent.append({})

    lines: list[str] = []
    lines.append(f"{'═' * 60}")
    lines.append(f"  ТЕПЛОВАЯ КАРТА AI-ДЕТЕКЦИИ ({len(sentences)} предл.)")
    lines.append(f"{'═' * 60}")
    lines.append("")

    # Карта-полоска
    heatstrip = ""
    for s in scores:
        heatstrip += _heatmap_char(s, 0.0, 1.0)
    lines.append(f"  Карта: [{heatstrip}]")
    lines.append(f"         {'0.0 (human)':^{len(heatstrip)//2}}")
    lines.append("")

    # Легенда
    lines.append("  ' '=human  '░'=low  '▒'=mixed  '▓'=high  '█'=AI")
    lines.append("")

    # Таблица
    lines.append(f"  {'#':>3}  {'Score':>6}  {'│':^3}  {'Бар':^25}  Текст")
    lines.append(f"  {'─' * 75}")

    mean_score = sum(scores) / len(scores) if scores else 0
    for i, (sc, sent) in enumerate(zip(scores, sentences)):
        bar = _bar(sc, 1.0, 20)
        short = sent[:35] + "…" if len(sent) > 35 else sent

        if use_color:
            if sc > 0.7:
                bar = _c("red", bar)
            elif sc > 0.4:
                bar = _c("yellow", bar)
            else:
                bar = _c("green", bar)

        lines.append(f"  {i+1:>3}  {sc:>6.3f}  {_VBAR}  {bar}  {short}")

    lines.append("")
    lines.append(f"  Средний AI-score: {mean_score:.3f}")

    if mean_score > 0.7:
        lines.append("  ⚠ Текст сильно похож на AI-генерированный")
    elif mean_score > 0.4:
        lines.append("  ~ Текст имеет смешанные характеристики")
    else:
        lines.append("  ✓ Текст выглядит человеческим")

    lines.append("")

    chart = "\n".join(lines)
    data = {
        "scores": scores,
        "mean_score": mean_score,
        "details": details_per_sent,
        "sentence_count": len(sentences),
    }

    return VisualizationResult(text=text, chart=chart, data=data)


def sentence_length_chart(
    text: str,
    *,
    width: int = 50,
    use_color: bool = False,
) -> VisualizationResult:
    """
    Распределение длин предложений (в словах).

    AI-тексты часто имеют малую вариацию длин.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return VisualizationResult(text=text, chart="(текст пустой)", data={})

    lengths = [len(_tokenize(s)) for s in sentences]
    mn = min(lengths) if lengths else 0
    mx = max(lengths) if lengths else 0
    mean_len = sum(lengths) / len(lengths) if lengths else 0

    lines: list[str] = []
    lines.append(f"{'═' * 60}")
    lines.append(f"  ДЛИНЫ ПРЕДЛОЖЕНИЙ ({len(sentences)} предл.)")
    lines.append(f"{'═' * 60}")
    lines.append("")
    lines.append(f"  Sparkline: {_sparkline([float(x) for x in lengths], width)}")
    lines.append("")

    for i, (ln, sent) in enumerate(zip(lengths, sentences)):
        bar = _bar(float(ln), float(mx), 20)
        short = sent[:35] + "…" if len(sent) > 35 else sent
        lines.append(f"  {i+1:>3}  {ln:>3} слов  {bar}  {short}")

    lines.append("")
    lines.append(f"  Среднее: {mean_len:.1f} слов  |  Мин: {mn}  |  Макс: {mx}")

    cv = (
        (sum((l - mean_len) ** 2 for l in lengths) / len(lengths)) ** 0.5
        / mean_len if mean_len > 0 else 0.0
    )
    lines.append(f"  CV (вариация длин): {cv:.4f}")

    if cv > 0.4:
        lines.append("  ✓ Хорошая вариация длин (человеческий стиль)")
    elif cv > 0.2:
        lines.append("  ~ Умеренная вариация")
    else:
        lines.append("  ✗ Подозрительно однородные длины (AI-паттерн)")

    lines.append("")

    chart = "\n".join(lines)
    data = {
        "lengths": lengths,
        "mean": mean_len,
        "cv": cv,
        "min": mn,
        "max": mx,
    }

    return VisualizationResult(text=text, chart=chart, data=data)


def lexical_diversity_chart(
    text: str,
    *,
    window_size: int = 50,
    use_color: bool = False,
) -> VisualizationResult:
    """
    Скользящее лексическое разнообразие (Moving TTR).

    Показывает как меняется TTR по ходу текста.
    Ровная линия = подозрительно (AI часто поддерживает стабильный TTR).
    """
    tokens = _tokenize(text)
    if len(tokens) < window_size:
        overall_ttr = _ttr(tokens)
        chart = (
            f"  Текст слишком короткий для скользящего анализа.\n"
            f"  Общий TTR: {overall_ttr:.4f} ({len(set(tokens))}/{len(tokens)} уникальных)"
        )
        return VisualizationResult(
            text=text, chart=chart,
            data={"overall_ttr": overall_ttr, "token_count": len(tokens)}
        )

    # Скользящий TTR
    mttr_values: list[float] = []
    for i in range(len(tokens) - window_size + 1):
        window = tokens[i:i + window_size]
        mttr_values.append(_ttr(window))

    mean_ttr = sum(mttr_values) / len(mttr_values)
    cv = (
        (sum((v - mean_ttr) ** 2 for v in mttr_values) / len(mttr_values)) ** 0.5
        / mean_ttr if mean_ttr > 0 else 0.0
    )

    lines: list[str] = []
    lines.append(f"{'═' * 60}")
    lines.append(f"  ЛЕКСИЧЕСКОЕ РАЗНООБРАЗИЕ (окно={window_size} токенов)")
    lines.append(f"{'═' * 60}")
    lines.append("")
    lines.append(f"  Кривая MTTR: {_sparkline(mttr_values, 50)}")
    lines.append("")
    lines.append(f"  Средний TTR: {mean_ttr:.4f}")
    lines.append(f"  CV вариация: {cv:.4f}")
    lines.append(f"  Всего токенов: {len(tokens)}")
    lines.append(f"  Уникальных: {len(set(tokens))}")
    lines.append("")

    if cv > 0.08:
        lines.append("  ✓ Естественная вариация разнообразия")
    elif cv > 0.03:
        lines.append("  ~ Умеренная стабильность")
    else:
        lines.append("  ✗ Подозрительно стабильный TTR (AI-паттерн)")

    lines.append("")

    chart = "\n".join(lines)
    data = {
        "mttr_values": mttr_values,
        "mean_ttr": mean_ttr,
        "cv": cv,
        "total_tokens": len(tokens),
        "unique_tokens": len(set(tokens)),
    }

    return VisualizationResult(text=text, chart=chart, data=data)


def entropy_chart(
    text: str,
    *,
    chunk_size: int = 100,
    use_color: bool = False,
) -> VisualizationResult:
    """
    Энтропия Шеннона по чанкам текста.

    AI-тексты часто имеют стабильную энтропию. Человеческие — варьируют.
    """
    if len(text) < chunk_size:
        ent = _entropy(text)
        chart = f"  Текст короткий. Энтропия: {ent:.4f} бит/символ"
        return VisualizationResult(
            text=text, chart=chart,
            data={"entropy": ent, "length": len(text)}
        )

    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    entropies = [_entropy(ch) for ch in chunks]

    mean_ent = sum(entropies) / len(entropies)
    cv = (
        (sum((e - mean_ent) ** 2 for e in entropies) / len(entropies)) ** 0.5
        / mean_ent if mean_ent > 0 else 0.0
    )

    lines: list[str] = []
    lines.append(f"{'═' * 60}")
    lines.append(f"  ЭНТРОПИЯ ШЕННОНА (чанки по {chunk_size} символов)")
    lines.append(f"{'═' * 60}")
    lines.append("")
    lines.append(f"  Кривая: {_sparkline(entropies, 50)}")
    lines.append("")

    for i, ent in enumerate(entropies):
        bar = _bar(ent, max(entropies), 20)
        lines.append(f"  Чанк {i+1:>3}  {ent:.3f} бит  {bar}")

    lines.append("")
    lines.append(f"  Средняя энтропия: {mean_ent:.4f} бит/символ")
    lines.append(f"  CV вариация: {cv:.4f}")
    lines.append("")

    chart = "\n".join(lines)
    data = {
        "entropies": entropies,
        "mean": mean_ent,
        "cv": cv,
        "chunks": len(chunks),
    }

    return VisualizationResult(text=text, chart=chart, data=data)


def comparison_chart(
    text_before: str,
    text_after: str,
    *,
    lang: str = "en",
    use_color: bool = False,
) -> VisualizationResult:
    """
    Сравнительный анализ текста ДО и ПОСЛЕ гуманизации.

    Показывает изменения перплексии, лексического разнообразия,
    длин предложений и AI-score.
    """
    lines: list[str] = []
    lines.append(f"{'═' * 65}")
    lines.append("  СРАВНЕНИЕ: ДО vs ПОСЛЕ ГУМАНИЗАЦИИ")
    lines.append(f"{'═' * 65}")
    lines.append("")

    # Перплексия
    sent_before = _split_sentences(text_before)
    sent_after = _split_sentences(text_after)
    ppl_b = [_word_perplexity(s) for s in sent_before]
    ppl_a = [_word_perplexity(s) for s in sent_after]

    try:
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang=lang)
        ab = ps.analyze_curve(text_before)
        aa = ps.analyze_curve(text_after)
        ps_b = ab.get("per_sentence", [])
        ps_a = aa.get("per_sentence", [])
        if ps_b:
            ppl_b = [s["perplexity"] for s in ps_b]
        if ps_a:
            ppl_a = [s["perplexity"] for s in ps_a]
    except Exception:
        pass

    mean_ppl_b = sum(ppl_b) / len(ppl_b) if ppl_b else 0
    mean_ppl_a = sum(ppl_a) / len(ppl_a) if ppl_a else 0

    lines.append(f"  {'Метрика':<28} {'ДО':>10} {'ПОСЛЕ':>10} {'Δ':>10}")
    lines.append(f"  {'─' * 60}")

    # 1. Перплексия
    lines.append(
        f"  {'Ср. перплексия':<28} {mean_ppl_b:>10.1f} {mean_ppl_a:>10.1f} "
        f"{mean_ppl_a - mean_ppl_b:>+10.1f}"
    )

    # 2. CV перплексии
    cv_b = (
        (sum((p - mean_ppl_b)**2 for p in ppl_b) / len(ppl_b))**0.5 / mean_ppl_b
        if mean_ppl_b > 0 and ppl_b else 0
    )
    cv_a = (
        (sum((p - mean_ppl_a)**2 for p in ppl_a) / len(ppl_a))**0.5 / mean_ppl_a
        if mean_ppl_a > 0 and ppl_a else 0
    )
    lines.append(
        f"  {'CV перплексии':<28} {cv_b:>10.4f} {cv_a:>10.4f} "
        f"{cv_a - cv_b:>+10.4f}"
    )

    # 3. Кол-во предложений
    lines.append(
        f"  {'Предложений':<28} {len(sent_before):>10} {len(sent_after):>10} "
        f"{len(sent_after) - len(sent_before):>+10}"
    )

    # 4. TTR
    tok_b = _tokenize(text_before)
    tok_a = _tokenize(text_after)
    ttr_b = _ttr(tok_b)
    ttr_a = _ttr(tok_a)
    lines.append(
        f"  {'TTR (лекс. разнообразие)':<28} {ttr_b:>10.4f} {ttr_a:>10.4f} "
        f"{ttr_a - ttr_b:>+10.4f}"
    )

    # 5. Энтропия
    ent_b = _entropy(text_before)
    ent_a = _entropy(text_after)
    lines.append(
        f"  {'Энтропия (бит/символ)':<28} {ent_b:>10.4f} {ent_a:>10.4f} "
        f"{ent_a - ent_b:>+10.4f}"
    )

    # 6. AI-score
    try:
        from texthumanize.detectors import AIDetector
        det = AIDetector(lang=lang)
        r_b = det.detect(text_before, lang=lang)
        r_a = det.detect(text_after, lang=lang)
        score_b = float(r_b.ai_probability)
        score_a = float(r_a.ai_probability)
        lines.append(
            f"  {'AI-score':<28} {score_b:>10.3f} {score_a:>10.3f} "
            f"{score_a - score_b:>+10.3f}"
        )
    except Exception:
        pass

    # 7. Средняя длина предложений
    len_b = [len(_tokenize(s)) for s in sent_before]
    len_a = [len(_tokenize(s)) for s in sent_after]
    ml_b = sum(len_b) / len(len_b) if len_b else 0
    ml_a = sum(len_a) / len(len_a) if len_a else 0
    lines.append(
        f"  {'Ср. длина предл. (слов)':<28} {ml_b:>10.1f} {ml_a:>10.1f} "
        f"{ml_a - ml_b:>+10.1f}"
    )

    lines.append("")

    # Sparklines
    lines.append(f"  Перплексия ДО:    {_sparkline(ppl_b, 40)}")
    lines.append(f"  Перплексия ПОСЛЕ: {_sparkline(ppl_a, 40)}")
    lines.append("")

    chart = "\n".join(lines)
    data = {
        "ppl_before": ppl_b,
        "ppl_after": ppl_a,
        "cv_before": cv_b,
        "cv_after": cv_a,
        "ttr_before": ttr_b,
        "ttr_after": ttr_a,
        "entropy_before": ent_b,
        "entropy_after": ent_a,
    }

    return VisualizationResult(text=text_before, chart=chart, data=data)


def dashboard(
    text: str,
    *,
    lang: str = "en",
    use_color: bool = False,
) -> VisualizationResult:
    """
    Единая сводная дашборд-панель: все метрики текста.

    Объединяет перплексию, детекцию, длины, разнообразие и энтропию
    в один компактный отчёт.
    """
    lines: list[str] = []
    lines.append("")
    lines.append(f"  ╔{'═' * 62}╗")
    lines.append(f"  ║{'ДАШБОРД АНАЛИЗА ТЕКСТА':^62}║")
    lines.append(f"  ╚{'═' * 62}╝")
    lines.append("")

    sentences = _split_sentences(text)
    tokens = _tokenize(text)

    # Базовая статистика
    lines.append("  📊 Базовые метрики")
    lines.append(f"  ├─ Символов: {len(text)}")
    lines.append(f"  ├─ Слов: {len(tokens)}")
    lines.append(f"  ├─ Предложений: {len(sentences)}")
    lines.append(f"  ├─ Уникальных слов: {len(set(tokens))}")
    lines.append(f"  └─ TTR: {_ttr(tokens):.4f}")
    lines.append("")

    # Перплексия
    ppl_res = perplexity_chart(text, lang=lang, use_color=use_color)
    ppl_data = ppl_res.data
    if ppl_data:
        lines.append("  📈 Перплексия")
        lines.append(f"  ├─ Sparkline: {_sparkline(ppl_data.get('per_sentence_ppl', []), 40)}")
        lines.append(f"  ├─ Средняя: {ppl_data.get('mean', 0):.1f}")
        lines.append(f"  └─ CV: {ppl_data.get('cv', 0):.4f}")
        lines.append("")

    # AI-detection
    det_res = detection_heatmap(text, lang=lang, use_color=use_color)
    det_data = det_res.data
    if det_data:
        scores = det_data.get("scores", [])
        heatstrip = "".join(_heatmap_char(s) for s in scores)
        lines.append("  🔍 AI-Detection")
        lines.append(f"  ├─ Карта: [{heatstrip}]")
        lines.append(f"  └─ Средний score: {det_data.get('mean_score', 0):.3f}")
        lines.append("")

    # Длины предложений
    lengths = [len(_tokenize(s)) for s in sentences]
    if lengths:
        mean_l = sum(lengths) / len(lengths)
        lines.append("  📏 Длины предложений")
        lines.append(f"  ├─ Sparkline: {_sparkline([float(x) for x in lengths], 40)}")
        lines.append(f"  └─ Среднее: {mean_l:.1f} слов (мин {min(lengths)}, макс {max(lengths)})")
        lines.append("")

    # Энтропия
    ent = _entropy(text)
    lines.append(f"  🎲 Энтропия: {ent:.4f} бит/символ")
    lines.append("")

    # Общий вердикт
    lines.append(f"  {'─' * 62}")
    mean_score = det_data.get("mean_score", 0) if det_data else 0
    ppl_cv = ppl_data.get("cv", 0) if ppl_data else 0

    if mean_score > 0.7:
        verdict = "⚠ ВЫСОКАЯ вероятность AI-текста"
    elif mean_score > 0.4:
        verdict = "~ СМЕШАННЫЕ характеристики"
    else:
        verdict = "✓ НИЗКАЯ вероятность AI"

    lines.append(f"  ВЕРДИКТ: {verdict}")
    lines.append(f"  (AI-score={mean_score:.3f}, PPL-CV={ppl_cv:.4f})")
    lines.append("")

    chart = "\n".join(lines)
    data = {
        "char_count": len(text),
        "word_count": len(tokens),
        "sentence_count": len(sentences),
        "ttr": _ttr(tokens),
        "entropy": ent,
        "ai_score": mean_score,
        "ppl_cv": ppl_cv,
    }

    return VisualizationResult(text=text, chart=chart, data=data)


# ═══════════════════════════════════════════════════════════════
#  OOP ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════════

class TextVisualizer:
    """
    Унифицированный визуализатор текста.

    Пример использования::

        viz = TextVisualizer(lang="en")
        result = viz.dashboard(text)
        print(result.chart)

        cmp = viz.compare(original, humanized)
        print(cmp.chart)
    """

    def __init__(self, lang: str = "en", use_color: bool = False):
        self.lang = lang
        self.use_color = use_color

    def perplexity(self, text: str, **kw: Any) -> VisualizationResult:
        """График перплексии по предложениям."""
        return perplexity_chart(
            text, lang=self.lang, use_color=self.use_color, **kw
        )

    def detection(self, text: str, **kw: Any) -> VisualizationResult:
        """Тепловая карта AI-детекции."""
        return detection_heatmap(
            text, lang=self.lang, use_color=self.use_color, **kw
        )

    def lengths(self, text: str, **kw: Any) -> VisualizationResult:
        """Распределение длин предложений."""
        return sentence_length_chart(
            text, use_color=self.use_color, **kw
        )

    def diversity(self, text: str, **kw: Any) -> VisualizationResult:
        """Лексическое разнообразие (скользящий TTR)."""
        return lexical_diversity_chart(
            text, use_color=self.use_color, **kw
        )

    def entropy(self, text: str, **kw: Any) -> VisualizationResult:
        """Энтропия по чанкам."""
        return entropy_chart(
            text, use_color=self.use_color, **kw
        )

    def compare(self, before: str, after: str, **kw: Any) -> VisualizationResult:
        """Сравнение ДО и ПОСЛЕ гуманизации."""
        return comparison_chart(
            before, after, lang=self.lang, use_color=self.use_color, **kw
        )

    def dashboard(self, text: str, **kw: Any) -> VisualizationResult:
        """Полная дашборд-панель."""
        return dashboard(
            text, lang=self.lang, use_color=self.use_color, **kw
        )

    def full_report(self, text: str) -> str:
        """Полный отчёт: все графики в одном."""
        parts = [
            self.dashboard(text).chart,
            self.perplexity(text).chart,
            self.detection(text).chart,
            self.lengths(text).chart,
        ]
        tokens = _tokenize(text)
        if len(tokens) >= 50:
            parts.append(self.diversity(text).chart)

        if len(text) >= 100:
            parts.append(self.entropy(text).chart)

        return "\n".join(parts)
