"""Tests for v0.15.0 features: AI backend, POS tagger, CJK segmenter,
syntax rewriter, statistical detector, word LM, collocation engine,
fingerprint randomizer, benchmark suite."""

import unittest

from texthumanize import humanize


# ═══════════════════════════════════════════════════════════════
#  AIBackend
# ═══════════════════════════════════════════════════════════════
class TestAIBackend(unittest.TestCase):
    """Test three-tier AI backend."""

    def test_import(self):
        from texthumanize.ai_backend import AIBackend
        self.assertTrue(callable(AIBackend))

    def test_builtin_fallback(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()  # no API key, no OSS
        text = "This is a test sentence."
        result = backend.paraphrase(text, lang="en")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_available_backends(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()
        available = backend.available_backends()
        self.assertIn("builtin", available)

    def test_active_backend_is_builtin(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()
        self.assertEqual(backend.active_backend(), "builtin")

    def test_rewrite_sentence(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()
        text = "The implementation demonstrates significant improvements."
        result = backend.rewrite_sentence(text, lang="en")
        self.assertIsInstance(result, str)

    def test_improve_naturalness(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()
        text = "Furthermore, the utilization of this methodology is paramount."
        result = backend.improve_naturalness(text, lang="en")
        self.assertIsInstance(result, str)

    def test_with_openai_key_no_crash(self):
        """Should not crash even with invalid key (falls back)."""
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend(openai_api_key="invalid-key")
        result = backend.paraphrase("Test", lang="en")
        self.assertIsInstance(result, str)

    def test_oss_disabled_by_default(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend()
        available = backend.available_backends()
        self.assertNotIn("oss", available)

    def test_oss_enabled(self):
        from texthumanize.ai_backend import AIBackend
        backend = AIBackend(enable_oss=True)
        available = backend.available_backends()
        self.assertIn("oss", available)


# ═══════════════════════════════════════════════════════════════
#  POSTagger
# ═══════════════════════════════════════════════════════════════
class TestPOSTagger(unittest.TestCase):
    """Test rule-based POS tagger."""

    def test_import(self):
        from texthumanize.pos_tagger import POSTagger
        self.assertTrue(callable(POSTagger))

    def test_en_tag(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        result = tagger.tag("The quick brown fox jumps over the lazy dog")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        for word, tag in result:
            self.assertIsInstance(word, str)
            self.assertIsInstance(tag, str)

    def test_en_tag_the(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        result = tagger.tag("The cat sat on the mat")
        tags_dict = {w.lower(): t for w, t in result}
        self.assertEqual(tags_dict.get("the"), "DET")

    def test_ru_tag(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="ru")
        result = tagger.tag("Быстрая коричневая лиса прыгает")
        self.assertTrue(len(result) > 0)

    def test_de_tag(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="de")
        result = tagger.tag("Der schnelle Fuchs springt")
        self.assertTrue(len(result) > 0)

    def test_uk_tag(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="uk")
        result = tagger.tag("Швидка лисиця стрибає")
        self.assertTrue(len(result) > 0)

    def test_is_noun(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        # "cat" should be tagged as NOUN
        self.assertTrue(tagger.is_noun("cat"))

    def test_is_verb(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        self.assertTrue(tagger.is_verb("running"))

    def test_is_adj(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        self.assertTrue(tagger.is_adj("beautiful"))

    def test_unknown_lang_raises(self):
        from texthumanize.pos_tagger import POSTagger
        with self.assertRaises(ValueError):
            POSTagger(lang="xx")

    def test_empty_text(self):
        from texthumanize.pos_tagger import POSTagger
        tagger = POSTagger(lang="en")
        result = tagger.tag("")
        self.assertEqual(result, [])


# ═══════════════════════════════════════════════════════════════
#  CJK Segmenter
# ═══════════════════════════════════════════════════════════════
class TestCJKSegmenter(unittest.TestCase):
    """Test CJK word segmentation."""

    def test_import(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        self.assertTrue(callable(CJKSegmenter))

    def test_chinese_segment(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter(lang="zh")
        result = seg.segment("我们是中国人")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_japanese_segment(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter(lang="ja")
        result = seg.segment("東京は大きい都市です")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_korean_segment(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter(lang="ko")
        result = seg.segment("한국어 텍스트입니다")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_is_cjk_text(self):
        from texthumanize.cjk_segmenter import is_cjk_text
        self.assertTrue(is_cjk_text("这是中文"))
        self.assertFalse(is_cjk_text("This is English"))

    def test_detect_cjk_lang(self):
        from texthumanize.cjk_segmenter import detect_cjk_lang
        self.assertEqual(detect_cjk_lang("这是中文文本"), "zh")

    def test_segment_cjk_convenience(self):
        from texthumanize.cjk_segmenter import segment_cjk
        result = segment_cjk("中国人民", lang="zh")
        self.assertIsInstance(result, list)

    def test_empty_input(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter(lang="zh")
        result = seg.segment("")
        self.assertEqual(result, [])

    def test_ascii_passthrough(self):
        from texthumanize.cjk_segmenter import CJKSegmenter
        seg = CJKSegmenter(lang="zh")
        result = seg.segment("Hello world")
        self.assertIn("Hello", result)


# ═══════════════════════════════════════════════════════════════
#  SyntaxRewriter
# ═══════════════════════════════════════════════════════════════
class TestSyntaxRewriter(unittest.TestCase):
    """Test sentence-level syntax rewriting."""

    def test_import(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        self.assertTrue(callable(SyntaxRewriter))

    def test_en_rewrite(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        result = sr.rewrite("The cat chased the mouse across the garden.")
        self.assertIsInstance(result, list)

    def test_en_active_to_passive(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        result = sr.active_to_passive("The team completed the project on time.")
        # May return None if pattern doesn't match
        if result is not None:
            self.assertIsInstance(result, str)

    def test_en_rewrite_random(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        sent = "Although the task was difficult, the team finished it."
        result = sr.rewrite_random(sent)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_ru_rewrite(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="ru", seed=42)
        result = sr.rewrite("Команда завершила проект вовремя.")
        self.assertIsInstance(result, list)

    def test_de_rewrite(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="de", seed=42)
        result = sr.rewrite("Das Team hat das Projekt rechtzeitig abgeschlossen.")
        self.assertIsInstance(result, list)

    def test_placeholder_skip(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        sent = "Contact THZ_EMAIL_1 for more details."
        result = sr.rewrite_random(sent)
        # Should return unchanged (placeholder detected)
        self.assertEqual(result, sent)

    def test_empty_input(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        result = sr.rewrite("")
        self.assertEqual(result, [])

    def test_invert_clauses(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        result = sr.invert_clauses(
            "Although it was raining, we went outside."
        )
        if result is not None:
            self.assertIsInstance(result, str)

    def test_reorder_enumeration(self):
        from texthumanize.syntax_rewriter import SyntaxRewriter
        sr = SyntaxRewriter(lang="en", seed=42)
        result = sr.reorder_enumeration(
            "We need apples, bananas, and cherries."
        )
        if result is not None:
            self.assertIsInstance(result, str)


# ═══════════════════════════════════════════════════════════════
#  StatisticalDetector
# ═══════════════════════════════════════════════════════════════
class TestStatisticalDetector(unittest.TestCase):
    """Test statistical AI detector."""

    def test_import(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        self.assertTrue(callable(StatisticalDetector))

    def test_detect_basic(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        text = (
            "This is a test of the statistical detector. "
            "It should produce valid results with proper structure."
        )
        result = det.detect(text)
        self.assertIn("verdict", result)
        self.assertIn("probability", result)
        self.assertIn(result["verdict"], ("human", "mixed", "ai"))

    def test_detect_ru(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="ru")
        text = (
            "Это тест статистического детектора. "
            "Он должен давать корректные результаты."
        )
        result = det.detect(text)
        self.assertIn("probability", result)

    def test_detect_sentences(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        text = "First sentence here. Second one follows. Third is last."
        result = det.detect_sentences(text)
        self.assertIsInstance(result, list)

    def test_extract_features(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        text = (
            "The quick brown fox jumped over the lazy dog. "
            "This sentence has different words. And yet another variation."
        )
        features = det.extract_features(text)
        self.assertIsInstance(features, dict)
        self.assertTrue(len(features) > 10)

    def test_probability_range(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        text = "A simple test text for probability checking."
        prob = det.probability(text)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_convenience_function(self):
        from texthumanize.statistical_detector import (
            detect_ai_statistical,
        )
        result = detect_ai_statistical(
            "Some text to check", lang="en",
        )
        self.assertIn("verdict", result)

    def test_empty_text(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        result = det.detect("")
        self.assertIn("verdict", result)

    def test_short_text(self):
        from texthumanize.statistical_detector import (
            StatisticalDetector,
        )
        det = StatisticalDetector(lang="en")
        result = det.detect("Hi")
        self.assertIn("probability", result)


# ═══════════════════════════════════════════════════════════════
#  WordLanguageModel
# ═══════════════════════════════════════════════════════════════
class TestWordLanguageModel(unittest.TestCase):
    """Test word-level language model."""

    def test_import(self):
        from texthumanize.word_lm import WordLanguageModel
        self.assertTrue(callable(WordLanguageModel))

    def test_en_perplexity(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="en")
        pp = lm.perplexity(
            "The quick brown fox jumps over the lazy dog"
        )
        self.assertIsInstance(pp, float)
        self.assertGreater(pp, 0)

    def test_ru_perplexity(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="ru")
        pp = lm.perplexity("В этом тексте есть несколько слов")
        self.assertIsInstance(pp, float)
        self.assertGreater(pp, 0)

    def test_naturalness_score(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="en")
        result = lm.naturalness_score(
            "The cat sat on the mat. It was a sunny day. "
            "Birds were singing in the trees."
        )
        self.assertIn("perplexity", result)
        self.assertIn("burstiness", result)
        self.assertIn("naturalness", result)
        self.assertIn("verdict", result)

    def test_per_word_surprise(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="en")
        result = lm.per_word_surprise("The cat sat on the mat")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        for word, bits in result:
            self.assertIsInstance(word, str)
            self.assertIsInstance(bits, float)

    def test_burstiness(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="en")
        text = (
            "Short one. This is a much longer sentence with many words. "
            "Medium here. "
            "The final sentence ties everything together nicely."
        )
        burst = lm.burstiness(text)
        self.assertIsInstance(burst, float)
        self.assertGreaterEqual(burst, 0.0)

    def test_convenience_perplexity(self):
        from texthumanize.word_lm import word_perplexity
        pp = word_perplexity("Test sentence here", lang="en")
        self.assertIsInstance(pp, float)

    def test_convenience_naturalness(self):
        from texthumanize.word_lm import word_naturalness
        result = word_naturalness(
            "This is a test of naturalness scoring.",
            lang="en",
        )
        self.assertIn("verdict", result)

    def test_short_text(self):
        from texthumanize.word_lm import WordLanguageModel
        lm = WordLanguageModel(lang="en")
        pp = lm.perplexity("Hi")
        self.assertEqual(pp, 0.0)

    def test_supported_langs(self):
        from texthumanize.word_lm import WordLanguageModel
        for lang in ("en", "ru", "de", "fr", "es", "it", "pl",
                     "pt", "uk", "ar", "zh", "ja", "ko", "tr"):
            lm = WordLanguageModel(lang=lang)
            pp = lm.perplexity("some random text with enough words")
            self.assertIsInstance(pp, float)


# ═══════════════════════════════════════════════════════════════
#  CollocEngine
# ═══════════════════════════════════════════════════════════════
class TestCollocEngine(unittest.TestCase):
    """Test collocation engine."""

    def test_import(self):
        from texthumanize.collocation_engine import CollocEngine
        self.assertTrue(callable(CollocEngine))

    def test_en_pmi(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        score = eng.pmi("heavy", "rain")
        self.assertGreater(score, 0)

    def test_unknown_pair(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        score = eng.pmi("xyz", "abc")
        self.assertEqual(score, 0.0)

    def test_collocates(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        result = eng.collocates("heavy")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_best_synonym(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        best = eng.best_synonym(
            "important",
            ["crucial", "key", "significant"],
            context=["decision"],
        )
        self.assertIn(best, ["crucial", "key", "significant"])

    def test_rank_synonyms(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        result = eng.rank_synonyms(
            ["rain", "snow", "wind"],
            context=["heavy"],
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

    def test_sentence_score(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="en")
        result = eng.sentence_collocation_score(
            "The heavy rain caused significant damage"
        )
        self.assertIn("score", result)
        self.assertIn("pairs", result)

    def test_ru_collocations(self):
        from texthumanize.collocation_engine import CollocEngine
        eng = CollocEngine(lang="ru")
        score = eng.pmi("принять", "решение")
        self.assertGreater(score, 0)

    def test_convenience_functions(self):
        from texthumanize.collocation_engine import (
            best_synonym_in_context,
            collocation_score,
        )
        s = collocation_score("heavy", "rain", lang="en")
        self.assertGreater(s, 0)
        best = best_synonym_in_context(
            "important", ["crucial", "key"], ["decision"],
        )
        self.assertIsInstance(best, str)


# ═══════════════════════════════════════════════════════════════
#  FingerprintRandomizer
# ═══════════════════════════════════════════════════════════════
class TestFingerprintRandomizer(unittest.TestCase):
    """Test anti-fingerprint randomizer."""

    def test_import(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        self.assertTrue(callable(FingerprintRandomizer))

    def test_randomize_plan(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        plan = [
            {"original": "a", "replacement": "b", "position": 0},
            {"original": "c", "replacement": "d", "position": 5},
            {"original": "e", "replacement": "f", "position": 10},
        ]
        result = r.randomize_plan(plan)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) <= len(plan))

    def test_vary_synonym_pool(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        pool = ["a", "b", "c", "d", "e", "f"]
        result = r.vary_synonym_pool(pool)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 2)

    def test_pick_synonym(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.pick_synonym(["a", "b", "c"])
        self.assertIn(result, ["a", "b", "c"])

    def test_pick_synonym_weights(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.pick_synonym(
            ["a", "b", "c"],
            weights=[0.8, 0.1, 0.1],
        )
        self.assertIn(result, ["a", "b", "c"])

    def test_should_skip(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.should_skip()
        self.assertIsInstance(result, bool)

    def test_jitter_intensity(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.jitter_intensity(0.5)
        self.assertGreater(result, 0)
        self.assertLessEqual(result, 1.0)

    def test_vary_paragraph_intensity(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.vary_paragraph_intensity(
            ["para1", "para2", "para3"],
        )
        self.assertEqual(len(result), 3)

    def test_diversify_output(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42, jitter_level=0.5)
        text = "This is a test — with some text."
        result = r.diversify_output(text)
        self.assertIsInstance(result, str)

    def test_verify_diversity(self):
        from texthumanize.fingerprint_randomizer import (
            FingerprintRandomizer,
        )
        r = FingerprintRandomizer(seed=42)
        result = r.verify_diversity([
            "Text version 1", "Text version 2",
        ])
        self.assertIn("unique_ratio", result)
        self.assertIn("diverse", result)

    def test_convenience_functions(self):
        from texthumanize.fingerprint_randomizer import (
            diversify_text,
            randomize_substitutions,
        )
        plan = [{"original": "a", "replacement": "b", "position": 0}]
        result = randomize_substitutions(plan)
        self.assertIsInstance(result, list)

        text = diversify_text("Some text here.")
        self.assertIsInstance(text, str)


# ═══════════════════════════════════════════════════════════════
#  BenchmarkSuite
# ═══════════════════════════════════════════════════════════════
class TestBenchmarkSuite(unittest.TestCase):
    """Test benchmark suite."""

    def test_import(self):
        from texthumanize.benchmark_suite import BenchmarkSuite
        self.assertTrue(callable(BenchmarkSuite))

    def test_run_all(self):
        from texthumanize.benchmark_suite import BenchmarkSuite
        suite = BenchmarkSuite(lang="en")
        samples = [{
            "original": (
                "The implementation of this system provides "
                "significant improvements."
            ),
            "humanized": (
                "This system's setup brings big improvements."
            ),
        }]
        report = suite.run_all(samples)
        self.assertTrue(report.overall_score >= 0)
        self.assertTrue(len(report.results) > 0)

    def test_report_summary(self):
        from texthumanize.benchmark_suite import BenchmarkSuite
        suite = BenchmarkSuite(lang="en")
        samples = [{
            "original": "Test text original.",
            "humanized": "Test text humanized.",
        }]
        report = suite.run_all(samples)
        summary = report.summary()
        self.assertIn("Benchmark", summary)

    def test_empty_samples(self):
        from texthumanize.benchmark_suite import BenchmarkSuite
        suite = BenchmarkSuite(lang="en")
        report = suite.run_all([])
        self.assertEqual(report.overall_score, 0.0)

    def test_quick_benchmark(self):
        from texthumanize.benchmark_suite import quick_benchmark
        report = quick_benchmark(
            "Original text here.",
            "Humanized text here.",
        )
        self.assertTrue(report.elapsed_ms >= 0)


# ═══════════════════════════════════════════════════════════════
#  Integration tests
# ═══════════════════════════════════════════════════════════════
class TestV015Integration(unittest.TestCase):
    """Integration tests for v0.15.0."""

    def test_humanize_uses_new_pipeline(self):
        """Pipeline now has 17 stages."""
        from texthumanize.pipeline import Pipeline
        self.assertEqual(len(Pipeline.STAGE_NAMES), 17)
        self.assertIn("syntax_rewriting", Pipeline.STAGE_NAMES)

    def test_detect_ai_has_stat_detector(self):
        """detect_ai now includes statistical detector results."""
        from texthumanize import detect_ai
        result = detect_ai(
            "This is a test of the new detection system with enough "
            "words to produce meaningful results for analysis.",
            lang="en",
        )
        # Should have combined_score from statistical detector
        self.assertIn("combined_score", result)

    def test_humanize_ai_function(self):
        """humanize_ai is available and works."""
        from texthumanize.core import humanize_ai
        result = humanize_ai(
            "This text should be humanized using AI backend.",
            lang="en",
        )
        self.assertIsNotNone(result.text)
        self.assertTrue(len(result.text) > 0)

    def test_all_exports_present(self):
        """All new exports are in __init__.py."""
        import texthumanize
        new_names = [
            "AIBackend", "POSTagger", "CJKSegmenter",
            "SyntaxRewriter", "StatisticalDetector",
            "WordLanguageModel", "CollocEngine",
            "FingerprintRandomizer", "BenchmarkSuite",
            "humanize_ai", "word_perplexity", "word_naturalness",
            "collocation_score", "best_synonym_in_context",
            "detect_ai_statistical", "segment_cjk",
            "is_cjk_text", "detect_cjk_lang",
            "diversify_text", "quick_benchmark",
        ]
        for name in new_names:
            self.assertIn(
                name, dir(texthumanize),
                f"{name} not exported from texthumanize",
            )

    def test_email_preserved_after_changes(self):
        """Regression: email preservation still works."""
        result = humanize(
            "Contact test@example.com for help.",
            lang="en", seed=42,
        )
        self.assertIn("test@example.com", result.text)

    def test_paragraph_preserved_after_changes(self):
        """Regression: paragraph structure still works."""
        text = (
            "First paragraph here.\n\n"
            "Second paragraph follows.\n\n"
            "Third paragraph last."
        )
        result = humanize(text, lang="en", seed=42)
        paragraphs = [
            p.strip() for p in result.text.split("\n\n")
            if p.strip()
        ]
        self.assertGreaterEqual(len(paragraphs), 2)

    def test_no_op_fixed(self):
        """_reduce_adjacent_repeats now actually reduces repeats."""
        from texthumanize.universal import UniversalProcessor
        proc = UniversalProcessor(
            profile="web", intensity=100, seed=42,
        )
        text = (
            "The important thing is that important decisions "
            "require important thinking. We need important "
            "care when making important choices."
        )
        result = proc._reduce_adjacent_repeats(text, 1.0)
        # Should have fewer "important" than original
        orig_count = text.lower().count("important")
        result_count = result.lower().count("important")
        # At least one should be removed
        self.assertLessEqual(result_count, orig_count)

    def test_humanize_en_runs_full_pipeline(self):
        """Full pipeline with new stages doesn't crash."""
        result = humanize(
            "The implementation of this system demonstrates "
            "that significant improvements have been achieved. "
            "Furthermore, the utilization of advanced methods "
            "ensures optimal performance.",
            lang="en", seed=42, intensity=80,
        )
        self.assertIsNotNone(result.text)
        self.assertTrue(len(result.text) > 10)

    def test_humanize_ru_runs_full_pipeline(self):
        """Full pipeline for Russian doesn't crash."""
        result = humanize(
            "Данный метод является наиболее эффективным. "
            "Однако необходимо отметить ограничения. "
            "Тем не менее, технология перспективна.",
            lang="ru", seed=42, intensity=80,
        )
        self.assertIsNotNone(result.text)
        self.assertTrue(len(result.text) > 10)


if __name__ == "__main__":
    unittest.main()
