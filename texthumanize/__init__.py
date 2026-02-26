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

Новое в v0.10.0:
    - ``check_grammar()``       — проверка грамматики (правила для 9 языков)
    - ``fix_grammar()``         — автоисправление грамматики
    - ``uniqueness_score()``    — уникальность текста (n-gram fingerprinting)
    - ``compare_texts()``       — сравнение двух текстов
    - ``content_health()``      — комплексная оценка качества
    - ``semantic_similarity()`` — семантическое сходство оригинал/обработка
    - ``sentence_readability()`` — читабельность на уровне предложений

Использование:
    >>> from texthumanize import humanize, analyze, detect_ai
    >>> result = humanize("Данный текст является примером.", lang="ru")
    >>> print(result.text)
    >>> ai = detect_ai("Some text to check", lang="en")
    >>> print(ai["verdict"])
"""

__version__ = "0.14.0"
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
    humanize_sentences,
    humanize_stream,
    humanize_variants,
    paraphrase,
    spin,
    spin_variants,
)
from texthumanize.dict_trainer import TrainingResult, export_custom_dict, train_from_corpus
from texthumanize.diff_report import (
    explain_html,
    explain_json_patch,
    explain_side_by_side,
)
from texthumanize.grammar import GrammarIssue, GrammarReport, check_grammar, fix_grammar
from texthumanize.health_score import ContentHealthReport, HealthComponent, content_health
from texthumanize.perplexity_v2 import cross_entropy, perplexity_score
from texthumanize.pipeline import Pipeline
from texthumanize.plagiarism import PlagiarismReport, check_originality, compare_originality
from texthumanize.semantic import SemanticReport, semantic_similarity
from texthumanize.sentence_readability import (
    SentenceReadabilityReport,
    SentenceScore,
    sentence_readability,
)
from texthumanize.stylistic import (
    STYLE_PRESETS,
    AnonymizeResult,
    StylisticAnalyzer,
    StylisticFingerprint,
    StylometricAnonymizer,
)
from texthumanize.uniqueness import (
    SimilarityReport,
    UniquenessReport,
    compare_texts,
    text_fingerprint,
    uniqueness_score,
)
from texthumanize.utils import AnalysisReport, HumanizeOptions, HumanizeResult

__all__ = [
    # Core
    "humanize",
    "humanize_batch",
    "humanize_chunked",
    "humanize_sentences",
    "humanize_stream",
    "humanize_variants",
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
    # Grammar
    "check_grammar",
    "fix_grammar",
    "GrammarIssue",
    "GrammarReport",
    # Uniqueness
    "uniqueness_score",
    "compare_texts",
    "text_fingerprint",
    "UniquenessReport",
    "SimilarityReport",
    # Content Health Score
    "content_health",
    "ContentHealthReport",
    "HealthComponent",
    # Semantic Similarity
    "semantic_similarity",
    "SemanticReport",
    # Sentence Readability
    "sentence_readability",
    "SentenceReadabilityReport",
    "SentenceScore",
    # Perplexity v2
    "perplexity_score",
    "cross_entropy",
    # Dictionary Training
    "train_from_corpus",
    "export_custom_dict",
    "TrainingResult",
    # Plagiarism Detection
    "check_originality",
    "compare_originality",
    "PlagiarismReport",
    "__version__",
]
