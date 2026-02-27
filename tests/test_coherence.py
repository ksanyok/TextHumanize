"""Тесты для анализа когерентности (coherence.py)."""

from texthumanize.coherence import CoherenceAnalyzer, CoherenceReport

COHERENT_TEXT = (
    "Machine learning is a subset of artificial intelligence. "
    "It allows systems to learn from data without explicit programming. "
    "These algorithms improve their performance over time through experience. "
    "As a result, machine learning has become essential in many industries. "
    "\n\n"
    "Moreover, deep learning represents a further advancement. "
    "Deep neural networks can process complex patterns in data. "
    "This technology drives innovations in image recognition and language processing. "
    "Consequently, deep learning applications are rapidly expanding."
)

INCOHERENT_TEXT = (
    "The weather is sunny today. "
    "Python is a programming language. "
    "Cats are independent animals. "
    "Stock markets fluctuated yesterday. "
    "\n\n"
    "Basketball requires agility and height. "
    "Quantum physics describes subatomic particles. "
    "Chocolate cake is best served warm. "
    "The treaty was signed in 1648."
)


class TestCoherenceAnalyzer:
    """Тесты для CoherenceAnalyzer."""

    def test_analyze_returns_report(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        assert isinstance(report, CoherenceReport)

    def test_overall_range(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        assert 0.0 <= report.overall <= 1.0

    def test_coherent_scores_higher(self):
        """Связный текст должен получать более высокий скор."""
        analyzer = CoherenceAnalyzer(lang="en")
        coh = analyzer.analyze(COHERENT_TEXT)
        incoh = analyzer.analyze(INCOHERENT_TEXT)
        assert coh.overall >= incoh.overall

    def test_lexical_cohesion_range(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        assert 0.0 <= report.lexical_cohesion <= 1.0

    def test_transition_score(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        # Связный текст содержит переходные слова
        assert report.transition_score > 0.0

    def test_topic_consistency_range(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        assert 0.0 <= report.topic_consistency <= 1.0

    def test_paragraph_count(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(COHERENT_TEXT)
        assert report.paragraph_count == 2

    def test_issues_type(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze(INCOHERENT_TEXT)
        assert isinstance(report.issues, list)

    def test_empty_text(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze("")
        assert isinstance(report, CoherenceReport)

    def test_single_sentence(self):
        analyzer = CoherenceAnalyzer(lang="en")
        report = analyzer.analyze("Just one sentence.")
        assert isinstance(report, CoherenceReport)

    def test_russian_text(self):
        ru_text = (
            "Машинное обучение — подраздел искусственного интеллекта. "
            "Оно позволяет системам учиться на данных. "
            "Кроме того, алгоритмы улучшаются со временем."
        )
        analyzer = CoherenceAnalyzer(lang="ru")
        report = analyzer.analyze(ru_text)
        assert isinstance(report, CoherenceReport)
        assert report.overall > 0.0
