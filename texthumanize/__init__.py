"""TextHumanize — алгоритмическая гуманизация текста.

Преобразует автоматически сгенерированные тексты в естественные: нормализует типографику,
устраняет канцеляризмы, разнообразит структуру, повышает burstiness и perplexity.

Полные словари: RU, UK, EN, DE, FR, ES, PL, PT, IT.
Универсальный процессор: любой язык.
Профили: chat, web, seo, docs, formal.

Инструменты AI:
    - ``detect_ai()``       — проверка AI-генерации (12 метрик)
    - ``paraphrase()``      — перефразирование
    - ``analyze_tone()``    — тональный анализ
    - ``adjust_tone()``     — коррекция тональности
    - ``detect_watermarks()`` — обнаружение водяных знаков
    - ``clean_watermarks()``  — очистка водяных знаков
    - ``spin()``            — спиннинг текста
    - ``spin_variants()``   — генерация вариантов
    - ``analyze_coherence()`` — анализ когерентности
    - ``full_readability()``  — полная читабельность

Использование:
    >>> from texthumanize import humanize, analyze, detect_ai
    >>> result = humanize("Данный текст является примером.", lang="ru")
    >>> print(result.text)
    >>> ai = detect_ai("Some text to check", lang="en")
    >>> print(ai["verdict"])
"""

__version__ = "0.9.0"
__author__ = "TextHumanize Contributors"
__license__ = "Personal Use Only"

from texthumanize.autotune import AutoTuner
from texthumanize.core import (
    adjust_tone,
    adversarial_calibrate,
    analyze,
    analyze_coherence,
    analyze_tone,
    anonymize_style,
    build_author_profile,
    clean_watermarks,
    compare_fingerprint,
    detect_ab,
    detect_ai,
    detect_ai_batch,
    detect_ai_mixed,
    detect_ai_sentences,
    detect_watermarks,
    evasion_resistance,
    explain,
    full_readability,
    humanize,
    humanize_batch,
    humanize_chunked,
    paraphrase,
    spin,
    spin_variants,
)
from texthumanize.diff_report import (
    explain_html,
    explain_json_patch,
    explain_side_by_side,
)
from texthumanize.pipeline import Pipeline
from texthumanize.stylistic import (
    STYLE_PRESETS,
    AnonymizeResult,
    StylisticAnalyzer,
    StylisticFingerprint,
    StylometricAnonymizer,
)
from texthumanize.utils import AnalysisReport, HumanizeOptions, HumanizeResult

__all__ = [
    # Core
    "humanize",
    "humanize_batch",
    "humanize_chunked",
    "analyze",
    "explain",
    # AI Detection
    "detect_ai",
    "detect_ai_batch",
    "detect_ai_sentences",
    "detect_ai_mixed",
    # Author Fingerprint
    "build_author_profile",
    "compare_fingerprint",
    # A/B Detection
    "detect_ab",
    # Evasion Resistance
    "evasion_resistance",
    # Adversarial Calibration
    "adversarial_calibrate",
    # Stylometric Anonymization
    "anonymize_style",
    "StylometricAnonymizer",
    "AnonymizeResult",
    # Paraphrase
    "paraphrase",
    # Tone
    "analyze_tone",
    "adjust_tone",
    # Watermarks
    "detect_watermarks",
    "clean_watermarks",
    # Spinner
    "spin",
    "spin_variants",
    # Coherence
    "analyze_coherence",
    # Readability
    "full_readability",
    # Diff Reports
    "explain_html",
    "explain_json_patch",
    "explain_side_by_side",
    # Infrastructure
    "Pipeline",
    "HumanizeOptions",
    "HumanizeResult",
    "AnalysisReport",
    "StylisticFingerprint",
    "StylisticAnalyzer",
    "STYLE_PRESETS",
    "AutoTuner",
    "__version__",
]
