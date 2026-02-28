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

import sys as _sys
import types as _types
from typing import Any

try:
    from importlib.metadata import version as _meta_version
    __version__ = _meta_version("texthumanize")
except Exception:
    __version__ = "0.19.0"
__author__ = "TextHumanize Contributors"
__license__ = "Personal Use Only"

# Exceptions — always available (lightweight module, no heavy deps)
from texthumanize.exceptions import (
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
    "humanize_until_human": ("texthumanize.core", "humanize_until_human"),
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
    # neural_engine.py
    "FeedForwardNet": ("texthumanize.neural_engine", "FeedForwardNet"),
    "LSTMCell": ("texthumanize.neural_engine", "LSTMCell"),
    "EmbeddingTable": ("texthumanize.neural_engine", "EmbeddingTable"),
    "HMM": ("texthumanize.neural_engine", "HMM"),
    # neural_detector.py
    "NeuralAIDetector": ("texthumanize.neural_detector", "NeuralAIDetector"),
    # neural_lm.py
    "NeuralPerplexity": ("texthumanize.neural_lm", "NeuralPerplexity"),
    # word_embeddings.py
    "WordVec": ("texthumanize.word_embeddings", "WordVec"),
    # hmm_tagger.py
    "HMMTagger": ("texthumanize.hmm_tagger", "HMMTagger"),
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
    # neural_paraphraser.py
    "NeuralParaphraser": ("texthumanize.neural_paraphraser", "NeuralParaphraser"),
    "NeuralParaphraseResult": ("texthumanize.neural_paraphraser", "NeuralParaphraseResult"),
    "Seq2SeqParaphraser": ("texthumanize.neural_paraphraser", "Seq2SeqParaphraser"),
    "neural_paraphrase": ("texthumanize.neural_paraphraser", "neural_paraphrase"),
    # gptzero.py
    "GPTZeroClient": ("texthumanize.gptzero", "GPTZeroClient"),
    "GPTZeroResult": ("texthumanize.gptzero", "GPTZeroResult"),
    "SentenceResult": ("texthumanize.gptzero", "SentenceResult"),
    "BatchResult": ("texthumanize.gptzero", "BatchResult"),
    # ai_markers.py
    "load_ai_markers": ("texthumanize.ai_markers", "load_ai_markers"),
    "load_all_markers": ("texthumanize.ai_markers", "load_all_markers"),
    "export_markers_to_json": ("texthumanize.ai_markers", "export_markers_to_json"),
    "import_markers_from_json": ("texthumanize.ai_markers", "import_markers_from_json"),
    "update_markers": ("texthumanize.ai_markers", "update_markers"),
    # pos_benchmark.py
    "run_benchmark": ("texthumanize.pos_benchmark", "run_benchmark"),
    "assert_accuracy": ("texthumanize.pos_benchmark", "assert_accuracy"),
    "POSBenchmarkError": ("texthumanize.pos_benchmark", "POSBenchmarkError"),
    # cjk_segmenter.py (new additions)
    "run_cjk_benchmark": ("texthumanize.cjk_segmenter", "run_cjk_benchmark"),
}


def __getattr__(name: str) -> Any:
    """PEP 562: lazy-load heavy modules on first attribute access."""
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib
        mod = importlib.import_module(module_path)
        val = getattr(mod, attr)
        globals()[name] = val  # cache for subsequent accesses
        return val
    raise AttributeError(f"module 'texthumanize' has no attribute {name!r}")


# ── Prevent submodule shadows ────────────────────────────────
# Python's import machinery sets ``texthumanize.<submodule>`` in the
# package __dict__ when *any* code does ``import texthumanize.<submodule>``
# or ``from texthumanize.<submodule> import …``.  If a lazy-import name
# collides with a submodule file name (e.g. ``paraphrase`` is both a
# function in _LAZY_IMPORTS and a module ``texthumanize/paraphrase.py``),
# the module object shadows the function and __getattr__ is never called.
#
# We use a lightweight custom module class whose __getattribute__
# detects when a submodule has shadowed a lazy-import entry and
# transparently resolves the function instead.


class _LazyModule(_types.ModuleType):
    """Module subclass that resolves lazy-import / submodule name collisions."""

    def __getattribute__(self, name: str) -> object:
        d = super().__getattribute__("__dict__")
        lazy = d.get("_LAZY_IMPORTS")
        if lazy and name in lazy:
            current = d.get(name)
            if isinstance(current, _types.ModuleType):
                # A same-named submodule has been imported — resolve the
                # lazy-import entry (the *function*) and cache it.
                module_path, attr = lazy[name]
                import importlib

                mod = importlib.import_module(module_path)
                val = getattr(mod, attr)
                d[name] = val
                return val
        return super().__getattribute__(name)


_sys.modules[__name__].__class__ = _LazyModule


def __dir__() -> list[str]:
    """Include lazy-loaded names in dir() output."""
    return list(set(globals().keys()) | set(_LAZY_IMPORTS.keys()))

__all__ = [
    "HMM",
    "STYLE_PRESETS",
    "AIBackend",
    "AIBackendError",
    "AIBackendRateLimitError",
    "AIBackendUnavailableError",
    "AnalysisReport",
    "AnonymizeResult",
    "AutoTuner",
    "BatchResult",
    "BenchmarkReport",
    "BenchmarkResult",
    "BenchmarkSuite",
    "CJKSegmenter",
    "CollocEngine",
    "ConfigError",
    "ContentHealthReport",
    "DetectionError",
    "DetectionMetrics",
    "DetectionReport",
    "EmbeddingTable",
    "FeedForwardNet",
    "FingerprintRandomizer",
    "GPTZeroClient",
    "GPTZeroResult",
    "GrammarIssue",
    "GrammarReport",
    "HMMTagger",
    "HealthComponent",
    "HumanizeOptions",
    "HumanizeResult",
    "InputTooLargeError",
    "LSTMCell",
    "NeuralAIDetector",
    "NeuralParaphraseResult",
    "NeuralParaphraser",
    "NeuralPerplexity",
    "POSBenchmarkError",
    "POSTagger",
    "Pipeline",
    "PipelineError",
    "PlagiarismReport",
    "SemanticReport",
    "SentenceReadabilityReport",
    "SentenceResult",
    "SentenceScore",
    "Seq2SeqParaphraser",
    "SimilarityReport",
    "StageError",
    "StatisticalDetector",
    "StylisticAnalyzer",
    "StylisticFingerprint",
    "StylometricAnonymizer",
    "SyntaxRewriter",
    "TextHumanizeError",
    "TrainingResult",
    "UniquenessReport",
    "UnsupportedLanguageError",
    "WordLanguageModel",
    "WordVec",
    "__version__",
    "adjust_tone",
    "adversarial_calibrate",
    "analyze",
    "analyze_coherence",
    "analyze_tone",
    "anonymize_style",
    "assert_accuracy",
    "async_analyze",
    "async_detect_ai",
    "async_detect_ai_batch",
    "async_humanize",
    "async_humanize_batch",
    "async_paraphrase",
    "best_synonym_in_context",
    "build_author_profile",
    "check_grammar",
    "check_originality",
    "clean_watermarks",
    "collocation_score",
    "compare_fingerprint",
    "compare_originality",
    "compare_texts",
    "content_health",
    "cross_entropy",
    "detect_ab",
    "detect_ai",
    "detect_ai_batch",
    "detect_ai_mixed",
    "detect_ai_sentences",
    "detect_ai_statistical",
    "detect_cjk_lang",
    "detect_watermarks",
    "diversify_text",
    "evasion_resistance",
    "explain",
    "explain_html",
    "explain_json_patch",
    "explain_side_by_side",
    "export_custom_dict",
    "export_markers_to_json",
    "fix_grammar",
    "full_readability",
    "humanize",
    "humanize_ai",
    "humanize_batch",
    "humanize_chunked",
    "humanize_sentences",
    "humanize_stream",
    "humanize_until_human",
    "humanize_variants",
    "import_markers_from_json",
    "is_cjk_text",
    "load_ai_markers",
    "load_all_markers",
    "neural_paraphrase",
    "paraphrase",
    "perplexity_score",
    "quick_benchmark",
    "run_benchmark",
    "run_cjk_benchmark",
    "segment_cjk",
    "semantic_similarity",
    "sentence_readability",
    "spin",
    "spin_variants",
    "text_fingerprint",
    "train_from_corpus",
    "uniqueness_score",
    "update_markers",
    "word_naturalness",
    "word_perplexity",
]
