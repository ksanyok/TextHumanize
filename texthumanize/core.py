"""Основной API библиотеки TextHumanize."""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from texthumanize.analyzer import TextAnalyzer
from texthumanize.cache import result_cache
from texthumanize.exceptions import ConfigError, InputTooLargeError
from texthumanize.lang_detect import detect_language
from texthumanize.pipeline import Pipeline
from texthumanize.utils import AnalysisReport, DetectionReport, HumanizeOptions, HumanizeResult

logger = logging.getLogger(__name__)

# ─── Generic lazy module loader ──────────────────────────────

_lazy_lock = threading.Lock()
_lazy_modules: dict[str, object] = {}


def _lazy_import(module_path: str) -> object:
    """Thread-safe lazy import with double-checked locking.

    Args:
        module_path: Fully qualified module name (e.g. 'texthumanize.detectors').

    Returns:
        The imported module object (cached after first import).
    """
    mod = _lazy_modules.get(module_path)
    if mod is not None:
        return mod
    with _lazy_lock:
        mod = _lazy_modules.get(module_path)
        if mod is not None:
            return mod
        import importlib
        mod = importlib.import_module(module_path)
        _lazy_modules[module_path] = mod
        return mod


def _get_detectors():
    return _lazy_import("texthumanize.detectors")


def _get_paraphrase():
    return _lazy_import("texthumanize.paraphrase")


def _get_tone():
    return _lazy_import("texthumanize.tone")


def _get_watermark():
    return _lazy_import("texthumanize.watermark")


def _get_spinner():
    return _lazy_import("texthumanize.spinner")


def _get_stat_detector():
    return _lazy_import("texthumanize.statistical_detector")


def _get_ai_backend():
    return _lazy_import("texthumanize.ai_backend")


def _get_coherence():
    return _lazy_import("texthumanize.coherence")


def humanize(
    text: str,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    target_style: object | str | None = None,
    only_flagged: bool = False,
    custom_dict: dict[str, str | list[str]] | None = None,
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
        only_flagged: Если True, гуманизировать только предложения,
            которые detect_ai_sentences помечает как AI (ai_probability > 0.5).
            Предложения с label="human" остаются без изменений.
        custom_dict: Пользовательский словарь замен.
            Формат: {"слово": "замена"} или {"слово": ["вар1", "вар2"]}.
            Замены применяются дополнительно к встроенным словарям.
            При списке вариантов выбирается случайный.

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
    # Input sanitization
    if not isinstance(text, str):
        raise ConfigError(f"Expected str, got {type(text).__name__}")
    if not text or not text.strip():
        return HumanizeResult(
            original=text, text=text, lang=lang or "en",
            profile=profile, intensity=intensity,
            changes=[], metrics_before={}, metrics_after={},
        )
    MAX_TEXT_LENGTH = 1_000_000  # 1M chars safety limit
    if len(text) > MAX_TEXT_LENGTH:
        raise InputTooLargeError(len(text), MAX_TEXT_LENGTH)

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
        custom_dict=custom_dict,
    )

    if preserve:
        options.preserve.update(preserve)
    if constraints:
        options.constraints.update(constraints)

    # ── Cache lookup ────────────────────────────────────────────
    if seed is not None:
        cached = result_cache.get(
            text, lang=detected_lang, profile=profile, intensity=intensity, seed=seed,
        )
        if cached is not None:
            return cached

    # Запускаем пайплайн
    pipeline = Pipeline(options=options)

    # ── Selective humanization ────────────────────────────────
    if only_flagged:
        return _humanize_flagged_only(
            text, detected_lang, pipeline, options,
        )

    result = pipeline.run(text, detected_lang)

    # ── Cache result (only deterministic calls with seed) ─────
    if seed is not None:
        result_cache.put(
            text, result, lang=detected_lang, profile=profile,
            intensity=intensity, seed=seed,
        )

    return result


def humanize_ai(
    text: str,
    lang: str = "auto",
    *,
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    enable_oss: bool = False,
    profile: str = "web",
) -> HumanizeResult:
    """Humanize using AI backend (OpenAI / OSS / fallback).

    Three-tier strategy:
    1. OpenAI (if api_key provided)
    2. OSS model via Gradio (if enable_oss=True)
    3. Built-in rules (always available)
    """
    if lang == "auto":
        lang = detect_language(text)

    ab = _get_ai_backend()
    # LRU cache for backend instances (preserves circuit breaker state,
    # bounded to 16 entries to prevent memory leaks in server contexts)
    _cache_key = (openai_api_key, openai_model, enable_oss)
    if not hasattr(humanize_ai, '_instances'):
        humanize_ai._instances: dict = {}
        humanize_ai._order: list = []
    if _cache_key not in humanize_ai._instances:
        _MAX_CACHE = 16
        if len(humanize_ai._order) >= _MAX_CACHE:
            _evict = humanize_ai._order.pop(0)
            humanize_ai._instances.pop(_evict, None)
        humanize_ai._instances[_cache_key] = ab.AIBackend(
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            enable_oss=enable_oss,
        )
        humanize_ai._order.append(_cache_key)
    backend = humanize_ai._instances[_cache_key]
    result_text = backend.paraphrase(text, lang=lang, style=profile)

    # Run through pipeline for cleanup
    return humanize(result_text, lang=lang, profile=profile, intensity=40)


def _humanize_flagged_only(
    text: str,
    lang: str,
    pipeline: Pipeline,
    options: HumanizeOptions,
) -> HumanizeResult:
    """Гуманизировать только предложения, помеченные как AI.

    Разбивает текст на предложения, пропускает «человеческие» и
    обрабатывает только те, где ``ai_probability > 0.5``.
    """
    sentences = detect_ai_sentences(text, lang=lang)
    if not sentences:
        return pipeline.run(text, lang)

    parts: list[str] = []
    all_changes: list[dict] = []
    flagged_count = 0
    skipped_count = 0

    # Recover whitespace between sentences using original offsets
    prev_end = 0
    for sent in sentences:
        start = sent.get("start", prev_end)
        # Preserve inter-sentence whitespace
        if start > prev_end:
            parts.append(text[prev_end:start])

        sent_text = sent["text"]
        if sent.get("ai_probability", 0) > 0.5:
            # Humanize this sentence individually
            flagged_count += 1
            sub = pipeline.run(sent_text, lang)
            parts.append(sub.text)
            all_changes.extend(sub.changes)
        else:
            # Keep untouched
            skipped_count += 1
            parts.append(sent_text)
            all_changes.append({
                "type": "selective_skip",
                "description": (
                    f"Пропущено (human, p={sent.get('ai_probability', 0):.2f}): "
                    f"{sent_text[:60]}…"
                    if len(sent_text) > 60 else
                    f"Пропущено (human, p={sent.get('ai_probability', 0):.2f}): "
                    f"{sent_text}"
                ),
            })
        prev_end = sent.get("end", start + len(sent_text))

    # Trailing text
    if prev_end < len(text):
        parts.append(text[prev_end:])

    combined = "".join(parts)

    # Analyze before/after
    analyzer_obj = TextAnalyzer(lang=lang)
    metrics_before = analyzer_obj.analyze(text)
    metrics_after = analyzer_obj.analyze(combined)

    all_changes.insert(0, {
        "type": "selective_mode",
        "description": (
            f"Selective: {flagged_count} AI / {skipped_count} human sentences"
        ),
    })

    return HumanizeResult(
        original=text,
        text=combined,
        lang=lang,
        profile=options.profile,
        intensity=options.intensity,
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


def explain(
    result: HumanizeResult,
    fmt: str = "text",
    **kwargs,
) -> str:
    """Объяснить что было изменено — в нескольких форматах.

    Args:
        result: Результат humanize().
        fmt: Формат вывода: ``"text"`` (default), ``"html"``,
            ``"json"`` (RFC 6902 patch), ``"diff"`` (unified diff).
        **kwargs: Передаются в соответствующий рендерер.

    Returns:
        Отчёт об изменениях в выбранном формате.

    Examples:
        >>> result = humanize("Данный текст является примером.")
        >>> print(explain(result))
        === Отчёт TextHumanize ===
        Язык: ru | Профиль: web | Интенсивность: 60
        ...
        >>> html = explain(result, fmt="html")
        >>> json_str = explain(result, fmt="json")
    """
    if fmt == "html":
        from texthumanize.diff_report import explain_html
        return explain_html(result, **kwargs)
    if fmt == "json":
        from texthumanize.diff_report import explain_json_patch
        return explain_json_patch(result, **kwargs)
    if fmt == "diff":
        from texthumanize.diff_report import explain_side_by_side
        return explain_side_by_side(result, **kwargs)
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

    # Split into paragraph-based chunks (overlap applied between adjacent chunks)
    chunks = _split_into_chunks(text, chunk_size, overlap=overlap)

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


def _split_into_chunks(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text at paragraph boundaries, respecting chunk_size.

    When *overlap* > 0, the last `overlap` characters of each chunk
    are prepended to the next chunk to preserve cross-boundary context.
    """
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
            # Overlap: carry trailing characters into next chunk
            if overlap > 0:
                tail = chunks[-1][-overlap:]
                current = [tail]
                current_len = len(tail)
            else:
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

def detect_ai(text: str, lang: str = "auto") -> DetectionReport:
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
    if not isinstance(text, str):
        raise ConfigError(f"Expected str, got {type(text).__name__}")
    if not text or not text.strip():
        return {"score": 0.0, "combined_score": 0.0, "stat_probability": None,
                "verdict": "human", "confidence": 0.0, "metrics": {}}
    MAX_DETECT_LENGTH = 1_000_000
    if len(text) > MAX_DETECT_LENGTH:
        raise InputTooLargeError(len(text), MAX_DETECT_LENGTH)

    if lang == "auto":
        lang = detect_language(text)

    det = _get_detectors()
    result = det.detect_ai(text, lang=lang)

    # Enhance with statistical detector
    try:
        sd = _get_stat_detector()
        stat_result = sd.detect_ai_statistical(text, lang=lang)
        # Weighted merge: 60% heuristic, 40% statistical
        combined_score = result.ai_probability * 0.6 + stat_result.get("probability", 0.5) * 0.4
        # Override if statistical detector is confident
        stat_prob = stat_result.get("probability", 0.5)
    except Exception:
        combined_score = result.ai_probability
        stat_prob = None

    return {
        "score": result.ai_probability,
        "combined_score": combined_score,
        "stat_probability": stat_prob,
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
    intensity: int = 50,
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
            intensity=min(intensity, 100),
        )

        # Increase intensity slightly for next round
        intensity = min(intensity + 10, 100)

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


def humanize_sentences(
    text: str,
    lang: str = "auto",
    *,
    profile: str = "web",
    intensity: int = 60,
    ai_threshold: float = 0.5,
    preserve: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Humanize only sentences flagged as AI-generated.

    Unlike humanize(only_flagged=True) which uses a binary flag,
    this function applies graduated intensity per sentence based
    on individual AI probability scores.

    Args:
        text: Input text.
        lang: Language code.
        profile: Processing profile.
        intensity: Base intensity (0-100).
        ai_threshold: Minimum AI probability to trigger processing.
        preserve: Preservation settings.
        seed: Random seed.

    Returns:
        Dict with: text, original, sentences (list of per-sentence results),
        human_kept, ai_processed, avg_ai_before, avg_ai_after.
    """
    if lang == "auto":
        lang = detect_language(text)

    # Score each sentence
    sentences_data = detect_ai_sentences(text, lang=lang)

    result_sentences = []
    processed_parts = []
    human_count = 0
    ai_count = 0
    scores_before = []
    scores_after = []

    for sent_info in sentences_data:
        sent_text = sent_info.get("sentence", sent_info.get("text", ""))
        ai_prob = sent_info.get("ai_probability", 0.0)
        scores_before.append(ai_prob)

        if ai_prob >= ai_threshold and len(sent_text.split()) >= 3:
            # Apply graduated intensity based on AI score
            grad_intensity = min(100, int(intensity * (ai_prob / 0.8)))
            result = humanize(
                sent_text,
                lang=lang,
                profile=profile,
                intensity=grad_intensity,
                preserve=preserve,
                seed=seed,
            )
            processed_parts.append(result.text)
            result_sentences.append({
                "original": sent_text,
                "processed": result.text,
                "ai_probability": ai_prob,
                "intensity_applied": grad_intensity,
                "action": "humanized",
            })
            ai_count += 1
            # Re-score after humanization
            re_sents = detect_ai_sentences(result.text, lang=lang)
            scores_after.append(
                re_sents[0].get("ai_probability", ai_prob) if re_sents else ai_prob
            )
        else:
            processed_parts.append(sent_text)
            result_sentences.append({
                "original": sent_text,
                "processed": sent_text,
                "ai_probability": ai_prob,
                "intensity_applied": 0,
                "action": "kept",
            })
            human_count += 1
            scores_after.append(ai_prob)

    final_text = " ".join(processed_parts)

    return {
        "text": final_text,
        "original": text,
        "lang": lang,
        "sentences": result_sentences,
        "human_kept": human_count,
        "ai_processed": ai_count,
        "avg_ai_before": sum(scores_before) / len(scores_before) if scores_before else 0.0,
        "avg_ai_after": sum(scores_after) / len(scores_after) if scores_after else 0.0,
    }


def humanize_variants(
    text: str,
    lang: str = "auto",
    *,
    variants: int = 3,
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    seed: int | None = None,
) -> list[dict]:
    """Generate multiple humanization variants for comparison.

    Each variant uses a different random seed derived from the base seed,
    producing different but valid humanizations. Results are sorted
    by quality score (best first).

    Args:
        text: Input text.
        lang: Language code.
        variants: Number of variants to generate (1-10).
        profile: Processing profile.
        intensity: Processing intensity (0-100).
        preserve: Preservation settings.
        seed: Base seed (variants derive from this).

    Returns:
        List of dicts sorted by quality, each with: text, variant_id,
        seed_used, change_ratio, quality_score, ai_score, changes_count.
    """
    import random as _rnd

    variants = max(1, min(variants, 10))

    if lang == "auto":
        lang = detect_language(text)

    base_seed = seed if seed is not None else _rnd.randint(0, 2**31)
    results = []

    for i in range(variants):
        variant_seed = base_seed + i * 7919  # prime offset
        result = humanize(
            text,
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            seed=variant_seed,
        )

        # Score the variant
        ai_check = detect_ai(result.text, lang=lang)

        results.append({
            "text": result.text,
            "variant_id": i + 1,
            "seed_used": variant_seed,
            "change_ratio": round(result.change_ratio, 4),
            "quality_score": round(result.quality_score, 4),
            "ai_score": round(ai_check.get("score", 0.0), 4),
            "changes_count": len(result.changes),
            "metrics_after": result.metrics_after,
        })

    # Sort by quality: low AI score + high quality score
    results.sort(key=lambda r: (r["ai_score"], -r["quality_score"]))

    return results


def humanize_stream(
    text: str,
    lang: str = "auto",
    *,
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    seed: int | None = None,
    chunk_size: int = 500,
):
    """Stream humanized text in chunks (generator).

    Processes text paragraph-by-paragraph and yields results
    incrementally. Useful for real-time UIs and chat integrations.

    Args:
        text: Input text.
        lang: Language code.
        profile: Processing profile.
        intensity: Processing intensity (0-100).
        preserve: Preservation settings.
        seed: Random seed.
        chunk_size: Approximate characters per chunk.

    Yields:
        Dict with: chunk, chunk_index, is_last, progress (0.0-1.0),
        original_chunk.
    """
    if lang == "auto":
        lang = detect_language(text)

    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    if not paragraphs:
        return

    total_chars = len(text)
    processed_chars = 0
    chunk_index = 0

    # Group paragraphs into chunks of approximate size
    current_chunk = []
    current_size = 0
    chunks = []

    for para in paragraphs:
        current_chunk.append(para)
        current_size += len(para)
        if current_size >= chunk_size:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_size = 0

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        result = humanize(
            chunk,
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            seed=seed + i if seed is not None else None,
        )

        processed_chars += len(chunk)
        chunk_index = i

        yield {
            "chunk": result.text,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "is_last": i == total_chunks - 1,
            "progress": min(1.0, processed_chars / total_chars) if total_chars > 0 else 1.0,
            "original_chunk": chunk,
            "change_ratio": round(result.change_ratio, 4),
        }


def anonymize_style(
    text: str,
    lang: str = "auto",
    target: object | str | None = None,
    seed: int | None = None,
) -> dict:
    """Анонимизировать стилистический отпечаток текста.

    Трансформирует текст так, чтобы его стилистика отличалась от
    оригинального авторского стиля. Применимо для whistleblower
    protection, anonymous peer review, authorship privacy.

    Args:
        text: Текст для анонимизации.
        lang: Код языка (или ``"auto"``).
        target: Целевой стиль — ``StylisticFingerprint``, имя пресета
            (``'student'``, ``'copywriter'``, ``'scientist'``,
            ``'journalist'``, ``'blogger'``) или ``None`` (default
            = ``'journalist'``).
        seed: Сид для воспроизводимости.

    Returns:
        dict с ключами: ``text``, ``original``, ``target_preset``,
        ``similarity_before``, ``similarity_after``, ``changes``.

    Examples:
        >>> result = anonymize_style("My very recognizable text...", target="blogger")
        >>> print(result["similarity_before"], "→", result["similarity_after"])
    """
    from texthumanize.stylistic import StylometricAnonymizer

    detected_lang = lang
    if lang == "auto":
        detected_lang = detect_language(text)

    anonymizer = StylometricAnonymizer(lang=detected_lang, seed=seed)
    result = anonymizer.anonymize(text, target=target)

    return {
        "text": result.text,
        "original": result.original,
        "target_preset": result.target_preset,
        "similarity_before": result.similarity_before,
        "similarity_after": result.similarity_after,
        "changes": result.changes,
    }

