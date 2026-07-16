"""Основной API библиотеки TextHumanize."""

from __future__ import annotations

import difflib
import hashlib
import logging
import math
import re
import threading
import time
import unicodedata
from collections.abc import Callable, Iterable, Sized
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, cast

from texthumanize.cache import result_cache
from texthumanize.exceptions import ConfigError, InputTooLargeError
from texthumanize.utils import AnalysisReport, DetectionReport, HumanizeOptions, HumanizeResult

if TYPE_CHECKING:
    from collections.abc import Generator

    from texthumanize.analyzer import TextAnalyzer
    from texthumanize.pipeline import Pipeline
    from texthumanize.stylistic import StylisticFingerprint

logger = logging.getLogger(__name__)

_MEMORY_LIMIT_OVERHEAD_FACTOR = 2.5


def _memory_limit_bytes(memory_limit_mb: float | None) -> int | None:
    """Normalize an optional memory limit to bytes."""
    if memory_limit_mb is None:
        return None
    if memory_limit_mb <= 0:
        raise ConfigError("memory_limit_mb must be positive")
    return int(memory_limit_mb * 1024 * 1024)


def _estimated_text_bytes(text: str) -> int:
    """Conservative in-memory estimate for one Python text string."""
    return int(len(text.encode("utf-8")) * _MEMORY_LIMIT_OVERHEAD_FACTOR)


def _ensure_memory_window(active_bytes: int, limit_bytes: int | None, label: str) -> None:
    """Raise ConfigError if the active processing window exceeds a limit."""
    if limit_bytes is not None and active_bytes > limit_bytes:
        raise ConfigError(
            f"{label} memory window exceeds memory_limit_mb: "
            f"{active_bytes:,} estimated bytes > {limit_bytes:,}"
        )

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


def _get_detectors() -> Any:
    return _lazy_import("texthumanize.detectors")


def _get_paraphrase() -> Any:
    return _lazy_import("texthumanize.paraphrase")


def _get_tone() -> Any:
    return _lazy_import("texthumanize.tone")


def _get_watermark() -> Any:
    return _lazy_import("texthumanize.watermark")


def _get_spinner() -> Any:
    return _lazy_import("texthumanize.spinner")


def _get_stat_detector() -> Any:
    return _lazy_import("texthumanize.statistical_detector")


def _get_ai_backend() -> Any:
    return _lazy_import("texthumanize.ai_backend")


def _get_coherence() -> Any:
    return _lazy_import("texthumanize.coherence")


def _get_neural_detector() -> Any:
    return _lazy_import("texthumanize.neural_detector")


def _get_neural_lm() -> Any:
    return _lazy_import("texthumanize.neural_lm")


def _get_word_embeddings() -> Any:
    return _lazy_import("texthumanize.word_embeddings")


def _get_hmm_tagger() -> Any:
    return _lazy_import("texthumanize.hmm_tagger")


def _detect_language(text: str) -> str:
    lang_mod = _lazy_import("texthumanize.lang_detect")
    return cast(str, lang_mod.detect_language(text))


def _new_pipeline(*, options: HumanizeOptions) -> Pipeline:
    pipeline_mod = _lazy_import("texthumanize.pipeline")
    return cast("Pipeline", pipeline_mod.Pipeline(options=options))


def _new_text_analyzer(*, lang: str) -> TextAnalyzer:
    analyzer_mod = _lazy_import("texthumanize.analyzer")
    return cast("TextAnalyzer", analyzer_mod.TextAnalyzer(lang=lang))


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
    minimal: bool = False,
    custom_dict: dict[str, str | list[str]] | None = None,
    quality_gate: str | None = None,
    *,
    with_quality_score: bool = False,
    auto_evade: bool = False,
    target_ai_score: float = 0.30,
    max_evade_attempts: int = 4,
    phantom: bool = False,
    phantom_budget: float = 1.0,
    phantom_target: float = 0.30,
    backend: str = "local",
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    oss_api_url: str | None = None,
    ollama_model: str = "llama3.2",
    ollama_url: str | None = None,
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
            - numbers (bool): Защита чисел. По умолчанию True.
            - dates (bool): Защита дат. По умолчанию True.
            - prices (bool): Защита цен/валют. По умолчанию True.
            - identifiers (bool): Защита версий, SKU, order id, UUID. По умолчанию True.
            - quoted_text (bool): Защита цитат. По умолчанию True.
            - named_entities (bool): Автозащита multi-token named entities. По умолчанию True.
            - brand_terms (list[str]): Список брендовых терминов.
        constraints: Ограничения обработки:
            - max_change_ratio (float): Максимальная доля изменений (0-1).
            - min_sentence_length (int): Минимальная длина предложения.
            - keep_keywords (list[str]): Ключевые слова для SEO.
        quality_gate: Если "strict", откатывает результат при падении
            similarity, ухудшении grammar score или readability.
        seed: Сид для воспроизводимости результатов.
        target_style: Целевой стилистический отпечаток.
            Может быть StylisticFingerprint или имя пресета/алиаса (str):
            'student', 'copywriter', 'scientist', 'journalist', 'blogger',
            'editor', 'founder', 'expert', 'support', а также RU-алиасы
            вроде 'редактор', 'основатель', 'эксперт', 'журналист'.
        only_flagged: Если True, гуманизировать только предложения,
            которые detect_ai_sentences помечает как AI (ai_probability > 0.5).
            Предложения с label="human" остаются без изменений.
        minimal: Алиас для only_flagged=True. Используется для минимального
            вмешательства: править только AI-like предложения.
        custom_dict: Пользовательский словарь замен.
            Формат: {"слово": "замена"} или {"слово": ["вар1", "вар2"]}.
            Замены применяются дополнительно к встроенным словарям.
            При списке вариантов выбирается случайный.
        backend: Бэкенд гуманизации:
            - 'local' — встроенный rule-based движок (по умолчанию, offline)
            - 'ollama' — локальная LLM через Ollama (без API key, нужен сервер)
            - 'oss' — бесплатная OSS LLM (amd/gpt-oss-120b) через Gradio, без ключей
            - 'openai' — OpenAI API (требуется api_key)
            - 'auto' — пробует openai → ollama → oss → local (fallback)
        openai_api_key: API ключ OpenAI (только для backend='openai'/'auto').
        openai_model: Модель OpenAI (по умолчанию 'gpt-4o-mini').
        oss_api_url: URL для OSS Gradio endpoint (по умолчанию amd/gpt-oss-120b-chatbot).
        ollama_model: Модель Ollama (по умолчанию 'llama3.2').
        ollama_url: URL сервера Ollama (по умолчанию 'http://localhost:11434').

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

        >>> # offline, без ключей — использует бесплатную OSS LLM
        >>> result = humanize("AI-generated text here.", backend="oss")

        >>> # с OpenAI
        >>> result = humanize("Text.", backend="openai", openai_api_key="sk-...")

        >>> # auto-evade: повторяет гуманизацию, пока AI-score не упадёт ниже 0.30
        >>> result = humanize("AI text.", auto_evade=True, target_ai_score=0.25)
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

    # ── auto_evade shortcut ──────────────────────────────────────
    # Delegates to humanize_until_human() with adaptive strategy.
    if auto_evade:
        return humanize_until_human(
            text, lang=lang, profile=profile, intensity=intensity,
            target_score=target_ai_score, max_attempts=max_evade_attempts,
            intensity_step=8, seed=seed, strategy="adaptive",
        )

    # ── AI backend routing ──────────────────────────────────────
    _valid_backends = ("local", "ollama", "oss", "openai", "auto")
    if backend not in _valid_backends:
        raise ConfigError(
            f"backend must be one of {_valid_backends}, got {backend!r}"
        )
    if backend != "local":
        return _humanize_via_backend(
            text=text,
            lang=lang,
            profile=profile,
            intensity=intensity,
            backend=backend,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            oss_api_url=oss_api_url,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
        )

    # Определяем язык
    detected_lang = lang
    if lang == "auto":
        detected_lang = _detect_language(text)

    # Строим опции
    options = HumanizeOptions(
        lang=detected_lang,
        profile=profile,
        intensity=intensity,
        seed=seed,
        target_style=target_style,
        custom_dict=custom_dict,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
    )

    if preserve:
        options.preserve.update(preserve)
    if constraints:
        options.constraints.update(constraints)
    if quality_gate is not None:
        options.constraints["quality_gate"] = quality_gate

    # ── Cache lookup ────────────────────────────────────────────
    if seed is not None:
        cached = result_cache.get(
            text, lang=detected_lang, profile=profile, intensity=intensity,
            seed=seed, phantom=phantom,
        )
        if cached is not None:
            return cast(HumanizeResult, cached)

    fast_path_result = _try_short_text_fast_path(
        text,
        detected_lang,
        options,
        has_custom_controls=bool(preserve) or bool(constraints) or quality_gate is not None,
    )
    if fast_path_result is not None and not (only_flagged or minimal or phantom):
        fast_path_result = _attach_humanize_explain(fast_path_result, detected_lang)
        fast_path_result = _maybe_attach_quality(
            fast_path_result, detected_lang, with_quality_score
        )
        if seed is not None:
            result_cache.put(
                text, fast_path_result, lang=detected_lang, profile=profile,
                intensity=intensity, seed=seed, phantom=phantom,
            )
        return fast_path_result

    # Запускаем пайплайн
    pipeline = _new_pipeline(options=options)

    # ── Selective humanization ────────────────────────────────
    if only_flagged or minimal:
        selective_result = _humanize_flagged_only(
            text, detected_lang, pipeline, options,
        )
        selective_result = _attach_humanize_explain(selective_result, detected_lang)
        return _maybe_attach_quality(
            selective_result, detected_lang, with_quality_score
        )

    result = pipeline.run(text, detected_lang)

    # ── PHANTOM™ post-processing ─────────────────────────────
    # Gradient-guided neural optimization: fine-tunes the humanized text
    # to minimize detection score by targeting specific neural features.
    # Only runs if the base result still has a high detection score.
    if phantom:
        try:
            current_det = detect_ai(result.text, lang=detected_lang)
            current_combined = current_det.get("combined_score", current_det.get("score", 0.5))
            if current_combined > phantom_target:
                from texthumanize.phantom import get_phantom
                engine = get_phantom()
                phantom_result = engine.optimize(
                    result.text, lang=detected_lang,
                    target_score=phantom_target,
                    budget=phantom_budget,
                    max_iterations=15,
                    seed=seed,
                )
                if phantom_result.final_score < current_combined:
                    result = HumanizeResult(
                        original=result.original,
                        text=phantom_result.optimized_text,
                        lang=result.lang,
                        profile=result.profile,
                        intensity=result.intensity,
                        changes=result.changes + [
                            {"type": "phantom", "description": f"PHANTOM™: {phantom_result.original_score:.3f}→{phantom_result.final_score:.3f}"}
                        ],
                        metrics_before=result.metrics_before,
                        metrics_after=result.metrics_after,
                    )
        except Exception as e:
            logger.warning("PHANTOM™ post-processing failed: %s", e)

    # ── Grammar post-processing for Slavic languages ──────────
    # Applied regardless of whether PHANTOM ran,
    # fixes agreement/government issues from dictionary replacements.
    # Uses paragraph-safe grammar fixes (not full _cleanup_text which
    # may collapse paragraph structure).
    if detected_lang in ("ru", "uk"):
        try:
            from texthumanize.phantom import (
                _fix_grammar_slavic,
                _fix_sentence_caps,
            )
            lines = result.text.split("\n")
            fixed_lines = []
            in_code_block = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_code_block = not in_code_block
                    fixed_lines.append(line)
                    continue
                if in_code_block:
                    fixed_lines.append(line)
                    continue
                if stripped:
                    line = _fix_grammar_slavic(line, detected_lang)
                    line = _fix_sentence_caps(line)
                fixed_lines.append(line)
            fixed_text = "\n".join(fixed_lines)
            if fixed_text != result.text:
                result = HumanizeResult(
                    original=result.original,
                    text=fixed_text,
                    lang=result.lang,
                    profile=result.profile,
                    intensity=result.intensity,
                    changes=result.changes,
                    metrics_before=result.metrics_before,
                    metrics_after=result.metrics_after,
                )
        except Exception:
            pass  # Grammar cleanup is best-effort

    result = _attach_humanize_explain(result, detected_lang)
    result = _maybe_attach_quality(result, detected_lang, with_quality_score)

    # ── Cache result (only deterministic calls with seed) ─────
    if seed is not None:
        result_cache.put(
            text, result, lang=detected_lang, profile=profile,
            intensity=intensity, seed=seed, phantom=phantom,
        )

    return result


# ── AI-backend humanization helper ──────────────────────────

def _humanize_via_backend(
    text: str,
    lang: str,
    profile: str,
    intensity: int,
    backend: str,
    openai_api_key: str | None,
    openai_model: str,
    oss_api_url: str | None,
    ollama_model: str = "llama3.2",
    ollama_url: str | None = None,
) -> HumanizeResult:
    """Route humanization through an AI backend, then polish via local pipeline.

    1. Sends text to the chosen backend (ollama / oss / openai / auto).
    2. Runs the result through the local pipeline at low intensity
       for typography, grammar, and coherence cleanup.
    """
    detected_lang = lang
    if lang == "auto":
        detected_lang = _detect_language(text)

    ab = _get_ai_backend()

    # Build backend with appropriate settings
    enable_oss = backend in ("oss", "auto")
    enable_ollama = backend in ("ollama", "auto")
    api_key = openai_api_key if backend in ("openai", "auto") else None

    prefer = "auto" if backend == "auto" else backend
    if prefer == "oss":
        prefer = "oss"
    elif prefer == "openai":
        prefer = "openai"
    elif prefer == "ollama":
        prefer = "ollama"

    try:
        ai = ab.AIBackend(
            openai_api_key=api_key,
            openai_model=openai_model,
            enable_ollama=enable_ollama,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
            enable_oss=enable_oss,
            oss_api_url=oss_api_url,
            prefer=prefer,
        )
        rewritten = ai.paraphrase(text, lang=detected_lang, style=profile)
        used = ai.active_backend()
        logger.info("AI backend used: %s", used)
    except Exception:
        logger.warning("AI backend failed, falling back to local pipeline", exc_info=True)
        rewritten = text

    # Polish via local rule-based pipeline (low intensity for cleanup only)
    cleanup_intensity = min(40, intensity)
    return humanize(
        rewritten,
        lang=detected_lang,
        profile=profile,
        intensity=cleanup_intensity,
        backend="local",  # avoid recursion
    )


_ai_cache: dict[Any, Any] = {}
_ai_order: list[Any] = []
_ai_cache_lock = threading.Lock()


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
        lang = _detect_language(text)

    ab = _get_ai_backend()
    # LRU cache for backend instances (preserves circuit breaker state,
    # bounded to 16 entries to prevent memory leaks in server contexts)
    _cache_key = (openai_api_key, openai_model, enable_oss)
    with _ai_cache_lock:
        if _cache_key not in _ai_cache:
            _MAX_CACHE = 16
            if len(_ai_order) >= _MAX_CACHE:
                _evict = _ai_order.pop(0)
                _ai_cache.pop(_evict, None)
            _ai_cache[_cache_key] = ab.AIBackend(
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                enable_oss=enable_oss,
            )
            _ai_order.append(_cache_key)
        backend = _ai_cache[_cache_key]
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
        end = sent.get("end", start + len(sent_text))
        # detect_ai_sentences() trims leading/trailing whitespace from
        # sent["text"] but keeps it inside [start:end], so end == next start
        # and the gap branch above never fires. Reattach that whitespace
        # explicitly or every inter-sentence space is silently dropped.
        original_slice = text[start:end]
        leading_ws = original_slice[:len(original_slice) - len(original_slice.lstrip())]
        trailing_ws = original_slice[len(original_slice.rstrip()):]
        if leading_ws:
            parts.append(leading_ws)
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
        if trailing_ws:
            parts.append(trailing_ws)
        prev_end = end

    # Trailing text
    if prev_end < len(text):
        parts.append(text[prev_end:])

    combined = "".join(parts)

    # Analyze before/after
    analyzer_obj = _new_text_analyzer(lang=lang)
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


_HUMANIZE_CHANGE_GUIDANCE: dict[str, tuple[str, str]] = {
    "watermark_cleaning": (
        "Watermark or invisible Unicode cleanup",
        "Removed hidden characters or watermark-like Unicode artifacts.",
    ),
    "debureaucratization": (
        "Formal wording softened",
        "Replaced bureaucratic or over-formal phrasing with more natural wording.",
    ),
    "naturalization": (
        "AI-like phrasing naturalized",
        "Adjusted generic AI-style phrasing toward a more human style.",
    ),
    "universal": (
        "Universal naturalization",
        "Applied language-neutral cleanup for generic AI markers and stiff phrasing.",
    ),
    "repetitions": (
        "Repetition reduced",
        "Reduced repeated wording or repeated sentence patterns.",
    ),
    "structure": (
        "Sentence rhythm varied",
        "Changed structure to avoid uniform, template-like sentence flow.",
    ),
    "syntax_rewrite": (
        "Syntax varied",
        "Changed clause order or sentence shape while preserving meaning.",
    ),
    "sentence_restructuring": (
        "Sentence structure diversified",
        "Adjusted sentence length and structure for more natural rhythm.",
    ),
    "readability": (
        "Readability improved",
        "Adjusted sentence length and flow for easier reading.",
    ),
    "tone": (
        "Tone aligned",
        "Aligned wording with the requested profile and audience.",
    ),
    "grammar": (
        "Grammar polished",
        "Applied grammar and punctuation cleanup after rewriting.",
    ),
    "grammar_guard": (
        "Grammar guard applied",
        "Checked and rolled back awkward collocations or agreement artifacts.",
    ),
    "coherence": (
        "Coherence repaired",
        "Smoothed transitions and paragraph-level flow.",
    ),
    "custom_dict": (
        "Custom dictionary applied",
        "Applied user-provided terminology replacements.",
    ),
    "detection_loop": (
        "AI detector loop improved output",
        "Ran an extra targeted pass because detector risk stayed elevated.",
    ),
    "phantom": (
        "PHANTOM optimization applied",
        "Optimized the output against detector-style statistical signals.",
    ),
    "quality_gate_strict_rollback": (
        "Strict quality gate rollback",
        "Restored safer text because similarity, grammar, or readability regressed.",
    ),
    "final_sanitization": (
        "Final artifact cleanup",
        "Removed late-stage connector or punctuation artifacts.",
    ),
    "fast_path": (
        "Short-text fast path",
        "Skipped heavy pipeline stages because the short input had no strong AI-like marker.",
    ),
}

_SHORT_FAST_PATH_MAX_CHARS = 320
_SHORT_FAST_PATH_MAX_WORDS = 45
_SHORT_FAST_PATH_MAX_INTENSITY = 60
_SHORT_FAST_PATH_MARKERS = (
    "furthermore",
    "moreover",
    "additionally",
    "nevertheless",
    "consequently",
    "it is important to note",
    "it should be noted",
    "comprehensive",
    "implementation",
    "methodology",
    "utilization",
    "facilitates",
    "significant",
    "оптимизац",
    "необходимо отметить",
    "следует отметить",
    "данный",
    "является",
    "безусловно",
    "необхідно зазначити",
    "слід зазначити",
    "даний",
    "являє собою",
)


def _short_text_fast_path_risk(text: str) -> str | None:
    """Return a reason to skip the short-text fast path, or None if safe."""
    stripped = text.strip()
    if len(stripped) > _SHORT_FAST_PATH_MAX_CHARS:
        return "too_long"

    words = re.findall(r"\b[\w'-]+\b", stripped, flags=re.UNICODE)
    if len(words) > _SHORT_FAST_PATH_MAX_WORDS:
        return "too_many_words"
    if stripped.count("\n\n") > 0:
        return "multi_paragraph"
    if any(unicodedata.category(ch) in {"Cf", "Cc"} for ch in stripped):
        return "unicode_marker"

    lowered = stripped.lower()
    for marker in _SHORT_FAST_PATH_MARKERS:
        if marker in lowered:
            return f"ai_marker:{marker}"

    sentence_count = len(re.findall(r"[.!?]+", stripped))
    if sentence_count >= 4:
        return "many_short_sentences"
    if re.search(r"\b(\w{4,})\b(?:\W+\b\1\b){1,}", lowered):
        return "repeated_word"
    return None


def _fast_path_metrics(text: str, artificiality_score: float) -> dict[str, Any]:
    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    sentences = _sentence_spans(text)
    return {
        "total_chars": len(text),
        "total_words": len(words),
        "total_sentences": len(sentences),
        "artificiality_score": artificiality_score,
        "connector_ratio": 0.0,
        "bureaucratic_ratio": 0.0,
        "repetition_score": 0.0,
        "predictability_score": 0.0,
    }


def _try_short_text_fast_path(
    text: str,
    lang: str,
    options: HumanizeOptions,
    *,
    has_custom_controls: bool,
) -> HumanizeResult | None:
    """Return a lightweight result for low-risk short text, else None."""
    if has_custom_controls:
        return None
    if options.target_style is not None or options.custom_dict:
        return None
    if options.constraints.get("quality_gate") == "strict":
        return None
    if options.intensity > _SHORT_FAST_PATH_MAX_INTENSITY:
        return None

    skip_reason = _short_text_fast_path_risk(text)
    if skip_reason is not None:
        return None

    from texthumanize.normalizer import TypographyNormalizer

    normalizer = TypographyNormalizer(profile=options.profile, lang=lang)
    normalized = normalizer.normalize(text)
    changes = list(normalizer.changes)
    changes.append({
        "type": "fast_path",
        "description": (
            "Short low-risk text skipped heavy humanization stages; "
            "typography cleanup only."
        ),
    })
    metrics_before = _fast_path_metrics(text, artificiality_score=8.0)
    metrics_after = {
        **_fast_path_metrics(normalized, artificiality_score=8.0),
        "fast_path": {
            "enabled": True,
            "max_chars": _SHORT_FAST_PATH_MAX_CHARS,
            "max_words": _SHORT_FAST_PATH_MAX_WORDS,
            "skipped_heavy_stages": True,
        },
    }
    return HumanizeResult(
        original=text,
        text=normalized,
        lang=lang,
        profile=options.profile,
        intensity=options.intensity,
        changes=changes,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
    )


def _change_reason_key(change_type: str) -> str:
    if change_type in _HUMANIZE_CHANGE_GUIDANCE:
        return change_type
    if "bureau" in change_type:
        return "debureaucratization"
    if "natural" in change_type:
        return "naturalization"
    if "repeat" in change_type:
        return "repetitions"
    if "syntax" in change_type:
        return "syntax_rewrite"
    if "readability" in change_type:
        return "readability"
    if "grammar" in change_type:
        return "grammar"
    if "coherence" in change_type:
        return "coherence"
    if "watermark" in change_type:
        return "watermark_cleaning"
    return change_type


def _top_humanize_change_reasons(
    changes: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for index, change in enumerate(changes):
        change_type = str(change.get("type", "unknown"))
        key = _change_reason_key(change_type)
        title, reason = _HUMANIZE_CHANGE_GUIDANCE.get(
            key,
            (
                change_type.replace("_", " ").title(),
                str(change.get("description") or "Pipeline stage changed the text."),
            ),
        )
        entry = grouped.setdefault(
            key,
            {
                "type": key,
                "title": title,
                "reason": reason,
                "count": 0,
                "first_seen": index,
                "examples": [],
            },
        )
        entry["count"] = int(entry["count"]) + 1
        description = str(change.get("description") or "").strip()
        examples = cast(list[str], entry["examples"])
        if description and description not in examples and len(examples) < 3:
            examples.append(description)

    ranked = sorted(
        grouped.values(),
        key=lambda item: (-int(item["count"]), int(item["first_seen"])),
    )
    for item in ranked:
        item.pop("first_seen", None)
    return ranked[:limit]


def _humanize_remaining_risks(
    result: HumanizeResult,
    lang: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    after = result.metrics_after
    risks: list[dict[str, Any]] = []

    metric_rules = [
        (
            "artificiality_score",
            _safe_float(after.get("artificiality_score")) / 100.0,
            0.25,
            "Residual artificiality is still visible in the output.",
            "Review the highest-risk sentences or use minimal=False with a higher intensity.",
        ),
        (
            "connector_ratio",
            _safe_float(after.get("connector_ratio")),
            0.08,
            "Connector usage may still look template-like.",
            "Replace generic transitions with context-specific cause, contrast, or sequence.",
        ),
        (
            "bureaucratic_ratio",
            _safe_float(after.get("bureaucratic_ratio")),
            0.06,
            "Some formal or bureaucratic phrasing may remain.",
            "Use shorter verbs and remove unnecessary abstract nouns.",
        ),
        (
            "repetition_score",
            _safe_float(after.get("repetition_score")),
            0.30,
            "Repeated wording or repeated structure may remain.",
            "Merge repeated claims and vary sentence starts.",
        ),
        (
            "predictability_score",
            _safe_float(after.get("predictability_score")),
            0.65,
            "The output may still be too predictable.",
            "Add specific examples, concrete entities, and less uniform rhythm where true.",
        ),
    ]
    for metric, score, threshold, message, action in metric_rules:
        if score < threshold:
            continue
        risks.append({
            "type": "metric",
            "metric": metric,
            "severity": _severity(score),
            "score": round(_clamp(score), 4),
            "message": message,
            "suggested_action": action,
        })

    try:
        marker_spans = _scan_ai_marker_spans(result.text, lang, max_spans=limit)
    except Exception:
        marker_spans = []
    for span in marker_spans:
        risks.append({
            "type": "highlighted_span",
            "metric": "ai_marker",
            "severity": span.get("severity", "medium"),
            "score": 0.55,
            "message": f"AI-like phrase remains: {span.get('text', '')}",
            "suggested_action": span.get(
                "suggested_action",
                "Rewrite the phrase in a more specific, context-aware way.",
            ),
            "span": {
                "start": span.get("start"),
                "end": span.get("end"),
                "text": span.get("text"),
            },
        })

    if not risks:
        risks.append({
            "type": "residual_detector_risk",
            "severity": "low",
            "score": 0.0,
            "message": "No strong residual AI-like signal was isolated.",
            "suggested_action": "Review highlighted spans only if the text is business-critical.",
        })

    return sorted(
        risks,
        key=lambda risk: _safe_float(risk.get("score")),
        reverse=True,
    )[:limit]


def _sentence_spans(text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for match in re.finditer(r"\S[^.!?\n]*(?:[.!?]+|$)", text):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        offset = match.group(0).find(sentence)
        start = match.start() + max(offset, 0)
        spans.append({
            "start": start,
            "end": start + len(sentence),
            "text": sentence,
        })
    return spans


def _humanize_sentence_report(
    result: HumanizeResult,
    lang: str,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    before_sentences = _sentence_spans(result.original)
    after_sentences = _sentence_spans(result.text)
    try:
        marker_spans = _scan_ai_marker_spans(result.text, lang, max_spans=50)
    except Exception:
        marker_spans = []
    top_operations = [
        reason["type"]
        for reason in _top_humanize_change_reasons(
            cast(list[dict[str, Any]], result.changes),
            limit=3,
        )
    ]
    rows: list[dict[str, Any]] = []

    for index, after_sentence in enumerate(after_sentences[:limit]):
        before_sentence = before_sentences[index] if index < len(before_sentences) else {}
        start = int(after_sentence["start"])
        end = int(after_sentence["end"])
        sentence_markers = [
            span for span in marker_spans
            if start <= int(span.get("start", -1)) < end
        ]
        changed = before_sentence.get("text", "") != after_sentence.get("text", "")
        risk_score = 0.55 if sentence_markers else 0.0
        if sentence_markers:
            status = "remaining_ai_risk"
        elif changed:
            status = "improved"
        else:
            status = "ok"
        rows.append({
            "index": index,
            "status": status,
            "risk_score": risk_score,
            "changed": changed,
            "before_text": before_sentence.get("text", ""),
            "after_text": after_sentence.get("text", ""),
            "applied_operations": top_operations if changed else [],
            "remaining_markers": [
                {
                    "text": marker.get("text"),
                    "category": marker.get("category"),
                    "reason": marker.get("reason"),
                }
                for marker in sentence_markers[:3]
            ],
            "reason": (
                "AI-like marker remains in this sentence."
                if sentence_markers
                else "Sentence changed and no AI-marker span remains."
                if changed
                else "No sentence-level AI-marker signal was isolated."
            ),
        })

    return rows


def attach_quality_score(
    result: HumanizeResult,
    lang: str = "auto",
    *,
    fast: bool = True,
) -> HumanizeResult:
    """Attach a unified quality score to ``result.metrics_after["quality_score"]``.

    Opt-in: the regular ``humanize()`` path does not run this on every call to
    keep the hot path cheap. Pass ``with_quality_score=True`` to ``humanize()``
    or call this helper directly. The score compares the output against the
    original and is stored in place; the same ``result`` is returned.
    """
    resolved_lang = lang if lang != "auto" else (result.lang or "auto")
    try:
        report = quality_score_report(
            result.text,
            original=result.original,
            lang=resolved_lang,
            fast=fast,
        )
    except Exception:
        return result
    result.metrics_after["quality_score"] = report
    return result


def _maybe_attach_quality(
    result: HumanizeResult, lang: str, enabled: bool
) -> HumanizeResult:
    if not enabled:
        return result
    return attach_quality_score(result, lang)


def _attach_humanize_explain(result: HumanizeResult, lang: str) -> HumanizeResult:
    """Attach top reasons and remaining risks to HumanizeResult metadata."""
    changes = cast(list[dict[str, Any]], result.changes)
    try:
        before_ai = _safe_float(result.metrics_before.get("artificiality_score")) / 100.0
        after_ai = _safe_float(result.metrics_after.get("artificiality_score")) / 100.0
        report = {
            "schema_version": "text-humanize.humanize_explain.v1",
            "top_change_reasons": _top_humanize_change_reasons(changes),
            "remaining_risks": _humanize_remaining_risks(result, lang),
            "sentence_report": _humanize_sentence_report(result, lang),
            "ai_score_before": round(_clamp(before_ai), 4),
            "ai_score_after": round(_clamp(after_ai), 4),
            "ai_score_delta": round(_clamp(before_ai) - _clamp(after_ai), 4),
            "method": "lightweight_from_pipeline_metrics_and_marker_spans",
            "quality": {
                "change_ratio": round(result.change_ratio, 4),
                "similarity": round(result.similarity, 4),
                "quality_score": round(result.quality_score, 4),
            },
        }
    except Exception as exc:
        report = {
            "schema_version": "text-humanize.humanize_explain.v1",
            "error": str(exc),
            "top_change_reasons": _top_humanize_change_reasons(changes),
            "remaining_risks": [],
            "sentence_report": [],
        }

    return HumanizeResult(
        original=result.original,
        text=result.text,
        lang=result.lang,
        profile=result.profile,
        intensity=result.intensity,
        changes=result.changes,
        metrics_before=result.metrics_before,
        metrics_after={
            **result.metrics_after,
            "humanize_explain": report,
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
        detected_lang = _detect_language(text)

    analyzer = _new_text_analyzer(lang=detected_lang)
    return analyzer.analyze(text)


def explain(
    result: HumanizeResult,
    fmt: str = "text",
    **kwargs: Any,
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


def humanize_until_human(
    text: str,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    target_score: float = 0.35,
    max_attempts: int = 5,
    intensity_step: int = 10,
    seed: int | None = None,
    verbose: bool = False,
    strategy: str = "adaptive",
) -> HumanizeResult:
    """Humanize text repeatedly until AI detection score drops below target.

    Two strategies:
    - ``"escalate"`` — simple intensity escalation each round (legacy).
    - ``"adaptive"`` — analyses per-metric AI signals and adjusts
      pipeline parameters to target the weakest metrics (default).

    Args:
        text: Text to humanize.
        lang: Language code.
        profile: Humanization profile.
        intensity: Starting intensity.
        target_score: Target AI score (stop when below this).
        max_attempts: Maximum retry attempts.
        intensity_step: Intensity increase per retry.
        seed: Random seed for reproducibility.
        verbose: Log each attempt.
        strategy: ``"adaptive"`` (default) or ``"escalate"``.

    Returns:
        HumanizeResult from the best (lowest AI score) attempt.
    """
    if lang == "auto":
        lang = _detect_language(text)

    best_result: HumanizeResult | None = None
    best_score = float("inf")
    current_text = text
    current_intensity = min(intensity, 100)

    # Adaptive state: per-metric overrides accumulate across rounds
    _adapt_overrides: dict[str, int] = {}

    for attempt in range(max_attempts):
        # Build effective intensity for this round
        effective_intensity = current_intensity
        if strategy == "adaptive" and _adapt_overrides:
            # Use the max of all individual boosts
            boost = max(_adapt_overrides.values())
            effective_intensity = min(current_intensity + boost, 100)

        # Humanize
        result = humanize(
            current_text, lang=lang, profile=profile,
            intensity=effective_intensity, seed=seed,
        )

        # Detect AI score on humanized text
        detection = detect_ai(result.text, lang=lang)
        score = detection.get("combined_score", detection.get("score", 0.5))

        if verbose:
            logger.info(
                "Attempt %d/%d: intensity=%d (eff=%d), ai_score=%.3f (target <%.3f)%s",
                attempt + 1, max_attempts, current_intensity,
                effective_intensity, score, target_score,
                f" overrides={_adapt_overrides}" if _adapt_overrides else "",
            )

        if score < best_score:
            best_score = score
            best_result = result

        # Check if we've reached the target
        if score <= target_score:
            if verbose:
                logger.info("Target reached at attempt %d", attempt + 1)
            break

        # ── Adaptive metric analysis ────────────────────────
        if strategy == "adaptive":
            metrics: dict[str, float] = dict(detection.get("metrics", {}))  # type: ignore[arg-type]
            _adapt_overrides = _compute_adaptive_overrides(
                metrics, current_intensity, verbose=verbose,
            )

        # Increase intensity for next attempt
        current_intensity = min(current_intensity + intensity_step, 100)
        # Use the humanized text as input for next round
        current_text = result.text

    if best_result is None:
        # Should not happen, but fallback
        best_result = humanize(text, lang=lang, profile=profile, intensity=intensity)

    # ── PHANTOM™ final refinement ─────────────────────────────
    # If the naturalizer pipeline didn't reach target, apply PHANTOM™
    # gradient-guided optimization as a last-mile refinement.
    if best_score > target_score:
        try:
            from texthumanize.phantom import get_phantom
            engine = get_phantom()
            phantom_result = engine.optimize(
                best_result.text, lang=lang,
                target_score=target_score,
                budget=1.0,
                max_iterations=15,
                seed=seed,
            )
            if phantom_result.final_score < best_score:
                best_result = HumanizeResult(
                    original=best_result.original,
                    text=phantom_result.optimized_text,
                    lang=best_result.lang,
                    profile=best_result.profile,
                    intensity=best_result.intensity,
                    changes=best_result.changes + [
                        {"type": "phantom", "description": f"PHANTOM™: {phantom_result.original_score:.3f}→{phantom_result.final_score:.3f}"}
                    ],
                    metrics_before=best_result.metrics_before,
                    metrics_after=best_result.metrics_after,
                )
                best_score = phantom_result.final_score
                if verbose:
                    logger.info(
                        "PHANTOM™ refinement: %.3f → %.3f (%s)",
                        phantom_result.original_score, phantom_result.final_score,
                        "HUMAN" if phantom_result.bypassed else "mixed",
                    )
        except Exception as e:
            logger.warning("PHANTOM™ refinement failed: %s", e)

    return best_result


# Metric → pipeline capability mapping for adaptive strategy.
# Each entry: (threshold_above_which_flagged, intensity_boost).
_METRIC_BOOST_MAP: dict[str, tuple[float, int]] = {
    "entropy":                  (0.55, 15),  # low entropy → boost entropy_injection
    "burstiness":               (0.55, 15),  # uniform sentence length → boost variation
    "vocabulary":               (0.55, 12),  # limited vocab → boost lexical diversity
    "ai_patterns":              (0.55, 15),  # AI phrase patterns → boost naturalizer
    "punctuation":              (0.55, 8),   # perfect punctuation → boost typography
    "coherence":                (0.55, 10),  # too coherent → boost entropy
    "grammar_perfection":       (0.55, 8),   # too perfect → inject imperfections
    "opening_diversity":        (0.55, 10),  # repetitive openings → boost restructuring
    "readability_consistency":  (0.55, 8),   # uniform readability → boost burstiness
    "rhythm":                   (0.55, 12),  # rhythmic patterns → boost entropy
    "stylometry":               (0.55, 10),  # stylistic uniformity → boost paraphrasing
    "zipf":                     (0.55, 8),   # non-Zipfian dist → boost vocab diversity
}


def _compute_adaptive_overrides(
    metrics: dict[str, float],
    current_intensity: int,
    *,
    verbose: bool = False,
) -> dict[str, int]:
    """Analyze detection metrics and compute per-area intensity boosts.

    Returns a dict of area → extra intensity to apply.
    """
    overrides: dict[str, int] = {}

    if not metrics:
        return overrides

    # Find metrics that are still flagging AI (score > threshold)
    flagged: list[tuple[str, float, int]] = []
    for metric_name, (threshold, boost) in _METRIC_BOOST_MAP.items():
        value = metrics.get(metric_name, 0.0)
        if value > threshold:
            flagged.append((metric_name, value, boost))

    if not flagged:
        return overrides

    # Sort by severity (highest score first)
    flagged.sort(key=lambda x: x[1], reverse=True)

    # Group boosted metrics into pipeline areas
    # entropy/burstiness/rhythm/coherence/readability_consistency → "entropy"
    # vocabulary/zipf → "vocabulary"
    # ai_patterns/grammar_perfection/punctuation → "naturalizer"
    # opening_diversity/stylometry → "structure"
    area_map = {
        "entropy": "entropy",
        "burstiness": "entropy",
        "rhythm": "entropy",
        "coherence": "entropy",
        "readability_consistency": "entropy",
        "vocabulary": "vocabulary",
        "zipf": "vocabulary",
        "ai_patterns": "naturalizer",
        "grammar_perfection": "naturalizer",
        "punctuation": "naturalizer",
        "opening_diversity": "structure",
        "stylometry": "structure",
    }

    for metric_name, value, boost in flagged:
        area = area_map.get(metric_name, "general")
        # Scale boost by severity: the higher the score, the more boost
        severity_factor = min((value - 0.55) / 0.3, 1.0)  # 0..1
        scaled_boost = int(boost * (0.5 + 0.5 * severity_factor))
        overrides[area] = max(overrides.get(area, 0), scaled_boost)

    if verbose:
        for metric_name, value, _boost in flagged[:5]:
            area = area_map.get(metric_name, "general")
            logger.info(
                "  Adaptive: %s=%.3f (flagged) → boost %s +%d",
                metric_name, value, area, overrides.get(area, 0),
            )

    return overrides


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
    memory_limit_mb: float | None = None,
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
        memory_limit_mb: Optional estimated active-window memory limit.
            Sequential mode validates one chunk at a time; parallel mode
            validates all submitted chunks.

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

    limit_bytes = _memory_limit_bytes(memory_limit_mb)
    detected_lang = lang
    if lang == "auto":
        detected_lang = _detect_language(text[:2000])

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

    ordered: list[HumanizeResult] = []
    if max_workers and max_workers >= 2:
        chunks = list(_iter_text_chunks(text, chunk_size, overlap=overlap))
        _ensure_memory_window(
            sum(_estimated_text_bytes(chunk) for chunk in chunks),
            limit_bytes,
            "humanize_chunked parallel chunks",
        )
        # Параллельная обработка
        results_map: dict[int, HumanizeResult] = {}
        indexed_chunks = list(enumerate(chunks))
        if len(indexed_chunks) == 1:
            _idx, result = _process_chunk(indexed_chunks[0])
            ordered = [result]
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_process_chunk, ic): ic[0]
                    for ic in indexed_chunks
                }
                for future in as_completed(futures):
                    idx, result = future.result()
                    results_map[idx] = result
            ordered = [results_map[i] for i in range(len(chunks))]
    else:
        for idx, chunk in enumerate(_iter_text_chunks(text, chunk_size, overlap=overlap)):
            _ensure_memory_window(
                _estimated_text_bytes(chunk),
                limit_bytes,
                "humanize_chunked chunk",
            )
            _idx, result = _process_chunk((idx, chunk))
            ordered.append(result)

    # Собираем в порядке
    all_processed = [r.text for r in ordered]
    all_changes: list[dict] = []
    for r in ordered:
        all_changes.extend(r.changes)

    processed_text = "\n\n".join(all_processed)
    metrics_after: dict[str, Any] = {
        "memory_bounded": {
            "enabled": memory_limit_mb is not None,
            "memory_limit_mb": memory_limit_mb,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "chunks": len(ordered),
            "max_workers": max_workers or 1,
        }
    }

    return HumanizeResult(
        original=text,
        text=processed_text,
        lang=detected_lang,
        profile=profile,
        intensity=intensity,
        changes=all_changes,
        metrics_after=metrics_after,
    )


def humanize_batch_stream(
    texts: Iterable[str],
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    memory_limit_mb: float | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Stream batch humanization results with a bounded active memory window."""
    limit_bytes = _memory_limit_bytes(memory_limit_mb)
    total = len(texts) if isinstance(texts, Sized) else None

    for idx, text in enumerate(texts):
        _ensure_memory_window(
            _estimated_text_bytes(text),
            limit_bytes,
            "humanize_batch_stream input",
        )
        item_seed = seed + idx if seed is not None else None
        result = humanize(
            text,
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            constraints=constraints,
            seed=item_seed,
        )
        _ensure_memory_window(
            _estimated_text_bytes(text) + _estimated_text_bytes(result.text),
            limit_bytes,
            "humanize_batch_stream result",
        )
        result = HumanizeResult(
            original=result.original,
            text=result.text,
            lang=result.lang,
            profile=result.profile,
            intensity=result.intensity,
            changes=result.changes,
            metrics_before=result.metrics_before,
            metrics_after={
                **result.metrics_after,
                "memory_bounded": {
                    "enabled": memory_limit_mb is not None,
                    "memory_limit_mb": memory_limit_mb,
                    "mode": "batch_stream",
                    "index": idx,
                    "total": total,
                },
            },
        )
        yield {
            "index": idx,
            "total": total,
            "is_last": total is not None and idx == total - 1,
            "result": result,
        }


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
    memory_limit_mb: float | None = None,
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
        memory_limit_mb: Optional estimated active-window memory limit. When set,
            batch uses the streaming sequential path to avoid submitting the
            entire batch to worker threads at once.

    Returns:
        Список HumanizeResult — по одному для каждого входного текста.
    """
    total = len(texts)

    if memory_limit_mb is not None:
        results: list[HumanizeResult] = []
        for item in humanize_batch_stream(
            texts,
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            constraints=constraints,
            seed=seed,
            memory_limit_mb=memory_limit_mb,
        ):
            idx = int(item["index"])
            result = cast(HumanizeResult, item["result"])
            if on_progress is not None:
                on_progress(idx, total, result)
            results.append(result)
        return results

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


def _iter_text_chunks(
    text: str,
    chunk_size: int,
    overlap: int = 0,
) -> Generator[str, None, None]:
    """Yield text chunks at paragraph boundaries without materializing all chunks.

    When *overlap* > 0, the last `overlap` characters of each chunk
    are prepended to the next chunk to preserve cross-boundary context.
    """
    if chunk_size <= 0:
        raise ConfigError("chunk_size must be positive")

    current: list[str] = []
    current_len = 0
    yielded = False

    for para in re.split(r'\n\s*\n', text):
        para = para.strip()
        if not para:
            continue
        para_len = len(para)

        if current_len + para_len > chunk_size and current:
            chunk = "\n\n".join(current)
            yielded = True
            yield chunk
            # Overlap: carry trailing characters into next chunk
            if overlap > 0:
                tail = chunk[-overlap:]
                current = [tail]
                current_len = len(tail)
            else:
                current = []
                current_len = 0

        current.append(para)
        current_len += para_len

    if current:
        yielded = True
        yield "\n\n".join(current)

    if not yielded:
        yield text


def _count_text_chunks(text: str, chunk_size: int) -> int:
    """Count stream chunks without storing their contents."""
    if chunk_size <= 0:
        raise ConfigError("chunk_size must be positive")
    count = 0
    current_size = 0
    for para in re.split(r'\n\s*\n', text):
        if current_size + len(para) >= chunk_size and current_size:
            count += 1
            current_size = 0
        current_size += len(para)
    if current_size or not text:
        count += 1
    return max(count, 1)


def _split_into_chunks(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text at paragraph boundaries, respecting chunk_size.

    Compatibility wrapper around the streaming chunk iterator.
    """
    return list(_iter_text_chunks(text, chunk_size, overlap=overlap))


_FORMAL_FALSE_POSITIVE_DOMAINS = {
    "academic",
    "docs",
    "documentation",
    "finance",
    "financial",
    "legal",
    "medical",
}

_AI_METRIC_GUIDANCE: dict[str, tuple[str, str]] = {
    "entropy": (
        "Token distribution is too even or too compressed.",
        "Add concrete details and keep natural word-choice variety.",
    ),
    "burstiness": (
        "Sentence rhythm is unusually uniform.",
        "Mix short and longer sentences where it helps the reader.",
    ),
    "vocabulary": (
        "Vocabulary variety differs from expected human baselines.",
        "Use more domain-specific wording and fewer generic terms.",
    ),
    "zipf": (
        "Word-frequency distribution looks less natural than expected.",
        "Prefer common direct wording unless a precise term is needed.",
    ),
    "stylometry": (
        "Style markers are internally too consistent.",
        "Vary openings, clause shapes, and punctuation naturally.",
    ),
    "ai_patterns": (
        "Known AI-like phrases or connectors were detected.",
        "Rewrite formulaic transitions and replace generic claims with specifics.",
    ),
    "punctuation": (
        "Punctuation pattern is unusually regular.",
        "Let punctuation follow the sentence, not a repeated template.",
    ),
    "coherence": (
        "Paragraph flow is too template-like or too smooth.",
        "Add concrete transitions that reflect the actual argument.",
    ),
    "grammar_perfection": (
        "The text is very polished with few natural irregularities.",
        "Keep correctness, but remove sterile phrasing and over-formal turns.",
    ),
    "opening_diversity": (
        "Many sentences start in similar ways.",
        "Vary sentence openings and move context after the main claim.",
    ),
    "readability_consistency": (
        "Readability is too consistent across the text.",
        "Allow natural shifts between simple explanation and denser details.",
    ),
    "rhythm": (
        "Cadence is repetitive.",
        "Break repeated sentence lengths and connector patterns.",
    ),
    "perplexity": (
        "Language-model perplexity is outside the expected range.",
        "Use natural collocations and avoid generic boilerplate.",
    ),
    "discourse": (
        "Discourse structure looks template-driven.",
        "Make transitions reflect cause, contrast, or sequence explicitly.",
    ),
    "semantic_repetition": (
        "Similar ideas are repeated with small wording changes.",
        "Merge repeated claims and add new evidence or examples.",
    ),
    "entity_specificity": (
        "The text lacks names, numbers, dates, or concrete references.",
        "Add verifiable entities, examples, figures, and constraints where true.",
    ),
    "voice": (
        "Author voice is weak or generic.",
        "Use a clearer point of view and domain-specific judgment.",
    ),
    "topic_sentence": (
        "Topic-sentence pattern is too predictable.",
        "Vary paragraph starts and lead with the most useful detail.",
    ),
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _detector_verdict(score: float) -> str:
    if score > 0.55:
        return "ai"
    if score > 0.34:
        return "mixed"
    return "human"


def _severity(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _ai_length_bucket(text: str) -> dict[str, Any]:
    chars = len(text)
    words = len(re.findall(r"\w+", text, flags=re.UNICODE))

    if chars < 300:
        name = "lt_300"
        reliability = "low"
        factor = 0.72
        margin = 0.20
    elif chars < 1000:
        name = "300_1000"
        reliability = "medium"
        factor = 0.88
        margin = 0.14
    elif chars < 5000:
        name = "1000_5000"
        reliability = "high"
        factor = 0.97
        margin = 0.09
    else:
        name = "gte_5000"
        reliability = "very_high"
        factor = 1.0
        margin = 0.06

    return {
        "name": name,
        "chars": chars,
        "words": words,
        "reliability": reliability,
        "calibration_factor": factor,
        "base_margin": margin,
    }


def _calibrate_detector_score(
    score: float,
    bucket: dict[str, Any],
    domain: str | None,
    metrics: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    factor = _safe_float(bucket.get("calibration_factor"), 1.0)
    calibrated = 0.5 + (score - 0.5) * factor

    guard_applied = 0.0
    domain_key = (domain or "").lower()
    if domain_key in _FORMAL_FALSE_POSITIVE_DOMAINS:
        pattern_score = _safe_float(metrics.get("ai_patterns"))
        if pattern_score < 0.55:
            guard_applied = min(0.06, (0.55 - pattern_score) * 0.08)
            calibrated -= guard_applied

    return _clamp(calibrated), {
        "method": "length_bucket_plus_formal_domain_guard",
        "length_factor": factor,
        "formal_domain_guard": round(guard_applied, 4),
        "note": (
            "Short texts and formal domains are pulled toward neutral to reduce "
            "false positives. Raw score is preserved separately."
        ),
    }


def _confidence_interval(
    score: float,
    confidence: float,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    base_margin = _safe_float(bucket.get("base_margin"), 0.14)
    confidence = _clamp(confidence)
    margin = min(0.25, base_margin * (1.10 - confidence * 0.35))
    return {
        "lower": round(_clamp(score - margin), 4),
        "upper": round(_clamp(score + margin), 4),
        "margin": round(margin, 4),
        "method": "heuristic_by_text_length_and_detector_confidence",
    }


def _metric_contributions(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    values = {
        name: _clamp(_safe_float(value))
        for name, value in metrics.items()
    }
    total = sum(values.values()) or 1.0
    signals: list[dict[str, Any]] = []
    for name, value in sorted(values.items(), key=lambda item: item[1], reverse=True):
        description, recommendation = _AI_METRIC_GUIDANCE.get(
            name,
            (
                name.replace("_", " "),
                "Review this metric with a domain-specific sample.",
            ),
        )
        signals.append({
            "metric": name,
            "score": round(value, 4),
            "relative_contribution": round(value / total, 4),
            "severity": _severity(value),
            "description": description,
            "recommendation": recommendation,
        })
    return signals


def _ai_reasons(
    detection: dict[str, Any],
    signals: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []

    for signal in signals:
        if signal["score"] < 0.35 and len(reasons) >= 3:
            continue
        if signal["score"] < 0.25 and reasons:
            continue
        reasons.append({
            "type": "metric",
            "metric": signal["metric"],
            "severity": signal["severity"],
            "score": signal["score"],
            "message": signal["description"],
            "suggested_action": signal["recommendation"],
        })
        if len(reasons) >= limit:
            break

    for explanation in detection.get("explanations") or []:
        if len(reasons) >= limit:
            break
        reasons.append({
            "type": "detector_explanation",
            "severity": "info",
            "message": str(explanation),
        })

    return reasons


def _unique_actions(signals: list[dict[str, Any]], domain: str | None) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for signal in signals:
        if signal["score"] < 0.30:
            continue
        action = str(signal["recommendation"])
        if action not in seen:
            seen.add(action)
            actions.append(action)
        if len(actions) >= 7:
            break

    domain_key = (domain or "").lower()
    if domain_key in _FORMAL_FALSE_POSITIVE_DOMAINS:
        action = (
            "For formal text, keep required terminology and fix only the spans "
            "that carry explicit AI-like markers."
        )
        if action not in seen:
            actions.append(action)

    if not actions:
        actions.append("No strong AI-like signal was isolated; review only flagged spans.")
    return actions


def _scan_ai_marker_spans(
    text: str,
    lang: str,
    *,
    max_spans: int = 12,
) -> list[dict[str, Any]]:
    try:
        markers_mod = _lazy_import("texthumanize.ai_markers")
        markers = markers_mod.load_ai_markers(lang)
        if not markers and lang != "en":
            markers = markers_mod.load_ai_markers("en")
    except Exception:
        return []

    candidates: list[tuple[str, str]] = []
    for category, values in markers.items():
        for marker in values:
            marker_text = str(marker).strip()
            if len(marker_text) >= 3:
                candidates.append((marker_text, str(category)))

    spans: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    candidates.sort(key=lambda item: (len(item[0]), item[0].lower()), reverse=True)

    for marker, category in candidates:
        if len(spans) >= max_spans:
            break
        escaped = re.escape(marker)
        if marker[0].isalnum() and marker[-1].isalnum():
            pattern = rf"(?<![\w-]){escaped}(?![\w-])"
        else:
            pattern = escaped
        try:
            matches = re.finditer(pattern, text, flags=re.IGNORECASE)
        except re.error:
            continue
        for match in matches:
            key = (match.start(), match.end(), "ai_marker")
            if key in seen:
                continue
            seen.add(key)
            spans.append({
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0),
                "kind": "ai_marker",
                "category": category,
                "severity": "medium",
                "reason": f"Known AI-marker {category}",
                "suggested_action": (
                    "Rewrite the phrase in a more specific, context-aware way."
                ),
            })
            if len(spans) >= max_spans:
                break

    return sorted(spans, key=lambda span: (span["start"], span["end"]))


def _sentence_ai_report(
    text: str,
    lang: str,
    *,
    max_highlights: int = 12,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        sentences = detect_ai_sentences(text, lang=lang)
    except Exception as exc:
        return [], [{
            "type": "sentence_report_error",
            "severity": "info",
            "message": f"Sentence-level detector unavailable: {exc}",
        }]

    highlights: list[dict[str, Any]] = []
    for sentence in sentences:
        score = _safe_float(sentence.get("ai_probability"))
        sentence["severity"] = _severity(score)
        if len(highlights) < max_highlights and (
            sentence.get("label") != "human" or score >= 0.34
        ):
            highlights.append({
                "start": sentence["start"],
                "end": sentence["end"],
                "text": sentence["text"],
                "kind": "sentence_ai_signal",
                "severity": _severity(score),
                "score": round(score, 4),
                "label": sentence.get("label", "unknown"),
                "reason": "Sentence-level AI probability is elevated.",
                "suggested_action": (
                    "Edit this sentence first and preserve surrounding context."
                ),
            })

    return highlights, sentences


def _mixed_content_report(text: str, lang: str) -> dict[str, Any]:
    try:
        segments = detect_ai_mixed(text, lang=lang)
    except Exception as exc:
        return {
            "segments": [],
            "shares": {"human": 0.0, "mixed": 0.0, "ai": 0.0},
            "error": str(exc),
        }

    total_chars = max(1, sum(len(segment.get("text", "")) for segment in segments))
    shares = {"human": 0.0, "mixed": 0.0, "ai": 0.0}
    for segment in segments:
        label = str(segment.get("label", "mixed"))
        if label not in shares:
            label = "mixed"
        shares[label] += len(segment.get("text", "")) / total_chars

    return {
        "segments": segments,
        "shares": {key: round(value, 4) for key, value in shares.items()},
    }


def _normal_p_value_from_z(z_score: float) -> float:
    return 0.5 * math.erfc(z_score / math.sqrt(2.0))


def _watermark_category(kind: str) -> str:
    if "zero_width" in kind or "unicode" in kind or "homoglyph" in kind:
        return "unicode"
    if "spacing" in kind:
        return "spacing"
    if "metadata" in kind or "provenance" in kind:
        return "metadata"
    if "statistical" in kind or "kirchenbauer" in kind:
        return "statistical"
    return "unknown"


def _codepoint(ch: str) -> str:
    return f"U+{ord(ch):04X}"


def _watermark_spans(text: str, report: Any, wm_mod: Any) -> list[dict[str, Any]]:
    zero_width_chars = set(getattr(wm_mod, "_ZERO_WIDTH_CHARS", set()))
    spans: list[dict[str, Any]] = []

    for index, ch in enumerate(text):
        if ch in zero_width_chars:
            spans.append({
                "start": index,
                "end": index + 1,
                "text": ch,
                "kind": "zero_width_character",
                "category": "unicode",
                "severity": "high",
                "codepoint": _codepoint(ch),
                "unicode_name": unicodedata.name(ch, "UNKNOWN"),
                "safe_replacement": "",
                "safe_action": "remove",
            })
            continue

        category = unicodedata.category(ch)
        if category == "Cf" and ch not in ("\n", "\r", "\t", " "):
            spans.append({
                "start": index,
                "end": index + 1,
                "text": ch,
                "kind": "invisible_unicode",
                "category": "unicode",
                "severity": "high",
                "codepoint": _codepoint(ch),
                "unicode_name": unicodedata.name(ch, "UNKNOWN"),
                "safe_replacement": "",
                "safe_action": "remove",
            })

    cleaned_index_to_original = [
        index for index, ch in enumerate(text) if ch not in zero_width_chars
    ]
    for original, expected, position in getattr(report, "homoglyphs_found", []):
        original_index = None
        if 0 <= position < len(cleaned_index_to_original):
            original_index = cleaned_index_to_original[position]
        else:
            found_at = text.find(original)
            if found_at >= 0:
                original_index = found_at
        if original_index is None:
            continue
        spans.append({
            "start": original_index,
            "end": original_index + len(original),
            "text": original,
            "kind": "homoglyph_substitution",
            "category": "unicode",
            "severity": "high",
            "codepoint": _codepoint(original),
            "unicode_name": unicodedata.name(original, "UNKNOWN"),
            "safe_replacement": expected,
            "safe_action": "replace",
        })

    return sorted(spans, key=lambda span: (span["start"], span["end"], span["kind"]))


def _text_diff(original: str, revised: str, *, max_changes: int = 20) -> list[dict[str, Any]]:
    # Fast path: when nothing changed (the common case for clean text) skip the
    # SequenceMatcher entirely — on long, highly repetitive inputs it can take
    # tens of seconds for an empty diff.
    if original == revised:
        return []
    changes: list[dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(a=original, b=revised, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append({
            "op": tag,
            "original_start": i1,
            "original_end": i2,
            "revised_start": j1,
            "revised_end": j2,
            "original": original[i1:i2],
            "replacement": revised[j1:j2],
        })
        if len(changes) >= max_changes:
            break
    return changes


def _is_green_hypothesis(
    tokens: list[str],
    index: int,
    *,
    scheme_id: int,
    gamma: float,
    window: int,
) -> bool:
    start = max(0, index - window)
    context = " ".join(tokens[start:index])
    current = tokens[index]
    seed = hashlib.sha256(
        f"{scheme_id}:{window}:{context}".encode("utf-8", errors="ignore")
    ).digest()
    # Deterministic PRNG for scheme rotation — not security-sensitive.
    current_hash = hashlib.md5(
        f"{scheme_id}:{current}".encode("utf-8", errors="ignore"),
        usedforsecurity=False,
    ).digest()
    rotated = ((current_hash[0] / 256.0) + (seed[0] / 256.0)) % 1.0
    return rotated < gamma


# A few thousand tokens give overwhelming statistical power for a z-test
# (std ~ sqrt(0.25 * N); at N=4000 a 3% green-ratio deviation already yields
# z ~ 3.8). Capping the scan keeps watermark detection O(1) in document length
# instead of growing to tens of seconds on very long inputs.
_MAX_STAT_TOKENS = 4000


def _statistical_watermark_hypotheses(text: str) -> dict[str, Any]:
    tokens = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    if len(tokens) < 10:
        return {
            "tested": 0,
            "best": None,
            "results": [],
            "note": "Need at least 10 tokens for a statistical hypothesis scan.",
        }
    truncated = len(tokens) > _MAX_STAT_TOKENS
    if truncated:
        tokens = tokens[:_MAX_STAT_TOKENS]

    results: list[dict[str, Any]] = []
    for gamma in (0.25, 0.50, 0.75):
        for window in (1, 2, 3):
            for scheme_id in range(8):
                green_count = 0
                total = 0
                for index in range(window, len(tokens)):
                    total += 1
                    if _is_green_hypothesis(
                        tokens,
                        index,
                        scheme_id=scheme_id,
                        gamma=gamma,
                        window=window,
                    ):
                        green_count += 1
                if total < 5:
                    continue
                expected = gamma * total
                std = math.sqrt(gamma * (1.0 - gamma) * total)
                if std == 0:
                    continue
                z_score = (green_count - expected) / std
                p_value = _normal_p_value_from_z(z_score)
                results.append({
                    "gamma": gamma,
                    "ngram_window": window,
                    "hash_scheme": scheme_id,
                    "green_ratio": round(green_count / total, 4),
                    "z_score": round(z_score, 4),
                    "p_value": round(p_value, 6),
                    "tokens_analyzed": total,
                })

    results.sort(key=lambda item: item["z_score"], reverse=True)
    best = results[0] if results else None
    if best is None:
        confidence = 0.0
    else:
        confidence = 1.0 / (1.0 + math.exp(-1.5 * (best["z_score"] - 2.0)))
    return {
        "tested": len(results),
        "best": best,
        "results": results[:8],
        "confidence": round(_clamp(confidence), 4),
        "tokens_capped": truncated,
        "max_tokens": _MAX_STAT_TOKENS,
    }


def _watermark_findings(report: Any, statistical: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    details = list(getattr(report, "details", []) or [])
    for index, kind in enumerate(getattr(report, "watermark_types", []) or []):
        detail = details[index] if index < len(details) else kind.replace("_", " ")
        category = _watermark_category(kind)
        findings.append({
            "type": kind,
            "category": category,
            "severity": "high" if category == "unicode" else "medium",
            "message": detail,
            "safe_action": "remove_or_replace" if category == "unicode" else "review",
        })

    verdict = str(statistical.get("verdict", "no_watermark"))
    if verdict != "no_watermark":
        findings.append({
            "type": "statistical_watermark",
            "category": "statistical",
            "severity": "high" if verdict == "strong_watermark" else "medium",
            "message": (
                f"Statistical watermark hypothesis: {verdict}, "
                f"z={statistical.get('z_score')}, p={statistical.get('p_value')}"
            ),
            "safe_action": "review_or_aggressive_neutralise",
        })

    best = (statistical.get("hypotheses") or {}).get("best")
    if best and _safe_float(best.get("z_score")) >= 3.0:
        findings.append({
            "type": "statistical_hypothesis",
            "category": "statistical",
            "severity": "medium",
            "message": (
                f"Best gamma/window/hash scan: gamma={best['gamma']}, "
                f"window={best['ngram_window']}, z={best['z_score']}"
            ),
            "safe_action": "review",
        })

    return findings


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
        lang = _detect_language(text)

    det = _get_detectors()
    result = det.detect_ai(text, lang=lang)

    # Enhance with statistical detector
    try:
        sd = _get_stat_detector()
        stat_result = sd.detect_ai_statistical(text, lang=lang)
        stat_prob = stat_result.get("probability", 0.5)
    except Exception:
        stat_prob = None

    # Enhance with neural MLP detector (35→64→32→1)
    neural_prob = None
    neural_details: dict = {}
    try:
        nd_mod = _get_neural_detector()
        nd = nd_mod.NeuralAIDetector()
        neural_result = nd.detect(text, lang=lang)
        neural_prob = neural_result.get("score")
        neural_details = {
            "neural_score": neural_prob,
            "neural_verdict": neural_result.get("verdict"),
            "neural_confidence": neural_result.get("confidence"),
            "neural_top_features": neural_result.get("top_features"),
        }
    except Exception:
        pass

    # Enhance with neural perplexity (character-level LSTM)
    # Use max_chars=500 — sufficient for accurate perplexity estimation
    # while being ~4x faster than 2000. Score is derived from perplexity
    # without a second forward pass.
    neural_ppl = None
    neural_ppl_score = None
    try:
        nlm_mod = _get_neural_lm()
        nlm = nlm_mod.get_neural_lm()
        neural_ppl = nlm.perplexity(text, max_chars=500)
        # Inline score computation (avoids second forward pass)
        neural_ppl_score = max(0.0, min(1.0,
            1.0 / (1.0 + __import__('math').exp(0.8 * (neural_ppl - 4.5)))))
    except Exception:
        pass

    # Ensemble: weighted merge of 3 signals
    # Neural trained MLP is most accurate for EN/RU (trained on those).
    # For other languages, heuristic+stat get higher weight since the
    # neural model may not generalise well.
    heuristic_score = result.ai_probability
    stat_score = stat_prob if stat_prob is not None else heuristic_score
    neural_score = neural_prob if neural_prob is not None else heuristic_score

    _neural_trained_langs = {"en", "ru"}
    if lang in _neural_trained_langs:
        # High confidence in neural model for trained languages
        combined_score = (
            heuristic_score * 0.05
            + stat_score * 0.15
            + neural_score * 0.80
        )
    else:
        # For other languages: boost heuristic + stat weight
        combined_score = (
            heuristic_score * 0.35
            + stat_score * 0.30
            + neural_score * 0.35
        )

    return {
        "score": combined_score,
        "heuristic_score": result.ai_probability,
        "combined_score": combined_score,
        "stat_probability": stat_prob,
        "neural_probability": neural_prob,
        "neural_perplexity": neural_ppl,
        "neural_perplexity_score": neural_ppl_score,
        "verdict": (
            "ai" if combined_score > 0.55 else
            "mixed" if combined_score > 0.34 else
            "human"
        ),
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
        "neural_details": neural_details,
        "explanations": result.explanations,
        "domain": result.detected_domain,
        "lang": lang,
    }


def detect_ai_explain(
    text: str,
    lang: str = "auto",
    *,
    include_sentences: bool = True,
    max_highlights: int = 12,
) -> dict:
    """Explain AI-detection risk with calibrated score and actionable spans.

    The result keeps the raw detector output but adds a Promopilot-ready layer:
    score, verdict, confidence, highlighted_spans, reasons, suggested_actions,
    metric contributions, length calibration and confidence interval.
    """
    if not isinstance(text, str):
        raise ConfigError(f"Expected str, got {type(text).__name__}")
    if not text or not text.strip():
        bucket = _ai_length_bucket(text)
        return {
            "schema_version": "text-humanize.ai_explain.v1",
            "score": 0.0,
            "raw_score": 0.0,
            "calibrated_score": 0.0,
            "verdict": "human",
            "raw_verdict": "human",
            "confidence": 0.0,
            "confidence_interval": _confidence_interval(0.0, 0.0, bucket),
            "length_bucket": bucket,
            "lang": lang,
            "domain": None,
            "metric_contributions": [],
            "reasons": [],
            "highlighted_spans": [],
            "sentence_report": [],
            "mixed_content": {"segments": [], "shares": {"human": 0.0, "mixed": 0.0, "ai": 0.0}},
            "suggested_actions": ["Provide non-empty text for a reliable audit."],
            "raw_detection": {},
        }

    detection = detect_ai(text, lang=lang)
    detected_lang = str(detection.get("lang") or lang)
    metrics = dict(detection.get("metrics") or {})
    raw_score = _clamp(_safe_float(detection.get("score")))
    confidence = _clamp(_safe_float(detection.get("confidence")))
    bucket = _ai_length_bucket(text)
    calibrated_score, calibration = _calibrate_detector_score(
        raw_score,
        bucket,
        detection.get("domain"),
        metrics,
    )
    signals = _metric_contributions(metrics)
    reasons = _ai_reasons(detection, signals)

    highlighted_spans = _scan_ai_marker_spans(
        text,
        detected_lang,
        max_spans=max_highlights,
    )
    if include_sentences:
        sentence_highlights, sentence_report = _sentence_ai_report(
            text,
            detected_lang,
            max_highlights=max(0, max_highlights - len(highlighted_spans)),
        )
        highlighted_spans.extend(sentence_highlights)
    else:
        sentence_report = []

    highlighted_spans = sorted(
        highlighted_spans[:max_highlights],
        key=lambda span: (span.get("start", 0), span.get("end", 0)),
    )

    return {
        "schema_version": "text-humanize.ai_explain.v1",
        "score": round(calibrated_score, 4),
        "raw_score": round(raw_score, 4),
        "calibrated_score": round(calibrated_score, 4),
        "verdict": _detector_verdict(calibrated_score),
        "raw_verdict": detection.get("verdict", "unknown"),
        "confidence": confidence,
        "confidence_interval": _confidence_interval(calibrated_score, confidence, bucket),
        "length_bucket": bucket,
        "length_calibration": calibration,
        "lang": detected_lang,
        "domain": detection.get("domain"),
        "metric_contributions": signals,
        "metrics": metrics,
        "reasons": reasons,
        "highlighted_spans": highlighted_spans,
        "sentence_report": sentence_report,
        "mixed_content": _mixed_content_report(text, detected_lang),
        "suggested_actions": _unique_actions(signals, detection.get("domain")),
        "raw_detection": detection,
    }


def detect_ai_fast(text: str, lang: str = "auto") -> dict:
    """Fast AI detection using only the neural MLP.

    ~3-5x faster than full detect_ai() — skips heuristic analysis,
    statistical detector, and character-level LSTM. Uses only the
    trained MLP (which accounts for 80% of the combined score).
    Suitable for in-the-loop detection where speed matters more than
    detailed metrics.

    Returns:
        dict with ``combined_score``, ``verdict``, ``confidence``.
    """
    if not text or not text.strip():
        return {"combined_score": 0.0, "verdict": "human", "confidence": 0.0}

    if lang == "auto":
        lang = _detect_language(text)

    try:
        nd_mod = _get_neural_detector()
        nd = nd_mod.NeuralAIDetector()
        neural_result = nd.detect(text, lang=lang)
        score = neural_result.get("score", 0.5)
    except Exception:
        score = 0.5

    return {
        "combined_score": score,
        "verdict": (
            "ai" if score > 0.55 else
            "mixed" if score > 0.34 else
            "human"
        ),
        "confidence": min(abs(score - 0.5) * 2.0, 1.0),
    }


def detect_ai_batch(texts: list[str], lang: str = "auto") -> list[DetectionReport]:
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
    text, start, end, leading_ws, trailing_ws, ai_probability,
    label ("human"/"mixed"/"ai").

    Contract note: ``text`` is stripped of surrounding whitespace while
    ``[start:end]`` spans the original slice including that whitespace, so
    for adjacent sentences ``end == next start``. Consumers that rejoin
    sentences from ``text`` must reattach ``leading_ws`` and ``trailing_ws``
    (or slice the source by offsets) or inter-sentence spacing is lost.

    Args:
        text: Text to analyse.
        lang: Language code (or "auto").
        window: Sliding window size in sentences.
    """
    mod = _get_detectors()
    detector = mod.AIDetector(lang=lang)
    results = detector.detect_sentences(text, lang=lang, window=window)
    sentences: list[dict] = []
    for r in results:
        raw = text[r.start:r.end]
        sentences.append({
            "text": r.text,
            "start": r.start,
            "end": r.end,
            "leading_ws": raw[:len(raw) - len(raw.lstrip())],
            "trailing_ws": raw[len(raw.rstrip()):],
            "ai_probability": r.ai_probability,
            "label": r.label,
        })
    return sentences


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
        lang = _detect_language(text)
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
        lang = _detect_language(text)

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
        lang = _detect_language(text)
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
        lang = _detect_language(text)

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
        lang = _detect_language(text)
    return str(_get_watermark().clean_watermarks(text, lang=lang))


def watermark_report(
    text: str,
    lang: str = "auto",
    *,
    include_statistical: bool = True,
    aggressive: bool = False,
    intensity: float = 0.6,
    seed: int | None = None,
) -> dict:
    """Return a unified Unicode + statistical watermark audit report.

    The safe branch removes invisible Unicode, homoglyph and metadata markers.
    The aggressive branch is optional and may apply lexical substitutions through
    Watermark Forensics for statistical watermark neutralisation.
    """
    if not isinstance(text, str):
        raise ConfigError(f"Expected str, got {type(text).__name__}")
    max_length = 1_000_000
    if len(text) > max_length:
        raise InputTooLargeError(len(text), max_length)

    if lang == "auto":
        lang = _detect_language(text) if text.strip() else "en"

    wm_mod = _get_watermark()
    unicode_report = wm_mod.detect_watermarks(text, lang=lang)
    spans = _watermark_spans(text, unicode_report, wm_mod)
    diff = _text_diff(text, unicode_report.cleaned_text)

    statistical: dict[str, Any] = {
        "enabled": include_statistical,
        "verdict": "no_watermark",
        "z_score": 0.0,
        "p_value": 1.0,
        "confidence": 0.0,
        "green_ratio": None,
        "tokens_analyzed": 0,
        "hash_schemes_tested": 0,
        "hypotheses": _statistical_watermark_hypotheses(text)
        if include_statistical else {"tested": 0, "best": None, "results": []},
    }
    aggressive_result = None

    if include_statistical:
        try:
            wf_mod = _lazy_import("texthumanize.watermark_forensics")
            forensics = wf_mod.WatermarkForensics(lang=lang, seed=seed)
            forensic = forensics.detect(text)
            z_score = _safe_float(getattr(forensic, "watermark_strength", 0.0))
            statistical.update({
                "verdict": forensic.verdict,
                "z_score": round(z_score, 4),
                "p_value": round(_normal_p_value_from_z(z_score), 6),
                "confidence": _clamp(_safe_float(getattr(forensic, "confidence", 0.0))),
                "green_ratio": getattr(forensic, "green_ratio", None),
                "tokens_analyzed": getattr(forensic, "tokens_analyzed", 0),
                "hash_schemes_tested": getattr(forensic, "hash_schemes_tested", 0),
            })
            if aggressive:
                neutralised = forensics.neutralise(text, intensity=intensity)
                aggressive_result = {
                    "text": neutralised.text,
                    "changed": neutralised.text != text,
                    "tokens_neutralised": neutralised.tokens_neutralised,
                    "green_ratio_before": neutralised.green_ratio,
                    "green_ratio_after": neutralised.green_ratio_after,
                    "changes": neutralised.changes,
                    "diff": _text_diff(text, neutralised.text),
                }
        except Exception as exc:
            statistical["error"] = str(exc)

    best_hypothesis = (statistical.get("hypotheses") or {}).get("best") or {}
    best_hypothesis_z = _safe_float(best_hypothesis.get("z_score"))
    hypothesis_confidence = _safe_float((statistical.get("hypotheses") or {}).get("confidence"))
    if best_hypothesis_z < 3.0:
        hypothesis_confidence = min(hypothesis_confidence, 0.35)
    statistical_confidence = max(_safe_float(statistical.get("confidence")), hypothesis_confidence)
    unicode_confidence = _safe_float(getattr(unicode_report, "confidence", 0.0))
    kirchenbauer_z = _safe_float(getattr(unicode_report, "kirchenbauer_score", 0.0))
    if kirchenbauer_z > 0:
        statistical_confidence = max(statistical_confidence, min(1.0, kirchenbauer_z / 5.0))

    watermark_types = set(getattr(unicode_report, "watermark_types", []) or [])
    # Only treat the statistical channel as a positive finding at a meaningful
    # z-score. A "possible_watermark" verdict (z 1.5-2.0) is reported in the
    # statistical detail but must not flip has_watermarks on otherwise clean
    # text — that produced false positives on ordinary prose.
    if _safe_float(statistical.get("z_score")) >= 2.0 and str(
        statistical.get("verdict")
    ) not in ("no_watermark", "possible_watermark"):
        watermark_types.add("statistical_watermark")
    best = (statistical.get("hypotheses") or {}).get("best")
    if best and _safe_float(best.get("z_score")) >= 3.0:
        watermark_types.add("statistical_hypothesis")

    risk_score = max(unicode_confidence, statistical_confidence)
    findings = _watermark_findings(unicode_report, statistical)

    suggested_actions = [
        "Use clean_safe.text for publishing when only Unicode or metadata markers are present.",
        "Review highlighted_spans before replacing homoglyphs in brand names or code.",
    ]
    if statistical_confidence >= 0.50:
        suggested_actions.append(
            "For statistical signals, compare clean_safe.text and neutralise_aggressive.text before accepting lexical changes."
        )
    if not findings:
        suggested_actions = ["No watermark evidence was found; keep the original text."]

    return {
        "schema_version": "text-humanize.watermark_report.v1",
        "has_watermarks": bool(watermark_types),
        "risk_score": round(_clamp(risk_score), 4),
        "confidence": round(_clamp(risk_score), 4),
        "lang": lang,
        "watermark_types": sorted(watermark_types),
        "findings": findings,
        "highlighted_spans": spans,
        "unicode": {
            "has_watermarks": bool(getattr(unicode_report, "has_watermarks", False)),
            "watermark_types": list(getattr(unicode_report, "watermark_types", []) or []),
            "details": list(getattr(unicode_report, "details", []) or []),
            "characters_removed": getattr(unicode_report, "characters_removed", 0),
            "zero_width_count": getattr(unicode_report, "zero_width_count", 0),
            "homoglyphs_found": [
                {
                    "original": original,
                    "replacement": replacement,
                    "position": position,
                }
                for original, replacement, position
                in getattr(unicode_report, "homoglyphs_found", []) or []
            ],
            "kirchenbauer_z_score": getattr(unicode_report, "kirchenbauer_score", 0.0),
            "kirchenbauer_p_value": getattr(unicode_report, "kirchenbauer_p_value", 1.0),
        },
        "statistical": statistical,
        "safe_cleaned_text": unicode_report.cleaned_text,
        "clean_safe": {
            "text": unicode_report.cleaned_text,
            "changed": unicode_report.cleaned_text != text,
            "diff": diff,
        },
        "neutralise_aggressive": aggressive_result,
        "suggested_actions": suggested_actions,
    }


def watermark_report_batch(
    texts: list[str],
    lang: str = "auto",
    *,
    include_statistical: bool = True,
    aggressive: bool = False,
) -> list[dict]:
    """Batch wrapper for watermark_report()."""
    return [
        watermark_report(
            text,
            lang=lang,
            include_statistical=include_statistical,
            aggressive=aggressive,
        )
        for text in texts
    ]


def clean_safe(text: str, lang: str = "auto") -> str:
    """Safely remove Unicode/metadata watermarks without lexical rewriting."""
    return clean_watermarks(text, lang=lang)


def neutralise_aggressive(
    text: str,
    lang: str = "auto",
    *,
    intensity: float = 0.6,
    seed: int | None = None,
) -> str:
    """Aggressively neutralise statistical watermark signals."""
    result = neutralise_watermark(text, lang=lang, intensity=intensity, seed=seed)
    return str(getattr(result, "text", text))


def audit_report(
    text: str,
    lang: str = "auto",
    *,
    aggressive_watermark: bool = False,
) -> dict:
    """Combined AI and watermark audit report for product integrations."""
    ai = detect_ai_explain(text, lang=lang)
    resolved_lang = str(ai.get("lang") or lang)
    watermark = watermark_report(
        text,
        lang=resolved_lang,
        aggressive=aggressive_watermark,
    )
    actions: list[str] = []
    for action in list(ai.get("suggested_actions", [])) + list(watermark.get("suggested_actions", [])):
        if action not in actions:
            actions.append(action)
        if len(actions) >= 10:
            break

    return {
        "schema_version": "text-humanize.audit_report.v1",
        "lang": resolved_lang,
        "score": round(max(_safe_float(ai.get("score")), _safe_float(watermark.get("risk_score"))), 4),
        "ai": ai,
        "watermark": watermark,
        "suggested_actions": actions,
    }


# ═════════════════════════════════════════════════════════════
#  UNIFIED QUALITY SCORE
# ═════════════════════════════════════════════════════════════

_QUALITY_GRADE_BANDS: tuple[tuple[float, str], ...] = (
    (0.90, "A+"),
    (0.82, "A"),
    (0.74, "B"),
    (0.64, "C"),
    (0.52, "D"),
    (0.0, "F"),
)

# Default contribution weights for the composite score. The "full" set is
# used when a reference (pre-humanization) text is supplied; otherwise
# semantic_similarity and change_ratio are dropped and the rest renormalised.
_QUALITY_WEIGHTS: dict[str, float] = {
    "semantic_similarity": 0.26,
    "naturalness": 0.22,
    "ai_pattern_risk": 0.20,
    "readability": 0.12,
    "watermark_risk": 0.10,
    "change_ratio": 0.06,
    "speed": 0.04,
}

_QUALITY_LABELS: dict[str, str] = {
    "semantic_similarity": "Semantic similarity",
    "naturalness": "Naturalness",
    "ai_pattern_risk": "AI-pattern resistance",
    "readability": "Readability",
    "watermark_risk": "Watermark cleanliness",
    "change_ratio": "Edit balance",
    "speed": "Processing speed",
}


def _quality_grade(score: float) -> str:
    for threshold, grade in _QUALITY_GRADE_BANDS:
        if score >= threshold:
            return grade
    return "F"


def _quality_verdict(score: float) -> str:
    if score >= 0.82:
        return "excellent"
    if score >= 0.68:
        return "good"
    if score >= 0.52:
        return "fair"
    return "poor"


def _text_similarity(original: str, revised: str) -> float:
    """Blended lexical similarity (Jaccard + sequence ratio), 0..1."""
    if original == revised:
        return 1.0
    if not original or not revised:
        return 0.0
    orig_words = original.lower().split()
    new_words = revised.lower().split()
    if not orig_words or not new_words:
        return 0.0
    orig_set = set(orig_words)
    new_set = set(new_words)
    union = orig_set | new_set
    jaccard = len(orig_set & new_set) / len(union) if union else 1.0
    seq = difflib.SequenceMatcher(None, orig_words, new_words).ratio()
    return _clamp(0.5 * jaccard + 0.5 * seq)


def _readability_quality(grade_level: float) -> float:
    """Map a Flesch-Kincaid grade level to a 0..1 readability quality score.

    Broadly accessible prose (grade ~9) maps to ~1.0; very low or very high
    grade levels are penalised on a 12-grade tolerance window.
    """
    if grade_level <= 0:
        return 0.6  # degenerate / too short to grade reliably
    return _clamp(1.0 - abs(grade_level - 9.0) / 12.0)


def _change_balance_quality(change_ratio: float) -> float:
    """Reward meaningful-but-not-destructive editing (0..1)."""
    if change_ratio <= 0.0:
        return 0.55  # nothing changed — neutral, not ideal
    if change_ratio < 0.08:
        return _clamp(0.6 + change_ratio / 0.08 * 0.4)
    if change_ratio <= 0.32:
        return 1.0  # sweet spot
    if change_ratio < 0.60:
        return _clamp(1.0 - (change_ratio - 0.32) / 0.28)
    return _clamp(0.5 * (1.0 - (change_ratio - 0.60) / 0.40))


def _quality_recommendations(dimensions: dict[str, Any]) -> list[str]:
    recs: list[str] = []

    def _dim(name: str) -> dict[str, Any]:
        return dimensions.get(name) or {}

    if _safe_float(_dim("ai_pattern_risk").get("raw_risk")) >= 0.5:
        recs.append(
            "AI-pattern risk is elevated; run humanize() (try a higher "
            "intensity or the strict quality gate) and re-check."
        )
    if _safe_float(_dim("watermark_risk").get("raw_risk")) >= 0.4:
        recs.append(
            "Watermark signals detected; review watermark_report() and "
            "publish clean_safe.text."
        )
    if "semantic_similarity" in dimensions and _safe_float(
        _dim("semantic_similarity").get("value")
    ) < 0.55:
        recs.append(
            "Semantic similarity to the reference is low; lower intensity or "
            "enable minimal mode to preserve meaning."
        )
    if _safe_float(_dim("naturalness").get("value")) < 0.6:
        recs.append(
            "Naturalness is below target; vary sentence length and reduce "
            "bureaucratic connectors."
        )
    if _safe_float(_dim("readability").get("value")) < 0.55:
        recs.append(
            "Readability is outside the accessible band; split long sentences "
            "or simplify vocabulary for the target audience."
        )
    if "change_ratio" in dimensions and _safe_float(
        _dim("change_ratio").get("raw_change_ratio")
    ) > 0.5:
        recs.append(
            "Edit volume is high relative to the reference; consider minimal "
            "mode to reduce drift."
        )
    if not recs:
        recs.append("Quality is in a healthy range; no corrective action needed.")
    return recs


def quality_score_report(
    text: str,
    original: str | None = None,
    lang: str = "auto",
    *,
    weights: dict[str, float] | None = None,
    fast: bool = False,
    target_chars_per_sec: float = 20000.0,
) -> dict:
    """Unified TextHumanize Quality Score across seven dimensions.

    Combines semantic similarity, naturalness, readability, AI-pattern risk,
    watermark risk, edit balance and processing speed into a single,
    explainable score (0..1) with a letter grade, strengths/weaknesses and
    actionable recommendations.

    Args:
        text: The text to score (typically the humanized output).
        original: Optional pre-humanization reference. When provided, the
            ``semantic_similarity`` and ``change_ratio`` dimensions are added;
            otherwise they are dropped and the remaining weights renormalised.
        lang: Language code or ``"auto"``.
        weights: Optional overrides for per-dimension contribution weights.
        fast: Use the lightweight detector and skip statistical watermark
            hypotheses for a faster, slightly coarser score.
        target_chars_per_sec: Throughput that maps to a perfect speed score.

    Returns:
        A ``text-humanize.quality_score.v1`` dict.
    """
    if not isinstance(text, str):
        raise ConfigError(f"Expected str, got {type(text).__name__}")

    started = time.perf_counter()

    if not text or not text.strip():
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "schema_version": "text-humanize.quality_score.v1",
            "score": 0.0,
            "score_100": 0.0,
            "grade": "F",
            "verdict": "poor",
            "lang": lang if lang != "auto" else "en",
            "has_reference": original is not None,
            "dimensions": {},
            "strengths": [],
            "weaknesses": [],
            "recommendations": [
                "Provide non-empty text to compute a quality score."
            ],
            "timing": {"latency_ms": round(elapsed_ms, 3), "chars_per_sec": 0.0},
        }

    resolved_lang = lang
    if lang == "auto":
        resolved_lang = _detect_language(text)

    report = analyze(text, lang=resolved_lang)
    artificiality = _clamp(
        _safe_float(getattr(report, "artificiality_score", 0.0)) / 100.0
    )
    naturalness = _clamp(1.0 - artificiality)
    readability = _readability_quality(
        _safe_float(getattr(report, "flesch_kincaid_grade", 0.0))
    )

    if fast:
        ai = detect_ai_fast(text, lang=resolved_lang)
        ai_risk = _clamp(_safe_float(ai.get("combined_score")))
        ai_verdict = ai.get("verdict")
        ai_source = "detect_ai_fast"
    else:
        ai = detect_ai_explain(
            text, lang=resolved_lang, include_sentences=False
        )
        ai_risk = _clamp(_safe_float(ai.get("score")))
        ai_verdict = ai.get("verdict")
        ai_source = "detect_ai_explain"

    wm = watermark_report(
        text, lang=resolved_lang, include_statistical=not fast
    )
    watermark_risk = _clamp(_safe_float(wm.get("risk_score")))

    dimensions: dict[str, Any] = {}

    if original is not None:
        sim = _text_similarity(original, text)
        change_result = HumanizeResult(
            original=original,
            text=text,
            lang=resolved_lang,
            profile="web",
            intensity=60,
        )
        change = change_result.change_ratio
        dimensions["semantic_similarity"] = {
            "label": _QUALITY_LABELS["semantic_similarity"],
            "value": round(sim, 4),
            "detail": "Lexical + sequence similarity vs. the reference text.",
        }
        dimensions["change_ratio"] = {
            "label": _QUALITY_LABELS["change_ratio"],
            "value": round(_change_balance_quality(change), 4),
            "raw_change_ratio": round(change, 4),
            "detail": "Editing should be meaningful but not destructive.",
        }

    dimensions["naturalness"] = {
        "label": _QUALITY_LABELS["naturalness"],
        "value": round(naturalness, 4),
        "artificiality_score": round(
            _safe_float(getattr(report, "artificiality_score", 0.0)), 2
        ),
        "detail": "Inverse of the artificiality score from analyze().",
    }
    dimensions["readability"] = {
        "label": _QUALITY_LABELS["readability"],
        "value": round(readability, 4),
        "flesch_kincaid_grade": round(
            _safe_float(getattr(report, "flesch_kincaid_grade", 0.0)), 2
        ),
        "detail": "Closeness to a broadly accessible reading grade.",
    }
    dimensions["ai_pattern_risk"] = {
        "label": _QUALITY_LABELS["ai_pattern_risk"],
        "value": round(_clamp(1.0 - ai_risk), 4),
        "raw_risk": round(ai_risk, 4),
        "verdict": ai_verdict,
        "source": ai_source,
        "detail": "Resistance to the built-in AI detector (higher is better).",
    }
    dimensions["watermark_risk"] = {
        "label": _QUALITY_LABELS["watermark_risk"],
        "value": round(_clamp(1.0 - watermark_risk), 4),
        "raw_risk": round(watermark_risk, 4),
        "has_watermarks": bool(wm.get("has_watermarks")),
        "detail": "Absence of Unicode/statistical watermark signals.",
    }

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    chars = len(text)
    chars_per_sec = (
        chars / (elapsed_ms / 1000.0) if elapsed_ms > 0 else float(chars)
    )
    speed_value = (
        _clamp(chars_per_sec / target_chars_per_sec)
        if target_chars_per_sec > 0
        else 1.0
    )
    dimensions["speed"] = {
        "label": _QUALITY_LABELS["speed"],
        "value": round(speed_value, 4),
        "chars_per_sec": round(chars_per_sec, 1),
        "latency_ms": round(elapsed_ms, 3),
        "detail": "Throughput relative to the target chars/sec.",
    }

    base_weights = dict(_QUALITY_WEIGHTS)
    if weights:
        for key, value in weights.items():
            base_weights[key] = float(value)
    active = {
        key: weight
        for key, weight in base_weights.items()
        if key in dimensions and weight > 0
    }
    total_weight = sum(active.values()) or 1.0
    composite = 0.0
    for key, weight in active.items():
        normalised = weight / total_weight
        dimensions[key]["weight"] = round(normalised, 4)
        composite += _safe_float(dimensions[key]["value"]) * normalised
    for key in dimensions:
        dimensions[key].setdefault("weight", 0.0)

    composite = _clamp(composite)

    ranked = sorted(
        active,
        key=lambda key: _safe_float(dimensions[key]["value"]),
        reverse=True,
    )
    strengths = [
        dimensions[key]["label"]
        for key in ranked
        if _safe_float(dimensions[key]["value"]) >= 0.75
    ][:3]
    weaknesses = [
        dimensions[key]["label"]
        for key in reversed(ranked)
        if _safe_float(dimensions[key]["value"]) < 0.6
    ][:3]

    score_rounded = round(composite, 4)
    return {
        "schema_version": "text-humanize.quality_score.v1",
        "score": score_rounded,
        "score_100": round(score_rounded * 100.0, 1),
        "grade": _quality_grade(composite),
        "verdict": _quality_verdict(composite),
        "lang": resolved_lang,
        "has_reference": original is not None,
        "dimensions": dimensions,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": _quality_recommendations(dimensions),
        "timing": {
            "latency_ms": round(elapsed_ms, 3),
            "chars_per_sec": round(chars_per_sec, 1),
        },
    }


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
        lang = _detect_language(text)
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
        lang = _detect_language(text)
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
        lang = _detect_language(text)

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
        lang = _detect_language(text)

    analyzer = _new_text_analyzer(lang=lang)
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

    before_metrics = cast(dict[str, float], before["metrics"])
    after_metrics = cast(dict[str, float], after["metrics"])
    deltas: dict[str, float] = {}
    for key in before_metrics:
        deltas[key] = round(after_metrics[key] - before_metrics[key], 4)

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
    metrics = cast(dict[str, float], result["metrics"])

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
        lang = _detect_language(text)

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
        ).text

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
        lang = _detect_language(text)

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
        # Preserve the original inter-sentence whitespace (newlines, double
        # spaces) instead of normalising everything to a single space.
        leading_ws = sent_info.get("leading_ws", "")
        trailing_ws = sent_info.get("trailing_ws", " ")
        if leading_ws:
            processed_parts.append(leading_ws)

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
            # Re-score after humanization. The pipeline may split or merge
            # sentences, so aggregate over all result spans instead of
            # assuming the first span matches the processed sentence.
            re_sents = detect_ai_sentences(result.text, lang=lang)
            if re_sents:
                re_scores = [
                    s.get("ai_probability", ai_prob) for s in re_sents
                ]
                scores_after.append(sum(re_scores) / len(re_scores))
            else:
                scores_after.append(ai_prob)
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
        if trailing_ws:
            processed_parts.append(trailing_ws)

    final_text = "".join(processed_parts)

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
        lang = _detect_language(text)

    base_seed = seed if seed is not None else _rnd.randint(0, 2**31)
    results: list[dict[str, Any]] = []

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
    memory_limit_mb: float | None = None,
) -> Generator[dict[str, Any], None, None]:
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
        memory_limit_mb: Optional estimated active-window memory limit.

    Yields:
        Dict with: chunk, chunk_index, is_last, progress (0.0-1.0),
        original_chunk.
    """
    if lang == "auto":
        lang = _detect_language(text)

    limit_bytes = _memory_limit_bytes(memory_limit_mb)
    total_chars = len(text)
    processed_chars = 0
    total_chunks = _count_text_chunks(text, chunk_size)

    for i, chunk in enumerate(_iter_text_chunks(text, chunk_size)):
        _ensure_memory_window(
            _estimated_text_bytes(chunk),
            limit_bytes,
            "humanize_stream chunk",
        )
        result = humanize(
            chunk,
            lang=lang,
            profile=profile,
            intensity=intensity,
            preserve=preserve,
            seed=seed + i if seed is not None else None,
        )
        _ensure_memory_window(
            _estimated_text_bytes(chunk) + _estimated_text_bytes(result.text),
            limit_bytes,
            "humanize_stream result",
        )

        processed_chars += len(chunk)

        yield {
            "chunk": result.text,
            "chunk_index": i,
            "total_chunks": total_chunks,
            "is_last": i == total_chunks - 1,
            "progress": min(1.0, processed_chars / total_chars) if total_chars > 0 else 1.0,
            "original_chunk": chunk,
            "change_ratio": round(result.change_ratio, 4),
            "memory_bounded": {
                "enabled": memory_limit_mb is not None,
                "memory_limit_mb": memory_limit_mb,
                "chunk_size": chunk_size,
            },
        }


def anonymize_style(
    text: str,
    lang: str = "auto",
    target: StylisticFingerprint | str | None = None,
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
            ``'journalist'``, ``'blogger'``, ``'editor'``,
            ``'founder'``, ``'expert'``, ``'support'`` or RU aliases)
            или ``None`` (default = ``'journalist'``).
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
        detected_lang = _detect_language(text)

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


# ══════════════════════════════════════════════════════════════════
#  ASH™ — Adaptive Statistical Humanization
#  Proprietary technology by Oleksandr K. / TextHumanize
# ══════════════════════════════════════════════════════════════════

def ash_humanize(
    text: str,
    lang: str = "auto",
    *,
    preset: str = "balanced",
    intensity: float | None = None,
    seed: int | None = None,
    use_pipeline: bool = True,
    pipeline_intensity: int = 60,
    pipeline_profile: str = "web",
    corpus_profile: str | None = None,
) -> Any:
    """Гуманизировать текст через полный ASH™ конвейер.

    ASH™ (Adaptive Statistical Humanization) — проприетарная
    технология, объединяющая 5 методов + ядро пайплайна:

    1. Watermark Forensics™ — нейтрализация водяных знаков LLM
    2. Perplexity Sculpting™ — ремоделирование кривой перплексии
    3. Statistical Signature Transfer™ — перенос статистического отпечатка
    3½. **Base Pipeline** — 20-stage core humanization (typography,
        debureaucratization, paraphrasing, naturalization, etc.)
    4. Sentence Restructuring™ — структурная трансформация предложений
    5. Cognitive Load Modeling™ — моделирование когнитивных паттернов
    6. Adversarial Ensemble Self-Play™ — итеративная доводка

    Args:
        text: Текст для обработки.
        lang: Код языка ('auto', 'en', 'ru', 'uk').
        preset: Пресет: 'stealth', 'balanced', 'light', 'forensic', 'academic'.
        intensity: Интенсивность (0.0–1.0), перекрывает пресет.
        seed: Зерно RNG.
        use_pipeline: Использовать ядро пайплайна (рекомендуется).
        pipeline_intensity: Интенсивность ядра пайплайна (0-100).
        pipeline_profile: Профиль ядра пайплайна.
        corpus_profile: ASH corpus target profile. Defaults to pipeline_profile.

    Returns:
        ASHResult с полями: text, original_text, lang,
        watermark, perplexity, signature, cognitive, adversarial,
        elapsed_ms, steps_applied, methods_used.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.ash_engine")
    return mod.ASHEngine(
        lang=lang, seed=seed,
        pipeline_intensity=pipeline_intensity,
        pipeline_profile=pipeline_profile,
        corpus_profile=corpus_profile,
    ).humanize(
        text, preset=preset, intensity=intensity,
        use_pipeline=use_pipeline,
    )


def ash_analyze(
    text: str,
    lang: str = "auto",
    corpus_profile: str | None = None,
) -> dict:
    """Комплексный ASH™ анализ текста.

    Возвращает: watermark verdict, perplexity curve,
    signature distance, cognitive uniformity, problem map.

    Args:
        text: Текст для анализа.
        lang: Код языка.
        corpus_profile: ASH corpus target profile for signature distance.

    Returns:
        dict со всеми диагностиками ASH™.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.ash_engine")
    return mod.ASHEngine(lang=lang, corpus_profile=corpus_profile).analyze(text)


def sculpt_perplexity(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
) -> Any:
    """Perplexity Sculpting™ — ремоделирование кривой перплексии.

    Делает кривую перплексии похожей на человеческую: вводит
    контролируемые «сюрпризы» в слишком гладкие участки.

    Args:
        text: Текст для обработки.
        lang: Код языка.
        intensity: 0.0–1.0.
        seed: Зерно RNG.

    Returns:
        SculptResult.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.perplexity_sculptor")
    return mod.PerplexitySculptor(lang=lang, seed=seed).sculpt(text, intensity)


def transfer_signature(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
    corpus_profile: str | None = None,
) -> Any:
    """Statistical Signature Transfer™ — перенос статистического отпечатка.

    Сдвигает 30-мерный статистический отпечаток текста
    в зону человеческих текстов.

    Args:
        text: Текст для обработки.
        lang: Код языка.
        intensity: 0.0–1.0.
        seed: Зерно RNG.
        corpus_profile: ASH corpus target profile.

    Returns:
        TransferResult.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.signature_transfer")
    return mod.SignatureTransfer(
        lang=lang,
        seed=seed,
        corpus_profile=corpus_profile,
    ).transfer(text, intensity)


def detect_statistical_watermark(text: str, lang: str = "auto") -> Any:
    """Watermark Forensics™ — обнаружение статистических водяных знаков LLM.

    Обнаруживает Kirchenbauer-style green/red token bias
    по 8 хэш-схемам.

    Args:
        text: Текст для проверки.
        lang: Код языка.

    Returns:
        ForensicResult с verdict, z_score, green_ratio.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.watermark_forensics")
    return mod.WatermarkForensics(lang=lang).detect(text)


def neutralise_watermark(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
) -> Any:
    """Watermark Forensics™ — нейтрализация водяных знаков LLM.

    Заменяет «зелёные» токены на синонимы из «красной» зоны,
    разрушая статистический паттерн watermark.

    Args:
        text: Текст для обработки.
        lang: Код языка.
        intensity: 0.0–1.0.
        seed: Зерно RNG.

    Returns:
        ForensicResult.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.watermark_forensics")
    return mod.WatermarkForensics(lang=lang, seed=seed).neutralise(text, intensity)


def model_cognition(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    seed: int | None = None,
) -> Any:
    """Cognitive Load Modeling™ — моделирование когнитивных паттернов.

    Вносит человеческие «дефекты»: хеджи, самокоррекции,
    усталостное упрощение к концу текста.

    Args:
        text: Текст для обработки.
        lang: Код языка.
        intensity: 0.0–1.0.
        seed: Зерно RNG.

    Returns:
        CognitiveResult.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.cognitive_model")
    return mod.CognitiveModeler(lang=lang, seed=seed).model(text, intensity)


def adversarial_humanize(
    text: str,
    lang: str = "auto",
    intensity: float = 0.5,
    max_rounds: int = 4,
    target_score: float = 0.35,
    seed: int | None = None,
) -> Any:
    """Adversarial Ensemble Self-Play™ — итеративная гуманизация.

    Три детектора строят «карту проблем» по предложениям;
    точечные правки применяются только к помеченным предложениям;
    цикл повторяется до достижения target_score или max_rounds.

    Args:
        text: Текст для обработки.
        lang: Код языка.
        intensity: Базовая интенсивность (0.0–1.0).
        max_rounds: Максимум раундов.
        target_score: Целевой AI-score.
        seed: Зерно RNG.

    Returns:
        PlayResult.
    """
    if lang == "auto":
        lang = _detect_language(text)

    mod = _lazy_import("texthumanize.adversarial_play")
    return mod.AdversarialPlay(lang=lang, seed=seed).play(
        text, intensity=intensity,
        max_rounds=max_rounds, target_score=target_score,
    )


def list_ash_presets() -> dict:
    """Список доступных ASH™ пресетов.

    Returns:
        dict с конфигурацией каждого пресета:
        stealth, balanced, light, forensic, academic.
    """
    mod = _lazy_import("texthumanize.ash_engine")
    return mod.list_ash_presets()
