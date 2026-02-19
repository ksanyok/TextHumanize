"""Основной API библиотеки TextHumanize."""

from __future__ import annotations

import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from texthumanize.analyzer import TextAnalyzer
from texthumanize.lang_detect import detect_language
from texthumanize.pipeline import Pipeline
from texthumanize.utils import AnalysisReport, HumanizeOptions, HumanizeResult

# Ленивый импорт новых модулей (для обратной совместимости)
_detectors = None
_paraphrase = None
_tone = None
_watermark = None
_spinner = None
_coherence = None


def _get_detectors():
    global _detectors
    if _detectors is None:
        import texthumanize.detectors as _d
        _detectors = _d
    return _detectors


def _get_paraphrase():
    global _paraphrase
    if _paraphrase is None:
        import texthumanize.paraphrase as _p
        _paraphrase = _p
    return _paraphrase


def _get_tone():
    global _tone
    if _tone is None:
        import texthumanize.tone as _t
        _tone = _t
    return _tone


def _get_watermark():
    global _watermark
    if _watermark is None:
        import texthumanize.watermark as _w
        _watermark = _w
    return _watermark


def _get_spinner():
    global _spinner
    if _spinner is None:
        import texthumanize.spinner as _s
        _spinner = _s
    return _spinner


def _get_coherence():
    global _coherence
    if _coherence is None:
        import texthumanize.coherence as _c
        _coherence = _c
    return _coherence


def humanize(
    text: str,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    target_style: object | str | None = None,
) -> HumanizeResult:
    """Гуманизировать текст — сделать его более естественным.

    Основная функция библиотеки. Принимает текст и возвращает
    его обработанную версию с метриками и списком изменений.

    Args:
        text: Текст для обработки.
        lang: Код языка: 'auto', 'ru', 'uk', 'en', 'de', 'fr', 'es', 'pl', 'pt', 'it'
            или любой ISO-код. При 'auto' язык определяется автоматически.
            Для языков без полного словаря используется универсальный процессор.
        profile: Профиль обработки:
            - 'chat' — живой, разговорный стиль
            - 'web' — нейтральный веб-контент
            - 'seo' — SEO-безопасный режим
            - 'docs' — документация, технический стиль
            - 'formal' — формальный стиль
        intensity: Интенсивность обработки (0-100).
            0 = без изменений, 100 = максимум.
        preserve: Настройки защиты элементов:
            - code_blocks (bool): Защита блоков кода. По умолчанию True.
            - urls (bool): Защита URL. По умолчанию True.
            - emails (bool): Защита email. По умолчанию True.
            - hashtags (bool): Защита хэштегов. По умолчанию True.
            - mentions (bool): Защита @упоминаний. По умолчанию True.
            - markdown (bool): Защита markdown. По умолчанию True.
            - html (bool): Защита HTML-тегов. По умолчанию True.
            - numbers (bool): Защита чисел. По умолчанию False.
            - brand_terms (list[str]): Список брендовых терминов.
        constraints: Ограничения обработки:
            - max_change_ratio (float): Максимальная доля изменений (0-1).
            - min_sentence_length (int): Минимальная длина предложения.
            - keep_keywords (list[str]): Ключевые слова для SEO.
        seed: Сид для воспроизводимости результатов.
        target_style: Целевой стилистический отпечаток.
            Может быть StylisticFingerprint или имя пресета (str):
            'student', 'copywriter', 'scientist', 'journalist', 'blogger'.

    Returns:
        HumanizeResult с полями:
            - text: Обработанный текст
            - original: Исходный текст
            - lang: Определённый язык
            - profile: Использованный профиль
            - intensity: Использованная интенсивность
            - changes: Список сделанных изменений
            - metrics_before: Метрики до обработки
            - metrics_after: Метрики после обработки
            - change_ratio: Доля изменений

    Examples:
        >>> result = humanize("Данный текст является примером.")
        >>> print(result.text)
        Этот текст - пример.

        >>> result = humanize(
        ...     "Осуществляем обработку текста.",
        ...     profile="chat",
        ...     intensity=80,
        ... )
        >>> print(result.text)
        Обрабатываем текст.
    """
    if not text or not text.strip():
        return HumanizeResult(
            original=text,
            text=text,
            lang=lang if lang != "auto" else "en",
            profile=profile,
            intensity=intensity,
        )

    # Определяем язык
    detected_lang = lang
    if lang == "auto":
        detected_lang = detect_language(text)

    # Строим опции
    options = HumanizeOptions(
        lang=detected_lang,
        profile=profile,
        intensity=intensity,
        seed=seed,
        target_style=target_style,
    )

    if preserve:
        options.preserve.update(preserve)
    if constraints:
        options.constraints.update(constraints)

    # Запускаем пайплайн
    pipeline = Pipeline(options=options)
    result = pipeline.run(text, detected_lang)

    return result


def analyze(text: str, lang: str = "auto") -> AnalysisReport:
    """Анализировать текст — получить метрики «искусственности».

    Args:
        text: Текст для анализа.
        lang: Код языка: 'auto', 'ru', 'uk', 'en', 'de', 'fr', 'es', 'pl', 'pt', 'it'
            или любой ISO-код.

    Returns:
        AnalysisReport с метриками:
            - artificiality_score: Общий балл (0-100)
            - avg_sentence_length: Средняя длина предложения
            - bureaucratic_ratio: Доля канцеляризмов
            - connector_ratio: Доля ИИ-связок
            - repetition_score: Показатель повторяемости
            - typography_score: «Идеальность» типографики

    Examples:
        >>> report = analyze("Данный текст является примером.")
        >>> print(f"Искусственность: {report.artificiality_score:.1f}/100")
        Искусственность: 35.0/100
    """
    if not text or not text.strip():
        return AnalysisReport(lang=lang if lang != "auto" else "en")

    detected_lang = lang
    if lang == "auto":
        detected_lang = detect_language(text)

    analyzer = TextAnalyzer(lang=detected_lang)
    return analyzer.analyze(text)


def explain(result: HumanizeResult) -> str:
    """Объяснить что было изменено — человекочитаемый отчёт.

    Args:
        result: Результат humanize().

    Returns:
        Текстовый отчёт с перечислением изменений.

    Examples:
        >>> result = humanize("Данный текст является примером.")
        >>> print(explain(result))
        === Отчёт TextHumanize ===
        Язык: ru | Профиль: web | Интенсивность: 60
        ...
    """
    lines = [
        "=== Отчёт TextHumanize ===",
        f"Язык: {result.lang} | Профиль: {result.profile} "
        f"| Интенсивность: {result.intensity}",
        f"Доля изменений: {result.change_ratio:.1%}",
        "",
    ]

    # Метрики
    if result.metrics_before and result.metrics_after:
        lines.append("--- Метрики ---")
        before = result.metrics_before
        after = result.metrics_after

        metrics = [
            ("Искусственность", "artificiality_score", ""),
            ("Средн. длина предложения", "avg_sentence_length", " сл."),
            ("Канцеляризмы", "bureaucratic_ratio", ""),
            ("ИИ-связки", "connector_ratio", ""),
            ("Повторяемость", "repetition_score", ""),
            ("Типографика", "typography_score", ""),
        ]

        for label, key, unit in metrics:
            b = before.get(key, 0)
            a = after.get(key, 0)
            direction = "↓" if a < b else "↑" if a > b else "="
            lines.append(f"  {label}: {b:.2f}{unit} → {a:.2f}{unit} {direction}")

        lines.append("")

    # Изменения
    if result.changes:
        lines.append(f"--- Изменения ({len(result.changes)}) ---")
        for change in result.changes[:20]:  # Ограничиваем вывод
            change_type = change.get("type", "unknown")
            if "original" in change and "replacement" in change:
                lines.append(
                    f"  [{change_type}] "
                    f'"{change["original"]}" → "{change["replacement"]}"'
                )
            elif "description" in change:
                lines.append(f"  [{change_type}] {change['description']}")

        if len(result.changes) > 20:
            lines.append(f"  ... и ещё {len(result.changes) - 20} изменений")
    else:
        lines.append("--- Изменений нет ---")

    return "\n".join(lines)


def humanize_chunked(
    text: str,
    chunk_size: int = 5000,
    overlap: int = 200,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    max_workers: int | None = None,
) -> HumanizeResult:
    """Process large texts by splitting into manageable chunks.

    Splits the text at paragraph or sentence boundaries, processes each
    chunk independently (optionally in parallel), then reassembles.

    Args:
        text: Text to process (any length).
        chunk_size: Target chunk size in characters (default 5000).
        overlap: Character overlap between chunks to preserve context.
        lang: Language code ('auto' for auto-detection).
        profile: Processing profile.
        intensity: Processing intensity (0-100).
        preserve: Preservation settings.
        constraints: Processing constraints.
        seed: Random seed for reproducibility.
        max_workers: Number of parallel workers (None = sequential,
            1 = sequential, 2+ = parallel threads).

    Returns:
        HumanizeResult with the fully processed text.
    """
    if not text or not text.strip():
        return HumanizeResult(
            original=text or "",
            text=text or "",
            lang=lang if lang != "auto" else "en",
            profile=profile,
            intensity=intensity,
        )

    # For small texts, just use the regular function
    if len(text) <= chunk_size:
        return humanize(
            text, lang=lang, profile=profile, intensity=intensity,
            preserve=preserve, constraints=constraints, seed=seed,
        )

    # Split into paragraph-based chunks
    chunks = _split_into_chunks(text, chunk_size)

    detected_lang = lang
    if lang == "auto":
        detected_lang = detect_language(text[:2000])

    def _process_chunk(idx_chunk: tuple[int, str]) -> tuple[int, HumanizeResult]:
        i, chunk = idx_chunk
        chunk_seed = seed + i if seed is not None else None
        result = humanize(
            chunk,
            lang=detected_lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            constraints=constraints,
            seed=chunk_seed,
        )
        return (i, result)

    indexed_chunks = list(enumerate(chunks))
    results_map: dict[int, HumanizeResult] = {}

    if max_workers and max_workers >= 2 and len(chunks) > 1:
        # Параллельная обработка
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_chunk, ic): ic[0]
                for ic in indexed_chunks
            }
            for future in as_completed(futures):
                idx, result = future.result()
                results_map[idx] = result
    else:
        # Последовательная обработка
        for ic in indexed_chunks:
            idx, result = _process_chunk(ic)
            results_map[idx] = result

    # Собираем в порядке
    ordered = [results_map[i] for i in range(len(chunks))]
    all_processed = [r.text for r in ordered]
    all_changes: list[dict] = []
    for r in ordered:
        all_changes.extend(r.changes)

    processed_text = "\n\n".join(all_processed)

    return HumanizeResult(
        original=text,
        text=processed_text,
        lang=detected_lang,
        profile=profile,
        intensity=intensity,
        changes=all_changes,
    )


def humanize_batch(
    texts: list[str],
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    on_progress: Callable[[int, int, HumanizeResult], None] | None = None,
    max_workers: int | None = None,
) -> list[HumanizeResult]:
    """Гуманизировать несколько текстов за один вызов.

    Удобная обёртка для пакетной обработки. Каждый текст обрабатывается
    независимо с собственным сидом (seed + index) для воспроизводимости.

    Args:
        texts: Список текстов для обработки.
        lang: Код языка ('auto' для автоопределения).
        profile: Профиль обработки.
        intensity: Интенсивность обработки (0-100).
        preserve: Настройки защиты элементов.
        constraints: Ограничения обработки.
        seed: Базовый сид. Для i-го текста используется seed + i.
        on_progress: Callback, вызываемый после обработки каждого текста.
            Принимает (current_index, total_count, result).
        max_workers: Число потоков (None/1 = последовательно, 2+ = параллельно).
            Внимание: при max_workers > 1 on_progress может вызываться не по порядку.

    Returns:
        Список HumanizeResult — по одному для каждого входного текста.
    """
    total = len(texts)

    def _process_item(idx: int) -> tuple[int, HumanizeResult]:
        item_seed = seed + idx if seed is not None else None
        result = humanize(
            texts[idx],
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            constraints=constraints,
            seed=item_seed,
        )
        if on_progress is not None:
            on_progress(idx, total, result)
        return (idx, result)

    results_map: dict[int, HumanizeResult] = {}

    if max_workers and max_workers >= 2 and total > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_item, i): i
                for i in range(total)
            }
            for future in as_completed(futures):
                idx, result = future.result()
                results_map[idx] = result
    else:
        for i in range(total):
            idx, result = _process_item(i)
            results_map[idx] = result

    return [results_map[i] for i in range(total)]


def _split_into_chunks(text: str, chunk_size: int) -> list[str]:
    """Split text at paragraph boundaries, respecting chunk_size."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para)

        if current_len + para_len > chunk_size and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


# ═══════════════════════════════════════════════════════════════
#  НОВЫЕ API ФУНКЦИИ v0.4.0
# ═══════════════════════════════════════════════════════════════

def detect_ai(text: str, lang: str = "auto") -> dict:
    """Определить вероятность AI-генерации текста.

    Использует 12 независимых статистических метрик:
    entropy, burstiness, vocabulary, zipf, stylometry,
    ai_patterns, punctuation, coherence, grammar_perfection,
    opening_diversity, readability_consistency, rhythm.

    Args:
        text: Текст для проверки (рекомендуется 100+ слов).
        lang: Код языка ('auto' для автоопределения).

    Returns:
        Словарь с результатами:
            - score (float): 0..1, вероятность AI-генерации
            - verdict (str): 'human', 'mixed', или 'ai'
            - confidence (float): 0..1, уверенность
            - metrics (dict): Подробные метрики

    Examples:
        >>> result = detect_ai("This is a remarkably compelling text.")
        >>> print(f"AI: {result['score']:.2f}, verdict: {result['verdict']}")
    """
    if lang == "auto":
        lang = detect_language(text)

    det = _get_detectors()
    result = det.detect_ai(text, lang=lang)
    return {
        "score": result.ai_probability,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "metrics": {
            "entropy": result.entropy_score,
            "burstiness": result.burstiness_score,
            "vocabulary": result.vocabulary_score,
            "zipf": result.zipf_score,
            "stylometry": result.stylometry_score,
            "ai_patterns": result.pattern_score,
            "punctuation": result.punctuation_score,
            "coherence": result.coherence_score,
            "grammar_perfection": result.grammar_score,
            "opening_diversity": result.opening_score,
            "readability_consistency": result.readability_score,
            "rhythm": result.rhythm_score,
            "perplexity": result.perplexity_score,
            "discourse": result.discourse_score,
            "semantic_repetition": result.semantic_rep_score,
            "entity_specificity": result.entity_score,
            "voice": result.voice_score,
            "topic_sentence": result.topic_sent_score,
        },
        "explanations": result.explanations,
        "domain": result.detected_domain,
        "lang": lang,
    }


def detect_ai_batch(texts: list[str], lang: str = "auto") -> list[dict]:
    """Пакетная проверка текстов на AI-генерацию.

    Args:
        texts: Список текстов.
        lang: Код языка.

    Returns:
        Список результатов detect_ai для каждого текста.
    """
    return [detect_ai(t, lang=lang) for t in texts]


def detect_ai_sentences(
    text: str,
    lang: str = "auto",
    *,
    window: int = 3,
) -> list[dict]:
    """Per-sentence AI detection.

    Returns a list of dicts, one per sentence, with keys:
    text, start, end, ai_probability, label ("human"/"mixed"/"ai").

    Args:
        text: Text to analyse.
        lang: Language code (or "auto").
        window: Sliding window size in sentences.
    """
    mod = _get_detectors()
    detector = mod.AIDetector(lang=lang)
    results = detector.detect_sentences(text, lang=lang, window=window)
    return [
        {
            "text": r.text,
            "start": r.start,
            "end": r.end,
            "ai_probability": r.ai_probability,
            "label": r.label,
        }
        for r in results
    ]


def detect_ai_mixed(text: str, lang: str = "auto") -> list[dict]:
    """Detect mixed AI/human text by finding boundaries.

    Groups consecutive sentences with the same label into segments.

    Returns a list of dicts with keys:
    text, start, end, label, ai_probability, sentence_count.
    """
    mod = _get_detectors()
    detector = mod.AIDetector(lang=lang)
    segments = detector.detect_mixed(text, lang=lang)
    return [
        {
            "text": seg.text,
            "start": seg.start,
            "end": seg.end,
            "label": seg.label,
            "ai_probability": seg.ai_probability,
            "sentence_count": seg.sentence_count,
        }
        for seg in segments
    ]


def paraphrase(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
) -> str:
    """Перефразировать текст, сохраняя смысл.

    Применяет синтаксические трансформации:
    - Перестановка клауз
    - Active ↔ Passive (EN)
    - Номинализация/вербализация
    - Расщепление/объединение предложений

    Args:
        text: Текст для перефразирования.
        lang: Код языка.
        intensity: 0..1, доля предложений для изменения.
        seed: Зерно RNG.

    Returns:
        Перефразированный текст.
    """
    if lang == "auto":
        lang = detect_language(text)
    return str(_get_paraphrase().paraphrase_text(
        text, lang=lang, intensity=intensity, seed=seed
    ))


def analyze_tone(text: str, lang: str = "auto") -> dict:
    """Анализировать тональность текста.

    Определяет тон (formal, casual, academic, marketing и т.д.),
    формальность, субъективность.

    Args:
        text: Текст для анализа.
        lang: Код языка.

    Returns:
        Словарь с результатами:
            - primary_tone (str): Основной тон.
            - formality (float): 0=разговорный, 1=формальный.
            - subjectivity (float): 0=объективный, 1=субъективный.
            - scores (dict): Баллы по всем тонам.
            - confidence (float): Уверенность.
    """
    if lang == "auto":
        lang = detect_language(text)

    report = _get_tone().analyze_tone(text, lang=lang)
    return {
        "primary_tone": report.primary_tone.value,
        "formality": report.formality,
        "subjectivity": report.subjectivity,
        "scores": report.scores,
        "confidence": report.confidence,
        "markers": report.markers,
    }


def adjust_tone(
    text: str,
    target: str = "neutral",
    lang: str = "auto",
    intensity: float = 0.5,
) -> str:
    """Скорректировать тональность текста.

    Args:
        text: Текст.
        target: Целевой тон — 'formal', 'casual', 'friendly',
                'academic', 'professional', 'neutral', 'marketing'.
        lang: Код языка.
        intensity: 0..1, степень коррекции.

    Returns:
        Текст с скорректированной тональностью.
    """
    if lang == "auto":
        lang = detect_language(text)
    return str(_get_tone().adjust_tone(
        text, target=target, lang=lang, intensity=intensity
    ))


def detect_watermarks(text: str, lang: str = "auto") -> dict:
    """Обнаружить скрытые водяные знаки в тексте.

    Проверяет: zero-width символы, гомоглифы, стеганографию,
    статистические AI watermarks.

    Args:
        text: Текст для проверки.
        lang: Код языка.

    Returns:
        Словарь:
            - has_watermarks (bool): Найдены ли водяные знаки.
            - watermark_types (list): Типы обнаруженных знаков.
            - cleaned_text (str): Очищенный текст.
            - details (list): Подробности.
    """
    if lang == "auto":
        lang = detect_language(text)

    report = _get_watermark().detect_watermarks(text, lang=lang)
    return {
        "has_watermarks": report.has_watermarks,
        "watermark_types": report.watermark_types,
        "cleaned_text": report.cleaned_text,
        "details": report.details,
        "characters_removed": report.characters_removed,
        "confidence": report.confidence,
    }


def clean_watermarks(text: str, lang: str = "auto") -> str:
    """Очистить текст от водяных знаков.

    Args:
        text: Текст.
        lang: Код языка.

    Returns:
        Текст без водяных знаков.
    """
    if lang == "auto":
        lang = detect_language(text)
    return str(_get_watermark().clean_watermarks(text, lang=lang))


def spin(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
) -> str:
    """Спиннинг текста — создание уникальной версии.

    Args:
        text: Исходный текст.
        lang: Код языка.
        intensity: 0..1, доля слов для замены.
        seed: Зерно RNG.

    Returns:
        Уникальная версия текста.
    """
    if lang == "auto":
        lang = detect_language(text)
    return str(_get_spinner().spin_text(
        text, lang=lang, intensity=intensity, seed=seed
    ))


def spin_variants(
    text: str,
    count: int = 5,
    lang: str = "auto",
    intensity: float = 0.5,
) -> list[str]:
    """Сгенерировать несколько уникальных версий текста.

    Args:
        text: Исходный текст.
        count: Количество вариантов.
        lang: Код языка.
        intensity: 0..1, доля слов для замены.

    Returns:
        Список уникальных версий.
    """
    if lang == "auto":
        lang = detect_language(text)
    return list(_get_spinner().generate_variants(
        text, count=count, lang=lang, intensity=intensity
    ))


def analyze_coherence(text: str, lang: str = "auto") -> dict:
    """Анализ когерентности (связности) текста.

    Args:
        text: Текст для анализа.
        lang: Код языка.

    Returns:
        Словарь с метриками когерентности:
            - overall (float): 0..1
            - lexical_cohesion (float)
            - transition_score (float)
            - topic_consistency (float)
            - issues (list): Обнаруженные проблемы
    """
    if lang == "auto":
        lang = detect_language(text)

    coh = _get_coherence()
    analyzer = coh.CoherenceAnalyzer(lang=lang)
    report = analyzer.analyze(text)
    return {
        "overall": report.overall,
        "lexical_cohesion": report.lexical_cohesion,
        "transition_score": report.transition_score,
        "topic_consistency": report.topic_consistency,
        "sentence_opening_diversity": report.sentence_opening_diversity,
        "paragraph_count": report.paragraph_count,
        "avg_paragraph_length": report.avg_paragraph_length,
        "issues": report.issues,
    }


def full_readability(text: str, lang: str = "auto") -> dict:
    """Полный анализ читабельности текста.

    Включает: Flesch-Kincaid, Coleman-Liau, ARI, SMOG,
    Gunning Fog, Dale-Chall.

    Args:
        text: Текст для анализа.
        lang: Код языка.

    Returns:
        Словарь со всеми метриками читабельности.
    """
    if lang == "auto":
        lang = detect_language(text)

    analyzer = TextAnalyzer(lang=lang)
    return analyzer.full_readability(text)


# ═════════════════════════════════════════════════════════════
#  AUTHOR FINGERPRINT
# ═════════════════════════════════════════════════════════════

def build_author_profile(texts: list[str], lang: str = "auto") -> dict:
    """Build a style profile from reference texts by one author.

    Args:
        texts: Reference texts written by the author.
        lang: Language code.

    Returns:
        Dict with profile data (can be stored as JSON).
    """
    from texthumanize.fingerprint import AuthorFingerprint
    fp = AuthorFingerprint()
    profile = fp.build_profile(texts, lang=lang)
    # Convert to dict for serialization
    from dataclasses import asdict
    return asdict(profile)


def compare_fingerprint(
    profile: dict,
    text: str,
    lang: str | None = None,
) -> dict:
    """Compare text against an author profile.

    Args:
        profile: Profile dict from build_author_profile().
        text: New text to compare.
        lang: Language code (uses profile's lang if None).

    Returns:
        Dict with similarity, verdict, confidence, deviations.
    """
    from texthumanize.fingerprint import AuthorFingerprint, StyleProfile
    fp = AuthorFingerprint()

    # Reconstruct StyleProfile from dict
    style = StyleProfile(**{
        k: v for k, v in profile.items()
        if k in StyleProfile.__dataclass_fields__
    })

    result = fp.compare(style, text, lang=lang)
    return {
        "similarity": result.similarity,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "deviations": result.deviations,
    }


# ═════════════════════════════════════════════════════════════
#  A/B DETECTION
# ═════════════════════════════════════════════════════════════

def detect_ab(
    original: str,
    processed: str,
    lang: str = "auto",
) -> dict:
    """Compare AI detection scores before and after processing.

    Useful for checking how humanization or editing changed
    the AI detection outcome.

    Args:
        original: Original text.
        processed: Processed (humanized/edited) text.
        lang: Language code.

    Returns:
        Dict with before/after scores and per-metric deltas.
    """
    before = detect_ai(original, lang=lang)
    after = detect_ai(processed, lang=lang)

    deltas = {}
    for key in before["metrics"]:
        deltas[key] = round(after["metrics"][key] - before["metrics"][key], 4)

    return {
        "before": {
            "score": before["score"],
            "verdict": before["verdict"],
        },
        "after": {
            "score": after["score"],
            "verdict": after["verdict"],
        },
        "score_delta": round(after["score"] - before["score"], 4),
        "metric_deltas": deltas,
        "improved": after["score"] < before["score"],
    }


# ═════════════════════════════════════════════════════════════
#  EVASION RESISTANCE SCORE
# ═════════════════════════════════════════════════════════════

def evasion_resistance(text: str, lang: str = "auto") -> dict:
    """Score how many detection signals catch this text.

    A high resistance score means the text is detectable by
    many independent metrics — harder to evade.

    Args:
        text: Text to evaluate.
        lang: Language code.

    Returns:
        Dict with resistance score, triggered metrics, and details.
    """
    result = detect_ai(text, lang=lang)
    metrics = result["metrics"]

    # Count how many metrics flag the text as AI
    ai_threshold = 0.55
    triggered = {k: v for k, v in metrics.items() if v >= ai_threshold}
    resistance = len(triggered) / len(metrics) if metrics else 0.0

    # Categorize strength
    if resistance >= 0.7:
        strength = "strong"
    elif resistance >= 0.4:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "resistance_score": round(resistance, 4),
        "strength": strength,
        "triggered_count": len(triggered),
        "total_metrics": len(metrics),
        "triggered_metrics": triggered,
        "overall_score": result["score"],
        "verdict": result["verdict"],
    }


# ═════════════════════════════════════════════════════════════
#  ADVERSARIAL LOOP CALIBRATION
# ═════════════════════════════════════════════════════════════

def adversarial_calibrate(
    text: str,
    lang: str = "auto",
    *,
    max_rounds: int = 5,
    target_score: float = 0.35,
    intensity: float = 0.5,
) -> dict:
    """Run humanize → detect loop until target score is reached.

    Repeatedly humanizes and checks AI score, adjusting parameters
    to find the minimum humanization needed to pass detection.

    Args:
        text: AI-generated text to calibrate.
        lang: Language code.
        max_rounds: Maximum humanization rounds.
        target_score: Target AI probability (stop when reached).
        intensity: Starting humanization intensity.

    Returns:
        Dict with: final_text, rounds, score_history, final_score.
    """
    if lang == "auto":
        lang = detect_language(text)

    current_text = text
    score_history: list[dict] = []

    for round_num in range(1, max_rounds + 1):
        # Detect current
        result = detect_ai(current_text, lang=lang)
        score_history.append({
            "round": round_num,
            "score": result["score"],
            "verdict": result["verdict"],
        })

        if result["score"] <= target_score:
            break

        # Humanize with current intensity
        current_text = humanize(
            current_text,
            lang=lang,
            intensity=min(intensity, 1.0),
        )

        # Increase intensity slightly for next round
        intensity = min(intensity + 0.1, 1.0)

    # Final check
    final = detect_ai(current_text, lang=lang)

    return {
        "original_score": score_history[0]["score"] if score_history else 0.0,
        "final_score": final["score"],
        "final_verdict": final["verdict"],
        "rounds": len(score_history),
        "target_reached": final["score"] <= target_score,
        "score_history": score_history,
        "final_text": current_text,
    }

