"""Тесты для модуля AI-детекции (detectors.py)."""

import pytest
from texthumanize.detectors import AIDetector, DetectionResult, detect_ai, detect_ai_batch


# Типичный AI-текст (очень однородный, формальный, без ошибок)
AI_TEXT_EN = (
    "Artificial intelligence has revolutionized the way we approach complex problems. "
    "Furthermore, it enables machines to learn from data and make intelligent decisions. "
    "Moreover, the technology continues to advance at an unprecedented pace. "
    "Additionally, it is transforming industries and creating new opportunities for innovation. "
    "Consequently, organizations are increasingly adopting AI solutions. "
    "Furthermore, the implementation of machine learning algorithms has demonstrated "
    "remarkable efficacy in various domains. Subsequently, researchers have developed "
    "sophisticated methodologies that leverage deep learning architectures. "
    "It is important to note that these advancements have significantly impacted "
    "the technological landscape. In conclusion, artificial intelligence represents "
    "a transformative force in modern society."
)

# Человеческий текст (разная длина, разговорный, неидеальный)
HUMAN_TEXT_EN = (
    "So I tried this new coffee shop downtown yesterday - wow, what a find! "
    "The barista made the best latte I've had in years. Seriously. "
    "I mean, the foam was perfect, the temp was just right... you know? "
    "My friend Sarah says it's overpriced, but whatever. "
    "I'll take good coffee over cheap stuff any day. "
    "They also had these amazing pastries. Took one home for later. "
    "Can't wait to go back! Maybe this weekend? "
    "Oh and they play great music too - lots of jazz and indie stuff. "
    "The only downside: parking is terrible. Like really bad. "
    "But hey, that's downtown for you."
)

AI_TEXT_RU = (
    "Искусственный интеллект кардинально изменил подход к решению сложных задач. "
    "Более того, данная технология позволяет машинам обучаться на данных "
    "и принимать интеллектуальные решения. Кроме того, технологии продолжают "
    "развиваться беспрецедентными темпами. В дополнение к этому, они "
    "трансформируют отрасли и создают новые возможности для инноваций. "
    "Следовательно, организации всё активнее внедряют решения на основе "
    "искусственного интеллекта. Необходимо отметить, что данные достижения "
    "оказали значительное влияние на технологический ландшафт. "
    "В заключение следует подчеркнуть, что искусственный интеллект "
    "представляет собой трансформирующую силу современного общества."
)


class TestDetectionResult:
    """Тесты для DetectionResult."""

    def test_default_values(self):
        r = DetectionResult()
        assert r.ai_probability == 0.0
        assert r.confidence == 0.0
        assert r.verdict == "unknown"

    def test_human_probability(self):
        r = DetectionResult(ai_probability=0.3)
        assert abs(r.human_probability - 0.7) < 0.001

    def test_summary_format(self):
        r = DetectionResult(ai_probability=0.8, verdict="ai", confidence=0.9)
        s = r.summary()
        assert "AI Probability" in s
        assert "ai" in s
        assert "Entropy" in s


class TestAIDetector:
    """Тесты для AIDetector."""

    def test_detect_returns_result(self):
        det = AIDetector(lang="en")
        result = det.detect(AI_TEXT_EN)
        assert isinstance(result, DetectionResult)
        assert 0.0 <= result.ai_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.verdict in ("human", "mixed", "ai", "unknown")

    def test_ai_text_scores_higher(self):
        """AI-текст должен получать более высокий скор, чем человеческий."""
        det = AIDetector(lang="en")
        ai_result = det.detect(AI_TEXT_EN)
        human_result = det.detect(HUMAN_TEXT_EN)
        assert ai_result.ai_probability > human_result.ai_probability

    def test_short_text_low_confidence(self):
        """На коротких текстах уверенность должна быть низкой."""
        det = AIDetector(lang="en")
        result = det.detect("Hello world.")
        assert result.confidence < 0.5

    def test_empty_text(self):
        det = AIDetector(lang="en")
        result = det.detect("")
        assert result.ai_probability == 0.0 or result.verdict == "unknown"

    def test_russian_detection(self):
        det = AIDetector(lang="ru")
        result = det.detect(AI_TEXT_RU)
        assert isinstance(result, DetectionResult)
        assert result.ai_probability > 0.0

    def test_all_metrics_populated(self):
        det = AIDetector(lang="en")
        result = det.detect(AI_TEXT_EN)
        # Все 12 метрик должны быть заполнены (или хотя бы не все нулевые)
        metrics = [
            result.entropy_score, result.burstiness_score,
            result.vocabulary_score, result.zipf_score,
            result.stylometry_score, result.pattern_score,
            result.punctuation_score, result.coherence_score,
            result.grammar_score, result.opening_score,
            result.readability_score, result.rhythm_score,
        ]
        assert any(m > 0 for m in metrics), "Хотя бы одна метрика должна быть > 0"

    def test_explanations_for_ai_text(self):
        det = AIDetector(lang="en")
        result = det.detect(AI_TEXT_EN)
        assert isinstance(result.explanations, list)


class TestModuleLevelFunctions:
    """Тесты для module-level detect_ai / detect_ai_batch."""

    def test_detect_ai_function(self):
        result = detect_ai(AI_TEXT_EN, lang="en")
        assert isinstance(result, DetectionResult)

    def test_detect_ai_batch_function(self):
        results = detect_ai_batch([AI_TEXT_EN, HUMAN_TEXT_EN], lang="en")
        assert len(results) == 2
        assert all(isinstance(r, DetectionResult) for r in results)

    def test_detect_ai_auto_lang(self):
        result = detect_ai(AI_TEXT_RU)
        assert isinstance(result, DetectionResult)
