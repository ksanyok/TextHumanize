"""AI Text Detector — статистический детектор AI-сгенерированного текста.

Превосходит наивные подходы GPTZero/Originality.ai за счёт комбинации
12+ метрик без зависимости от нейросетей. Работает полностью локально.

Метрики:
1. Энтропия текста (character-level, word-level, conditional)
2. Burstiness (вариативность длины предложений и абзацев)
3. Лексическое разнообразие (TTR, MATTR, Yule's K, Hapax ratio)
4. Распределение Zipf (соответствие закону Ципфа)
5. Стилометрия (функциональные слова, пунктуация)
6. AI-паттерны (overused слова, коннекторы)
7. Ритм текста (syllable patterns, stress)
8. Пунктуационный профиль
9. Когерентность (однородность абзацев)
10. Грамматическая «идеальность»
11. Sentence opening diversity
12. Readability consistency

Итоговый скор: 0.0 (точно человек) — 1.0 (точно AI).
"""

from __future__ import annotations

import logging
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from texthumanize.lang import get_lang_pack
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  РЕЗУЛЬТАТ ДЕТЕКЦИИ
# ═══════════════════════════════════════════════════════════════

@dataclass
class DetectionResult:
    """Результат AI-детекции текста."""

    # Основной скор
    ai_probability: float = 0.0      # 0.0–1.0 (главный показатель)
    confidence: float = 0.0          # 0.0–1.0 (уверенность в оценке)
    verdict: str = "unknown"         # "human", "mixed", "ai", "unknown"

    # Детальные метрики (каждая 0.0–1.0, где 1.0 = "типично AI")
    entropy_score: float = 0.0       # Энтропия
    burstiness_score: float = 0.0    # Вариативность длины
    vocabulary_score: float = 0.0    # Лексическое разнообразие
    zipf_score: float = 0.0          # Соответствие Zipf
    stylometry_score: float = 0.0    # Стилометрический анализ
    pattern_score: float = 0.0       # AI-паттерны
    punctuation_score: float = 0.0   # Пунктуационный профиль
    coherence_score: float = 0.0     # Когерентность
    grammar_score: float = 0.0       # Грамматическая идеальность
    opening_score: float = 0.0       # Разнообразие начал
    readability_score: float = 0.0   # Стабильность readability
    rhythm_score: float = 0.0        # Ритм текста
    perplexity_score: float = 0.0    # N-gram perplexity
    discourse_score: float = 0.0     # Дискурсивная структура
    semantic_rep_score: float = 0.0  # Семантические повторы
    entity_score: float = 0.0        # Специфичность упоминаний
    voice_score: float = 0.0         # Passive vs active voice
    topic_sent_score: float = 0.0    # Topic sentence паттерн

    # Домен и адаптация
    detected_domain: str = "general"  # academic/news/blog/legal/social/code_docs/general

    # Подробности
    details: dict[str, Any] = field(default_factory=dict)

    # Текстовые объяснения
    explanations: list[str] = field(default_factory=list)

    @property
    def human_probability(self) -> float:
        """Вероятность, что текст написан человеком."""
        return 1.0 - self.ai_probability

    def summary(self) -> str:
        """Краткое описание результата."""
        lines = [
            f"AI Probability: {self.ai_probability:.1%}",
            f"Verdict: {self.verdict}",
            f"Confidence: {self.confidence:.1%}",
            f"Domain: {self.detected_domain}",
            "",
            "Feature Scores (0=human, 1=AI):",
            f"  Entropy:        {self.entropy_score:.3f}",
            f"  Burstiness:     {self.burstiness_score:.3f}",
            f"  Vocabulary:     {self.vocabulary_score:.3f}",
            f"  Zipf Law:       {self.zipf_score:.3f}",
            f"  Stylometry:     {self.stylometry_score:.3f}",
            f"  AI Patterns:    {self.pattern_score:.3f}",
            f"  Punctuation:    {self.punctuation_score:.3f}",
            f"  Coherence:      {self.coherence_score:.3f}",
            f"  Grammar:        {self.grammar_score:.3f}",
            f"  Openings:       {self.opening_score:.3f}",
            f"  Readability:    {self.readability_score:.3f}",
            f"  Rhythm:         {self.rhythm_score:.3f}",
            f"  Perplexity:     {self.perplexity_score:.3f}",
            f"  Discourse:      {self.discourse_score:.3f}",
            f"  Semantic Rep:   {self.semantic_rep_score:.3f}",
            f"  Entity:         {self.entity_score:.3f}",
            f"  Voice:          {self.voice_score:.3f}",
            f"  Topic Sent:     {self.topic_sent_score:.3f}",
        ]
        if self.explanations:
            lines.append("")
            lines.append("Key Findings:")
            for exp in self.explanations[:10]:
                lines.append(f"  • {exp}")
        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
#  AI-ХАРАКТЕРНЫЕ СЛОВА (языково-специфичные)
# ═══════════════════════════════════════════════════════════════

_AI_WORDS = {
    "en": {
        "adverbs": {
            "significantly", "substantially", "considerably", "remarkably",
            "exceptionally", "tremendously", "profoundly", "fundamentally",
            "essentially", "particularly", "specifically", "notably",
            "increasingly", "effectively", "ultimately", "consequently",
            "inherently", "intrinsically", "predominantly", "invariably",
        },
        "adjectives": {
            "comprehensive", "crucial", "pivotal", "paramount",
            "innovative", "robust", "seamless", "holistic",
            "cutting-edge", "state-of-the-art", "groundbreaking",
            "transformative", "synergistic", "multifaceted",
            "nuanced", "intricate", "meticulous", "imperative",
        },
        "verbs": {
            "utilize", "leverage", "facilitate", "implement",
            "foster", "enhance", "streamline", "optimize",
            "underscore", "delve", "navigate", "harness",
            "exemplify", "spearhead", "revolutionize", "catalyze",
            "necessitate", "elucidate", "delineate", "substantiate",
        },
        "connectors": {
            "however", "furthermore", "moreover", "nevertheless",
            "nonetheless", "additionally", "consequently", "therefore",
            "thus", "hence", "accordingly", "subsequently",
            "in conclusion", "to summarize", "in essence",
            "it is important to note", "it is worth mentioning",
        },
        "phrases": {
            "plays a crucial role", "is of paramount importance",
            "in today's world", "in the modern era",
            "a wide range of", "it goes without saying",
            "in light of", "due to the fact that",
            "at the end of the day", "it is important to note that",
            "it should be noted that", "it is worth mentioning that",
            "first and foremost", "last but not least",
            "in order to", "with regard to", "as a matter of fact",
        },
    },
    "ru": {
        "adverbs": {
            "значительно", "существенно", "чрезвычайно", "безусловно",
            "несомненно", "неоспоримо", "принципиально", "непосредственно",
            "кардинально", "всесторонне", "исключительно", "преимущественно",
        },
        "adjectives": {
            "комплексный", "всеобъемлющий", "инновационный", "ключевой",
            "основополагающий", "первостепенный", "фундаментальный",
            "принципиальный", "многогранный", "всесторонний",
        },
        "verbs": {
            "осуществлять", "реализовывать", "способствовать",
            "обеспечивать", "характеризоваться", "представлять собой",
            "являться", "функционировать", "оказывать влияние",
        },
        "connectors": {
            "однако", "тем не менее", "вместе с тем", "кроме того",
            "более того", "помимо этого", "таким образом",
            "следовательно", "безусловно", "несомненно",
            "в заключение", "подводя итог", "исходя из вышесказанного",
            "необходимо отметить", "стоит подчеркнуть",
        },
        "phrases": {
            "играет ключевую роль", "имеет первостепенное значение",
            "в современном мире", "на сегодняшний день",
            "широкий спектр", "не подлежит сомнению",
            "является одним из", "представляет собой",
            "в рамках данного", "с учётом того что",
            "необходимо подчеркнуть", "следует отметить",
        },
    },
    "uk": {
        "adverbs": {
            "значно", "суттєво", "надзвичайно", "безумовно",
            "безсумнівно", "незаперечно", "принципово", "безпосередньо",
            "кардинально", "всебічно", "виключно", "переважно",
        },
        "adjectives": {
            "комплексний", "всеосяжний", "інноваційний", "ключовий",
            "основоположний", "першочерговий", "фундаментальний",
            "принциповий", "багатогранний", "всебічний",
        },
        "connectors": {
            "однак", "тим не менш", "разом з тим", "крім того",
            "більш того", "окрім цього", "таким чином",
            "отже", "безумовно", "безсумнівно",
            "на завершення", "підсумовуючи",
            "необхідно зазначити", "варто підкреслити",
        },
        "phrases": {
            "відіграє ключову роль", "має першочергове значення",
            "у сучасному світі", "на сьогоднішній день",
            "широкий спектр", "є одним з",
            "являє собою", "у рамках даного",
        },
    },
}

# ═══════════════════════════════════════════════════════════════
#  ОСНОВНОЙ ДЕТЕКТОР
# ═══════════════════════════════════════════════════════════════

class AIDetector:
    """Комплексный статистический детектор AI-сгенерированного текста.

    Использует 12 независимых метрик без ML-зависимостей.
    Все вычисления — чистая статистика и лингвистический анализ.
    """

    # Веса метрик (калиброваны для максимальной точности)
    _WEIGHTS = {
        "pattern": 0.20,           # AI patterns — самый сильный сигнал
        "burstiness": 0.14,        # Сильный сигнал: AI = равномерные предложения
        "stylometry": 0.09,        # Хорошая дискриминация (0.65 vs 0.19)
        "voice": 0.08,             # Отличная дискриминация (0.76 vs 0.00)
        "entity": 0.07,            # Хорошая (0.69 vs 0.17)
        "opening": 0.06,
        "grammar": 0.05,
        "entropy": 0.04,
        "discourse": 0.04,         # Дискурсивная структура
        "vocabulary": 0.04,
        "rhythm": 0.04,
        "perplexity": 0.03,
        "semantic_rep": 0.03,      # Семантические повторы
        "topic_sentence": 0.02,
        "readability": 0.02,       # Слабая дискриминация (~0.50 для всех)
        "punctuation": 0.02,       # Слабая дискриминация
        "coherence": 0.02,         # Слабая дискриминация
        "zipf": 0.01,              # Ненадёжен для коротких текстов
    }

    # Domain-specific weight adjustments
    _DOMAIN_WEIGHT_MODS: dict[str, dict[str, float]] = {
        "academic": {
            "grammar": 0.02,       # Academic text is naturally formal
            "voice": 0.01,         # Passive is normal in academic
            "pattern": -0.04,      # Formal words are expected
            "entity": -0.02,       # Less specific by nature
            "burstiness": 0.03,    # More uniform is normal
        },
        "news": {
            "entity": 0.03,        # News should have specific refs
            "discourse": -0.02,    # Inverted pyramid is normal
            "voice": 0.02,         # Active voice expected
        },
        "blog": {
            "entity": 0.02,
            "grammar": 0.03,       # Perfect grammar is suspicious
            "pattern": 0.03,       # AI patterns stand out more
        },
        "legal": {
            "grammar": 0.01,
            "voice": 0.01,         # Passive is standard
            "pattern": -0.06,      # Formal language is expected
            "vocabulary": -0.03,   # Repetitive vocabulary is normal
        },
        "social": {
            "grammar": 0.04,       # Perfect grammar = AI
            "pattern": 0.04,       # Formal patterns = AI
            "burstiness": 0.03,    # Uniform = very AI
            "discourse": 0.03,     # Rigid structure = AI
        },
        "code_docs": {
            "voice": 0.01,
            "pattern": -0.05,      # Technical language is expected
            "readability": -0.02,  # Uniform readability is normal
        },
    }

    @staticmethod
    def _detect_domain(text: str, words: list[str]) -> str:
        """Auto-detect text domain for adaptive thresholds.

        Returns: 'academic', 'news', 'blog', 'legal', 'social', 'code_docs', or 'general'
        """
        text_lower = text.lower()
        total = len(words) or 1

        # Academic markers
        academic_words = {
            "hypothesis", "methodology", "findings", "empirical",
            "theoretical", "correlation", "literature", "et al",
            "framework", "paradigm", "variables", "significant",
            "гипотеза", "методология", "эмпирический", "корреляция",
        }
        academic_count = sum(1 for w in words if w.lower().strip('.,;:') in academic_words)
        if academic_count / total > 0.02:
            return "academic"

        # Legal markers
        legal_words = {
            "herein", "thereof", "pursuant", "notwithstanding",
            "hereunder", "aforementioned", "jurisdiction",
            "warrant", "plaintiff", "defendant", "statute",
            "настоящим", "надлежащий", "нижеследующий", "истец",
        }
        if sum(1 for w in words if w.lower() in legal_words) >= 2:
            return "legal"

        # Code/tech docs
        if (text.count('```') >= 2 or text.count('`') > 5
                or "function" in text_lower and "return" in text_lower
                or "class " in text_lower and "def " in text_lower):
            return "code_docs"

        # Social media / informal
        informal_markers = {"lol", "omg", "tbh", "imo", "btw", "lmao",
                           "лол", "кек", "имхо", "ахах"}
        if (sum(1 for w in words if w.lower() in informal_markers) >= 1
                or text.count('!') > 3 or text.count('😂') + text.count('🤣') > 0):
            return "social"

        # News (datelines, who/what/when/where structure)
        if re.search(r'\b(?:REUTERS|AP|AFP|BBC|CNN)\b', text):
            return "news"
        # Short paragraphs with quotes = news style
        paragraphs = [p for p in text.split('\n') if p.strip()]
        has_quotes = text.count('"') >= 4 or text.count('«') >= 2
        avg_para_len = statistics.mean(len(p.split()) for p in paragraphs) if paragraphs else 50
        if has_quotes and avg_para_len < 30 and len(paragraphs) > 3:
            return "news"

        # Blog = personal pronouns + informal style
        personal_count = sum(
            1 for w in words if w.lower() in {"i", "my", "me", "я", "мой", "мне"}
        )
        if personal_count / total > 0.03:
            return "blog"

        return "general"

    def _get_adaptive_weights(self, domain: str) -> dict[str, float]:
        """Get domain-adjusted metric weights."""
        weights = dict(self._WEIGHTS)
        mods = self._DOMAIN_WEIGHT_MODS.get(domain, {})
        for metric, delta in mods.items():
            if metric in weights:
                weights[metric] = max(0.005, weights[metric] + delta)
        # Renormalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def __init__(self, lang: str = "auto"):
        self.lang = lang

    def detect(self, text: str, lang: str | None = None) -> DetectionResult:
        """Детектировать вероятность AI-генерации.

        Args:
            text: Текст для анализа.
            lang: Код языка (или auto-detect).

        Returns:
            DetectionResult с подробными метриками.
        """
        effective_lang = lang or self.lang
        if effective_lang == "auto":
            from texthumanize.lang_detect import detect_language
            effective_lang = detect_language(text)

        result = DetectionResult()

        if not text or len(text.strip()) < 50:
            result.verdict = "unknown"
            result.confidence = 0.0
            result.explanations.append("Text too short for reliable detection")
            return result

        # Подготовка
        sentences = split_sentences(text, effective_lang)
        words = text.split()
        lang_pack = get_lang_pack(effective_lang)

        if len(sentences) < 3:
            result.verdict = "unknown"
            result.confidence = 0.1
            result.explanations.append("Too few sentences for reliable detection")
            return result

        # ── Вычисляем все 18 метрик ──
        self._current_lang = effective_lang  # For cross-perplexity

        result.entropy_score = self._calc_entropy(text, words)
        result.burstiness_score = self._calc_burstiness(sentences)
        result.vocabulary_score = self._calc_vocabulary(text, words, lang_pack)
        result.zipf_score = self._calc_zipf(words, lang_pack)
        result.stylometry_score = self._calc_stylometry(text, words, sentences, lang_pack)
        result.pattern_score = self._calc_ai_patterns(text, words, sentences, effective_lang)
        result.punctuation_score = self._calc_punctuation(text, sentences)
        result.coherence_score = self._calc_coherence(text, sentences)
        result.grammar_score = self._calc_grammar(text, sentences)
        result.opening_score = self._calc_openings(sentences)
        result.readability_score = self._calc_readability_consistency(sentences)
        result.rhythm_score = self._calc_rhythm(sentences)
        result.perplexity_score = self._calc_perplexity(text, sentences)
        result.discourse_score = self._calc_discourse(text, sentences)
        result.semantic_rep_score = self._calc_semantic_repetition(text, sentences)
        result.entity_score = self._calc_entity_specificity(text, words)
        result.voice_score = self._calc_voice(text, sentences)
        result.topic_sent_score = self._calc_topic_sentence(text, sentences)

        # ── Domain detection & adaptive weights ──
        detected_domain = self._detect_domain(text, words)
        adaptive_weights = self._get_adaptive_weights(detected_domain)
        result.detected_domain = detected_domain

        # ── Взвешенная агрегация ──
        scores = {
            "entropy": result.entropy_score,
            "burstiness": result.burstiness_score,
            "vocabulary": result.vocabulary_score,
            "zipf": result.zipf_score,
            "stylometry": result.stylometry_score,
            "pattern": result.pattern_score,
            "punctuation": result.punctuation_score,
            "coherence": result.coherence_score,
            "grammar": result.grammar_score,
            "opening": result.opening_score,
            "readability": result.readability_score,
            "rhythm": result.rhythm_score,
            "perplexity": result.perplexity_score,
            "discourse": result.discourse_score,
            "semantic_rep": result.semantic_rep_score,
            "entity": result.entity_score,
            "voice": result.voice_score,
            "topic_sentence": result.topic_sent_score,
        }

        # ── Ensemble boosting aggregation ──
        raw_probability = self._ensemble_aggregate(scores, adaptive_weights)

        # Калибровка: sigmoidal transform для лучшего разделения
        calibrated = self._calibrate(raw_probability)

        # Демпфирование для коротких текстов (< 50 слов):
        # короткие тексты ненадёжны, двигаем score к 0.5
        n_words = len(words)
        if n_words < 50:
            damping = n_words / 50.0
            calibrated = 0.5 + (calibrated - 0.5) * damping

        result.ai_probability = calibrated

        # Уверенность зависит от длины текста, согласия метрик
        # и экстремальности итогового скора
        text_length_factor = min(len(words) / 100, 1.0)  # Full confidence at 100+ words
        metric_values = list(scores.values())
        metric_agreement = 1.0 - statistics.stdev(metric_values)

        # Extreme probability bonus: если скор очень высокий или низкий —
        # метрики единогласны => можно быть увереннее
        extreme_bonus = abs(result.ai_probability - 0.5) * 0.6  # max +0.3

        # Количество метрик, согласных с вердиктом
        threshold_for_ai = 0.55
        if result.ai_probability > 0.5:
            n_agree = sum(1 for v in metric_values if v >= threshold_for_ai)
        else:
            n_agree = sum(1 for v in metric_values if v < threshold_for_ai)
        agreement_ratio = n_agree / len(metric_values) if metric_values else 0

        result.confidence = min(
            text_length_factor * 0.35
            + metric_agreement * 0.2
            + extreme_bonus
            + agreement_ratio * 0.25,
            1.0
        )

        # Вердикт (primary: probability, secondary: metric agreement)
        # Count how many discriminative metrics lean AI (>0.55)
        key_metrics = ["pattern", "burstiness", "stylometry", "voice",
                       "entity", "grammar", "opening", "discourse"]
        n_ai_leaning = sum(1 for m in key_metrics if scores.get(m, 0.5) > 0.55)

        if result.ai_probability > 0.60:
            result.verdict = "ai"
        elif result.ai_probability > 0.42 and n_ai_leaning >= 4:
            result.verdict = "ai"
        elif result.ai_probability > 0.38 and n_ai_leaning >= 5:
            # Higher agreement needed for lower scores
            result.verdict = "ai"
        elif result.ai_probability > 0.32:
            result.verdict = "mixed"
        else:
            result.verdict = "human"

        # Объяснения
        result.explanations = self._generate_explanations(scores, result, effective_lang)

        # Детали
        result.details = {
            "lang": effective_lang,
            "word_count": len(words),
            "sentence_count": len(sentences),
            "raw_probability": raw_probability,
            "scores": scores,
            "weights": adaptive_weights,
            "domain": detected_domain,
        }

        return result

    # ─── SENTENCE-LEVEL DETECTION ─────────────────────────────

    @dataclass
    class SentenceScore:
        """Per-sentence AI probability."""

        text: str
        start: int
        end: int
        ai_probability: float
        label: str  # "human", "mixed", "ai"

    def detect_sentences(
        self, text: str, lang: str | None = None, *, window: int = 3,
    ) -> list["AIDetector.SentenceScore"]:
        """Per-sentence AI detection via sliding window.

        Each sentence gets a score computed from a window of
        surrounding sentences (±window//2). This provides sentence-level
        granularity while using enough context for reliable scoring.

        Args:
            text: Text to analyse.
            lang: Language code (or auto).
            window: Number of sentences in each evaluation window.

        Returns:
            List of SentenceScore for every sentence.
        """
        effective_lang = lang or self.lang
        if effective_lang == "auto":
            from texthumanize.lang_detect import detect_language
            effective_lang = detect_language(text)

        from texthumanize.sentence_split import split_sentences_with_spans
        spans = split_sentences_with_spans(text, effective_lang)
        if len(spans) < 2:
            return [
                self.SentenceScore(
                    text=s.text, start=s.start, end=s.end,
                    ai_probability=0.5, label="unknown",
                )
                for s in spans
            ]

        _lang_pack = get_lang_pack(effective_lang)  # noqa: F841
        half = max(window // 2, 1)

        # Pre-compute fast per-sentence features
        sent_texts = [s.text for s in spans]

        results: list[AIDetector.SentenceScore] = []

        for i, span in enumerate(spans):
            lo = max(0, i - half)
            hi = min(len(spans), i + half + 1)
            win_sents = sent_texts[lo:hi]
            win_text = " ".join(win_sents)
            win_words = win_text.split()

            # Compute subset of fast metrics on the window
            entropy = self._calc_entropy(win_text, win_words)
            pattern = self._calc_ai_patterns(
                win_text, win_words, win_sents, effective_lang,
            )
            grammar = self._calc_grammar(win_text, win_sents)
            voice = self._calc_voice(win_text, win_sents)

            # Simple average of the subset
            prob = (entropy * 0.20 + pattern * 0.40
                    + grammar * 0.20 + voice * 0.20)
            prob = max(0.0, min(1.0, prob))

            if prob >= 0.65:
                label = "ai"
            elif prob >= 0.40:
                label = "mixed"
            else:
                label = "human"

            results.append(self.SentenceScore(
                text=span.text, start=span.start, end=span.end,
                ai_probability=round(prob, 4), label=label,
            ))

        return results

    # ─── MIXED TEXT DETECTION ─────────────────────────────────

    @dataclass
    class TextSegment:
        """Segment of text with AI/human classification."""

        text: str
        start: int
        end: int
        label: str          # "human", "ai", "mixed"
        ai_probability: float
        sentence_count: int

    def detect_mixed(
        self, text: str, lang: str | None = None,
    ) -> list["AIDetector.TextSegment"]:
        """Detect mixed AI/human text by finding boundaries.

        Groups consecutive sentences that share the same label
        (human / ai / mixed) into coherent segments.

        Args:
            text: Text to analyse.
            lang: Language code or auto.

        Returns:
            List of TextSegment describing contiguous spans.
        """
        per_sentence = self.detect_sentences(text, lang, window=3)
        if not per_sentence:
            return []

        # Merge consecutive sentences with same label
        segments: list[AIDetector.TextSegment] = []
        cur_label = per_sentence[0].label
        cur_sents: list[AIDetector.SentenceScore] = [per_sentence[0]]

        for ss in per_sentence[1:]:
            if ss.label == cur_label:
                cur_sents.append(ss)
            else:
                # Flush current segment
                seg_text = text[cur_sents[0].start : cur_sents[-1].end]
                avg_prob = statistics.mean(s.ai_probability for s in cur_sents)
                segments.append(self.TextSegment(
                    text=seg_text,
                    start=cur_sents[0].start,
                    end=cur_sents[-1].end,
                    label=cur_label,
                    ai_probability=round(avg_prob, 4),
                    sentence_count=len(cur_sents),
                ))
                cur_label = ss.label
                cur_sents = [ss]

        # Flush last segment
        seg_text = text[cur_sents[0].start : cur_sents[-1].end]
        avg_prob = statistics.mean(s.ai_probability for s in cur_sents)
        segments.append(self.TextSegment(
            text=seg_text,
            start=cur_sents[0].start,
            end=cur_sents[-1].end,
            label=cur_label,
            ai_probability=round(avg_prob, 4),
            sentence_count=len(cur_sents),
        ))

        return segments

    # ─── 1. ЭНТРОПИЯ ──────────────────────────────────────────

    def _calc_entropy(self, text: str, words: list[str]) -> float:
        """Энтропия текста — AI имеет низкую энтропию (предсказуемый).

        Анализ:
        - Character-level entropy
        - Word-level entropy
        - Conditional entropy (bigrams)

        Возвращает: 0.0 (высокая энтропия = человек) — 1.0 (низкая = AI)
        """
        if len(words) < 10:
            return 0.5

        # Character-level entropy (Shannon entropy on chars)
        char_freq = Counter(text.lower())
        total_chars = sum(char_freq.values())
        char_entropy = -sum(
            (c / total_chars) * math.log2(c / total_chars)
            for c in char_freq.values() if c > 0
        )

        # Word-level entropy
        word_freq = Counter(w.lower().strip('.,;:!?"\'()[]{}') for w in words)
        total_words = sum(word_freq.values())
        word_entropy = -sum(
            (c / total_words) * math.log2(c / total_words)
            for c in word_freq.values() if c > 0
        )

        # Conditional entropy (bigram entropy - unigram entropy)
        punct = '.,;:!?"\'()[]{}'
        word_list = [w.lower().strip(punct) for w in words if w.strip(punct)]
        bigrams: Counter[tuple[str, str]] = Counter()
        for i in range(len(word_list) - 1):
            bigrams[(word_list[i], word_list[i + 1])] += 1
        total_bigrams = sum(bigrams.values())

        if total_bigrams > 0:
            bigram_entropy = -sum(
                (c / total_bigrams) * math.log2(c / total_bigrams)
                for c in bigrams.values() if c > 0
            )
            conditional_entropy = bigram_entropy - word_entropy
        else:
            conditional_entropy = word_entropy

        # Нормализация: AI текст имеет entropy ниже нормы
        # Текст человека: char entropy ~4.0-4.5, word entropy ~8-10
        # AI текст: char entropy ~3.5-4.0, word entropy ~6-8

        # Нормализуем в 0–1 шкалу (1 = AI-like low entropy)
        char_score = max(0, 1.0 - (char_entropy - 3.0) / 2.0)
        word_score = max(0, 1.0 - (word_entropy - 5.0) / 5.0)
        cond_score = max(0, 1.0 - conditional_entropy / 3.0)

        score = (char_score * 0.2 + word_score * 0.5 + cond_score * 0.3)
        return max(0.0, min(1.0, score))

    # ─── 2. BURSTINESS ────────────────────────────────────────

    def _calc_burstiness(self, sentences: list[str]) -> float:
        """Вариативность длины предложений.

        AI генерирует предложения равной длины (CV < 0.3).
        Люди: CV > 0.5.

        Возвращает: 0.0 (разнообразно = человек) — 1.0 (однообразно = AI)
        """
        if len(sentences) < 4:
            return 0.5

        lengths = [len(s.split()) for s in sentences]
        avg = statistics.mean(lengths)
        if avg == 0:
            return 0.5

        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        cv = stdev / avg  # Коэффициент вариации

        # AI: CV ≈ 0.15–0.35, Human: CV ≈ 0.5–0.9+
        # Маппим в 0–1
        score = max(0, 1.0 - (cv - 0.1) / 0.7)

        # Дополнительно: проверяем наличие очень коротких (< 5 слов)
        # и очень длинных (> 30 слов) предложений — у AI их мало
        short = sum(1 for sl in lengths if sl <= 5)
        long_cnt = sum(1 for sl in lengths if sl >= 30)
        extremes = (short + long_cnt) / len(lengths)

        # Если нет экстремальных длин — признак AI
        if extremes < 0.05:
            score = min(score + 0.15, 1.0)
        elif extremes > 0.2:
            score = max(score - 0.1, 0.0)

        # Проверяем: есть ли «однословные» предложения (фрагменты)
        # Люди иногда пишут "Точно." или "Нет." — AI почти никогда
        fragments = sum(1 for sl in lengths if sl <= 2)
        if fragments == 0 and len(sentences) > 8:
            score = min(score + 0.05, 1.0)

        return max(0.0, min(1.0, score))

    # ─── 3. ЛЕКСИЧЕСКОЕ РАЗНООБРАЗИЕ ──────────────────────────

    def _calc_vocabulary(
        self, text: str, words: list[str], lang_pack: dict
    ) -> float:
        """Лексическое разнообразие — AI использует «безопасный» словарь.

        Метрики:
        - TTR (Type-Token Ratio) — базовый
        - MATTR (Moving Average TTR) — устойчив к длине
        - Yule's K — статистическая мера разнообразия
        - Hapax legomena ratio — доля слов, встреченных 1 раз

        Возвращает: 0.0 (разнообразно = человек) — 1.0 (бедно = AI)
        """
        if len(words) < 20:
            return 0.5

        stop_words = lang_pack.get("stop_words", set())
        content_words = [
            w.lower().strip('.,;:!?"\'()[]{}')
            for w in words
            if w.lower().strip('.,;:!?"\'()[]{}') not in stop_words
            and len(w.strip('.,;:!?"\'()[]{}')) > 2
        ]

        if len(content_words) < 10:
            return 0.5

        # TTR
        types = len(set(content_words))
        tokens = len(content_words)
        ttr = types / tokens

        # MATTR (окно 25 слов)
        window = 25
        if tokens >= window:
            mattr_values = []
            for i in range(tokens - window + 1):
                w_slice = content_words[i:i + window]
                mattr_values.append(len(set(w_slice)) / window)
            mattr = statistics.mean(mattr_values)
        else:
            mattr = ttr

        # Yule's K
        freq_spectrum = Counter(Counter(content_words).values())
        N = tokens
        M = sum(i * i * freq_spectrum[i] for i in freq_spectrum)
        yule_k = 10000 * (M - N) / (N * N) if N > 1 else 0

        # Hapax legomena ratio (слова, встреченные 1 раз)
        hapax_count = sum(1 for c in Counter(content_words).values() if c == 1)
        hapax_ratio = hapax_count / types if types > 0 else 0

        # AI: TTR ~0.3-0.5, MATTR ~0.6-0.7, Yule's K > 100
        # Human: TTR ~0.5-0.7, MATTR ~0.7-0.85, Yule's K < 100
        # Для коротких текстов (<100 content words) TTR ненадёжен
        length_reliability = min(tokens / 150, 1.0)

        # TTR score (AI has lower TTR)
        ttr_score = max(0, 1.0 - (ttr - 0.3) / 0.4)

        # MATTR score
        mattr_score = max(0, 1.0 - (mattr - 0.6) / 0.3)

        # Yule's K score (higher K = less diverse = more AI-like)
        yule_score = min(yule_k / 150, 1.0)

        # Hapax ratio (lower = more AI-like)
        hapax_score = max(0, 1.0 - hapax_ratio / 0.5)

        raw_score = (
            ttr_score * 0.2
            + mattr_score * 0.3
            + yule_score * 0.25
            + hapax_score * 0.25
        )

        # Для коротких текстов: сдвигаем к 0.5 (ненадёжно)
        score = 0.5 + (raw_score - 0.5) * length_reliability

        return max(0.0, min(1.0, score))

    # ─── 4. ЗАКОН ЦИПФА ──────────────────────────────────────

    def _calc_zipf(self, words: list[str], lang_pack: dict) -> float:
        """Соответствие закону Ципфа.

        Естественный текст хорошо следует Zipf distribution.
        AI текст может отклоняться (слишком равномерный в mid-range).

        Возвращает: 0.0 (хорошее соответствие = human) — 1.0 (AI)
        """
        clean_words = [
            w.lower().strip('.,;:!?"\'()[]{}')
            for w in words
            if len(w.strip('.,;:!?"\'()[]{}')) > 0
        ]

        # Zipf unreliable for very short texts
        if len(clean_words) < 80:
            return 0.5

        freq = Counter(clean_words)
        sorted_freqs = sorted(freq.values(), reverse=True)

        if len(sorted_freqs) < 10:
            return 0.5

        # Нужно чтобы top-слово встречалось >= 3 раза для статистики
        if sorted_freqs[0] < 3:
            return 0.5

        # Теоретический Zipf: f(r) = f(1) / r^alpha (Mandelbrot)
        n = min(50, len(sorted_freqs))

        # Log-log линейная регрессия для оценки alpha
        log_ranks = [math.log(r) for r in range(1, n + 1)]
        log_freqs = [math.log(max(sorted_freqs[r - 1], 0.5)) for r in range(1, n + 1)]

        mean_lr = statistics.mean(log_ranks)
        mean_lf = statistics.mean(log_freqs)
        num = sum((lr - mean_lr) * (lf - mean_lf) for lr, lf in zip(log_ranks, log_freqs))
        den = sum((lr - mean_lr) ** 2 for lr in log_ranks)
        alpha = -num / den if den > 0 else 1.0  # alpha ~ 1.0 для естественного текста

        # R² — goodness of fit
        predicted = [mean_lf - alpha * (lr - mean_lr) for lr in log_ranks]
        ss_res = sum((lf - p) ** 2 for lf, p in zip(log_freqs, predicted))
        ss_tot = sum((lf - mean_lf) ** 2 for lf in log_freqs)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Естественный текст: alpha ≈ 0.8–1.2, R² > 0.9
        # AI текст: alpha может быть 0.5-0.7 (слишком плоский mid-range)
        alpha_dev = abs(alpha - 1.0)
        alpha_score = min(alpha_dev / 0.5, 1.0)  # 0 if alpha=1.0, 1 if alpha far

        # R² score: high R² = natural Zipf = human
        fit_score = max(0.0, 1.0 - r_squared)

        # Проверяем «хвост» распределения — AI делает его слишком плоским
        tail_start = len(sorted_freqs) // 3
        tail = sorted_freqs[tail_start:]
        tail_score = 0.5
        if tail and len(tail) > 2:
            tail_mean = statistics.mean(tail)
            tail_cv = statistics.stdev(tail) / tail_mean if tail_mean > 0 else 0
            if all(v == tail[0] for v in tail):
                tail_score = 0.5
            else:
                tail_score = max(0, 1.0 - tail_cv / 0.8)

        raw_score = alpha_score * 0.3 + fit_score * 0.4 + tail_score * 0.3

        # Reliability scaling: full trust at 500+ words
        length_reliability = min(len(clean_words) / 500, 1.0)
        score = 0.5 + (raw_score - 0.5) * length_reliability
        return max(0.0, min(1.0, score))

    # ─── 5. СТИЛОМЕТРИЯ ──────────────────────────────────────

    def _calc_stylometry(
        self,
        text: str,
        words: list[str],
        sentences: list[str],
        lang_pack: dict,
    ) -> float:
        """Стилометрический анализ.

        AI имеет характерный «стилевой отпечаток»:
        - Высокая доля функциональных слов
        - Равномерное распределение частей речи
        - Предпочтение определённых синтаксических конструкций

        Возвращает: 0.0 (человеческий стиль) — 1.0 (AI стиль)
        """
        if len(words) < 20:
            return 0.5

        stop_words = lang_pack.get("stop_words", set())
        punct = '.,;:!?"\'()[]{}'
        word_lengths = [len(w.strip(punct)) for w in words if w.strip(punct)]

        # 1. Средняя длина слова (AI предпочитает более длинные слова)
        avg_word_len = statistics.mean(word_lengths) if word_lengths else 0
        # Human: 4-5 букв, AI: 5-7 букв
        word_len_score = max(0, (avg_word_len - 4.0) / 3.0)

        # 2. Вариативность длины слов (AI более однообразен)
        if len(word_lengths) > 5:
            word_len_cv = statistics.stdev(word_lengths) / avg_word_len if avg_word_len > 0 else 0
            word_var_score = max(0, 1.0 - word_len_cv / 0.7)
        else:
            word_var_score = 0.5

        # 3. Доля длинных слов (> 8 букв) — AI использует больше
        long_words = sum(1 for wl in word_lengths if wl > 8)
        long_ratio = long_words / len(word_lengths) if word_lengths else 0
        # Human: 5-10%, AI: 10-20%
        long_score = min(long_ratio / 0.15, 1.0)

        # 4. Средняя длина предложения
        sent_lengths = [len(s.split()) for s in sentences]
        avg_sent_len = statistics.mean(sent_lengths) if sent_lengths else 0
        # AI: 15-22 слова, Human: 10-18
        sent_len_score = max(0, (avg_sent_len - 10) / 15)

        # 5. Доля стоп-слов (AI часто ниже)
        stop_count = sum(1 for w in words if w.lower().strip('.,;:!?"\'()[]{}') in stop_words)
        stop_ratio = stop_count / len(words) if words else 0
        # Human: 40-55%, AI: 30-45%
        stop_score = max(0, 1.0 - (stop_ratio - 0.25) / 0.3)

        score = (
            word_len_score * 0.2
            + word_var_score * 0.15
            + long_score * 0.2
            + sent_len_score * 0.25
            + stop_score * 0.2
        )
        return max(0.0, min(1.0, score))

    # ─── 6. AI ПАТТЕРНЫ ──────────────────────────────────────

    def _calc_ai_patterns(
        self,
        text: str,
        words: list[str],
        sentences: list[str],
        lang: str,
    ) -> float:
        """Детекция характерных AI-паттернов.

        Самый мощный сигнал: AI использует определённые слова
        и конструкции значительно чаще людей.

        Возвращает: 0.0 (нет паттернов = human) — 1.0 (много = AI)
        """
        if len(words) < 20:
            return 0.5

        text_lower = text.lower()
        total_words = len(words)

        ai_dict = _AI_WORDS.get(lang, _AI_WORDS.get("en", {}))

        total_hits = 0
        weighted_hits = 0.0

        # 1. AI-overused слова
        for category, weight in [
            ("adverbs", 1.5), ("adjectives", 1.3), ("verbs", 1.5), ("connectors", 2.0)
        ]:
            cat_words = ai_dict.get(category, set())
            for w in cat_words:
                count = text_lower.count(w.lower())
                if count > 0:
                    total_hits += count
                    weighted_hits += count * weight

        # 2. AI-фразы (сильнейший сигнал)
        phrases = ai_dict.get("phrases", set())
        for phrase in phrases:
            count = text_lower.count(phrase.lower())
            if count > 0:
                total_hits += count
                weighted_hits += count * 3.0  # Тройной вес для фраз

        # Нормализуем по длине текста
        density = weighted_hits / total_words if total_words > 0 else 0

        # 3. Connector density (AI: ~0.05-0.10, Human: ~0.02-0.04)
        connector_count = 0
        connectors = ai_dict.get("connectors", set())
        for conn in connectors:
            if conn.lower() in text_lower:
                connector_count += 1
        connector_density = connector_count / len(sentences) if sentences else 0

        # 4. "Furthermore/Moreover/However" в начале предложений
        formal_starts = 0
        formal_starters = {
            "however", "furthermore", "moreover", "additionally",
            "consequently", "nevertheless", "nonetheless",
            "однако", "кроме того", "более того", "помимо этого",
            "таким образом", "следовательно", "тем не менее",
            "однак", "крім того", "більш того", "окрім цього",
            "таким чином", "отже",
        }
        for sent in sentences:
            first_words = ' '.join(sent.split()[:3]).lower().rstrip('.,;:')
            for starter in formal_starters:
                if first_words.startswith(starter):
                    formal_starts += 1
                    break

        formal_start_ratio = formal_starts / len(sentences) if sentences else 0

        # Combining
        density_score = min(density / 0.05, 1.0)
        connector_score = min(connector_density / 0.15, 1.0)
        formal_score = min(formal_start_ratio / 0.2, 1.0)

        # 5. Impersonal / hedging constructions (very strong AI signal)
        hedging_patterns = [
            r"\bit is (?:important|essential|crucial|worth"
            r"|necessary|imperative|critical|noteworthy|undeniable"
            r"|evident|clear|apparent|undeniable|widely recognized)",
            r"\bit (?:should be|must be|can be|could be) "
            r"(?:noted|mentioned|emphasized|highlighted|stressed"
            r"|acknowledged|recognized|understood|argued)",
            r"\bthis (?:approach|method|strategy|technique"
            r"|framework|analysis|study|research|paper|article"
            r"|investigation) (?:has|enables|ensures|provides|facilitates"
            r"|demonstrates|highlights|reveals|examines|explores"
            r"|investigates|addresses|aims|seeks)",
            r"\bplays? (?:a |an )?(?:crucial|important|vital"
            r"|significant|key|essential|fundamental|pivotal"
            r"|indispensable|central|integral) role",
            r"\bin (?:today's|the modern|the current|the contemporary|an increasingly) ",
            r"\bone of the most (?:important|significant|pressing|critical|challenging"
            r"|notable|prominent|influential|impactful)",
            r"\bthe (?:importance|significance|impact|role|influence"
            r"|implications|consequences|relevance) of\b",
            r"\bgaining (?:traction|momentum|popularity|significance|attention)",
            r"\bboth .{5,40} and .{5,40}(?: alike)?[.]",
            r"\brepresents? (?:a |an )?(?:significant|important|major|critical|key"
            r"|fundamental|notable|promising|paradigm)",
            # Фразы-клише AI (EN)
            r"\bin (?:terms of|light of|the context of|the realm of|the field of)\b",
            r"\bwith (?:regard to|respect to|a focus on)\b",
            r"\bas (?:a result|such|mentioned|noted|previously stated)\b",
            r"\bon the other hand\b",
            r"\bin conclusion\b",
            r"\bto (?:sum up|summarize|conclude|recap)\b",
            r"\bit is (?:widely|generally|commonly) (?:known|accepted|believed|recognized)\b",
            r"\b(?:comprehensive|thorough|in-depth|extensive|holistic) (?:analysis|review"
            r"|examination|study|overview|understanding|approach|assessment)\b",
            r"\b(?:significant|substantial|considerable|remarkable|notable) (?:impact"
            r"|progress|improvement|advancement|growth|increase|benefits|advantages)\b",
            r"\bthe (?:utilization|implementation|optimization|integration"
            r"|facilitation|enhancement) of\b",
            r"\b(?:delve|delves|delving) (?:into|deeper)\b",
            r"\b(?:navigate|navigating|navigates) (?:the|this|these) (?:complex"
            r"|challenging|intricate|evolving|dynamic)\b",
            r"\b(?:landscape|paradigm|ecosystem|synergy|synergies)\b",
            r"\bleverage(?:s|d|ing)?\b",
            r"\bfoster(?:s|ed|ing)? (?:a |an )?(?:sense|culture|environment"
            r"|community|atmosphere|spirit|innovation|collaboration|growth)\b",
            # Русские паттерны
            r"\bявляется (?:одним|ключевым|важным|важнейшим|неотъемлемым|основ)",
            r"\bиграет (?:важную|ключевую|существенную|значительную) роль",
            r"\bпредставляет собой\b",
            r"\bоказывает (?:существенное|значительное|важное) влияние",
            r"\bодн(?:им|ой) из (?:наиболее|самых|важнейших|ключевых)",
            r"\bнеобходимо (?:отметить|подчеркнуть|учитывать)",
            r"\bследует (?:отметить|подчеркнуть|учитывать)",
            r"\bважно (?:отметить|подчеркнуть|учитывать)",
            r"\bв (?:рамках|контексте|условиях|сфере) данн",
            r"\bданн(?:ый|ая|ое|ые) (?:подход|метод|исследование|анализ"
            r"|работа|статья|факт|фактор|явление|процесс|результат)",
            r"\bв (?:данном|настоящем|современном) (?:контексте|исследовании"
            r"|мире|обществе|этапе)",
            r"\b(?:комплексный|всесторонний|тщательный|глубокий|детальный"
            r"|систематический) (?:анализ|подход|обзор|исследование|изучение)\b",
            r"\b(?:значительн|существенн|замет|ощутим)(?:ый|ая|ое|ые|о|ого)"
            r" (?:вклад|прогресс|рост|влияние|улучшение)\b",
            r"\bспособствует (?:оптимизации|улучшению|развитию|повышению"
            r"|укреплению|формированию|росту)\b",
            r"\bобеспечивает (?:повышение|улучшение|оптимизацию|эффективн"
            r"|надёжн|устойчив|комплексн)\b",
        ]
        hedge_count = 0
        for pat in hedging_patterns:
            hedge_count += len(re.findall(pat, text_lower))
        hedge_score = min(hedge_count / max(len(sentences) * 0.15, 1), 1.0)

        # 6. Enumeration / list patterns: "First,... Second,... Third,..."
        enum_patterns = [
            r"\b(?:first(?:ly)?|second(?:ly)?|third(?:ly)?|finally|lastly),?\s",
            r"\b(?:first and foremost|last but not least|in addition to)\b",
            r"\b(?:во-первых|во-вторых|в-третьих|наконец)\b",
        ]
        enum_count = sum(len(re.findall(p, text_lower)) for p in enum_patterns)
        enum_score = min(enum_count / 3, 1.0)

        # 7. Perfect paragraph symmetry (each paragraph starts with statement,
        #    then expands — very AI-like)
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        symmetry_score = 0.0
        if len(paragraphs) >= 3:
            para_lens = [len(p.split()) for p in paragraphs]
            if para_lens:
                mean_len = sum(para_lens) / len(para_lens)
                if mean_len > 0:
                    dev = sum((x - mean_len)**2 for x in para_lens)
                    cv = (dev / len(para_lens)) ** 0.5 / mean_len
                    symmetry_score = max(0, 1.0 - cv * 2)  # Low CV = symmetric = AI-like

        score = (
            density_score * 0.20
            + connector_score * 0.12
            + formal_score * 0.15
            + hedge_score * 0.30
            + enum_score * 0.10
            + symmetry_score * 0.13
        )

        return max(0.0, min(1.0, score))

    # ─── 7. ПУНКТУАЦИЯ ───────────────────────────────────────

    def _calc_punctuation(self, text: str, sentences: list[str]) -> float:
        """Анализ пунктуационного профиля.

        AI чрезмерно использует: точку с запятой, двоеточие, длинные тире.
        AI мало использует: многоточие, восклицательные, скобки-пояснения.

        Возвращает: 0.0 (human) — 1.0 (AI)
        """
        if len(text) < 50:
            return 0.5

        total_chars = len(text)

        # Считаем пунктуацию
        semicolons = text.count(';')
        colons = text.count(':')
        em_dashes = text.count('—') + text.count('–')
        ellipsis = text.count('...') + text.count('…')
        exclamations = text.count('!')
        questions = text.count('?')
        parens = text.count('(')
        # Per 1000 chars
        k = 1000 / total_chars

        semi_rate = semicolons * k
        colon_rate = colons * k
        dash_rate = em_dashes * k
        ellipsis_rate = ellipsis * k
        excl_rate = exclamations * k

        # AI: высокая частота ; и : , низкая ... и !
        # Human: больше ... и !, меньше ;

        # Semicolons: AI ~2-5 per 1K, Human ~0-1 per 1K
        semi_score = min(semi_rate / 3.0, 1.0)

        # Colons: AI ~2-4 per 1K, Human ~0.5-1.5 per 1K
        colon_score = min(colon_rate / 3.0, 1.0)

        # Em dashes: AI использует идеальные — , human чаще -
        dash_score = min(dash_rate / 4.0, 1.0)

        # Ellipsis: human ~1-3 per 1K, AI ~0
        ellipsis_score = max(0, 1.0 - ellipsis_rate / 2.0)

        # Exclamations: human uses more
        excl_score = max(0, 1.0 - excl_rate / 2.0)

        # Punctuation diversity: AI uses fewer types
        punct_types = sum(1 for v in [semicolons, colons, em_dashes, ellipsis,
                                        exclamations, questions, parens] if v > 0)
        diversity_score = max(0, 1.0 - punct_types / 5.0)

        score = (
            semi_score * 0.2
            + colon_score * 0.15
            + dash_score * 0.15
            + ellipsis_score * 0.15
            + excl_score * 0.1
            + diversity_score * 0.25
        )
        return max(0.0, min(1.0, score))

    # ─── 8. КОГЕРЕНТНОСТЬ ─────────────────────────────────────

    def _calc_coherence(self, text: str, sentences: list[str]) -> float:
        """Анализ когерентности — AI пишет «слишком связно».

        AI последовательно связывает каждое предложение с предыдущим.
        Люди иногда делают «прыжки» между темами, используют
        ассоциативные переходы, отступления.

        Возвращает: 0.0 (естественные переходы = human) — 1.0 (идеальная связь = AI)
        """
        if len(sentences) < 5:
            return 0.5

        # Считаем лексическое перекрытие между соседними предложениями
        overlaps = []
        for i in range(1, len(sentences)):
            words_prev = set(
                w.lower().strip('.,;:!?"\'()[]{}')
                for w in sentences[i - 1].split()
                if len(w.strip('.,;:!?"\'()[]{}')) > 3
            )
            words_curr = set(
                w.lower().strip('.,;:!?"\'()[]{}')
                for w in sentences[i].split()
                if len(w.strip('.,;:!?"\'()[]{}')) > 3
            )

            if words_prev and words_curr:
                overlap = len(words_prev & words_curr) / min(len(words_prev), len(words_curr))
                overlaps.append(overlap)

        if not overlaps:
            return 0.5

        avg_overlap = statistics.mean(overlaps)
        overlap_variance = statistics.variance(overlaps) if len(overlaps) > 1 else 0

        # AI: высокое среднее перекрытие (~0.15-0.30), низкая вариация
        # Human: lower overlap (~0.05-0.15), higher variance

        overlap_score = min(avg_overlap / 0.25, 1.0)

        # Низкая вариация = AI
        if len(overlaps) > 3:
            variance_score = max(0, 1.0 - overlap_variance / 0.02)
        else:
            variance_score = 0.5

        # Проверяем: каждый ли абзац начинается с transition word
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) > 2:
            transition_starts = 0
            for para in paragraphs[1:]:
                first_words = para.split()[:3]
                first_phrase = ' '.join(first_words).lower()
                if any(
                    first_phrase.startswith(t)
                    for t in [
                        "however", "furthermore", "moreover", "in addition",
                        "consequently", "therefore", "additionally", "on the other hand",
                        "однако", "кроме того", "более того", "в дополнение",
                        "таким образом", "в заключение", "помимо",
                        "однак", "крім того", "більш того", "таким чином",
                    ]
                ):
                    transition_starts += 1

            trans_ratio = transition_starts / (len(paragraphs) - 1)
            transition_score = min(trans_ratio / 0.4, 1.0)
        else:
            transition_score = 0.5

        score = overlap_score * 0.3 + variance_score * 0.3 + transition_score * 0.4
        return max(0.0, min(1.0, score))

    # ─── 9. ГРАММАТИЧЕСКАЯ ИДЕАЛЬНОСТЬ ────────────────────────

    def _calc_grammar(self, text: str, sentences: list[str]) -> float:
        """AI пишет грамматически «слишком идеально».

        Люди допускают:
        - Начало предложения со строчной (разговорный стиль)
        - Неформальные конструкции
        - Вводные без выделения запятыми
        - Непоследовательность в форматировании
        - Сокращения (don't, isn't)
        - Sentence fragments
        - Informal punctuation (!! ...)

        Возвращает: 0.0 (human-like = неидеально) — 1.0 (perfect grammar = AI)
        """
        if len(sentences) < 3:
            return 0.5

        indicators = []

        # 1. Все предложения начинаются с заглавной?
        all_uppercase = sum(
            1 for s in sentences
            if s and s[0].isupper()
        )
        upper_ratio = all_uppercase / len(sentences) if sentences else 0
        # Human sometimes doesn't capitalize ~ 95%
        indicators.append(1.0 if upper_ratio == 1.0 else max(0, upper_ratio - 0.9) * 10)

        # 2. Все предложения заканчиваются знаком препинания?
        all_punct_end = sum(
            1 for s in sentences
            if s and s.rstrip()[-1] in '.!?…'
        )
        punct_ratio = all_punct_end / len(sentences) if sentences else 0
        indicators.append(1.0 if punct_ratio == 1.0 else max(0, punct_ratio - 0.85) * 6.7)

        # 3. Парные кавычки/скобки — AI всегда закрывает
        open_parens = text.count('(')
        close_parens = text.count(')')
        paren_balance = abs(open_parens - close_parens)
        indicators.append(1.0 if paren_balance == 0 and open_parens > 0 else 0.0)

        # 4. Нет сокращений (don't, isn't) в EN — AI пишет полные формы
        if any(c.isascii() and c.isalpha() for c in text):
            contractions = len(re.findall(r"\b\w+'(?:t|s|re|ve|ll|d|m)\b", text, re.IGNORECASE))
            total_w = len(text.split())
            contraction_ratio = contractions / total_w if total_w > 0 else 0
            # Human EN: ~2-5% contractions, AI: ~0-1%
            indicators.append(max(0, 1.0 - contraction_ratio / 0.03))

        # 5. Однородная длина абзацев — AI делает их равными
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) > 2:
            para_lengths = [len(p.split()) for p in paragraphs]
            avg_para = statistics.mean(para_lengths)
            if avg_para > 0:
                para_cv = statistics.stdev(para_lengths) / avg_para if len(para_lengths) > 1 else 0
                # AI: CV < 0.3, Human: CV > 0.4
                indicators.append(max(0, 1.0 - para_cv / 0.5))

        # 6. Oxford comma перед "and" в списках — AI часто использует
        oxford_matches = len(re.findall(r',\s+and\b', text, re.IGNORECASE))
        list_ands = len(re.findall(r'\band\b', text, re.IGNORECASE))
        if list_ands > 2:
            oxford_ratio = oxford_matches / list_ands
            indicators.append(min(oxford_ratio / 0.3, 1.0))

        # 7. Отсутствие sentence fragments (все предложения >= 4 слова)
        fragment_count = sum(1 for s in sentences if len(s.split()) < 4)
        fragment_ratio = fragment_count / len(sentences) if sentences else 0
        # Human uses fragments (~10-20%), AI almost never (<3%)
        indicators.append(max(0, 1.0 - fragment_ratio / 0.15))

        # 8. Нет неформальной пунктуации (!! ... ??? — human markers)
        informal_punct = len(re.findall(r'[!?]{2,}|\.{3,}', text))
        if len(sentences) > 5:
            punct_informality = informal_punct / len(sentences)
            indicators.append(max(0, 1.0 - punct_informality / 0.1))

        # 9. Consistent list formatting — AI enumeates with same style
        bullet_lines = re.findall(r'^[\s]*[-•*]\s', text, re.MULTILINE)
        numbered_lines = re.findall(r'^[\s]*\d+[.)]\s', text, re.MULTILINE)
        if len(bullet_lines) + len(numbered_lines) >= 3:
            # Has formatted lists — AI signal (humans less frequently use structured lists)
            indicators.append(0.8)

        score = statistics.mean(indicators) if indicators else 0.5
        return max(0.0, min(1.0, score))

    # ─── 10. РАЗНООБРАЗИЕ НАЧАЛ ПРЕДЛОЖЕНИЙ ────────────────────

    def _calc_openings(self, sentences: list[str]) -> float:
        """AI часто начинает предложения одинаково.

        Паттерны AI:
        - Повторяющиеся 'The', 'This', 'It'
        - Subject-first всегда
        - Нет инверсии, вводных оборотов в начале

        Возвращает: 0.0 (разнообразно = human) — 1.0 (однообразно = AI)
        """
        if len(sentences) < 5:
            return 0.5

        # Извлекаем первые слова
        first_words = []
        first_bigrams = []
        for s in sentences:
            words = s.split()
            if words:
                first_words.append(words[0].lower().rstrip('.,;:'))
                if len(words) >= 2:
                    bigram = words[0].lower().rstrip('.,;:') + ' ' + words[1].lower().rstrip('.,;:')
                    first_bigrams.append(bigram)

        if not first_words:
            return 0.5

        # 1. Уникальность первых слов
        unique_ratio = len(set(first_words)) / len(first_words)
        # AI: unique ~0.3-0.5, Human: ~0.6-0.8
        unique_score = max(0, 1.0 - (unique_ratio - 0.2) / 0.6)

        # 2. Максимальное повторение одного начала
        first_counter = Counter(first_words)
        max_repeat = first_counter.most_common(1)[0][1]
        repeat_ratio = max_repeat / len(first_words)
        repeat_score = min(repeat_ratio / 0.3, 1.0)

        # 3. Начало с подлежащего vs. другие конструкции
        # AI: subject-first > 80%, Human: ~60%
        subject_prons = {
            "i", "he", "she", "it", "they", "we", "you", "the", "this",
            "я", "он", "она", "оно", "они", "мы", "вы", "это", "эти",
            "я", "він", "вона", "воно", "вони", "ми", "ви", "це", "ці",
        }
        subject_starts = sum(1 for w in first_words if w in subject_prons)
        subject_ratio = subject_starts / len(first_words) if first_words else 0
        subject_score = min(subject_ratio / 0.5, 1.0)

        # 4. Consecutive same starts — подряд одинаковые начала
        consecutive_same = 0
        for i in range(1, len(first_words)):
            if first_words[i] == first_words[i - 1]:
                consecutive_same += 1
        consec_ratio = consecutive_same / (len(first_words) - 1) if len(first_words) > 1 else 0
        consec_score = min(consec_ratio / 0.15, 1.0)

        score = (
            unique_score * 0.3
            + repeat_score * 0.25
            + subject_score * 0.2
            + consec_score * 0.25
        )
        return max(0.0, min(1.0, score))

    # ─── 11. СТАБИЛЬНОСТЬ READABILITY ─────────────────────────

    def _calc_readability_consistency(self, sentences: list[str]) -> float:
        """AI пишет с постоянной сложностью, люди — с варьирующей.

        Разбиваем текст на окна и считаем readability per window.
        У AI — минимальный разброс между окнами.

        Возвращает: 0.0 (varying = human) — 1.0 (uniform = AI)
        """
        if len(sentences) < 6:
            return 0.5

        # Группируем предложения в окна по 3
        window_size = 3
        windows = []
        for i in range(0, len(sentences) - window_size + 1, window_size):
            window_text = ' '.join(sentences[i:i + window_size])
            words = window_text.split()
            if words:
                avg_word_len = statistics.mean(len(w) for w in words)
                avg_sent_len = statistics.mean(
                    len(s.split()) for s in sentences[i:i + window_size]
                )
                # Простая readability metric на основе длин
                readability = avg_word_len * 0.5 + avg_sent_len * 0.5
                windows.append(readability)

        if len(windows) < 3:
            return 0.5

        # CV readability across windows
        avg_r = statistics.mean(windows)
        stdev_r = statistics.stdev(windows) if len(windows) > 1 else 0
        cv_r = stdev_r / avg_r

        # AI: CV < 0.1, Human: CV > 0.15
        score = max(0, 1.0 - cv_r / 0.2)

        return max(0.0, min(1.0, score))

    # ─── 12. РИТМ ТЕКСТА ─────────────────────────────────────

    def _calc_rhythm(self, sentences: list[str]) -> float:
        """Ритмический анализ — паттерн длин предложений.

        AI: длинное-длинное-длинное (монотонно)
        Human: длинное-короткое-среднее-длинное-короткое (нерегулярно)

        Возвращает: 0.0 (нерегулярный ритм = human) — 1.0 (монотонный = AI)
        """
        if len(sentences) < 5:
            return 0.5

        lengths = [len(s.split()) for s in sentences]

        # 1. Autocorrelation lag-1 (корреляция соседних длин)
        # AI: высокая autocorrelation (рядом стоящие предложения похожей длины)
        # Human: низкая
        n = len(lengths)
        mean_l = statistics.mean(lengths)
        var_l = statistics.variance(lengths) if n > 1 else 1

        if var_l == 0:
            autocorr = 1.0  # Все одинаковой длины — очень AI-like
        else:
            numerator = sum(
                (lengths[i] - mean_l) * (lengths[i + 1] - mean_l)
                for i in range(n - 1)
            ) / (n - 1)
            autocorr = numerator / var_l

        # AC: AI ~0.3-0.6, Human ~-0.1—0.2
        autocorr_score = max(0, (autocorr + 0.1) / 0.7)

        # 2. Длина «серий» (runs) одинаковых категорий длин
        # Категории: short (<10), medium (10-20), long (>20)
        categories = []
        for slen in lengths:
            if slen <= 8:
                categories.append('S')
            elif slen <= 20:
                categories.append('M')
            else:
                categories.append('L')

        # Считаем runs (серии одного типа)
        runs = 1
        for i in range(1, len(categories)):
            if categories[i] != categories[i - 1]:
                runs += 1

        expected_runs = n  # В идеале — каждое предложение другой категории
        run_ratio = runs / expected_runs if expected_runs > 0 else 0

        # AI: мало runs (~0.3-0.5), Human: много runs (~0.7-0.9)
        run_score = max(0, 1.0 - run_ratio / 0.8)

        # 3. Наличие «парных» длин — AI часто делает couplets
        # (два предложения подряд ±3 слова друг от друга)
        pairs = 0
        for i in range(n - 1):
            if abs(lengths[i] - lengths[i + 1]) <= 3:
                pairs += 1
        pair_ratio = pairs / (n - 1) if n > 1 else 0
        # AI: pair_ratio ~0.4-0.6, Human: ~0.2-0.3
        pair_score = min(pair_ratio / 0.5, 1.0)

        score = autocorr_score * 0.4 + run_score * 0.3 + pair_score * 0.3
        return max(0.0, min(1.0, score))

    # ─── 13. N-GRAM PERPLEXITY ────────────────────────────────

    def _calc_perplexity(self, text: str, sentences: list[str]) -> float:
        """Character-level n-gram perplexity with reference corpus.

        Uses both self-trained model and cross-perplexity against
        a pre-computed reference corpus of known human text.

        AI текст имеет низкую perplexity (предсказуемые последовательности
        символов), в то время как человеческий текст более разнообразен.

        Метод:
        - Строим character trigram модель из текста
        - Считаем per-sentence self-perplexity
        - Считаем cross-perplexity против reference corpus
        - Считаем per-sentence perplexity
        - Анализируем вариативность perplexity между предложениями

        AI: равномерная (низкая) perplexity → score → 1.0
        Human: высокая и вариативная perplexity → score → 0.0
        """
        if len(sentences) < 4:
            return 0.5

        # Build character trigram model
        text_lower = text.lower()
        trigram_counts: dict[str, int] = {}
        bigram_counts: dict[str, int] = {}

        for i in range(len(text_lower) - 2):
            trigram = text_lower[i:i + 3]
            bigram = text_lower[i:i + 2]
            trigram_counts[trigram] = trigram_counts.get(trigram, 0) + 1
            bigram_counts[bigram] = bigram_counts.get(bigram, 0) + 1

        if not bigram_counts:
            return 0.5

        # Calculate per-sentence perplexity
        sent_perplexities: list[float] = []

        for sent in sentences:
            sent_lower = sent.lower().strip()
            if len(sent_lower) < 5:
                continue

            log_prob_sum = 0.0
            n_trigrams = 0

            for i in range(len(sent_lower) - 2):
                trigram = sent_lower[i:i + 3]
                bigram = sent_lower[i:i + 2]

                tri_count = trigram_counts.get(trigram, 0)
                bi_count = bigram_counts.get(bigram, 0)

                if bi_count > 0:
                    # Conditional probability with Laplace smoothing
                    prob = (tri_count + 1) / (bi_count + len(trigram_counts) + 1)
                    log_prob_sum += math.log(prob)
                    n_trigrams += 1

            if n_trigrams > 0:
                avg_log_prob = log_prob_sum / n_trigrams
                perplexity = math.exp(-avg_log_prob)
                sent_perplexities.append(perplexity)

        if len(sent_perplexities) < 3:
            return 0.5

        # Analysis
        avg_perplexity = statistics.mean(sent_perplexities)
        perplexity_std = statistics.stdev(sent_perplexities)
        perplexity_cv = perplexity_std / avg_perplexity if avg_perplexity > 0 else 0

        # Low average perplexity = predictable = AI
        # Typical ranges: AI = 3-8, Human = 8-25
        avg_score = max(0.0, 1.0 - (avg_perplexity - 3.0) / 15.0)

        # Low CV of perplexity = uniform predictability = AI
        # AI: CV < 0.2, Human: CV > 0.3
        cv_score = max(0.0, 1.0 - perplexity_cv / 0.4)

        # Cross-perplexity against reference corpus
        from texthumanize.corpus_stats import cross_perplexity, get_reference_perplexity
        effective_lang = getattr(self, '_current_lang', 'en')
        xp = cross_perplexity(text, effective_lang)
        ref_pp = get_reference_perplexity(effective_lang)
        # AI cross-perplexity is usually close to reference (conformist text)
        # Human cross-perplexity deviates more (unique style)
        xp_deviation = abs(xp - ref_pp) / ref_pp if ref_pp > 0 else 0
        xp_score = max(0.0, 1.0 - xp_deviation / 0.5)

        score = avg_score * 0.35 + cv_score * 0.35 + xp_score * 0.30
        return max(0.0, min(1.0, score))

    # ─── 14. ДИСКУРСИВНАЯ СТРУКТУРА ──────────────────────────

    def _calc_discourse(self, text: str, sentences: list[str]) -> float:
        """AI форматирует текст как intro-body-conclusion ригидно.

        Признаки AI:
        - Чёткое intro (1-2 предложения с «обзорной» лексикой)
        - Body с параллельными абзацами равной длины
        - Conclusion с «в заключение», «таким образом»
        - Каждый абзац = ровно одна подтема

        Возвращает: 0.0 (человеческая структура) — 1.0 (AI-шаблон)
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            # Без абзацев — анализируем текст как единый поток
            return self._calc_discourse_flat(text, sentences)

        indicators: list[float] = []

        # 1. Conclusion markers в последнем абзаце
        last_para = paragraphs[-1].lower()
        conclusion_markers = {
            "in conclusion", "to summarize", "in summary", "overall",
            "to conclude", "in short", "ultimately", "all in all",
            "в заключение", "подводя итог", "таким образом", "итого",
            "резюмируя", "в итоге", "підсумовуючи", "на завершення",
        }
        has_conclusion = any(m in last_para for m in conclusion_markers)
        indicators.append(1.0 if has_conclusion else 0.0)

        # 2. Intro markers в первом абзаце
        first_para = paragraphs[0].lower()
        intro_markers = {
            "in today's", "in the modern", "in recent years",
            "the importance of", "it is widely", "has become",
            "plays a crucial", "is one of", "has emerged",
            "в современном", "на сегодняшний день", "в последние годы",
            "является одним из", "играет ключевую роль",
            "у сучасному", "на сьогоднішній",
        }
        has_intro = any(m in first_para for m in intro_markers)
        indicators.append(0.9 if has_intro else 0.1)

        # 3. Однородность длины средних абзацев (body)
        if len(paragraphs) > 3:
            body = paragraphs[1:-1]
            body_lengths = [len(p.split()) for p in body]
            if len(body_lengths) >= 2:
                avg_bl = statistics.mean(body_lengths)
                if avg_bl > 0:
                    cv_bl = statistics.stdev(body_lengths) / avg_bl
                    # AI: CV < 0.2, Human: CV > 0.4
                    indicators.append(max(0.0, 1.0 - cv_bl / 0.5))

        # 4. Каждый абзац начинается с transition word
        if len(paragraphs) > 2:
            trans_count = 0
            transitions = {
                "however", "furthermore", "moreover", "additionally",
                "in addition", "on the other hand", "consequently",
                "first", "second", "third", "finally",
                "однако", "кроме того", "более того", "во-первых",
                "во-вторых", "в-третьих", "наконец",
            }
            for p in paragraphs[1:]:
                first_w = ' '.join(p.split()[:3]).lower()
                if any(first_w.startswith(t) for t in transitions):
                    trans_count += 1
            ratio = trans_count / (len(paragraphs) - 1)
            indicators.append(min(ratio / 0.4, 1.0))

        # 5. Параллельная структура: абзацы начинаются одинаково
        if len(paragraphs) >= 4:
            first_words = [p.split()[0].lower().rstrip('.,;:') for p in paragraphs if p.split()]
            first_counter = Counter(first_words)
            max_same = first_counter.most_common(1)[0][1] if first_counter else 0
            parallelism = max_same / len(first_words) if first_words else 0
            indicators.append(min(parallelism / 0.3, 1.0))

        return max(0.0, min(1.0, statistics.mean(indicators))) if indicators else 0.5

    def _calc_discourse_flat(self, text: str, sentences: list[str]) -> float:
        """Дискурсивный анализ для текста без абзацев."""
        if len(sentences) < 5:
            return 0.5

        indicators: list[float] = []

        # Intro + conclusion
        first_sent = sentences[0].lower()
        last_sent = sentences[-1].lower()

        conclusion_words = {"conclusion", "summarize", "summary", "overall",
                           "заключение", "итог", "таким образом", "підсумовуючи"}
        indicators.append(0.8 if any(w in last_sent for w in conclusion_words) else 0.2)

        intro_words = {"today's", "modern", "importance", "crucial",
                      "современном", "сьогоднішній", "ключевую"}
        indicators.append(0.7 if any(w in first_sent for w in intro_words) else 0.3)

        return max(0.0, min(1.0, statistics.mean(indicators))) if indicators else 0.5

    # ─── 15. СЕМАНТИЧЕСКИЕ ПОВТОРЫ ────────────────────────────

    def _calc_semantic_repetition(self, text: str, sentences: list[str]) -> float:
        """AI часто перефразирует одну мысль в разных предложениях.

        Анализируем:
        - Jaccard similarity между предложениями (по content words)
        - Количество «повторных» предложений (similarity > 0.4)
        - AI перефразирует вместо того, чтобы добавлять новую информацию

        Возвращает: 0.0 (каждое предложение = новая мысль) — 1.0 (повторы)
        """
        if len(sentences) < 5:
            return 0.5

        # Extract content word sets for each sentence
        punct = '.,;:!?"\'()[]{}'
        sent_words: list[set[str]] = []
        for s in sentences:
            words = {
                w.lower().strip(punct)
                for w in s.split()
                if len(w.strip(punct)) > 3
            }
            if words:
                sent_words.append(words)

        if len(sent_words) < 4:
            return 0.5

        # Pairwise Jaccard similarity (non-adjacent only)
        high_sim_count = 0
        total_pairs = 0
        sim_values: list[float] = []

        for i in range(len(sent_words)):
            # Skip adjacent, check within window of 6
            for j in range(i + 2, min(i + 6, len(sent_words))):
                intersection = len(sent_words[i] & sent_words[j])
                union = len(sent_words[i] | sent_words[j])
                if union > 0:
                    sim = intersection / union
                    sim_values.append(sim)
                    total_pairs += 1
                    if sim > 0.35:
                        high_sim_count += 1

        if not sim_values:
            return 0.5

        avg_sim = statistics.mean(sim_values)
        high_sim_ratio = high_sim_count / total_pairs if total_pairs > 0 else 0

        # AI: avg_sim ~0.15-0.25, high_sim_ratio ~0.1-0.3
        # Human: avg_sim ~0.05-0.10, high_sim_ratio ~0-0.05
        sim_score = min(avg_sim / 0.2, 1.0)
        ratio_score = min(high_sim_ratio / 0.15, 1.0)

        score = sim_score * 0.5 + ratio_score * 0.5
        return max(0.0, min(1.0, score))

    # ─── 16. СПЕЦИФИЧНОСТЬ УПОМИНАНИЙ ─────────────────────────

    def _calc_entity_specificity(self, text: str, words: list[str]) -> float:
        """AI использует generic entities, люди — конкретные.

        AI: "a company", "researchers", "many experts", "a recent study"
        Human: "Google", "Dr. Smith", "my boss", "last Tuesday"

        Анализируем:
        - Наличие proper nouns (capitalized non-start words)
        - Конкретные числа/даты
        - Generic vs specific references
        - Наличие личного опыта (I, my, our)

        Возвращает: 0.0 (конкретно = human) — 1.0 (абстрактно = AI)
        """
        if len(words) < 20:
            return 0.5

        total = len(words)
        indicators: list[float] = []

        # 1. Generic quantifiers (AI loves vague quantities)
        generic_quants = {
            "various", "numerous", "several", "many", "multiple",
            "significant", "substantial", "considerable", "widespread",
            "a number of", "a variety of", "a wide range",
            "различные", "многочисленные", "многие", "множество",
            "значительный", "существенный", "ряд", "широкий спектр",
            "різні", "численні", "багато", "безліч",
        }
        generic_count = sum(1 for w in words if w.lower() in generic_quants)
        # Also check multi-word
        text_lower = text.lower()
        for phrase in ["a number of", "a variety of", "a wide range",
                       "широкий спектр", "ряд", "целый ряд"]:
            generic_count += text_lower.count(phrase)
        generic_ratio = generic_count / total
        indicators.append(min(generic_ratio / 0.03, 1.0))

        # 2. Specific numbers, dates, proper nouns (human marker)
        # Specific numbers (not round): 15, 2023, 42, $3.50
        specific_nums = len(re.findall(
            r'\b\d{1,2}(?:\.\d+)?\b|\$\d+|\b\d{4}\b|\b\d+%',
            text
        ))
        # Proper nouns (capitalized words not at sentence start)
        proper_nouns = 0
        for i, w in enumerate(words):
            if i > 0 and w[0:1].isupper() and w.isalpha() and len(w) > 1:
                # Check it's not after a period
                prev = words[i - 1] if i > 0 else ""
                if not prev.endswith(('.', '!', '?', ':', '"', '\n')):
                    proper_nouns += 1

        specificity = (specific_nums + proper_nouns) / total
        # High specificity = human
        indicators.append(max(0.0, 1.0 - specificity / 0.08))

        # 3. Personal references (I, my, me, we, our)
        personal = {"i", "my", "me", "we", "our", "mine",
                    "я", "мой", "моя", "моё", "мне", "меня", "мы", "наш",
                    "я", "мій", "моя", "моє", "мені", "мене", "ми", "наш"}
        personal_count = sum(1 for w in words if w.lower() in personal)
        personal_ratio = personal_count / total
        # Has personal references = likely human
        indicators.append(max(0.0, 1.0 - personal_ratio / 0.04))

        # 4. Hedging language (AI hedges a lot)
        hedges = {
            "arguably", "potentially", "relatively", "particularly",
            "generally", "typically", "essentially", "fundamentally",
            "по сути", "в целом", "как правило", "в значительной степени",
            "в основному", "як правило", "загалом",
        }
        hedge_count = sum(1 for w in words if w.lower() in hedges)
        for phrase in hedges:
            if ' ' in phrase:
                hedge_count += text_lower.count(phrase)
        hedge_ratio = hedge_count / total
        indicators.append(min(hedge_ratio / 0.02, 1.0))

        return max(0.0, min(1.0, statistics.mean(indicators))) if indicators else 0.5

    # ─── 17. АНАЛИЗ ЗАЛОГА (VOICE) ────────────────────────────

    def _calc_voice(self, text: str, sentences: list[str]) -> float:
        """AI overuses passive voice и номинализации.

        AI: "The implementation was carried out" "Analysis was performed"
        Human: "We implemented" "I analyzed"

        Возвращает: 0.0 (active = human) — 1.0 (passive-heavy = AI)
        """
        if len(sentences) < 4:
            return 0.5

        passive_count = 0
        nominalization_count = 0
        total_clauses = len(sentences)

        # Passive voice patterns (EN)
        passive_patterns = [
            r'\b(?:is|are|was|were|been|being|be)\s+\w+ed\b',
            r'\b(?:is|are|was|were|been|being|be)\s+\w+en\b',
            r'\b(?:has|have|had)\s+been\s+\w+ed\b',
            r'\bwas\s+\w+ed\b',
            r'\bwere\s+\w+ed\b',
        ]

        # Passive patterns (RU/UK)
        passive_patterns_ru = [
            r'\b\w+(?:ован|ирован|ен|ан|ят|ит)(?:а|о|ы|и)?\s+(?:был|была|было|были)\b',
            r'\b(?:был|была|было|были)\s+\w+(?:ован|ирован|ен|ан)\w*\b',
            r'\b\w+(?:ся|сь)\b',  # Reflexive verbs (often passive in RU)
        ]

        text_lower = text.lower()

        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, text_lower))

        for pattern in passive_patterns_ru:
            passive_count += len(re.findall(pattern, text_lower))

        # Nominalizations: -tion, -ment, -ness, -ity (overused by AI)
        nominalization_suffixes = [
            r'\b\w{4,}tion\b', r'\b\w{4,}ment\b', r'\b\w{4,}ness\b',
            r'\b\w{4,}ity\b', r'\b\w{4,}ence\b', r'\b\w{4,}ance\b',
            # RU: -ация, -ение, -ование
            r'\b\w{4,}ация\b', r'\b\w{4,}ение\b', r'\b\w{4,}ование\b',
        ]

        for suffix_pat in nominalization_suffixes:
            nominalization_count += len(re.findall(suffix_pat, text_lower))

        # Passive ratio
        passive_ratio = passive_count / total_clauses if total_clauses > 0 else 0
        # AI: ~0.3-0.6 passive per sentence, Human: ~0.1-0.2
        passive_score = min(passive_ratio / 0.4, 1.0)

        # Nominalization density
        word_count = len(text.split())
        nom_ratio = nominalization_count / word_count if word_count > 0 else 0
        # AI: ~0.05-0.10, Human: ~0.02-0.04
        nom_score = min(nom_ratio / 0.07, 1.0)

        # Active voice markers (human uses more)
        active_markers = len(re.findall(
            r'\b(?:I|we|you|he|she|they)\s+\w+(?:ed|s)\b',
            text, re.IGNORECASE
        ))
        active_ratio = active_markers / total_clauses if total_clauses > 0 else 0
        active_score = max(0.0, 1.0 - active_ratio / 0.3)

        score = passive_score * 0.35 + nom_score * 0.35 + active_score * 0.30
        return max(0.0, min(1.0, score))

    # ─── 18. TOPIC SENTENCE ПАТТЕРН ───────────────────────────

    def _calc_topic_sentence(self, text: str, sentences: list[str]) -> float:
        """AI ставит topic sentence (главную мысль) первой в каждом абзаце.

        Классическая 5-paragraph essay structure:
        - Каждый абзац начинается с обобщающего утверждения
        - Далее идут supporting details
        - AI делает это в 100% абзацев

        Люди часто:
        - Начинают с примера/анекдота
        - Используют delayed thesis
        - Не следуют шаблону paragraph structure

        Возвращает: 0.0 (нестандартная структура = human) — 1.0 (идеальная = AI)
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]

        if len(paragraphs) < 2:
            # Для текста без абзацев: анализируем по группам предложений
            if len(sentences) < 8:
                return 0.5
            # Group sentences by 3-4 as pseudo-paragraphs
            paragraphs = []
            for i in range(0, len(sentences) - 2, 3):
                paragraphs.append(' '.join(sentences[i:i + 3]))

        if len(paragraphs) < 2:
            return 0.5

        indicators: list[float] = []

        for para in paragraphs:
            para_sentences = [s.strip() for s in re.split(r'[.!?]+', para) if len(s.strip()) > 10]
            if len(para_sentences) < 2:
                continue

            first_sent = para_sentences[0].lower()
            _rest = ' '.join(para_sentences[1:]).lower()  # noqa: F841

            # Topic sentence indicators:
            # 1. First sentence contains abstract/general words
            general_words = {
                "important", "significant", "crucial", "essential", "key",
                "fundamental", "critical", "notable", "remarkable",
                "role", "impact", "influence", "factor", "aspect",
                "важно", "значимо", "ключевой", "существенно",
                "роль", "влияние", "фактор", "аспект",
            }
            has_general = sum(1 for w in first_sent.split() if w.strip('.,;:') in general_words)

            # 2. First sentence is longer than average of rest
            first_len = len(first_sent.split())
            rest_lens = [len(s.split()) for s in para_sentences[1:]]
            avg_rest_len = statistics.mean(rest_lens) if rest_lens else first_len

            is_topic_sent = (
                has_general >= 1
                or first_len >= avg_rest_len * 0.8
            )
            indicators.append(0.8 if is_topic_sent else 0.2)

        if not indicators:
            return 0.5

        # If ALL paragraphs have topic sentences → very AI-like
        topic_ratio = statistics.mean(indicators)
        return max(0.0, min(1.0, topic_ratio))

    # ─── ENSEMBLE AGGREGATION ─────────────────────────────────

    def _ensemble_aggregate(
        self,
        scores: dict[str, float],
        weights: dict[str, float] | None = None,
    ) -> float:
        """Ensemble boosting aggregation вместо простого weighted sum.

        Использует 3 «слабых классификатора»:
        1. Weighted sum (базовый)
        2. Strong signal detector (анализ ключевых метрик)
        3. Majority voting (количество метрик > порога)

        Финальный скор — взвешенная комбинация всех трёх.
        """
        w = weights if weights is not None else self._WEIGHTS
        # 1. Weighted sum (base learner)
        weighted_sum = sum(
            scores[k] * w[k] for k in scores
        )
        total_weight = sum(w.values())
        base_score = weighted_sum / total_weight

        # 2. Strong signal detector
        # Если ключевые «сильные» метрики все высокие/низкие —
        # это сильный сигнал независимо от остальных
        strong_metrics = [
            "pattern", "burstiness", "opening", "stylometry",
            "discourse", "voice", "grammar",
        ]
        strong_vals = [scores.get(m, 0.5) for m in strong_metrics]
        strong_avg = statistics.mean(strong_vals)

        # Нелинейное усиление: если сильные метрики все > 0.55 → boost up
        if strong_avg > 0.55:
            strong_score = 0.5 + (strong_avg - 0.5) * 1.8
        elif strong_avg < 0.35:
            strong_score = 0.5 + (strong_avg - 0.5) * 1.5
        else:
            strong_score = strong_avg

        strong_score = max(0.0, min(1.0, strong_score))

        # 3. Majority voting
        ai_threshold = 0.55
        n_ai = sum(1 for v in scores.values() if v >= ai_threshold)
        n_total = len(scores)
        vote_ratio = n_ai / n_total if n_total > 0 else 0.5

        # Нелинейное преобразование голосов
        if vote_ratio > 0.6:
            vote_score = 0.5 + (vote_ratio - 0.5) * 1.5
        elif vote_ratio < 0.4:
            vote_score = 0.5 + (vote_ratio - 0.5) * 1.5
        else:
            vote_score = vote_ratio

        vote_score = max(0.0, min(1.0, vote_score))

        # Ensemble: взвешенная комбинация трёх классификаторов
        ensemble = (
            base_score * 0.40      # Base weighted sum
            + strong_score * 0.40  # Strong signal detector
            + vote_score * 0.20    # Majority voting
        )

        return max(0.0, min(1.0, ensemble))

    # ─── КАЛИБРОВКА И ОБЪЯСНЕНИЯ ──────────────────────────────

    def _calibrate(self, raw: float) -> float:
        """Sigmoidal calibration для лучшего разделения.

        Усиливает разницу в средней зоне (0.25–0.70).
        """
        # Logistic function — смягчённая (center=0.35, k=8)
        # Не давит средние raw so агрессивно, позволяя
        # текстам с raw=0.30-0.40 получить заметный score.
        k = 8.0  # steepness (was 10)
        center = 0.35  # center (was 0.40)
        return 1.0 / (1.0 + math.exp(-k * (raw - center)))

    def _generate_explanations(
        self,
        scores: dict[str, float],
        result: DetectionResult,
        lang: str,
    ) -> list[str]:
        """Сгенерировать человекочитаемые объяснения."""
        explanations = []
        threshold = 0.6  # Выше = "AI-like"

        feature_names = {
            "entropy": "Low text entropy (predictable word choice)",
            "burstiness": "Uniform sentence lengths (low burstiness)",
            "vocabulary": "Limited vocabulary diversity",
            "zipf": "Word frequency deviation from natural distribution",
            "stylometry": "Formal/academic writing style typical of AI",
            "pattern": "AI-characteristic words and phrases detected",
            "punctuation": "Punctuation profile typical of AI",
            "coherence": "Overly consistent paragraph transitions",
            "grammar": "Unnaturally perfect grammar and formatting",
            "opening": "Repetitive sentence openings",
            "readability": "Uniform readability across text segments",
            "rhythm": "Monotonous sentence length rhythm",
            "perplexity": "Low character-level perplexity (predictable patterns)",
            "discourse": "Rigid intro-body-conclusion discourse structure",
            "semantic_rep": "Semantic paraphrasing of same ideas across paragraphs",
            "entity": "Generic/abstract entity references instead of specifics",
            "voice": "Heavy passive voice and nominalizations",
            "topic_sentence": "Every paragraph starts with a topic sentence",
        }

        feature_names_ru = {
            "entropy": "Низкая энтропия текста (предсказуемый выбор слов)",
            "burstiness": "Однородная длина предложений (низкая вариативность)",
            "vocabulary": "Ограниченное лексическое разнообразие",
            "zipf": "Отклонение частот слов от естественного распределения",
            "stylometry": "Формальный академический стиль, характерный для AI",
            "pattern": "Обнаружены AI-характерные слова и фразы",
            "punctuation": "Пунктуационный профиль характерный для AI",
            "coherence": "Излишне последовательные переходы между абзацами",
            "grammar": "Неестественно идеальная грамматика и форматирование",
            "opening": "Повторяющиеся начала предложений",
            "readability": "Одинаковая читаемость по всему тексту",
            "rhythm": "Монотонный ритм длины предложений",
            "perplexity": "Низкая перплексия символьных n-gram (предсказуемые паттерны)",
            "discourse": "Ригидная структура вступление-основа-вывод",
            "semantic_rep": "Семантическое перефразирование одних идей в разных абзацах",
            "entity": "Абстрактные упоминания вместо конкретных имён/дат",
            "voice": "Чрезмерный пассивный залог и номинализации",
            "topic_sentence": "Каждый абзац начинается с обобщающего утверждения",
        }

        names = feature_names_ru if lang in ("ru", "uk") else feature_names

        # Sort by score (most AI-like first)
        sorted_features = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for feature, score in sorted_features:
            if score >= threshold:
                explanations.append(
                    f"{names.get(feature, feature)} ({score:.0%})"
                )

        # Добавляем позитивные (human-like) индикаторы
        human_features = [
            (feature, score) for feature, score in sorted_features
            if score < 0.3
        ]
        if human_features:
            explanations.append("")
            for feature, score in human_features[:3]:
                names_human_en = {
                    "entropy": "Natural text entropy",
                    "burstiness": "Good sentence length variation",
                    "vocabulary": "Rich vocabulary",
                    "pattern": "Few AI-characteristic patterns",
                    "opening": "Diverse sentence openings",
                    "rhythm": "Natural writing rhythm",
                }
                names_human_ru = {
                    "entropy": "Естественная энтропия текста",
                    "burstiness": "Хорошая вариативность длины предложений",
                    "vocabulary": "Богатый словарный запас",
                    "pattern": "Мало AI-характерных паттернов",
                    "opening": "Разнообразные начала предложений",
                    "rhythm": "Естественный ритм письма",
                }
                hn = names_human_ru if lang in ("ru", "uk") else names_human_en
                explanation = hn.get(feature)
                if explanation:
                    explanations.append(f"✓ {explanation}")

        return explanations

# ─── Удобная функция ─────────────────────────────────────────

def detect_ai(text: str, lang: str = "auto") -> DetectionResult:
    """Детектировать AI-сгенерированный текст.

    Args:
        text: Текст для анализа.
        lang: Код языка ('auto', 'ru', 'uk', 'en', etc.)

    Returns:
        DetectionResult с вероятностью AI и детальными метриками.

    Examples:
        >>> result = detect_ai("This text utilizes comprehensive methodology.")
        >>> print(f"AI probability: {result.ai_probability:.1%}")
        >>> print(result.verdict)  # "human", "mixed", or "ai"
    """
    detector = AIDetector(lang=lang)
    return detector.detect(text)

def detect_ai_batch(
    texts: list[str], lang: str = "auto"
) -> list[DetectionResult]:
    """Детектировать AI в нескольких текстах.

    Args:
        texts: Список текстов.
        lang: Код языка.

    Returns:
        Список DetectionResult.
    """
    detector = AIDetector(lang=lang)
    return [detector.detect(t) for t in texts]
