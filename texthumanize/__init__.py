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

__version__ = "0.35.0"
__author__ = "TextHumanize Contributors"
__license__ = "Personal Use Only"

# SSRF-safety helper for outbound URLs (lightweight, stdlib-only).
from texthumanize._urlguard import validate_outbound_url

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
    UnsafeURLError,
    UnsupportedLanguageError,
)

# ── PEP 562 lazy loading ─────────────────────────────────────
# All heavy modules are loaded on first attribute access.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # core.py
    "humanize": ("texthumanize.core", "humanize"),
    "humanize_batch": ("texthumanize.core", "humanize_batch"),
    "humanize_batch_stream": ("texthumanize.core", "humanize_batch_stream"),
    "humanize_chunked": ("texthumanize.core", "humanize_chunked"),
    "humanize_until_human": ("texthumanize.core", "humanize_until_human"),
    "humanize_sentences": ("texthumanize.core", "humanize_sentences"),
    "humanize_stream": ("texthumanize.core", "humanize_stream"),
    "humanize_variants": ("texthumanize.core", "humanize_variants"),
    "humanize_ai": ("texthumanize.core", "humanize_ai"),
    "analyze": ("texthumanize.core", "analyze"),
    "explain": ("texthumanize.core", "explain"),
    "detect_ai": ("texthumanize.core", "detect_ai"),
    "detect_ai_fast": ("texthumanize.core", "detect_ai_fast"),
    "detect_ai_batch": ("texthumanize.core", "detect_ai_batch"),
    "detect_ai_sentences": ("texthumanize.core", "detect_ai_sentences"),
    "detect_ai_mixed": ("texthumanize.core", "detect_ai_mixed"),
    "detect_ai_explain": ("texthumanize.core", "detect_ai_explain"),
    "audit_report": ("texthumanize.core", "audit_report"),
    "quality_score_report": ("texthumanize.core", "quality_score_report"),
    "attach_quality_score": ("texthumanize.core", "attach_quality_score"),
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
    "watermark_report": ("texthumanize.core", "watermark_report"),
    "watermark_report_batch": ("texthumanize.core", "watermark_report_batch"),
    "clean_safe": ("texthumanize.core", "clean_safe"),
    "neutralise_aggressive": ("texthumanize.core", "neutralise_aggressive"),
    # media_watermark.py — image/audio/video provenance & watermark forensics
    "detect_media_watermarks": ("texthumanize.media_watermark", "detect_media_watermarks"),
    "clean_media_watermarks": ("texthumanize.media_watermark", "clean_media_watermarks"),
    "media_watermark_report": ("texthumanize.media_watermark", "media_watermark_report"),
    "media_format": ("texthumanize.media_watermark", "media_format"),
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
    "STYLE_PRESET_ALIASES": ("texthumanize.stylistic", "STYLE_PRESET_ALIASES"),
    "AnonymizeResult": ("texthumanize.stylistic", "AnonymizeResult"),
    "get_style_preset": ("texthumanize.stylistic", "get_style_preset"),
    "list_style_presets": ("texthumanize.stylistic", "list_style_presets"),
    "normalize_style_preset": ("texthumanize.stylistic", "normalize_style_preset"),
    "resolve_style_target": ("texthumanize.stylistic", "resolve_style_target"),
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
    "replacement_is_natural": ("texthumanize.collocation_engine", "replacement_is_natural"),
    # fingerprint_randomizer.py
    "FingerprintRandomizer": ("texthumanize.fingerprint_randomizer", "FingerprintRandomizer"),
    "diversify_text": ("texthumanize.fingerprint_randomizer", "diversify_text"),
    # _synonym_db.py
    "SynonymDB": ("texthumanize._synonym_db", "SynonymDB"),
    # benchmark_suite.py
    "BenchmarkSuite": ("texthumanize.benchmark_suite", "BenchmarkSuite"),
    "BenchmarkReport": ("texthumanize.benchmark_suite", "BenchmarkReport"),
    "BenchmarkResult": ("texthumanize.benchmark_suite", "BenchmarkResult"),
    "quick_benchmark": ("texthumanize.benchmark_suite", "quick_benchmark"),
    "detector_benchmark": ("texthumanize.benchmarks", "detector_benchmark"),
    "index_eval_corpus": ("texthumanize.benchmarks", "index_eval_corpus"),
    "load_eval_corpus": ("texthumanize.benchmarks", "load_eval_corpus"),
    # contributor_packs.py
    "list_contributor_packs": (
        "texthumanize.contributor_packs",
        "list_contributor_packs",
    ),
    "load_contributor_pack": (
        "texthumanize.contributor_packs",
        "load_contributor_pack",
    ),
    "validate_contributor_pack": (
        "texthumanize.contributor_packs",
        "validate_contributor_pack",
    ),
    # bad_output_bank.py
    "load_bad_output_bank": ("texthumanize.bad_output_bank", "load_bad_output_bank"),
    "validate_bad_output_bank": ("texthumanize.bad_output_bank", "validate_bad_output_bank"),
    # quality_metrics.py
    "benchmark_leaderboard": ("texthumanize.quality_metrics", "benchmark_leaderboard"),
    "detector_calibration": ("texthumanize.quality_metrics", "detector_calibration"),
    "release_snapshot": ("texthumanize.quality_metrics", "release_snapshot"),
    "acceptance_rate": ("texthumanize.quality_metrics", "acceptance_rate"),
    "semantic_drift_rate": ("texthumanize.quality_metrics", "semantic_drift_rate"),
    "watermark_eval": ("texthumanize.quality_metrics", "watermark_eval"),
    "count_regression_examples": ("texthumanize.quality_metrics", "count_regression_examples"),
    "funnel_metrics": ("texthumanize.quality_metrics", "funnel_metrics"),
    # product.py
    "audit_widget_html": ("texthumanize.product", "audit_widget_html"),
    "audit_batch": ("texthumanize.product", "audit_batch"),
    "compare_versions": ("texthumanize.product", "compare_versions"),
    "content_plan_risk": ("texthumanize.product", "content_plan_risk"),
    "make_brand_voice": ("texthumanize.product", "make_brand_voice"),
    "brand_voice_lock": ("texthumanize.product", "brand_voice_lock"),
    "client_report_html": ("texthumanize.product", "client_report_html"),
    # diff_report.py
    "explain_html": ("texthumanize.diff_report", "explain_html"),
    "explain_json_patch": ("texthumanize.diff_report", "explain_json_patch"),
    "explain_json_report": ("texthumanize.diff_report", "explain_json_report"),
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
    # entropy_injector.py (Phase 1)
    "EntropyInjector": ("texthumanize.entropy_injector", "EntropyInjector"),
    # ── ASH™ (Adaptive Statistical Humanization) ──
    # core.py wrappers
    "ash_humanize": ("texthumanize.core", "ash_humanize"),
    "ash_analyze": ("texthumanize.core", "ash_analyze"),
    "sculpt_perplexity": ("texthumanize.core", "sculpt_perplexity"),
    "transfer_signature": ("texthumanize.core", "transfer_signature"),
    "detect_statistical_watermark": ("texthumanize.core", "detect_statistical_watermark"),
    "neutralise_watermark": ("texthumanize.core", "neutralise_watermark"),
    "neutralize_watermark": ("texthumanize.core", "neutralise_watermark"),
    "model_cognition": ("texthumanize.core", "model_cognition"),
    "adversarial_humanize": ("texthumanize.core", "adversarial_humanize"),
    "list_ash_presets": ("texthumanize.core", "list_ash_presets"),
    # ASH classes (direct)
    "ASHEngine": ("texthumanize.ash_engine", "ASHEngine"),
    "ASHResult": ("texthumanize.ash_engine", "ASHResult"),
    "ASH_PRESETS": ("texthumanize.ash_engine", "ASH_PRESETS"),
    "PerplexitySculptor": ("texthumanize.perplexity_sculptor", "PerplexitySculptor"),
    "SculptResult": ("texthumanize.perplexity_sculptor", "SculptResult"),
    "SignatureTransfer": ("texthumanize.signature_transfer", "SignatureTransfer"),
    "TransferResult": ("texthumanize.signature_transfer", "TransferResult"),
    "ASH_CORPUS_PROFILES": ("texthumanize._human_profiles", "ASH_CORPUS_PROFILES"),
    "ASH_CORPUS_PROFILE_ALIASES": (
        "texthumanize._human_profiles",
        "ASH_CORPUS_PROFILE_ALIASES",
    ),
    "get_corpus_human_profile": ("texthumanize._human_profiles", "get_corpus_human_profile"),
    "get_human_profile": ("texthumanize._human_profiles", "get_human_profile"),
    "list_corpus_profiles": ("texthumanize._human_profiles", "list_corpus_profiles"),
    "normalize_corpus_profile": ("texthumanize._human_profiles", "normalize_corpus_profile"),
    "WatermarkForensics": ("texthumanize.watermark_forensics", "WatermarkForensics"),
    "ForensicResult": ("texthumanize.watermark_forensics", "ForensicResult"),
    "CognitiveModeler": ("texthumanize.cognitive_model", "CognitiveModeler"),
    "CognitiveResult": ("texthumanize.cognitive_model", "CognitiveResult"),
    "AdversarialPlay": ("texthumanize.adversarial_play", "AdversarialPlay"),
    "PlayResult": ("texthumanize.adversarial_play", "PlayResult"),
    # ── PHANTOM™ (Perceptual Humanization via Adversarial Neural Text Optimization) ──
    "PhantomEngine": ("texthumanize.phantom", "PhantomEngine"),
    "phantom_optimize": ("texthumanize.phantom", "phantom_optimize"),
    "get_phantom": ("texthumanize.phantom", "get_phantom"),
    "ForgeResult": ("texthumanize.phantom", "ForgeResult"),
    # Visualization
    "TextVisualizer": ("texthumanize.visualize", "TextVisualizer"),
    "VisualizationResult": ("texthumanize.visualize", "VisualizationResult"),
    "perplexity_chart": ("texthumanize.visualize", "perplexity_chart"),
    "detection_heatmap": ("texthumanize.visualize", "detection_heatmap"),
    "sentence_length_chart": ("texthumanize.visualize", "sentence_length_chart"),
    "lexical_diversity_chart": ("texthumanize.visualize", "lexical_diversity_chart"),
    "entropy_chart": ("texthumanize.visualize", "entropy_chart"),
    "dashboard": ("texthumanize.visualize", "dashboard"),
    "comparison_chart": ("texthumanize.visualize", "comparison_chart"),
    # ── Content classifier ──
    "ContentType": ("texthumanize.content_classifier", "ContentType"),
    "ContentProfile": ("texthumanize.content_classifier", "ContentProfile"),
    "classify_content": ("texthumanize.content_classifier", "classify"),
    # ── Grammar Guard ──
    "GrammarGuard": ("texthumanize.grammar_guard", "GrammarGuard"),
    "GuardResult": ("texthumanize.grammar_guard", "GuardResult"),
    # domain_dictionaries.py
    "detect_domains": ("texthumanize.domain_dictionaries", "detect_domains"),
    "domain_terms_for_text": ("texthumanize.domain_dictionaries", "domain_terms_for_text"),
    "get_domain_terms": ("texthumanize.domain_dictionaries", "get_domain_terms"),
    "list_domains": ("texthumanize.domain_dictionaries", "list_domains"),
    "normalize_domain": ("texthumanize.domain_dictionaries", "normalize_domain"),
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
    "STYLE_PRESET_ALIASES",
    "ASH_PRESETS",
    "ASH_CORPUS_PROFILE_ALIASES",
    "ASH_CORPUS_PROFILES",
    "ASHEngine",
    "ASHResult",
    "AdversarialPlay",
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
    "CognitiveModeler",
    "CognitiveResult",
    "CollocEngine",
    "ConfigError",
    "ContentHealthReport",
    "DetectionError",
    "DetectionMetrics",
    "DetectionReport",
    "EmbeddingTable",
    "FeedForwardNet",
    "FingerprintRandomizer",
    "ForensicResult",
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
    "PerplexitySculptor",
    "Pipeline",
    "PipelineError",
    "PlagiarismReport",
    "PlayResult",
    "SculptResult",
    "SemanticReport",
    "SentenceReadabilityReport",
    "SentenceResult",
    "SentenceScore",
    "Seq2SeqParaphraser",
    "SignatureTransfer",
    "SimilarityReport",
    "StageError",
    "StatisticalDetector",
    "StylisticAnalyzer",
    "StylisticFingerprint",
    "StylometricAnonymizer",
    "SyntaxRewriter",
    "TextHumanizeError",
    "TrainingResult",
    "TransferResult",
    "UniquenessReport",
    "UnsafeURLError",
    "UnsupportedLanguageError",
    "WatermarkForensics",
    "WordLanguageModel",
    "WordVec",
    "__version__",
    "adjust_tone",
    "adversarial_calibrate",
    "adversarial_humanize",
    "analyze",
    "analyze_coherence",
    "analyze_tone",
    "anonymize_style",
    "ash_analyze",
    "ash_humanize",
    "assert_accuracy",
    "async_analyze",
    "async_detect_ai",
    "async_detect_ai_batch",
    "async_humanize",
    "async_humanize_batch",
    "async_paraphrase",
    "best_synonym_in_context",
    "build_author_profile",
    "audit_report",
    "attach_quality_score",
    "acceptance_rate",
    "audit_batch",
    "audit_widget_html",
    "benchmark_leaderboard",
    "brand_voice_lock",
    "client_report_html",
    "compare_versions",
    "content_plan_risk",
    "count_regression_examples",
    "detector_calibration",
    "funnel_metrics",
    "load_bad_output_bank",
    "make_brand_voice",
    "detect_media_watermarks",
    "clean_media_watermarks",
    "media_watermark_report",
    "media_format",
    "release_snapshot",
    "semantic_drift_rate",
    "validate_bad_output_bank",
    "watermark_eval",
    "check_grammar",
    "check_originality",
    "clean_safe",
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
    "detect_ai_explain",
    "detect_ai_fast",
    "detect_ai_mixed",
    "detect_ai_sentences",
    "detect_ai_statistical",
    "detector_benchmark",
    "detect_cjk_lang",
    "detect_statistical_watermark",
    "detect_watermarks",
    "diversify_text",
    "evasion_resistance",
    "explain",
    "explain_html",
    "explain_json_patch",
    "explain_json_report",
    "explain_side_by_side",
    "export_custom_dict",
    "export_markers_to_json",
    "fix_grammar",
    "full_readability",
    "get_corpus_human_profile",
    "get_human_profile",
    "get_style_preset",
    "humanize",
    "humanize_ai",
    "humanize_batch",
    "humanize_batch_stream",
    "humanize_chunked",
    "humanize_sentences",
    "humanize_stream",
    "humanize_until_human",
    "humanize_variants",
    "import_markers_from_json",
    "index_eval_corpus",
    "is_cjk_text",
    "list_ash_presets",
    "list_contributor_packs",
    "list_corpus_profiles",
    "list_style_presets",
    "load_ai_markers",
    "load_all_markers",
    "load_contributor_pack",
    "load_eval_corpus",
    "model_cognition",
    "neural_paraphrase",
    "neutralise_watermark",
    "neutralise_aggressive",
    "neutralize_watermark",
    "normalize_corpus_profile",
    "normalize_style_preset",
    "paraphrase",
    "perplexity_score",
    "quality_score_report",
    "quick_benchmark",
    "replacement_is_natural",
    "resolve_style_target",
    "run_benchmark",
    "run_cjk_benchmark",
    "sculpt_perplexity",
    "segment_cjk",
    "semantic_similarity",
    "sentence_readability",
    "spin",
    "spin_variants",
    "SynonymDB",
    "text_fingerprint",
    "train_from_corpus",
    "transfer_signature",
    "uniqueness_score",
    "update_markers",
    "validate_contributor_pack",
    "validate_outbound_url",
    "word_naturalness",
    "word_perplexity",
    "watermark_report",
    "watermark_report_batch",
    # PHANTOM™
    "ForgeResult",
    "PhantomEngine",
    "get_phantom",
    "phantom_optimize",
    # Content classifier
    "ContentType",
    "ContentProfile",
    "classify_content",
    # Grammar Guard
    "GrammarGuard",
    "GuardResult",
    # Domain dictionaries
    "detect_domains",
    "domain_terms_for_text",
    "get_domain_terms",
    "list_domains",
    "normalize_domain",
]
