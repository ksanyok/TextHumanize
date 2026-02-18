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

import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from texthumanize.lang import get_lang_pack
from texthumanize.sentence_split import split_sentences

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
        "entropy": 0.08,
        "burstiness": 0.14,        # Сильный сигнал: AI = равномерные предложения
        "vocabulary": 0.07,
        "zipf": 0.03,              # Ненадёжен для коротких текстов
        "stylometry": 0.08,
        "pattern": 0.20,           # AI patterns — самый сильный сигнал
        "punctuation": 0.06,
        "coherence": 0.08,
        "grammar": 0.06,
        "opening": 0.09,
        "readability": 0.05,
        "rhythm": 0.06,
    }

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

        # ── Вычисляем все 12 метрик ──

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
        }

        weighted_sum = sum(
            scores[k] * self._WEIGHTS[k] for k in scores
        )
        total_weight = sum(self._WEIGHTS.values())
        raw_probability = weighted_sum / total_weight

        # Калибровка: sigmoidal transform для лучшего разделения
        result.ai_probability = self._calibrate(raw_probability)

        # Уверенность зависит от длины текста и разброса метрик
        text_length_factor = min(len(words) / 200, 1.0)
        metric_agreement = 1.0 - statistics.stdev(list(scores.values()))
        result.confidence = min(text_length_factor * 0.7 + metric_agreement * 0.3, 1.0)

        # Вердикт
        if result.ai_probability > 0.75:
            result.verdict = "ai"
        elif result.ai_probability > 0.45:
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
            "weights": dict(self._WEIGHTS),
        }

        return result

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
        bigrams = Counter()
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

        if len(clean_words) < 50:
            return 0.5

        freq = Counter(clean_words)
        sorted_freqs = sorted(freq.values(), reverse=True)

        if len(sorted_freqs) < 10:
            return 0.5

        # Теоретический Zipf: f(r) = f(1) / r
        f1 = sorted_freqs[0]
        n = min(50, len(sorted_freqs))

        # Считаем отклонение от идеального Zipf
        deviations = []
        for rank in range(1, n + 1):
            actual = sorted_freqs[rank - 1]
            expected = f1 / rank
            if expected > 0:
                dev = abs(actual - expected) / expected
                deviations.append(dev)

        if not deviations:
            return 0.5

        avg_deviation = statistics.mean(deviations)

        # Для коротких текстов (<200 слов) отклонение от Ципфа
        # ненадёжно — сдвигаем скор к 0.5
        length_reliability = min(len(clean_words) / 200, 1.0)

        # Проверяем «хвост» распределения — AI делает его слишком плоским
        tail_start = len(sorted_freqs) // 3
        tail = sorted_freqs[tail_start:]
        if tail and len(tail) > 2:
            tail_mean = statistics.mean(tail)
            tail_cv = statistics.stdev(tail) / tail_mean if tail_mean > 0 else 0
            # Низкий CV хвоста = AI (слишком равномерный)
            # Но для коротких текстов хвост часто = все по 1 => CV = 0 всегда
            if all(v == tail[0] for v in tail):
                # Все значения одинаковы (типично для коротких текстов) — ненадёжно
                tail_score = 0.5
            else:
                tail_score = max(0, 1.0 - tail_cv / 0.8)
        else:
            tail_score = 0.5

        raw_score = avg_deviation * 0.5 + tail_score * 0.5
        # Для коротких текстов: сдвигаем к 0.5
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

        score = (
            density_score * 0.4
            + connector_score * 0.3
            + formal_score * 0.3
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
        if avg_r == 0:
            return 0.5

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

    # ─── КАЛИБРОВКА И ОБЪЯСНЕНИЯ ──────────────────────────────

    def _calibrate(self, raw: float) -> float:
        """Sigmoidal calibration для лучшего разделения.

        Усиливает разницу в средней зоне (0.3–0.7).
        """
        # Logistic function centered at 0.45 (сдвиг: AI текст обычно > 0.45)
        k = 8.0  # steepness
        return 1.0 / (1.0 + math.exp(-k * (raw - 0.45)))

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
