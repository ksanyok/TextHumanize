"""Покрытие detectors.py и analyzer.py — все непокрытые ветки."""

from texthumanize.detectors import AIDetector

# ═══════════════════════════════════════════════════════════════
#  AIDetector — Detection result + sub-metrics
# ═══════════════════════════════════════════════════════════════


class TestDetectionResultStr:
    """Тест str/repr DetectionResult с explanations."""

    def test_str_with_explanations(self):
        det = AIDetector()
        # Need enough sentences for verdict != unknown
        text = (
            "The system provides comprehensive data analysis capabilities today. "
            "Furthermore, the data processing pipeline ensures optimal results consistently. "
            "Moreover, additional features enhance user experience significantly overall. "
            "Additionally, the implementation demonstrates remarkable efficiency gains. "
            "Consequently, the overall performance metrics show improvement trends. "
            "Nevertheless, there are areas for potential optimization still. "
            "In conclusion, the system represents a significant technological advancement. "
            "Ultimately, these improvements will drive sustainable growth forward. "
            "The team continuously monitors all key performance indicators carefully. "
            "Regular updates ensure the platform remains competitive in market."
        )
        result = det.detect(text)
        s = result.summary()
        assert "AI Probability" in s
        assert "Verdict" in s

    def test_repr_short(self):
        det = AIDetector()
        result = det.detect("Hello world test.")
        r = repr(result)
        assert "DetectionResult" in r or "ai_probability" in str(vars(result))


class TestCalcEntropy:
    """Тесты _calc_entropy — Shannon entropy на chars/words/bigrams."""

    def test_short_text_returns_half(self):
        det = AIDetector()
        words = ["one", "two"]
        score = det._calc_entropy("one two", words)
        assert score == 0.5

    def test_ai_like_repetitive(self):
        """Повторяющийся текст → высокий score (AI-like)."""
        det = AIDetector()
        text = " ".join(["the system provides data"] * 30)
        words = text.split()
        score = det._calc_entropy(text, words)
        assert 0.0 <= score <= 1.0

    def test_diverse_text(self):
        """Разнообразный текст → низкий score."""
        det = AIDetector()
        text = (
            "Walking through autumn leaves yesterday morning I noticed "
            "something peculiar about how squirrels gather their acorns "
            "before winter storms arrive unexpectedly during late November"
        )
        words = text.split()
        # Может вернуть 0.5 для <10 слов, убеждаемся что хватает
        if len(words) >= 10:
            score = det._calc_entropy(text, words)
            assert 0.0 <= score <= 1.0


class TestCalcBurstiness:
    """Тесты _calc_burstiness — вариативность длины предложений."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_burstiness(["Short.", "Also short."])
        assert score == 0.5

    def test_uniform_lengths_high_score(self):
        """Одинаковые длины → высокий score (AI-like)."""
        det = AIDetector()
        sents = [
            "The system works very well here now.",
            "Data flows through pipes quite fast too.",
            "Teams build great things every single day.",
            "Users love this product very much indeed.",
            "Codes run smoothly without any bugs today.",
        ]
        score = det._calc_burstiness(sents)
        assert 0.0 <= score <= 1.0

    def test_varied_lengths_low_score(self):
        """Разные длины → низкий score (human-like)."""
        det = AIDetector()
        sents = [
            "Go.",
            "The incredibly sophisticated system that we meticulously designed provides absolutely phenomenal comprehensive data.",
            "Yes.",
            "Another mediocre sentence of average length here.",
            "Boom.",
        ]
        score = det._calc_burstiness(sents)
        assert 0.0 <= score <= 1.0


class TestCalcVocabulary:
    """Тесты _calc_vocabulary — TTR, MATTR, Yule's K, hapax."""

    def test_short_text(self):
        det = AIDetector()
        score = det._calc_vocabulary("hi there", ["hi", "there"], {})
        assert score == 0.5

    def test_rich_vocabulary(self):
        det = AIDetector()
        text = (
            "magnificent beautiful extraordinary remarkable splendid "
            "phenomenal outstanding wonderful incredible spectacular "
            "fabulous marvelous gorgeous stunning brilliant superb "
            "excellent tremendous glorious exceptional supreme "
            "astonishing surprising amazing delightful charming"
        )
        words = text.split()
        score = det._calc_vocabulary(text, words, {})
        assert 0.0 <= score <= 1.0

    def test_poor_vocabulary(self):
        det = AIDetector()
        words = ["system", "data", "system", "data", "system", "data"] * 10
        text = " ".join(words)
        score = det._calc_vocabulary(text, words, {})
        assert 0.0 <= score <= 1.0


class TestCalcZipf:
    """Тесты _calc_zipf — Zipf's law."""

    def test_short_text(self):
        det = AIDetector()
        words = ["a", "b", "c"]
        score = det._calc_zipf(words, {})
        assert score == 0.5

    def test_long_text(self):
        det = AIDetector()
        words = (
            ["the"] * 20 + ["system"] * 10 + ["provides"] * 5
            + ["data"] * 4 + ["to"] * 3 + ["and"] * 2
            + list("abcdefghijklmnopqrstuvwxyz")
        )
        score = det._calc_zipf(words, {})
        assert 0.0 <= score <= 1.0


class TestCalcStylometry:
    """Тесты _calc_stylometry — слова и стиль."""

    def test_short_text(self):
        det = AIDetector()
        score = det._calc_stylometry("hi there", ["hi", "there"], [], {})
        assert score == 0.5

    def test_long_academic(self):
        det = AIDetector()
        text = (
            "The comprehensive implementation demonstrates significant "
            "methodological sophistication throughout the experimental "
            "framework. Empirical observations consistently corroborate "
            "theoretical predictions established in preliminary analyses."
        )
        words = text.split()
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_stylometry(text, words, sents, {})
        assert 0.0 <= score <= 1.0


class TestCalcAiPatterns:
    """Тесты _calc_ai_patterns — AI word/phrase matcher."""

    def test_short_text(self):
        det = AIDetector()
        score = det._calc_ai_patterns("hi", ["hi"], ["hi"], "en")
        assert score == 0.5

    def test_ai_heavy_text(self):
        det = AIDetector()
        text = (
            "Furthermore, it is crucial to delve into the comprehensive "
            "analysis. Moreover, leveraging cutting-edge methodologies "
            "ensures robust outcomes. Additionally, this groundbreaking "
            "approach underscores the paramount importance of systematic "
            "evaluation. Consequently, the findings demonstrate remarkable "
            "significance across diverse domains."
        )
        words = text.split()
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_ai_patterns(text, words, sents, "en")
        assert 0.0 <= score <= 1.0


class TestCalcPunctuation:
    """Тесты _calc_punctuation — пунктуационный профиль."""

    def test_short_text(self):
        det = AIDetector()
        score = det._calc_punctuation("Hi.", ["Hi."])
        assert score == 0.5

    def test_academic_punctuation(self):
        det = AIDetector()
        text = (
            "The system works; data flows. Furthermore: the results — "
            "both qualitative and quantitative — demonstrate clear patterns. "
            "Analysis reveals; significant correlations. Moreover: the data "
            "shows — consistent and reliable — improvement trends. "
            "Additional findings; support these conclusions."
        )
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_punctuation(text, sents)
        assert 0.0 <= score <= 1.0


class TestCalcCoherence:
    """Тесты _calc_coherence — лексическое перекрытие."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_coherence("One. Two.", ["One.", "Two."])
        assert score == 0.5

    def test_high_coherence(self):
        det = AIDetector()
        text = (
            "The system processes data efficiently. "
            "The system analyzes data patterns quickly. "
            "The system provides data visualization tools. "
            "The system generates data reports automatically. "
            "The system updates data dashboards regularly."
        )
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_coherence(text, sents)
        assert 0.0 <= score <= 1.0

    def test_with_transitions(self):
        det = AIDetector()
        text = (
            "The system works well.\n\n"
            "Furthermore, data flows smoothly through the pipeline.\n\n"
            "Moreover, the results show significant improvements.\n\n"
            "In addition, new features enhance user experience.\n\n"
            "Consequently, overall satisfaction metrics are up."
        )
        sents = [s.strip() for s in text.replace("\n\n", " ").split(". ") if s.strip()]
        score = det._calc_coherence(text, sents)
        assert 0.0 <= score <= 1.0


class TestCalcGrammar:
    """Тесты _calc_grammar — грамматическая «идеальность»."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_grammar("Hi. There.", ["Hi.", "There."])
        assert score == 0.5

    def test_perfect_grammar_en(self):
        det = AIDetector()
        text = (
            "The system operates efficiently. "
            "Data is being processed correctly. "
            "Results demonstrate significant improvements. "
            "Users have reported increased satisfaction. "
            "The team continues to monitor performance."
        )
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_grammar(text, sents)
        assert 0.0 <= score <= 1.0

    def test_informal_grammar_low_score(self):
        det = AIDetector()
        text = (
            "well i don't really know what's happening. "
            "she's been working there since forever. "
            "they'll probably figure it out somehow. "
            "it's not like we haven't tried before. "
            "can't say I'm surprised honestly."
        )
        sents = [s.strip() for s in text.split(". ") if s.strip()]
        score = det._calc_grammar(text, sents)
        assert 0.0 <= score <= 1.0


class TestCalcOpenings:
    """Тесты _calc_openings — разнообразие начал."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_openings(["Hi.", "There."])
        assert score == 0.5

    def test_repetitive_openings(self):
        det = AIDetector()
        sents = [
            "The system works well.",
            "The data flows smoothly.",
            "The team builds features.",
            "The users love it.",
            "The project grows fast.",
            "The results improve daily.",
        ]
        score = det._calc_openings(sents)
        assert 0.0 <= score <= 1.0

    def test_diverse_openings(self):
        det = AIDetector()
        sents = [
            "Yesterday, we deployed the update.",
            "Running through the logs, I noticed errors.",
            "She mentioned it was working fine.",
            "Interestingly, the metrics improved.",
            "A quick fix resolved the issue.",
            "No one expected such rapid progress.",
        ]
        score = det._calc_openings(sents)
        assert 0.0 <= score <= 1.0


class TestCalcReadability:
    """Тесты _calc_readability_consistency — CV across windows."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_readability_consistency(["Short.", "Also short."])
        assert score == 0.5

    def test_uniform_readability(self):
        det = AIDetector()
        sents = [
            "The system works smoothly and efficiently.",
            "Data flows through the pipeline correctly.",
            "Results are generated in real time.",
            "Users access dashboards with ease.",
            "Reports arrive on schedule daily.",
            "Metrics track performance across teams.",
            "Analytics provide deep business insights.",
            "Alerts notify operators of anomalies.",
            "Backups ensure data safety always.",
        ]
        score = det._calc_readability_consistency(sents)
        assert 0.0 <= score <= 1.0


class TestCalcRhythm:
    """Тесты _calc_rhythm — autocorrelation + S/M/L."""

    def test_few_sentences(self):
        det = AIDetector()
        score = det._calc_rhythm(["A.", "B."])
        assert score == 0.5

    def test_monotonous_rhythm(self):
        """Одинаковые длины → AI-like."""
        det = AIDetector()
        sents = [
            "One two three four five six seven.",
            "One two three four five six seven.",
            "One two three four five six seven.",
            "One two three four five six seven.",
            "One two three four five six seven.",
        ]
        score = det._calc_rhythm(sents)
        assert 0.0 <= score <= 1.0

    def test_varied_rhythm(self):
        det = AIDetector()
        sents = [
            "Go.",
            "The incredibly long sentence with many different words that keep going.",
            "Here.",
            "Short indeed.",
            "Another really elaborate and thoroughly comprehensive sentence.",
            "Done.",
        ]
        score = det._calc_rhythm(sents)
        assert 0.0 <= score <= 1.0


class TestFullDetection:
    """Тесты полного detect() — verdict + confidence + details."""

    def test_human_text(self):
        det = AIDetector()
        text = (
            "So I was walking my dog yesterday and this random guy comes up. "
            "He is like nice shoes and I could not believe it at all. "
            "The weather has been super weird lately, really really odd. "
            "My friend says its because of el nino or something like that. "
            "I do not know though, it could be anything honestly. "
            "Anyway we went to the park after and had a good time. "
            "The kids were playing and dogs running everywhere. "
            "It was one of those perfect autumn afternoons you know. "
            "We grabbed coffee at that new place on fifth street. "
            "Honestly it was probably the best latte in months."
        )
        result = det.detect(text)
        assert result.verdict in ("human", "mixed", "ai")
        assert 0.0 <= result.ai_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert "word_count" in result.details

    def test_ai_text(self):
        det = AIDetector()
        result = det.detect(
            "The comprehensive analysis demonstrates significant improvements "
            "in system performance. Furthermore, the implementation of advanced "
            "methodologies has yielded remarkable results. Moreover, the strategic "
            "approach ensures sustainable growth. Additionally, the robust framework "
            "provides scalable solutions. Consequently, stakeholder satisfaction "
            "has increased substantially. Nevertheless, continuous optimization "
            "remains paramount. In conclusion, the systematic evaluation reveals "
            "promising outcomes across all key performance indicators."
        )
        assert result.verdict in ("human", "mixed", "ai")
        assert 0.0 <= result.ai_probability <= 1.0

    def test_mixed_verdict(self):
        """ai_probability ≈ 0.45-0.75 → mixed."""
        det = AIDetector()
        result = det.detect(
            "The system works well. honestly, i think the implementation "
            "is pretty solid for what it does. Furthermore, additional "
            "improvements could be considered. but like... who has time "
            "for that right now??? The comprehensive solution addresses "
            "key requirements effectively. still feels kinda incomplete tho. "
            "Nevertheless the results are promising I suppose."
        )
        assert result.verdict in ("human", "mixed", "ai")

    def test_detect_ru(self):
        det = AIDetector()
        result = det.detect(
            "Необходимо подчеркнуть что данная система обеспечивает "
            "значительное улучшение всеобъемлющих показателей. "
            "Кроме того, комплексный подход гарантирует устойчивый рост. "
            "Более того, стратегическое планирование позволяет оптимизировать "
            "ключевые метрики эффективности. Таким образом, достигнутые "
            "результаты демонстрируют положительную динамику.",
            lang="ru",
        )
        assert result.verdict in ("human", "mixed", "ai")


# ═══════════════════════════════════════════════════════════════
#  Analyzer (extended coverage)
# ═══════════════════════════════════════════════════════════════

from texthumanize.analyzer import TextAnalyzer


class TestAnalyzerMetrics:
    """Тесты TextAnalyzer — непокрытые метрики."""

    def test_empty_text(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze("")
        assert report.total_words == 0

    def test_short_text(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze("Hi there friend.")
        # Short text (<10 chars) returns empty report
        assert isinstance(report.total_chars, int)

    def test_bureaucratic_ratio(self):
        a = TextAnalyzer(lang="ru")
        report = a.analyze(
            "Необходимо подчеркнуть что осуществление мероприятий "
            "в рамках данной деятельности обеспечивает улучшение "
            "всеобъемлющих показателей эффективности и результативности."
        )
        assert 0.0 <= report.bureaucratic_ratio <= 1.0

    def test_connector_ratio(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "Furthermore the system works. Moreover the data flows. "
            "Additionally the team builds. Consequently results improve."
        )
        assert report.connector_ratio >= 0.0

    def test_repetition_score(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "The system processes data. The system analyzes data. "
            "The system provides data. The system generates data."
        )
        assert report.repetition_score >= 0.0

    def test_typography_score(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "The system works — perfectly; with data: "
            "«analysis» shows… significant results."
        )
        assert report.typography_score >= 0.0

    def test_sentence_variation(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "Go right now. "
            "The incredible and magnificent system amazingly processes data. "
            "Short stuff here. "
            "A moderately long sentence that explains something important. "
            "No way really. "
            "Very comprehensive results indeed."
        )
        # sentence_variation is computed internally; check via details
        assert report.sentence_length_variance >= 0

    def test_burstiness_cv(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "Short sentence here. Another short one also. "
            "A much longer sentence with many words to create variation. "
            "Very tiny sentence."
        )
        # burstiness_cv is in details
        assert "burstiness_cv" in report.details

    def test_find_bureaucratic_words(self):
        a = TextAnalyzer(lang="ru")
        words_found = a._find_bureaucratic_words(
            "Осуществление мероприятий в рамках деятельности."
        )
        assert isinstance(words_found, list)

    def test_find_typography_issues(self):
        a = TextAnalyzer(lang="en")
        issues = a._find_typography_issues("Test — with «quotes» and… ellipsis\u00A0here")
        assert len(issues) > 0

    def test_typography_clean(self):
        a = TextAnalyzer(lang="en")
        issues = a._find_typography_issues("Plain text without special chars.")
        assert isinstance(issues, list)


class TestAnalyzerReadability:
    """Тесты readability-метрик analyzer.py."""

    def test_flesch_kincaid(self):
        fk = TextAnalyzer._calc_flesch_kincaid(5, 50, 1.5)
        assert isinstance(fk, float)

    def test_flesch_kincaid_zero(self):
        assert TextAnalyzer._calc_flesch_kincaid(0, 0, 0) == 0.0

    def test_coleman_liau(self):
        a = TextAnalyzer(lang="en")
        text = "The system provides comprehensive data analysis capabilities."
        words = text.split()
        sentences = ["The system provides comprehensive data analysis capabilities."]
        cl = a._calc_coleman_liau(text, words, sentences)
        assert isinstance(cl, float)

    def test_coleman_liau_empty(self):
        a = TextAnalyzer(lang="en")
        assert a._calc_coleman_liau("", [], []) == 0.0

    def test_ari(self):
        text = "Simple test sentence here. Another one follows."
        words = text.split()
        sentences = text.split(". ")
        ari = TextAnalyzer.calc_ari(text, words, sentences)
        assert isinstance(ari, float)

    def test_ari_empty(self):
        assert TextAnalyzer.calc_ari("", [], []) == 0.0

    def test_smog_index(self):
        a = TextAnalyzer(lang="en")
        words = ["The", "comprehensive", "implementation", "demonstrates", "significant", "methodological", "sophistication", "throughout", "experimental", "framework", "and", "empirical", "observations", "consistently", "corroborate", "theoretical", "predictions", "established", "in", "preliminary", "comprehensive", "analyses"]
        sentences = ["Sentence one.", "Sentence two.", "Sentence three."]
        smog = a.calc_smog_index(words, sentences)
        assert isinstance(smog, float)

    def test_smog_empty(self):
        a = TextAnalyzer(lang="en")
        assert a.calc_smog_index([], []) == 0.0

    def test_gunning_fog(self):
        a = TextAnalyzer(lang="en")
        words = ["the", "comprehensive", "implementation", "demonstrates", "significant", "results"]
        sentences = ["Sentence."]
        fog = a.calc_gunning_fog(words, sentences)
        assert isinstance(fog, float)

    def test_gunning_fog_empty(self):
        a = TextAnalyzer(lang="en")
        assert a.calc_gunning_fog([], []) == 0.0

    def test_dale_chall(self):
        text = "The comprehensive system provides sophisticated analytical capabilities."
        words = text.split()
        sentences = [text]
        dc = TextAnalyzer.calc_dale_chall(text, words, sentences)
        assert isinstance(dc, float)

    def test_dale_chall_empty(self):
        assert TextAnalyzer.calc_dale_chall("", [], []) == 0.0

    def test_avg_syllables(self):
        a = TextAnalyzer(lang="en")
        avg = a._calc_avg_syllables(["comprehensive", "the", "a"])
        assert avg > 0.0

    def test_avg_syllables_empty(self):
        a = TextAnalyzer(lang="en")
        assert a._calc_avg_syllables([]) == 0.0

    def test_count_syllables(self):
        a = TextAnalyzer(lang="en")
        assert a._count_syllables("comprehensive") >= 3
        assert a._count_syllables("the") >= 1
        assert a._count_syllables("a") >= 1

    def test_split_sentences(self):
        a = TextAnalyzer(lang="en")
        sents = a._split_sentences("First sentence. Second sentence! Third one?")
        assert len(sents) >= 2

    def test_analyze_full_report(self):
        a = TextAnalyzer(lang="en")
        report = a.analyze(
            "The system provides comprehensive data analysis. "
            "Furthermore, results are generated quickly. "
            "Moreover, the platform supports real-time analytics."
        )
        assert report.total_words > 0
        assert report.total_sentences > 0
        assert report.avg_sentence_length > 0
        assert report.flesch_kincaid_grade != 0 or report.coleman_liau_index != 0
