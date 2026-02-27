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

try:
    from importlib.metadata import version as _meta_version
    __version__ = _meta_version("texthumanize")
except Exception:
    __version__ = "0.16.0"
__author__ = "TextHumanize Contributors"
__license__ = "Personal Use Only"

# Exceptions — always available (lightweight module, no heavy deps)
from texthumanize.exceptions import (  # noqa: F401, E402
    AIBackendError,
    AIBackendRateLimitError,
    AIBackendUnavailableError,
    ConfigError,
    DetectionError,
    InputTooLargeError,
    PipelineError,
    StageError,
    TextHumanizeError,
    UnsupportedLanguageError,
)

# ── PEP 562 lazy loading ─────────────────────────────────────
# All heavy modules are loaded on first attribute access.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # core.py
    "humanize": ("texthumanize.core", "humanize"),
    "humanize_batch": ("texthumanize.core", "humanize_batch"),
    "humanize_chunked": ("texthumanize.core", "humanize_chunked"),
    "humanize_sentences": ("texthumanize.core", "humanize_sentences"),
    "humanize_stream": ("texthumanize.core", "humanize_stream"),
    "humanize_variants": ("texthumanize.core", "humanize_variants"),
    "humanize_ai": ("texthumanize.core", "humanize_ai"),
    "analyze": ("texthumanize.core", "analyze"),
    "explain": ("texthumanize.core", "explain"),
    "detect_ai": ("texthumanize.core", "detect_ai"),
    "detect_ai_batch": ("texthumanize.core", "detect_ai_batch"),
    "detect_ai_sentences": ("texthumanize.core", "detect_ai_sentences"),
    "detect_ai_mixed": ("texthumanize.core", "detect_ai_mixed"),
    "build_author_profile": ("texthumanize.core", "build_author_profile"),
    "compare_fingerprint": ("texthumanize.core", "compare_fingerprint"),
    "detect_ab": ("texthumanize.core", "detect_ab"),
    "evasion_resistance": ("texthumanize.core", "evasion_resistance"),
    "adversarial_calibrate": ("texthumanize.core", "adversarial_calibrate"),
    "anonymize_style": ("texthumanize.core", "anonymize_style"),
    "paraphrase": ("texthumanize.core", "paraphrase"),
    "analyze_tone": ("texthumanize.core", "analyze_tone"),
    "adjust_tone": ("texthumanize.core", "adjust_tone"),
    "detect_watermarks": ("texthumanize.core", "detect_watermarks"),
    "clean_watermarks": ("texthumanize.core", "clean_watermarks"),
    "spin": ("texthumanize.core", "spin"),
    "spin_variants": ("texthumanize.core", "spin_variants"),
    "analyze_coherence": ("texthumanize.core", "analyze_coherence"),
    "full_readability": ("texthumanize.core", "full_readability"),
    # utils.py
    "HumanizeOptions": ("texthumanize.utils", "HumanizeOptions"),
    "HumanizeResult": ("texthumanize.utils", "HumanizeResult"),
    "AnalysisReport": ("texthumanize.utils", "AnalysisReport"),
    "DetectionReport": ("texthumanize.utils", "DetectionReport"),
    "DetectionMetrics": ("texthumanize.utils", "DetectionMetrics"),
    # pipeline.py
    "Pipeline": ("texthumanize.pipeline", "Pipeline"),
    # async_api.py
    "async_humanize": ("texthumanize.async_api", "async_humanize"),
    "async_detect_ai": ("texthumanize.async_api", "async_detect_ai"),
    "async_analyze": ("texthumanize.async_api", "async_analyze"),
    "async_paraphrase": ("texthumanize.async_api", "async_paraphrase"),
    "async_humanize_batch": ("texthumanize.async_api", "async_humanize_batch"),
    "async_detect_ai_batch": ("texthumanize.async_api", "async_detect_ai_batch"),
    # stylistic.py
    "STYLE_PRESETS": ("texthumanize.stylistic", "STYLE_PRESETS"),
    "AnonymizeResult": ("texthumanize.stylistic", "AnonymizeResult"),
    "StylisticAnalyzer": ("texthumanize.stylistic", "StylisticAnalyzer"),
    "StylisticFingerprint": ("texthumanize.stylistic", "StylisticFingerprint"),
    "StylometricAnonymizer": ("texthumanize.stylistic", "StylometricAnonymizer"),
    # autotune.py
    "AutoTuner": ("texthumanize.autotune", "AutoTuner"),
    # grammar.py
    "check_grammar": ("texthumanize.grammar", "check_grammar"),
    "fix_grammar": ("texthumanize.grammar", "fix_grammar"),
    "GrammarIssue": ("texthumanize.grammar", "GrammarIssue"),
    "GrammarReport": ("texthumanize.grammar", "GrammarReport"),
    # uniqueness.py
    "uniqueness_score": ("texthumanize.uniqueness", "uniqueness_score"),
    "compare_texts": ("texthumanize.uniqueness", "compare_texts"),
    "text_fingerprint": ("texthumanize.uniqueness", "text_fingerprint"),
    "UniquenessReport": ("texthumanize.uniqueness", "UniquenessReport"),
    "SimilarityReport": ("texthumanize.uniqueness", "SimilarityReport"),
    # health_score.py
    "content_health": ("texthumanize.health_score", "content_health"),
    "ContentHealthReport": ("texthumanize.health_score", "ContentHealthReport"),
    "HealthComponent": ("texthumanize.health_score", "HealthComponent"),
    # semantic.py
    "semantic_similarity": ("texthumanize.semantic", "semantic_similarity"),
    "SemanticReport": ("texthumanize.semantic", "SemanticReport"),
    # sentence_readability.py
    "sentence_readability": ("texthumanize.sentence_readability", "sentence_readability"),
    "SentenceReadabilityReport": ("texthumanize.sentence_readability", "SentenceReadabilityReport"),
    "SentenceScore": ("texthumanize.sentence_readability", "SentenceScore"),
    # perplexity_v2.py
    "perplexity_score": ("texthumanize.perplexity_v2", "perplexity_score"),
    "cross_entropy": ("texthumanize.perplexity_v2", "cross_entropy"),
    # dict_trainer.py
    "train_from_corpus": ("texthumanize.dict_trainer", "train_from_corpus"),
    "export_custom_dict": ("texthumanize.dict_trainer", "export_custom_dict"),
    "TrainingResult": ("texthumanize.dict_trainer", "TrainingResult"),
    # plagiarism.py
    "check_originality": ("texthumanize.plagiarism", "check_originality"),
    "compare_originality": ("texthumanize.plagiarism", "compare_originality"),
    "PlagiarismReport": ("texthumanize.plagiarism", "PlagiarismReport"),
    # ai_backend.py
    "AIBackend": ("texthumanize.ai_backend", "AIBackend"),
    # pos_tagger.py
    "POSTagger": ("texthumanize.pos_tagger", "POSTagger"),
    # cjk_segmenter.py
    "CJKSegmenter": ("texthumanize.cjk_segmenter", "CJKSegmenter"),
    "segment_cjk": ("texthumanize.cjk_segmenter", "segment_cjk"),
    "is_cjk_text": ("texthumanize.cjk_segmenter", "is_cjk_text"),
    "detect_cjk_lang": ("texthumanize.cjk_segmenter", "detect_cjk_lang"),
    # syntax_rewriter.py
    "SyntaxRewriter": ("texthumanize.syntax_rewriter", "SyntaxRewriter"),
    # statistical_detector.py
    "StatisticalDetector": ("texthumanize.statistical_detector", "StatisticalDetector"),
    "detect_ai_statistical": ("texthumanize.statistical_detector", "detect_ai_statistical"),
    # word_lm.py
    "WordLanguageModel": ("texthumanize.word_lm", "WordLanguageModel"),
    "word_perplexity": ("texthumanize.word_lm", "word_perplexity"),
    "word_naturalness": ("texthumanize.word_lm", "word_naturalness"),
    # collocation_engine.py
    "CollocEngine": ("texthumanize.collocation_engine", "CollocEngine"),
    "collocation_score": ("texthumanize.collocation_engine", "collocation_score"),
    "best_synonym_in_context": ("texthumanize.collocation_engine", "best_synonym_in_context"),
    # fingerprint_randomizer.py
    "FingerprintRandomizer": ("texthumanize.fingerprint_randomizer", "FingerprintRandomizer"),
    "diversify_text": ("texthumanize.fingerprint_randomizer", "diversify_text"),
    # benchmark_suite.py
    "BenchmarkSuite": ("texthumanize.benchmark_suite", "BenchmarkSuite"),
    "BenchmarkReport": ("texthumanize.benchmark_suite", "BenchmarkReport"),
    "BenchmarkResult": ("texthumanize.benchmark_suite", "BenchmarkResult"),
    "quick_benchmark": ("texthumanize.benchmark_suite", "quick_benchmark"),
    # diff_report.py
    "explain_html": ("texthumanize.diff_report", "explain_html"),
    "explain_json_patch": ("texthumanize.diff_report", "explain_json_patch"),
    "explain_side_by_side": ("texthumanize.diff_report", "explain_side_by_side"),
}


def __getattr__(name: str):
    """PEP 562: lazy-load heavy modules on first attribute access."""
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib
        mod = importlib.import_module(module_path)
        val = getattr(mod, attr)
        globals()[name] = val  # cache for subsequent accesses
        return val
    raise AttributeError(f"module 'texthumanize' has no attribute {name!r}")


def __dir__():
    """Include lazy-loaded names in dir() output."""
    return list(set(globals().keys()) | set(_LAZY_IMPORTS.keys()))

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
    "DetectionReport",
    "DetectionMetrics",
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
    # AI Backend
    "AIBackend",
    "humanize_ai",
    # POS Tagger
    "POSTagger",
    # CJK Segmenter
    "CJKSegmenter",
    "segment_cjk",
    "is_cjk_text",
    "detect_cjk_lang",
    # Syntax Rewriter
    "SyntaxRewriter",
    # Statistical Detector
    "StatisticalDetector",
    "detect_ai_statistical",
    # Word Language Model
    "WordLanguageModel",
    "word_perplexity",
    "word_naturalness",
    # Collocation Engine
    "CollocEngine",
    "collocation_score",
    "best_synonym_in_context",
    # Fingerprint Randomizer
    "FingerprintRandomizer",
    "diversify_text",
    # Benchmark Suite
    "BenchmarkSuite",
    "BenchmarkReport",
    "BenchmarkResult",
    "quick_benchmark",
    # Async API
    "async_humanize",
    "async_detect_ai",
    "async_analyze",
    "async_paraphrase",
    "async_humanize_batch",
    "async_detect_ai_batch",
    # Exceptions
    "TextHumanizeError",
    "PipelineError",
    "StageError",
    "DetectionError",
    "ConfigError",
    "UnsupportedLanguageError",
    "InputTooLargeError",
    "AIBackendError",
    "AIBackendUnavailableError",
    "AIBackendRateLimitError",
    "__version__",
]
