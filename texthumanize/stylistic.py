"""Стилистический отпечаток — анализ и имитация авторского стиля.

Извлекает «отпечаток» авторского стиля из образца текста и позволяет
адаптировать обработку под него. Полностью rule-based, без ML.

Метрики стиля:
- Распределение длины предложений (мода, медиана, σ)
- Частота использования знаков препинания (;:—…!?)
- Предпочтения по типу предложений (простые vs сложные)
- Vocabulary level (бытовая vs книжная лексика)
- Частота вводных конструкций
- Среднее число абзацев и их длина
- Предпочитаемые конструкции начала предложений
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class StylisticFingerprint:
    """Стилистический отпечаток текста."""

    # Длины предложений
    sentence_length_mean: float = 0.0
    sentence_length_median: float = 0.0
    sentence_length_std: float = 0.0
    sentence_length_mode: int = 0

    # Пунктуация (частота на 1000 символов)
    semicolons_per_k: float = 0.0
    colons_per_k: float = 0.0
    dashes_per_k: float = 0.0
    exclamations_per_k: float = 0.0
    questions_per_k: float = 0.0
    ellipsis_per_k: float = 0.0
    commas_per_k: float = 0.0

    # Структура
    avg_paragraph_length: float = 0.0  # предложений на абзац
    complex_sentence_ratio: float = 0.0  # доля сложных предложений
    question_ratio: float = 0.0  # доля вопросительных
    exclamation_ratio: float = 0.0  # доля восклицательных

    # Лексика
    avg_word_length: float = 0.0
    long_word_ratio: float = 0.0  # слова > 8 символов
    vocabulary_richness: float = 0.0  # TTR

    # Начала предложений
    pronoun_start_ratio: float = 0.0  # начинаются с местоимения
    connector_start_ratio: float = 0.0  # начинаются со связки

    # Raw распределение длин (для matching)
    length_distribution: dict[int, float] = field(default_factory=dict)

    def similarity(self, other: StylisticFingerprint) -> float:
        """Вычислить сходство двух отпечатков (0-1, 1=идентичные)."""
        features_self = self._to_vector()
        features_other = other._to_vector()

        if not features_self or not features_other:
            return 0.5

        # Косинусное сходство
        dot = sum(a * b for a, b in zip(features_self, features_other))
        norm_a = math.sqrt(sum(x * x for x in features_self))
        norm_b = math.sqrt(sum(x * x for x in features_other))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def _to_vector(self) -> list[float]:
        """Преобразовать отпечаток в вектор признаков."""
        return [
            self.sentence_length_mean / 30.0,
            self.sentence_length_std / 15.0,
            self.semicolons_per_k / 5.0,
            self.colons_per_k / 5.0,
            self.dashes_per_k / 10.0,
            self.commas_per_k / 50.0,
            self.complex_sentence_ratio,
            self.question_ratio,
            self.exclamation_ratio,
            self.avg_word_length / 10.0,
            self.long_word_ratio,
            self.vocabulary_richness,
            self.pronoun_start_ratio,
            self.connector_start_ratio,
            self.avg_paragraph_length / 10.0,
        ]


# Местоимения по языкам (для подсчёта pronoun_start_ratio)
_PRONOUNS = {
    "en": {"i", "we", "he", "she", "it", "they", "you", "this", "that", "these", "those"},
    "ru": {"я", "мы", "он", "она", "оно", "они", "вы", "ты", "это", "тот", "та", "те"},
    "uk": {"я", "ми", "він", "вона", "воно", "вони", "ви", "ти", "це", "той", "та", "ті"},
    "de": {"ich", "wir", "er", "sie", "es", "du", "ihr", "dies", "diese", "dieser"},
    "fr": {"je", "nous", "il", "elle", "ils", "elles", "tu", "vous", "ce", "cette"},
    "es": {"yo", "nosotros", "él", "ella", "ellos", "ellas", "tú", "este", "esta"},
    "it": {"io", "noi", "lui", "lei", "loro", "tu", "voi", "questo", "questa"},
    "pl": {"ja", "my", "on", "ona", "ono", "oni", "one", "ty", "wy", "ten", "ta", "to"},
    "pt": {"eu", "nós", "ele", "ela", "eles", "elas", "tu", "este", "esta"},
}

# Типичные связки по языкам
_CONNECTORS = {
    "en": {"however", "moreover", "furthermore", "additionally", "nonetheless",
           "consequently", "therefore", "nevertheless", "thus", "hence"},
    "ru": {"однако", "кроме того", "более того", "тем не менее", "следовательно",
           "поэтому", "таким образом", "вместе с тем", "при этом", "впрочем"},
    "uk": {"однак", "крім того", "більш того", "тим не менш", "отже",
           "тому", "таким чином", "водночас", "при цьому", "втім"},
    "de": {"jedoch", "außerdem", "darüber hinaus", "dennoch", "folglich",
           "deshalb", "somit", "zudem", "ferner", "überdies"},
    "fr": {"cependant", "en outre", "de plus", "néanmoins", "par conséquent",
           "donc", "ainsi", "toutefois", "d'ailleurs", "par ailleurs"},
    "es": {"sin embargo", "además", "no obstante", "por lo tanto",
           "por consiguiente", "asimismo", "por otra parte", "en cambio"},
    "it": {"tuttavia", "inoltre", "ciononostante", "pertanto", "dunque",
           "perciò", "altresì", "nondimeno", "comunque"},
    "pl": {"jednak", "ponadto", "niemniej", "dlatego", "zatem",
           "co więcej", "poza tym", "jednakże", "w związku z tym"},
    "pt": {"no entanto", "além disso", "contudo", "portanto", "assim",
           "ademais", "todavia", "por conseguinte", "outrossim"},
}


class StylisticAnalyzer:
    """Анализатор стилистического отпечатка текста."""

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._pronouns = _PRONOUNS.get(lang, _PRONOUNS["en"])
        self._connectors = _CONNECTORS.get(lang, _CONNECTORS["en"])

    def extract(self, text: str) -> StylisticFingerprint:
        """Извлечь стилистический отпечаток из текста.

        Args:
            text: Текст-образец для анализа стиля.

        Returns:
            StylisticFingerprint с метриками стиля.
        """
        fp = StylisticFingerprint()

        if not text or len(text.strip()) < 100:
            return fp

        sentences = self._split_sentences(text)
        if not sentences:
            return fp

        words = text.lower().split()
        text_len = len(text)

        # ─── Длины предложений ───────────────────────────────
        lengths = [len(s.split()) for s in sentences]
        fp.sentence_length_mean = sum(lengths) / len(lengths)
        sorted_lengths = sorted(lengths)
        mid = len(sorted_lengths) // 2
        fp.sentence_length_median = float(
            sorted_lengths[mid] if len(sorted_lengths) % 2 == 1
            else (sorted_lengths[mid - 1] + sorted_lengths[mid]) / 2.0
        )
        variance = sum(
            (sl - fp.sentence_length_mean) ** 2 for sl in lengths
        ) / len(lengths)
        fp.sentence_length_std = variance ** 0.5

        # Мода
        length_counts = Counter(lengths)
        fp.sentence_length_mode = length_counts.most_common(1)[0][0]

        # Распределение длин (нормализованное)
        for length, count in length_counts.items():
            fp.length_distribution[length] = count / len(lengths)

        # ─── Пунктуация ──────────────────────────────────────
        k = text_len / 1000.0 if text_len > 0 else 1.0
        fp.semicolons_per_k = text.count(';') / k
        fp.colons_per_k = text.count(':') / k
        fp.dashes_per_k = (text.count('—') + text.count('–')) / k
        fp.exclamations_per_k = text.count('!') / k
        fp.questions_per_k = text.count('?') / k
        fp.ellipsis_per_k = (text.count('…') + text.count('...')) / k
        fp.commas_per_k = text.count(',') / k

        # ─── Структура ───────────────────────────────────────
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if paragraphs:
            para_sentence_counts = []
            for para in paragraphs:
                para_sents = self._split_sentences(para)
                para_sentence_counts.append(len(para_sents))
            fp.avg_paragraph_length = (
                sum(para_sentence_counts) / len(para_sentence_counts)
            )

        # Сложные предложения (содержат ;, :, или подчинительные союзы)
        complex_count = sum(
            1 for s in sentences
            if ';' in s or ':' in s or ', ' in s.split(' ', 5)[-1]
        )
        fp.complex_sentence_ratio = complex_count / len(sentences)

        # Типы предложений
        fp.question_ratio = sum(
            1 for s in sentences if s.strip().endswith('?')
        ) / len(sentences)
        fp.exclamation_ratio = sum(
            1 for s in sentences if s.strip().endswith('!')
        ) / len(sentences)

        # ─── Лексика ─────────────────────────────────────────
        clean_words = [
            w.strip('.,;:!?"\'()[]{}«»""')
            for w in words if len(w.strip('.,;:!?"\'()[]{}«»""')) > 0
        ]
        if clean_words:
            fp.avg_word_length = sum(len(w) for w in clean_words) / len(clean_words)
            fp.long_word_ratio = sum(
                1 for w in clean_words if len(w) > 8
            ) / len(clean_words)
            # TTR (на окне 100 слов)
            if len(clean_words) >= 100:
                segment = clean_words[:100]
                fp.vocabulary_richness = len(set(segment)) / 100.0
            else:
                fp.vocabulary_richness = len(set(clean_words)) / len(clean_words)

        # ─── Начала предложений ──────────────────────────────
        if sentences:
            pronoun_starts = sum(
                1 for s in sentences
                if s.split()[0].lower().rstrip('.,;') in self._pronouns
            )
            fp.pronoun_start_ratio = pronoun_starts / len(sentences)

            connector_starts = 0
            for s in sentences:
                first_words = ' '.join(s.split()[:3]).lower()
                if any(c in first_words for c in self._connectors):
                    connector_starts += 1
            fp.connector_start_ratio = connector_starts / len(sentences)

        return fp

    def _split_sentences(self, text: str) -> list[str]:
        """Простая разбивка на предложения (без тяжёлого сплиттера)."""
        sentences = re.split(r'(?<=[.!?…])\s+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.split()) > 1]


# ═══════════════════════════════════════════════════════════════
#  STYLOMETRIC ANONYMIZER
# ═══════════════════════════════════════════════════════════════


class StylometricAnonymizer:
    """Трансформирует текст, чтобы его стилистический отпечаток отличался от исходного.

    Стратегия: отдаляем метрики текста от его «настоящего» отпечатка,
    приближая к целевому (или генерируя случайный целевой, средний по корпусу).
    Все трансформации rule-based — без ML.

    Типичное применение — whistleblower protection, anonymous peer review,
    academic authorship privacy.
    """

    def __init__(self, lang: str = "en", seed: int | None = None):
        self.lang = lang
        self._analyzer = StylisticAnalyzer(lang=lang)
        import random as _random
        self._rng = _random.Random(seed)

    def anonymize(
        self,
        text: str,
        target: StylisticFingerprint | str | None = None,
    ) -> AnonymizeResult:
        """Анонимизировать стиль текста.

        Args:
            text: Исходный текст.
            target: Целевой отпечаток для «приближения».
                Может быть ``StylisticFingerprint``, имя пресета (str),
                или ``None`` (по умолчанию используется ``'journalist'``).

        Returns:
            ``AnonymizeResult`` с трансформированным текстом, сходствами
            до/после и списком изменений.
        """
        if isinstance(target, str):
            target = STYLE_PRESETS.get(target)
        if target is None:
            target = STYLE_PRESETS["journalist"]

        source_fp = self._analyzer.extract(text)
        source_sim = source_fp.similarity(target)

        changes: list[dict] = []
        result = text

        # 1. Sentence length adjustment
        result = self._adjust_sentence_lengths(result, source_fp, target, changes)

        # 2. Punctuation transformation
        result = self._adjust_punctuation(result, source_fp, target, changes)

        # 3. Sentence starters diversity
        result = self._adjust_starters(result, source_fp, target, changes)

        # 4. Vocabulary adjustment (word length)
        result = self._adjust_vocabulary(result, source_fp, target, changes)

        result_fp = self._analyzer.extract(result)
        result_sim = result_fp.similarity(target)

        return AnonymizeResult(
            text=result,
            original=text,
            target_preset=(
                next(
                    (k for k, v in STYLE_PRESETS.items() if v is target),
                    "custom",
                )
            ),
            similarity_before=round(source_sim, 4),
            similarity_after=round(result_sim, 4),
            changes=changes,
        )

    # ── Private transforms ────────────────────────────────────

    def _sentences(self, text: str) -> list[str]:
        return self._analyzer._split_sentences(text)

    def _adjust_sentence_lengths(
        self,
        text: str,
        src: StylisticFingerprint,
        tgt: StylisticFingerprint,
        changes: list[dict],
    ) -> str:
        """Split long / merge short sentences to match target mean."""
        sentences = self._sentences(text)
        if not sentences or len(sentences) < 2:
            return text

        diff = tgt.sentence_length_mean - src.sentence_length_mean

        if abs(diff) < 3:
            return text  # close enough

        new_sentences: list[str] = []

        if diff < -3:
            # Target wants shorter sentences → split long ones
            threshold = max(8, int(tgt.sentence_length_mean + 5))
            for s in sentences:
                words = s.split()
                if len(words) > threshold and self._rng.random() < 0.6:
                    mid = len(words) // 2
                    # Find a comma near the middle
                    best = mid
                    for i in range(max(3, mid - 5), min(len(words) - 3, mid + 5)):
                        if words[i].endswith(','):
                            best = i + 1
                            break
                    part1 = ' '.join(words[:best]).rstrip(',') + '.'
                    part2 = ' '.join(words[best:])
                    # Capitalize second part
                    if part2:
                        part2 = part2[0].upper() + part2[1:]
                    new_sentences.extend([part1, part2])
                    changes.append({
                        "type": "anon_split",
                        "description": f"Split: {s[:50]}…",
                    })
                else:
                    new_sentences.append(s)
        else:
            # Target wants longer sentences → merge short ones
            threshold = max(5, int(tgt.sentence_length_mean * 0.5))
            i = 0
            while i < len(sentences):
                s = sentences[i]
                if (
                    len(s.split()) < threshold
                    and i + 1 < len(sentences)
                    and len(sentences[i + 1].split()) < threshold
                    and self._rng.random() < 0.5
                ):
                    base = s.rstrip('.!?\u2026')
                    next_s = sentences[i + 1]
                    merged = (
                        base + ', '
                        + next_s[0].lower() + next_s[1:]
                    )
                    new_sentences.append(merged)
                    changes.append({
                        "type": "anon_merge",
                        "description": "Merged 2 short sentences",
                    })
                    i += 2
                else:
                    new_sentences.append(s)
                    i += 1

        return ' '.join(new_sentences)

    def _adjust_punctuation(
        self,
        text: str,
        src: StylisticFingerprint,
        tgt: StylisticFingerprint,
        changes: list[dict],
    ) -> str:
        """Shift punctuation frequencies toward target."""
        # Semicolons <-> periods
        if src.semicolons_per_k > tgt.semicolons_per_k + 1:
            count = text.count(';')
            remove = max(1, count // 2)
            for _ in range(remove):
                text = text.replace('; ', '. ', 1)
            if remove:
                changes.append({
                    "type": "anon_punct",
                    "description": f"Removed {remove} semicolons",
                })
        elif src.semicolons_per_k < tgt.semicolons_per_k - 1:
            sents = text.split('. ')
            additions = 0
            rebuilt = []
            for i, s in enumerate(sents):
                if (
                    additions < 3
                    and i > 0
                    and len(s.split()) > 5
                    and self._rng.random() < 0.3
                ):
                    rebuilt.append(s)
                    # Replace the preceding '. ' with '; '
                    if rebuilt:
                        prev = rebuilt[-2] if len(rebuilt) > 1 else ""
                        if prev and not prev.endswith(('?', '!')):
                            rebuilt[-2] = prev
                            rebuilt[-1] = s[0].lower() + s[1:] if s else s
                            # Mark join
                            if len(rebuilt) >= 2:
                                rebuilt[-2] = rebuilt[-2].rstrip('.') + ';'
                            additions += 1
                            continue
                rebuilt.append(s)
            if additions:
                text = '. '.join(rebuilt)
                changes.append({
                    "type": "anon_punct",
                    "description": f"Added {additions} semicolons",
                })

        # Dashes
        if src.dashes_per_k > tgt.dashes_per_k + 2:
            for old in ('— ', '– '):
                if old in text:
                    text = text.replace(old, ', ', 1)
                    changes.append({
                        "type": "anon_punct",
                        "description": "Replaced dash with comma",
                    })

        return text

    def _adjust_starters(
        self,
        text: str,
        src: StylisticFingerprint,
        tgt: StylisticFingerprint,
        changes: list[dict],
    ) -> str:
        """Diversify or homogenize sentence starters."""
        if abs(src.pronoun_start_ratio - tgt.pronoun_start_ratio) < 0.1:
            return text

        pronouns = _PRONOUNS.get(self.lang, _PRONOUNS["en"])
        sentences = self._sentences(text)
        if not sentences:
            return text

        new_sents: list[str] = []
        mods = 0

        for s in sentences:
            words = s.split()
            if not words:
                new_sents.append(s)
                continue

            first = words[0].lower().rstrip('.,;')
            if (
                src.pronoun_start_ratio > tgt.pronoun_start_ratio + 0.1
                and first in pronouns
                and mods < 3
                and self._rng.random() < 0.4
            ):
                # Remove pronoun start by restructuring
                # Simple: prepend a filler
                fillers = {
                    "en": ["In fact,", "Actually,", "Indeed,"],
                    "ru": ["На самом деле,", "По сути,", "Действительно,"],
                    "uk": ["Насправді,", "По суті,", "Власне,"],
                    "de": ["Tatsächlich,", "Im Grunde,", "Eigentlich,"],
                    "fr": ["En fait,", "En réalité,", "D'ailleurs,"],
                    "es": ["De hecho,", "En realidad,", "Realmente,"],
                }
                lang_fillers = fillers.get(self.lang, fillers["en"])
                filler = self._rng.choice(lang_fillers)
                rest = (
                    ' ' + ' '.join(words[1:])
                    if len(words) > 1 else ''
                )
                new_s = f"{filler} {words[0].lower()}{rest}"
                new_sents.append(new_s)
                mods += 1
                changes.append({
                    "type": "anon_starter",
                    "description": "Diversified pronoun start",
                })
            else:
                new_sents.append(s)

        return ' '.join(new_sents)

    def _adjust_vocabulary(
        self,
        text: str,
        src: StylisticFingerprint,
        tgt: StylisticFingerprint,
        changes: list[dict],
    ) -> str:
        """Very light vocabulary shift — not deep, just structural."""
        # Skip if close enough
        if abs(src.avg_word_length - tgt.avg_word_length) < 0.5:
            return text
        # This is a placeholder for deeper vocabulary transformations
        # that would require per-language synonym dictionaries
        return text


@dataclass
class AnonymizeResult:
    """Result of stylometric anonymization."""
    text: str
    original: str
    target_preset: str = "custom"
    similarity_before: float = 0.0
    similarity_after: float = 0.0
    changes: list[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  Предустановленные стилистические отпечатки
# ═══════════════════════════════════════════════════════════════
#
#  Использование:
#    from texthumanize import humanize, STYLE_PRESETS
#    result = humanize(text, target_style=STYLE_PRESETS["student"])
#
STYLE_PRESETS: dict[str, StylisticFingerprint] = {
    # Студент: короткие-средние предложения, простая лексика, мало сложных
    "student": StylisticFingerprint(
        sentence_length_mean=14.0,
        sentence_length_median=13.0,
        sentence_length_std=6.0,
        sentence_length_mode=12,
        semicolons_per_k=0.3,
        colons_per_k=0.5,
        dashes_per_k=1.0,
        exclamations_per_k=0.1,
        questions_per_k=0.5,
        ellipsis_per_k=0.2,
        commas_per_k=25.0,
        avg_paragraph_length=3.5,
        complex_sentence_ratio=0.25,
        question_ratio=0.03,
        exclamation_ratio=0.01,
        avg_word_length=5.2,
        long_word_ratio=0.12,
        vocabulary_richness=0.65,
        pronoun_start_ratio=0.15,
        connector_start_ratio=0.10,
    ),

    # Копирайтер: динамичные предложения, чередование длинных и коротких
    "copywriter": StylisticFingerprint(
        sentence_length_mean=12.0,
        sentence_length_median=10.0,
        sentence_length_std=8.5,
        sentence_length_mode=8,
        semicolons_per_k=0.1,
        colons_per_k=1.5,
        dashes_per_k=3.5,
        exclamations_per_k=1.0,
        questions_per_k=1.5,
        ellipsis_per_k=0.8,
        commas_per_k=22.0,
        avg_paragraph_length=2.5,
        complex_sentence_ratio=0.20,
        question_ratio=0.08,
        exclamation_ratio=0.05,
        avg_word_length=4.8,
        long_word_ratio=0.08,
        vocabulary_richness=0.72,
        pronoun_start_ratio=0.20,
        connector_start_ratio=0.05,
    ),

    # Учёный: длинные предложения, сложная лексика, формальные конструкции
    "scientist": StylisticFingerprint(
        sentence_length_mean=22.0,
        sentence_length_median=21.0,
        sentence_length_std=7.0,
        sentence_length_mode=20,
        semicolons_per_k=1.5,
        colons_per_k=2.0,
        dashes_per_k=2.5,
        exclamations_per_k=0.0,
        questions_per_k=0.3,
        ellipsis_per_k=0.0,
        commas_per_k=35.0,
        avg_paragraph_length=5.0,
        complex_sentence_ratio=0.55,
        question_ratio=0.02,
        exclamation_ratio=0.0,
        avg_word_length=6.0,
        long_word_ratio=0.22,
        vocabulary_richness=0.70,
        pronoun_start_ratio=0.05,
        connector_start_ratio=0.18,
    ),

    # Журналист: средние предложения, разнообразная структура
    "journalist": StylisticFingerprint(
        sentence_length_mean=16.0,
        sentence_length_median=15.0,
        sentence_length_std=7.5,
        sentence_length_mode=14,
        semicolons_per_k=0.5,
        colons_per_k=1.8,
        dashes_per_k=3.0,
        exclamations_per_k=0.2,
        questions_per_k=0.8,
        ellipsis_per_k=0.3,
        commas_per_k=28.0,
        avg_paragraph_length=3.0,
        complex_sentence_ratio=0.35,
        question_ratio=0.05,
        exclamation_ratio=0.01,
        avg_word_length=5.5,
        long_word_ratio=0.15,
        vocabulary_richness=0.72,
        pronoun_start_ratio=0.10,
        connector_start_ratio=0.12,
    ),

    # Блогер: неформальный, разговорный, с вопросами и восклицаниями
    "blogger": StylisticFingerprint(
        sentence_length_mean=11.0,
        sentence_length_median=9.0,
        sentence_length_std=7.0,
        sentence_length_mode=7,
        semicolons_per_k=0.0,
        colons_per_k=0.8,
        dashes_per_k=4.0,
        exclamations_per_k=2.0,
        questions_per_k=2.5,
        ellipsis_per_k=1.5,
        commas_per_k=18.0,
        avg_paragraph_length=2.0,
        complex_sentence_ratio=0.12,
        question_ratio=0.12,
        exclamation_ratio=0.08,
        avg_word_length=4.5,
        long_word_ratio=0.06,
        vocabulary_richness=0.60,
        pronoun_start_ratio=0.25,
        connector_start_ratio=0.03,
    ),
}
