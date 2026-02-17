"""Основной API библиотеки TextHumanize."""

from __future__ import annotations

import re

from texthumanize.lang_detect import detect_language
from texthumanize.analyzer import TextAnalyzer
from texthumanize.pipeline import Pipeline
from texthumanize.utils import HumanizeOptions, HumanizeResult, AnalysisReport


def humanize(
    text: str,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
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
) -> HumanizeResult:
    """Process large texts by splitting into manageable chunks.

    Splits the text at paragraph or sentence boundaries, processes each
    chunk independently, then reassembles the result.

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

    all_processed: list[str] = []
    all_changes: list[dict] = []
    detected_lang = lang

    for i, chunk in enumerate(chunks):
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
        all_processed.append(result.text)
        all_changes.extend(result.changes)
        # Use detected language from first chunk for consistency
        if i == 0:
            detected_lang = result.lang

    processed_text = "\n\n".join(all_processed)

    return HumanizeResult(
        original=text,
        text=processed_text,
        lang=detected_lang,
        profile=profile,
        intensity=intensity,
        changes=all_changes,
    )


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
