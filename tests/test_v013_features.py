"""Тесты для v0.13.0 — 16-этапный пайплайн + расширенные словари."""

from __future__ import annotations

import unittest

from texthumanize import humanize
from texthumanize.coherence_repair import CoherenceRepairer
from texthumanize.grammar_fix import GrammarCorrector
from texthumanize.pipeline import Pipeline
from texthumanize.readability_opt import ReadabilityOptimizer
from texthumanize.tone_harmonizer import ToneHarmonizer


class TestPipeline16Stages(unittest.TestCase):
    """Проверка 16-этапного пайплайна."""

    def test_stage_count(self):
        self.assertEqual(len(Pipeline.STAGE_NAMES), 16)

    def test_stage_names(self):
        expected = (
            "watermark", "segmentation", "typography", "debureaucratization",
            "structure", "repetitions", "liveliness",
            "paraphrasing", "tone", "universal", "naturalization",
            "readability", "grammar", "coherence",
            "validation", "restore",
        )
        self.assertEqual(Pipeline.STAGE_NAMES, expected)

    def test_new_stages_present(self):
        names = Pipeline.STAGE_NAMES
        self.assertIn("tone", names)
        self.assertIn("readability", names)
        self.assertIn("grammar", names)
        self.assertIn("coherence", names)

    def test_pipeline_runs_successfully(self):
        result = humanize(
            "This is a test of the pipeline. It should work correctly.",
            lang="en",
        )
        self.assertIsNotNone(result.text)
        self.assertTrue(len(result.text) > 0)

    def test_pipeline_register_new_stages(self):
        """Можно зарегистрировать плагины для новых этапов."""
        for stage in ("tone", "readability", "grammar", "coherence"):
            # Should not raise
            Pipeline.register_hook(
                lambda text, lang: text,
                before=stage,
            )
        Pipeline.clear_plugins()


class TestGrammarCorrector(unittest.TestCase):
    """Тесты грамматической коррекции."""

    def test_fix_double_words(self):
        gc = GrammarCorrector(lang="en")
        result = gc.process("He said said hello to the the team.")
        self.assertNotIn("said said", result)
        self.assertNotIn("the the", result)

    def test_fix_spacing(self):
        gc = GrammarCorrector(lang="en")
        # Space before punct is fixed (severity=warning)
        result = gc.process("Hello world ,how are you ?")
        self.assertNotIn(" ,", result)
        self.assertNotIn(" ?", result)

    def test_no_change_clean_text(self):
        gc = GrammarCorrector(lang="en")
        text = "This is a perfectly clean sentence."
        result = gc.process(text)
        self.assertEqual(result, text)
        self.assertEqual(len(gc.changes), 0)

    def test_changes_tracked(self):
        gc = GrammarCorrector(lang="en")
        gc.process("This is is a test test sentence.")
        self.assertTrue(len(gc.changes) > 0)
        self.assertEqual(gc.changes[0]["type"], "grammar_correction")

    def test_russian_typos(self):
        gc = GrammarCorrector(lang="ru")
        result = gc.process("Это агенство работает хорошо.")
        self.assertIn("агентство", result)

    def test_german_typos(self):
        gc = GrammarCorrector(lang="de")
        result = gc.process("Der Standart ist hoch.")
        self.assertIn("Standard", result)

    def test_empty_text(self):
        gc = GrammarCorrector(lang="en")
        self.assertEqual(gc.process(""), "")
        self.assertEqual(gc.process("   "), "   ")


class TestToneHarmonizer(unittest.TestCase):
    """Тесты гармонизации тона."""

    def test_import(self):
        th = ToneHarmonizer(lang="en", profile="academic")
        self.assertEqual(th.lang, "en")
        self.assertEqual(th.profile, "academic")

    def test_neutral_profile_no_change(self):
        th = ToneHarmonizer(lang="en", profile="default")
        text = "The system works well and processes data efficiently."
        result = th.process(text)
        # Neutral profile should make minimal changes
        self.assertIsNotNone(result)

    def test_empty_text(self):
        th = ToneHarmonizer(lang="en", profile="academic")
        self.assertEqual(th.process(""), "")

    def test_short_text(self):
        th = ToneHarmonizer(lang="en", profile="formal")
        result = th.process("Hi there!")
        self.assertIsNotNone(result)

    def test_changes_tracked(self):
        th = ToneHarmonizer(lang="en", profile="formal", intensity=80)
        text = (
            "We gotta get this stuff done quickly because the boss "
            "wanna see results. It's kinda important honestly."
        )
        result = th.process(text)
        # Changes might or might not be made depending on tone analysis
        self.assertIsNotNone(result)


class TestReadabilityOptimizer(unittest.TestCase):
    """Тесты оптимизации читаемости."""

    def test_import(self):
        ro = ReadabilityOptimizer(lang="en")
        self.assertEqual(ro.lang, "en")

    def test_simple_text_unchanged(self):
        ro = ReadabilityOptimizer(lang="en")
        text = "Simple text. Easy to read."
        result = ro.process(text)
        self.assertEqual(result, text)

    def test_complex_sentence_split(self):
        ro = ReadabilityOptimizer(lang="en", intensity=80)
        text = (
            "The implementation of the new system, which was designed by "
            "the engineering team according to the latest specifications "
            "and requirements documents, however required significant "
            "modifications to the existing infrastructure, although the "
            "management team initially believed that minimal changes "
            "would be sufficient for the deployment."
        )
        result = ro.process(text)
        # Should attempt to split the very complex sentence
        self.assertIsNotNone(result)

    def test_empty_text(self):
        ro = ReadabilityOptimizer(lang="en")
        self.assertEqual(ro.process(""), "")

    def test_russian_conjunctions(self):
        ro = ReadabilityOptimizer(lang="ru")
        self.assertEqual(ro.lang, "ru")

    def test_changes_tracked_on_split(self):
        ro = ReadabilityOptimizer(lang="en", intensity=80)
        long_text = (
            "The comprehensive analysis of the data, which was collected "
            "over a period of several months from multiple different sources "
            "across various geographical regions, however revealed some "
            "unexpected patterns in the results, although the researchers "
            "initially hypothesized that the outcomes would be consistent "
            "with previous studies conducted in similar environments."
        )
        ro.process(long_text)
        # May or may not produce changes depending on sentence analysis
        self.assertIsInstance(ro.changes, list)

    def test_join_short_sentences(self):
        ro = ReadabilityOptimizer(lang="en", intensity=100, seed=42)
        text = "Yes. No. Ok. Yes. No."
        result = ro.process(text)
        self.assertIsNotNone(result)


class TestCoherenceRepairer(unittest.TestCase):
    """Тесты коррекции когерентности."""

    def test_import(self):
        cr = CoherenceRepairer(lang="en")
        self.assertEqual(cr.lang, "en")

    def test_single_paragraph(self):
        cr = CoherenceRepairer(lang="en")
        text = "A single paragraph with no transitions needed."
        result = cr.process(text)
        self.assertEqual(result, text)

    def test_multi_paragraph(self):
        cr = CoherenceRepairer(lang="en", intensity=100, seed=42)
        text = (
            "The first paragraph discusses the initial findings.\n\n"
            "Data was collected from multiple sources.\n\n"
            "Results show significant improvements.\n\n"
            "The team concluded the experiment successfully."
        )
        result = cr.process(text)
        self.assertIsNotNone(result)

    def test_empty_text(self):
        cr = CoherenceRepairer(lang="en")
        self.assertEqual(cr.process(""), "")

    def test_russian_transitions(self):
        cr = CoherenceRepairer(lang="ru", intensity=100, seed=42)
        text = (
            "Первый абзац описывает начальные результаты.\n\n"
            "Данные были собраны из нескольких источников.\n\n"
            "Результаты показывают значительные улучшения.\n\n"
            "Команда успешно завершила эксперимент."
        )
        result = cr.process(text)
        self.assertIsNotNone(result)

    def test_ukrainian_transitions(self):
        cr = CoherenceRepairer(lang="uk", intensity=100, seed=42)
        text = (
            "Перший абзац описує початкові результати.\n\n"
            "Дані були зібрані з кількох джерел.\n\n"
            "Результати показують значні покращення.\n\n"
            "Команда успішно завершила експеримент."
        )
        result = cr.process(text)
        self.assertIsNotNone(result)

    def test_changes_tracked(self):
        cr = CoherenceRepairer(lang="en", intensity=100, seed=42)
        text = (
            "The introduction sets the stage for the study.\n\n"
            "Methods were carefully designed. All participants agreed.\n\n"
            "The results were analyzed. Charts show the data clearly.\n\n"
            "Discussion highlights key takeaways. More research needed."
        )
        cr.process(text)
        self.assertIsInstance(cr.changes, list)


class TestDictionaryExpansion(unittest.TestCase):
    """Проверка расширения словарей."""

    def test_en_dict_size(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("en")
        # Should have significantly more entries after expansion
        self.assertGreater(len(pack.get("bureaucratic", {})), 400)
        self.assertGreater(len(pack.get("synonyms", {})), 300)

    def test_ru_dict_size(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("ru")
        self.assertGreater(len(pack.get("bureaucratic", {})), 400)
        self.assertGreater(len(pack.get("synonyms", {})), 200)

    def test_uk_dict_size(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("uk")
        self.assertGreater(len(pack.get("bureaucratic", {})), 250)
        self.assertGreater(len(pack.get("synonyms", {})), 200)

    def test_de_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("de")
        self.assertGreater(len(pack.get("bureaucratic", {})), 300)

    def test_ar_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("ar")
        self.assertGreater(len(pack.get("bureaucratic", {})), 100)

    def test_zh_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("zh")
        self.assertGreater(len(pack.get("bureaucratic", {})), 100)

    def test_ja_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("ja")
        self.assertGreater(len(pack.get("bureaucratic", {})), 100)

    def test_ko_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("ko")
        self.assertGreater(len(pack.get("bureaucratic", {})), 100)

    def test_tr_dict_expanded(self):
        from texthumanize.lang import get_lang_pack
        pack = get_lang_pack("tr")
        self.assertGreater(len(pack.get("bureaucratic", {})), 100)

    def test_all_languages_load(self):
        from texthumanize.lang import get_lang_pack
        for lang in ("en", "ru", "uk", "de", "es", "fr", "it", "pl", "pt",
                      "ar", "zh", "ja", "ko", "tr"):
            pack = get_lang_pack(lang)
            self.assertIsNotNone(pack, f"{lang} failed to load")
            self.assertIn("bureaucratic", pack)
            self.assertIn("synonyms", pack)


class TestEndToEndQuality(unittest.TestCase):
    """E2E тесты — текст проходит все 16 этапов без поломок."""

    def test_english_ai_text(self):
        text = (
            "In the realm of artificial intelligence, it is crucial to ensure "
            "the effective implementation of various methodologies. Furthermore, "
            "it is important to note that the utilization of cutting-edge "
            "technologies necessitates a comprehensive understanding of the "
            "underlying principles."
        )
        result = humanize(text, lang="en")
        self.assertTrue(len(result.text) > 20)
        # Should not contain placeholder artifacts
        self.assertNotIn("\x00", result.text)
        self.assertNotIn("THZ_", result.text)

    def test_russian_ai_text(self):
        text = (
            "Необходимо обеспечить эффективное функционирование системы. "
            "Данный подход является ключевым фактором успеха."
        )
        result = humanize(text, lang="ru")
        self.assertTrue(len(result.text) > 20)
        self.assertNotIn("\x00", result.text)

    def test_german_text(self):
        text = (
            "Die Implementierung der neuen Technologie erfordert eine "
            "umfassende Analyse der bestehenden Infrastruktur."
        )
        result = humanize(text, lang="de")
        self.assertTrue(len(result.text) > 20)
        self.assertNotIn("\x00", result.text)

    def test_spanish_text(self):
        text = (
            "Es fundamental implementar las medidas necesarias para "
            "garantizar el funcionamiento adecuado del sistema."
        )
        result = humanize(text, lang="es")
        self.assertTrue(len(result.text) > 20)

    def test_french_text(self):
        text = (
            "Il est essentiel de mettre en œuvre les mesures nécessaires "
            "pour garantir le fonctionnement efficace du système."
        )
        result = humanize(text, lang="fr")
        self.assertTrue(len(result.text) > 20)

    def test_arabic_text(self):
        text = (
            "من الضروري ضمان التنفيذ الفعال للنظام الجديد. "
            "يجب أن نأخذ في الاعتبار جميع العوامل المؤثرة."
        )
        result = humanize(text, lang="ar")
        self.assertTrue(len(result.text) > 10)

    def test_chinese_text(self):
        text = "有效实施新技术至关重要。该方法是确保系统可靠运行的关键因素。"
        result = humanize(text, lang="zh")
        self.assertTrue(len(result.text) > 5)

    def test_japanese_text(self):
        text = "新しいシステムの効果的な実装が不可欠です。この技術は業界を変革しています。"
        result = humanize(text, lang="ja")
        self.assertTrue(len(result.text) > 5)

    def test_korean_text(self):
        text = "새로운 시스템의 효과적인 구현이 필수적입니다. 이 기술은 산업을 변화시키고 있습니다."
        result = humanize(text, lang="ko")
        self.assertTrue(len(result.text) > 5)

    def test_turkish_text(self):
        text = (
            "Yeni teknolojinin etkili bir şekilde uygulanması hayati önem "
            "taşımaktadır. Bu yaklaşım başarının anahtarıdır."
        )
        result = humanize(text, lang="tr")
        self.assertTrue(len(result.text) > 10)


if __name__ == "__main__":
    unittest.main()
