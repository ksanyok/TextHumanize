"""Tests for v0.14.0 features.

Covers: H1 error isolation, H3 adversarial_calibrate fix, H4 partial rollback,
H5 input sanitization, H6 pipeline profiling, M2 thread safety, M3 instance plugins,
N1 sentence-level humanize, N5 streaming, N8 multi-variant,
C4 perplexity_v2, N6 dict_trainer, N7 plagiarism.
"""

import unittest


# ── H3: adversarial_calibrate bug fix ─────────────────────────
class TestAdversarialCalibrateFix(unittest.TestCase):
    """Verify adversarial_calibrate uses int intensity (0-100)."""

    def test_default_intensity_is_int(self):
        import inspect

        from texthumanize.core import adversarial_calibrate
        sig = inspect.signature(adversarial_calibrate)
        default = sig.parameters["intensity"].default
        self.assertIsInstance(default, int)
        self.assertEqual(default, 50)

    def test_runs_without_error(self):
        from texthumanize import adversarial_calibrate
        result = adversarial_calibrate(
            "This is a test text.",
            lang="en",
            max_rounds=1,
        )
        self.assertIn("final_text", result)
        self.assertIn("final_score", result)


# ── H5: Input sanitization ───────────────────────────────────
class TestInputSanitization(unittest.TestCase):
    """Test input validation in humanize()."""

    def test_non_string_raises_type_error(self):
        from texthumanize import humanize
        with self.assertRaises(TypeError):
            humanize(123)

    def test_none_raises_type_error(self):
        from texthumanize import humanize
        with self.assertRaises(TypeError):
            humanize(None)

    def test_empty_string_returns_empty(self):
        from texthumanize import humanize
        r = humanize("")
        self.assertEqual(r.text, "")

    def test_whitespace_returns_unchanged(self):
        from texthumanize import humanize
        r = humanize("   ")
        self.assertEqual(r.text, "   ")

    def test_too_long_raises_value_error(self):
        from texthumanize import humanize
        with self.assertRaises(ValueError):
            humanize("x" * 600_000)


# ── H6: Pipeline profiling ───────────────────────────────────
class TestPipelineProfiling(unittest.TestCase):
    """Verify pipeline includes timing data."""

    def test_metrics_after_has_timings(self):
        from texthumanize import humanize
        r = humanize(
            "Artificial intelligence is transforming the way we work. "
            "It is important to note that this technology has both benefits and drawbacks.",
            lang="en",
        )
        self.assertIn("stage_timings", r.metrics_after)
        self.assertIn("total_time", r.metrics_after)
        self.assertIsInstance(r.metrics_after["stage_timings"], dict)
        self.assertGreater(r.metrics_after["total_time"], 0)


# ── M3: Instance-level plugins ────────────────────────────────
class TestInstancePlugins(unittest.TestCase):
    """Verify plugins are instance-level, not shared globally."""

    def test_pipeline_has_instance_dicts(self):
        from texthumanize.pipeline import Pipeline
        p1 = Pipeline()
        p2 = Pipeline()
        self.assertIsNot(p1._plugins_before, p2._plugins_before)
        self.assertIsNot(p1._plugins_after, p2._plugins_after)

    def test_class_level_register(self):
        from texthumanize.pipeline import Pipeline

        class DummyPlugin:
            def process(self, text, lang, profile, intensity):
                return text

        Pipeline.register_plugin(DummyPlugin(), after="typography")
        Pipeline.clear_plugins()


# ── N1: Sentence-level humanization ──────────────────────────
class TestSentenceLevelHumanize(unittest.TestCase):
    """Test humanize_sentences()."""

    def test_import(self):
        from texthumanize import humanize_sentences
        self.assertTrue(callable(humanize_sentences))

    def test_basic_call(self):
        from texthumanize import humanize_sentences
        result = humanize_sentences(
            "This is a test. Another sentence here.",
            lang="en",
        )
        self.assertIn("text", result)
        self.assertIn("sentences", result)
        self.assertIn("human_kept", result)
        self.assertIn("ai_processed", result)

    def test_returns_all_sentences(self):
        from texthumanize import humanize_sentences
        text = "First sentence. Second sentence. Third sentence."
        result = humanize_sentences(text, lang="en")
        self.assertGreater(len(result["sentences"]), 0)


# ── N8: Multi-variant output ─────────────────────────────────
class TestMultiVariant(unittest.TestCase):
    """Test humanize_variants()."""

    def test_import(self):
        from texthumanize import humanize_variants
        self.assertTrue(callable(humanize_variants))

    def test_returns_list(self):
        from texthumanize import humanize_variants
        results = humanize_variants(
            "This is a test text for variant generation.",
            lang="en",
            variants=2,
        )
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)

    def test_variant_fields(self):
        from texthumanize import humanize_variants
        results = humanize_variants("Test text.", lang="en", variants=1)
        r = results[0]
        self.assertIn("text", r)
        self.assertIn("variant_id", r)
        self.assertIn("seed_used", r)
        self.assertIn("change_ratio", r)
        self.assertIn("ai_score", r)

    def test_different_seeds(self):
        from texthumanize import humanize_variants
        results = humanize_variants("Test.", lang="en", variants=2, seed=42)
        self.assertNotEqual(results[0]["seed_used"], results[1]["seed_used"])


# ── N5: Streaming API ────────────────────────────────────────
class TestStreamingAPI(unittest.TestCase):
    """Test humanize_stream()."""

    def test_import(self):
        from texthumanize import humanize_stream
        self.assertTrue(callable(humanize_stream))

    def test_yields_chunks(self):
        from texthumanize import humanize_stream
        chunks = list(humanize_stream("Hello world. Test.", lang="en"))
        self.assertGreater(len(chunks), 0)

    def test_chunk_fields(self):
        from texthumanize import humanize_stream
        chunks = list(humanize_stream("Hello world.", lang="en"))
        c = chunks[0]
        self.assertIn("chunk", c)
        self.assertIn("chunk_index", c)
        self.assertIn("is_last", c)
        self.assertIn("progress", c)

    def test_last_chunk_is_last(self):
        from texthumanize import humanize_stream
        chunks = list(humanize_stream("Hello.", lang="en"))
        self.assertTrue(chunks[-1]["is_last"])


# ── C4: Perplexity v2 ────────────────────────────────────────
class TestPerplexityV2(unittest.TestCase):
    """Test enhanced perplexity model."""

    def test_import(self):
        from texthumanize import cross_entropy, perplexity_score
        self.assertTrue(callable(perplexity_score))
        self.assertTrue(callable(cross_entropy))

    def test_cross_entropy_returns_float(self):
        from texthumanize import cross_entropy
        ce = cross_entropy("The quick brown fox jumps.", lang="en")
        self.assertIsInstance(ce, float)
        self.assertGreater(ce, 0)

    def test_perplexity_score_fields(self):
        from texthumanize import perplexity_score
        result = perplexity_score("This is a test sentence for analysis.", lang="en")
        self.assertIn("cross_entropy", result)
        self.assertIn("perplexity", result)
        self.assertIn("naturalness", result)
        self.assertIn("verdict", result)

    def test_empty_text(self):
        from texthumanize import perplexity_score
        result = perplexity_score("")
        self.assertEqual(result["cross_entropy"], 0.0)
        self.assertEqual(result["verdict"], "unknown")

    def test_verdict_values(self):
        from texthumanize import perplexity_score
        result = perplexity_score("A" * 100, lang="en")
        self.assertIn(result["verdict"], ["human", "mixed", "ai", "unknown"])


# ── N6: Custom dictionary training ───────────────────────────
class TestDictTrainer(unittest.TestCase):
    """Test dictionary training module."""

    def test_import(self):
        from texthumanize import export_custom_dict, train_from_corpus
        self.assertTrue(callable(train_from_corpus))
        self.assertTrue(callable(export_custom_dict))

    def test_empty_corpus(self):
        from texthumanize import train_from_corpus
        result = train_from_corpus([])
        self.assertEqual(result.corpus_size, 0)
        self.assertEqual(len(result.overused_phrases), 0)

    def test_finds_overused_phrases(self):
        from texthumanize import train_from_corpus
        texts = [
            "Furthermore, this is important. Furthermore, we need more.",
            "Furthermore, testing matters. Furthermore, quality is key.",
        ]
        result = train_from_corpus(texts, lang="en", min_frequency=2)
        self.assertGreater(len(result.overused_phrases), 0)

    def test_export_custom_dict(self):
        from texthumanize import export_custom_dict, train_from_corpus
        texts = [
            "Furthermore this is a furthermore test with furthermore repetitions.",
        ] * 3
        result = train_from_corpus(texts, lang="en", min_frequency=2)
        d = export_custom_dict(result)
        self.assertIsInstance(d, dict)

    def test_vocabulary_stats(self):
        from texthumanize import train_from_corpus
        texts = ["The quick brown fox jumps over the lazy dog."]
        result = train_from_corpus(texts, lang="en")
        self.assertIn("type_token_ratio", result.vocabulary_stats)
        self.assertIn("hapax_ratio", result.vocabulary_stats)

    def test_ai_pattern_detection(self):
        from texthumanize import train_from_corpus
        texts = [
            "It is important to note that we must consider. "
            "In conclusion, the results show improvement. "
            "Moreover, the data supports our hypothesis."
        ]
        result = train_from_corpus(texts, lang="en", min_frequency=1)
        # Should detect AI markers
        found_ai = False
        for phrase in result.overused_phrases:
            if "important to note" in phrase or "in conclusion" in phrase:
                found_ai = True
                break
        self.assertTrue(found_ai)


# ── N7: Plagiarism detection ─────────────────────────────────
class TestPlagiarismDetection(unittest.TestCase):
    """Test plagiarism detection module."""

    def test_import(self):
        from texthumanize import check_originality
        self.assertTrue(callable(check_originality))

    def test_empty_text(self):
        from texthumanize import check_originality
        result = check_originality("")
        self.assertEqual(result.originality_score, 100.0)
        self.assertEqual(result.verdict, "original")

    def test_original_text(self):
        from texthumanize import check_originality
        result = check_originality(
            "This is a completely unique text about quantum mechanics "
            "and its applications in modern computing technology."
        )
        self.assertGreater(result.originality_score, 50)
        self.assertIn(result.verdict, ["original", "moderate_overlap"])

    def test_compare_against_reference(self):
        from texthumanize import check_originality
        text = "The cat sat on the mat in the sun."
        refs = ["The cat sat on the mat in the sun. It was warm."]
        result = check_originality(text, reference_texts=refs)
        self.assertIsInstance(result.originality_score, float)

    def test_compare_originality(self):
        from texthumanize import compare_originality
        result = compare_originality(
            "This is a modified sentence about testing.",
            "This is the original sentence about testing.",
        )
        self.assertIn("divergence", result)
        self.assertIn("is_sufficiently_different", result)
        self.assertIsInstance(result["divergence"], float)

    def test_self_repetition(self):
        from texthumanize import check_originality
        # Highly repetitive text
        text = "The same words repeat. " * 10
        result = check_originality(text)
        self.assertGreater(result.self_similarity, 0)

    def test_fingerprint_hash(self):
        from texthumanize import check_originality
        r1 = check_originality("Some text here.")
        r2 = check_originality("Some text here.")
        self.assertEqual(r1.fingerprint_hash, r2.fingerprint_hash)

    def test_different_texts_different_hash(self):
        from texthumanize import check_originality
        r1 = check_originality("First text.")
        r2 = check_originality("Second text.")
        self.assertNotEqual(r1.fingerprint_hash, r2.fingerprint_hash)


# ── H1: Error isolation ──────────────────────────────────────
class TestErrorIsolation(unittest.TestCase):
    """Test that pipeline stages fail gracefully."""

    def test_pipeline_has_safe_stage(self):
        from texthumanize.pipeline import Pipeline
        p = Pipeline()
        self.assertTrue(hasattr(p, "_safe_stage"))

    def test_safe_stage_skips_on_error(self):
        from texthumanize.pipeline import Pipeline
        p = Pipeline()

        def failing_fn():
            raise ValueError("Test error")

        timings = {}
        text, changes = p._safe_stage(
            "test_stage", "hello", "en", failing_fn, timings,
        )
        self.assertEqual(text, "hello")
        self.assertEqual(len(changes), 1)
        self.assertIn("stage_skipped", changes[0]["type"])
        self.assertIn("test_stage", timings)


# ── M2: Thread safety ────────────────────────────────────────
class TestThreadSafety(unittest.TestCase):
    """Test thread-safe lazy loading."""

    def test_lazy_lock_exists(self):
        import texthumanize.core as core
        self.assertTrue(hasattr(core, "_lazy_lock"))

    def test_concurrent_imports(self):
        import threading

        from texthumanize.core import _get_detectors
        results = []
        errors = []

        def worker():
            try:
                mod = _get_detectors()
                results.append(mod)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        # All should get the same module
        for r in results:
            self.assertIs(r, results[0])


if __name__ == "__main__":
    unittest.main()
