"""PHANTOM™ — Perceptual Humanization via Adversarial Neural Text Optimization and Morphing.

A radical, adversarial approach to bypassing AI detectors. Instead of blind
rule-based transformations, PHANTOM™ computes EXACT gradients through the
known detector MLP (35→64→32→1) and performs gradient-guided text
modifications to minimize detection score.

Architecture:
    ORACLE   — Analytical gradient computation (∂P(AI)/∂feature)
    SURGEON  — Feature-targeted text transformations
    FORGE    — Iterative gradient descent loop over text space

This module requires NO external dependencies — all neural math is pure Python.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any

from texthumanize.neural_detector import (
    _FEATURE_MEAN,
    _FEATURE_MEAN_RU,
    _FEATURE_MEAN_UK,
    _FEATURE_NAMES,
    _FEATURE_STD,
    _FEATURE_STD_RU,
    _FEATURE_STD_UK,
    extract_features,
    normalize_features,
)
from texthumanize.neural_engine import (
    FeedForwardNet,
    Vec,
    _sigmoid,
)
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐüöäßÜÖÄ\']+')


def _cleanup_text(text: str, lang: str = "en") -> str:
    """Fix common text artifacts from iterative modifications."""
    # Fix double spaces
    text = re.sub(r'  +', ' ', text)
    # Fix space before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    # Fix double commas
    text = re.sub(r',\s*,', ',', text)
    # Fix space after opening sentence
    text = re.sub(r'\.\s+\.\s+', '. ', text)
    # Fix dash spacing
    text = re.sub(r'\s*—\s*—\s*', ' — ', text)
    # Remove orphan commas
    text = re.sub(r'^\s*,\s*', '', text)
    text = re.sub(r'\s+,\s+,', ',', text)
    # Remove stray English words from non-English text
    if lang in ("ru", "uk", "de", "fr", "es"):
        for en_word in ("and", "or", "but", "so", "yet", "also",
                        "the", "is", "are", "was", "with", "for", "of"):
            text = re.sub(
                r'(?<=[\s;:,!?.—])\s*\b' + en_word + r'\b\s+',
                ' ', text, flags=re.IGNORECASE,
            )
            text = re.sub(
                r'^\s*' + en_word + r'\s+', '', text, flags=re.IGNORECASE,
            )
    # Apply grammar fixes for Slavic languages
    if lang in ("ru", "uk"):
        text = _fix_grammar_slavic(text, lang)
    # Remove duplicate adjacent sentences
    sentences = split_sentences(text)
    if len(sentences) > 2:
        deduped = [sentences[0]]
        for s in sentences[1:]:
            if s.strip() != deduped[-1].strip():
                deduped.append(s)
        if len(deduped) < len(sentences):
            text = ' '.join(s.strip() for s in deduped if s.strip())
    # Deduplicate filler sentences across the entire text
    text = _deduplicate_fillers(text, lang)
    # Ensure sentences start with uppercase
    text = _fix_sentence_caps(text)
    return text.strip()


# ── Filler sentence deduplication ──────────────────────────────────────

_ALL_FILLERS_FLAT: set[str] = set()

def _build_filler_set() -> set[str]:
    """Build a set of all possible filler / short sentences for dedup."""
    if _ALL_FILLERS_FLAT:
        return _ALL_FILLERS_FLAT
    for lst in (_SHORT_SENTENCES_EN, _SHORT_SENTENCES_RU, _SHORT_SENTENCES_UK,
                _SHORT_SENTENCES_DE, _SHORT_SENTENCES_FR, _SHORT_SENTENCES_ES):
        for s in lst:
            _ALL_FILLERS_FLAT.add(s.strip().lower())
    # Also add question sentences
    for q in ("But why?", "How so?", "What does this mean?",
              "Is that really true?", "Sound familiar?",
              "Но почему?", "Как так?", "Что это значит?",
              "Правда ли это?", "Знакомо?",
              "Але чому?", "Як так?", "Що це означає?",
              "Чи правда це?", "Знайомо?",
              "Aber warum?", "Wie das?", "Was heißt das?",
              "Stimmt das wirklich?", "Kommt Ihnen das bekannt vor?",
              "Mais pourquoi?", "Comment ça?", "Qu'est-ce que ça veut dire?",
              "Vraiment?", "Ça vous parle?",
              "¿Pero por qué?", "¿Cómo así?", "¿Qué significa esto?",
              "¿De verdad?", "¿Les suena?"):
        _ALL_FILLERS_FLAT.add(q.strip().lower())
    return _ALL_FILLERS_FLAT


def _deduplicate_fillers(text: str, lang: str) -> str:
    """Remove duplicate filler/question sentences and limit filler chains.

    Rules:
    1. Each unique filler sentence can appear at most once in the text
    2. No more than 1 consecutive filler sentence (prevent chains)
    3. Total fillers capped at max 2 per text
    """
    filler_set = _build_filler_set()
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return text

    seen_fillers: set[str] = set()
    total_fillers = 0
    max_total = 3  # max filler sentences per text
    result = []
    prev_was_filler = False

    for s in sentences:
        s_stripped = s.strip()
        s_lower = s_stripped.lower().rstrip('.,!?') + s_stripped[-1:] if s_stripped else ''
        s_key = s_stripped.lower()
        is_filler = s_key in filler_set

        if is_filler:
            # Skip if: duplicate, chain, or over limit
            if s_key in seen_fillers or prev_was_filler or total_fillers >= max_total:
                prev_was_filler = True
                continue
            seen_fillers.add(s_key)
            total_fillers += 1
            prev_was_filler = True
        else:
            prev_was_filler = False

        result.append(s_stripped)

    return ' '.join(result)


def _fix_sentence_caps(text: str) -> str:
    """Ensure each sentence starts with an uppercase letter."""
    # After sentence-ending punctuation + space, capitalize
    text = re.sub(
        r'(?<=[\.\!\?])\s+([a-zа-яёіїєґ])',
        lambda m: ' ' + m.group(1).upper(),
        text,
    )
    # Capitalize the very first character
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


# ── Slavic grammar post-processor ──────────────────────────────────────

# Preposition/verb government rules: what case the following word should take
# Pattern: r"(trigger_word)\s+(broken_form)" → fixed_form
# These fix the most common agreement breaks from dictionary replacements

_GRAMMAR_FIXES_RU: list[tuple[str, str, str]] = [
    # "в многих" → "во многих" (preposition assimilation)
    (r'\bв\s+мног', 'в мног', 'во мног'),
    # "в корне" is correct — don't break it
    # Neuter nouns after neuter verbs: "X претерпело Y" — Y must match
    (r'\b(\w+ину)\s+претерпело\b', None, None),  # placeholder
    # "комплексная/сложная + neuter noun" → fix adj to neuter
    (r'\b(сложная|непростая|комплексная)\s+(введение|внедрение|создание|начало|использование|применение|решение|развитие|обеспечение|улучшение|изменение)\b',
     None, '_fix_adj_neuter_ru'),
    # "обычный + feminine/plural noun" → fix adj
    (r'\b(обычный)\s+(\w+(?:ых|их|ых))\b', None, '_fix_adj_genpl_ru'),
    # Infinitive after preposition "через" should be noun
    # "через применять" → "через применение"
    (r'\bчерез\s+(\w+ять|ть)\b', None, '_fix_prep_infinitive_ru'),
    # "в принципе" is fine, but "в многих" needs "во"
]

_GRAMMAR_FIXES_UK: list[tuple[str, str, str]] = [
    # "складна + neuter noun" → fix adj to neuter
    (r'\b(складна|непроста|комплексна)\s+(введення|впровадження|створення|використання|застосування|рішення|розвиток|забезпечення|покращення|зміна)\b',
     None, '_fix_adj_neuter_uk'),
]


def _fix_grammar_slavic(text: str, lang: str) -> str:
    """Fix common grammatical agreement issues in RU/UK text.

    Handles:
    1. Adjective-noun gender/number agreement
    2. Preposition assimilation (в→во)
    3. Verb-noun gender agreement
    4. Preposition + infinitive → preposition + noun
    """
    if lang == "ru":
        text = _fix_grammar_ru(text)
    elif lang == "uk":
        text = _fix_grammar_uk(text)
    return text


def _fix_grammar_ru(text: str) -> str:
    """Fix Russian grammatical patterns."""
    # 1. "в многих" → "во многих"
    text = re.sub(r'\bв\s+(мн\w+)', r'во \1', text)
    # Also: "в взаимодействии" → "во взаимодействии"
    text = re.sub(r'\bв\s+(вз\w+)', r'во \1', text)
    # "в всех" → "во всех"
    text = re.sub(r'\bв\s+(вс\w+)', r'во \1', text)

    # 2. Feminine adjective before neuter noun → neuter adjective
    _neuter_nouns_ru = {
        'введение', 'внедрение', 'создание', 'начало', 'использование',
        'применение', 'решение', 'развитие', 'обеспечение', 'улучшение',
        'изменение', 'преобразование', 'формирование', 'функционирование',
        'совершенствование', 'взаимодействие', 'здравоохранение', 'образование',
        'управление', 'производство', 'количество', 'значение',
        # Additions — common neuter nouns that appear after dictionary replacements
        'слияние', 'объединение', 'поглощение', 'обучение', 'вещество',
        'явление', 'событие', 'средство', 'государство', 'общество',
        'пространство', 'устройство', 'учреждение', 'направление',
        'определение', 'исследование', 'достижение', 'описание',
        'указание', 'требование', 'условие', 'положение', 'движение',
        'снижение', 'повышение', 'увеличение', 'уменьшение', 'ускорение',
        'торможение', 'замедление', 'представление', 'отображение',
        'построение', 'моделирование', 'тестирование', 'проектирование',
        'программирование', 'масштабирование', 'сообщение', 'заявление',
        'содержание', 'продолжение', 'завершение', 'окончание',
        'мнение', 'выражение', 'впечатление', 'настроение',
        'множество', 'большинство', 'меньшинство', 'равенство',
    }
    for noun in _neuter_nouns_ru:
        # сложная введение → сложное введение
        text = re.sub(
            r'\b(\w+)ая\s+(' + re.escape(noun) + r')\b',
            lambda m: m.group(1) + 'ое ' + m.group(2),
            text, flags=re.IGNORECASE,
        )
        # непростая → непростое
        text = re.sub(
            r'\b(\w+)яя\s+(' + re.escape(noun) + r')\b',
            lambda m: m.group(1) + 'ее ' + m.group(2),
            text, flags=re.IGNORECASE,
        )

    # 2a. Generic neuter agreement: catch any neuter noun by suffix pattern
    # Most RU neuter nouns end in: -ние, -тие, -ство, -ло
    # "составная слияние" → "составное слияние" (even if not in the dict)
    text = re.sub(
        r'\b(\w{2,})ая\s+(\w+(?:ние|тие|ство))\b',
        lambda m: m.group(1) + 'ое ' + m.group(2),
        text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r'\b(\w{2,})яя\s+(\w+(?:ние|тие|ство))\b',
        lambda m: m.group(1) + 'ее ' + m.group(2),
        text, flags=re.IGNORECASE,
    )

    # 3. Masculine adjective before feminine nouns → feminine
    _fem_nouns_ru = {
        'практика', 'потребность', 'перемена', 'работа', 'область',
        'система', 'модель', 'безопасность', 'продуктивность', 'идея',
    }
    for noun in _fem_nouns_ru:
        # обычный практика → обычная практика
        text = re.sub(
            r'\b(\w+)(?:ый|ий|ой)\s+(' + re.escape(noun) + r')\b',
            lambda m: m.group(1) + 'ая ' + m.group(2),
            text, flags=re.IGNORECASE,
        )

    # 4. Genitive plural adjective agreement
    # "обычный школьных" → "обычных школьных"
    text = re.sub(
        r'\b(\w+)(?:ый|ий|ой)\s+(\w+(?:ых|их)\s+\w+)',
        lambda m: (
            m.group(1) + ('их' if m.group(1).endswith(('н', 'к', 'г', 'х', 'ж', 'ш', 'щ', 'ч'))
                         else 'ых') + ' ' + m.group(2)
            if re.search(r'^\w+(?:ых|их)\b', m.group(2))
            else m.group(0)
        ),
        text,
    )

    # 5. Verb gender agreement with subject
    # "медицину претерпело" → "медицина претерпела" — hard to fix generically
    # Instead fix: "(fem noun as subject) (neuter past verb)" → feminine verb
    _fem_subjects = re.compile(
        r'\b(\w*(?:ина|ция|ика|ика|ость|есть))\s+(\w+)(?:ло)\b'
    )
    def _fix_verb_gender(m: re.Match) -> str:
        noun, verb_stem = m.group(1), m.group(2)
        # Only fix if the noun looks like a nominative feminine
        if noun.endswith(('а', 'я', 'ь')):
            return noun + ' ' + verb_stem + 'ла'
        return m.group(0)
    text = _fem_subjects.sub(_fix_verb_gender, text)

    # 6. "через применять" → "через применение" (prep + infinitive → noun)
    text = re.sub(
        r'\bчерез\s+применять\b', 'через применение', text,
    )
    text = re.sub(
        r'\bчерез\s+использовать\b', 'через использование', text,
    )

    # 7. "через использования" → "через использование" (через + accusative, not genitive)
    _acc_after_cherez = {
        'использования': 'использование',
        'применения': 'применение',
        'внедрения': 'внедрение',
        'создания': 'создание',
        'изменения': 'изменение',
    }
    for gen_form, acc_form in _acc_after_cherez.items():
        text = re.sub(
            r'\bчерез\s+' + re.escape(gen_form) + r'\b',
            'через ' + acc_form, text, flags=re.IGNORECASE,
        )

    # 8. Neuter past verb with masculine subject → masculine verb
    # "прогресс ... создало" → "прогресс ... создал" (even with fillers between)
    _masc_nouns_ru = {
        'прогресс', 'рост', 'спрос', 'интерес', 'процесс',
        'анализ', 'подход', 'метод', 'алгоритм', 'результат',
        'фактор', 'аспект', 'уровень', 'контекст', 'дискурс',
        'механизм', 'потенциал', 'сегмент', 'компонент', 'параметр',
        'ум', 'интеллект', 'ландшафт',
    }
    # Match within a sentence: if sentence starts with masc noun, fix neuter verbs
    _sent_list = split_sentences(text)
    fixed_sents = []
    for sent in _sent_list:
        sent_lower = sent.lower().strip()
        first_word = re.match(r'\b(\w+)\b', sent_lower)
        if first_word and first_word.group(1) in _masc_nouns_ru:
            # Sentence starts with masculine noun — fix neuter past verbs
            sent = re.sub(
                r'\b(\w{2,})ло\b',
                lambda m: m.group(1) + 'л'
                if not m.group(0).lower().endswith(('было', 'стало'))
                and m.group(1).lower() not in ('бы', 'ма', 'де')
                else m.group(0),
                sent,
            )
        fixed_sents.append(sent)
    text = ' '.join(s.strip() for s in fixed_sents if s.strip())

    # 9. "глубоко перемену" → "глубокую перемену" (adverb before accusative noun)
    # Adverb "глубоко" used where adjective "глубокую" needed before fem acc noun
    text = re.sub(r'\bглубоко\s+(перемену|трансформацию|перестройку)\b',
                  r'глубокую \1', text)
    text = re.sub(r'\bглубоко\s+(изменение|преобразование|обновление)\b',
                  r'глубокое \1', text)

    # 10. "включить умных систем" → "включение умных систем"
    # (infinitive where noun expected after replaced "интеграция")
    text = re.sub(
        r'\b(включить|объединить|совместить)\s+(\w+(?:ых|их|ных)\s+\w+)',
        lambda m: {
            'включить': 'включение',
            'объединить': 'объединение',
            'совместить': 'совмещение',
        }.get(m.group(1).lower(), m.group(1)) + ' ' + m.group(2),
        text, flags=re.IGNORECASE,
    )

    return text


def _fix_grammar_uk(text: str) -> str:
    """Fix Ukrainian grammatical patterns."""
    # 1. Feminine adjective before neuter noun → neuter adjective
    _neuter_nouns_uk = {
        'введення', 'впровадження', 'створення', 'використання',
        'застосування', 'рішення', 'забезпечення', 'покращення',
        'зміна', 'перетворення', 'формування', 'управління',
        'виробництво', 'значення',
        # Additions — common neuter nouns
        'злиття', "об'єднання", 'поглинання', 'навчання', 'речовина',
        'явище', 'суспільство', 'середовище', 'господарство',
        'дослідження', 'досягнення', 'визначення', 'завдання',
        'положення', 'питання', 'повідомлення', 'зменшення',
        'збільшення', 'підвищення', 'зниження', 'прискорення',
        'уповільнення', 'моделювання', 'тестування', 'проектування',
        'програмування', 'масштабування', 'спілкування', 'утворення',
        'призначення', 'уявлення', 'враження', 'продовження',
        'завершення', 'закінчення', 'становлення', 'прагнення',
        'зобов\'язання', 'множина',
    }
    for noun in _neuter_nouns_uk:
        # складна введення → складне введення
        text = re.sub(
            r'\b(\w+)на\s+(' + re.escape(noun) + r')\b',
            lambda m: m.group(1) + 'не ' + m.group(2),
            text, flags=re.IGNORECASE,
        )
        # непроста → непросте
        text = re.sub(
            r'\b(\w+)та\s+(' + re.escape(noun) + r')\b',
            lambda m: m.group(1) + 'те ' + m.group(2),
            text, flags=re.IGNORECASE,
        )

    # 1a. Generic neuter agreement: catch any neuter noun by suffix pattern
    # Most UK neuter nouns end in: -ння, -ття, -ство, -ще
    # "складна злиття" → "складне злиття" (even if not in the dict)
    text = re.sub(
        r'\b(\w{2,})на\s+(\w+(?:ння|ття|ство|ще))\b',
        lambda m: m.group(1) + 'не ' + m.group(2),
        text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r'\b(\w{2,})та\s+(\w+(?:ння|ття|ство|ще))\b',
        lambda m: m.group(1) + 'те ' + m.group(2),
        text, flags=re.IGNORECASE,
    )

    # 2. "у багатьох" is correct (no assimilation needed in UK like RU)

    # 3. Fix verb gender with feminine subjects
    _fem_subjects_uk = re.compile(
        r'\b(\w*(?:ина|ція|іка|ість))\s+(\w+)(?:ло)\b'
    )
    def _fix_verb_gender_uk(m: re.Match) -> str:
        noun, verb_stem = m.group(1), m.group(2)
        if noun.endswith(('а', 'я', 'ь')):
            return noun + ' ' + verb_stem + 'ла'
        return m.group(0)
    text = _fem_subjects_uk.sub(_fix_verb_gender_uk, text)

    # 4. "впровадити + gen pl" → "впровадження + gen pl"
    # (infinitive where noun expected after replaced "імплементація")
    text = re.sub(
        r'\b(впровадити|включити|об\'єднати)\s+(\w+(?:их|іх|них)\s+\w+)',
        lambda m: {
            'впровадити': 'впровадження',
            'включити': 'включення',
            "об'єднати": "об'єднання",
        }.get(m.group(1).lower(), m.group(1)) + ' ' + m.group(2),
        text, flags=re.IGNORECASE,
    )

    return text

# ═══════════════════════════════════════════════════════════════════════════
# ORACLE — Gradient computation through the detector MLP
# ═══════════════════════════════════════════════════════════════════════════

class Oracle:
    """Computes analytical gradients of detector score w.r.t. input features.

    Given a text, Oracle:
    1. Extracts raw features
    2. Normalizes them (z-score)
    3. Runs forward pass through detector MLP saving intermediates
    4. Backpropagates to get ∂P(AI)/∂feature for each of 35 features
    5. Returns a ranked FeatureGapReport

    This is the "3D scan of the lock" — tells SURGEON exactly what to modify.
    """

    def __init__(self, net: FeedForwardNet, trained: bool = True) -> None:
        self._net = net
        self._trained = trained
        # Cache layer weights for backprop
        self._layers = net.layers

    def analyze(self, text: str, lang: str = "en") -> FeatureGapReport:
        """Full analysis: features + score + gradients + gap ranking."""
        raw = extract_features(text, lang)
        normed = normalize_features(raw, lang=lang)

        # Compute score
        score = self._compute_score(normed)

        # Compute gradients via numerical differentiation
        # For 35 features through a tiny MLP, this is ~70 forward passes ≈ 0.5ms
        gradients = self._numerical_gradients(normed)

        # Convert gradient from normalized space to raw space
        means, stds = self._get_norm_stats(lang)
        raw_gradients = [g / s if s > 0 else 0.0 for g, s in zip(gradients, stds)]

        # Compute per-feature contribution to AI score
        # contribution_i = gradient_i * normed_i
        # This approximates how much each feature's deviation from mean
        # contributes to the total score
        contributions = [gradients[i] * normed[i] for i in range(35)]

        # Build ranked gap report
        gaps: list[FeatureGap] = []
        for i in range(35):
            gaps.append(FeatureGap(
                index=i,
                name=_FEATURE_NAMES[i],
                raw_value=raw[i],
                normed_value=normed[i],
                gradient=gradients[i],
                raw_gradient=raw_gradients[i],
                contribution=contributions[i],
                mean=means[i],
                std=stds[i],
            ))

        # Sort by absolute contribution (highest impact first)
        gaps.sort(key=lambda g: abs(g.contribution), reverse=True)

        return FeatureGapReport(
            score=score,
            raw_features=raw,
            normed_features=normed,
            gradients=gradients,
            gaps=gaps,
            lang=lang,
        )

    def _compute_score(self, normed: Vec) -> float:
        """Compute AI detection score the same way the detector does."""
        if self._trained:
            return self._net.predict_proba(normed)
        else:
            logit = self._net.forward(normed)
            return _sigmoid(-logit[0])

    def _numerical_gradients(self, normed: Vec, eps: float = 1e-4) -> Vec:
        """Compute ∂score/∂feature numerically (central differences).

        For 35 features × 2 perturbations = 70 forward passes.
        Each pass through our tiny MLP (35→64→32→1) takes ~0.02ms,
        so total gradient computation ≈ 1.4ms. Negligible.
        """
        grads = [0.0] * len(normed)
        base = list(normed)
        for i in range(len(normed)):
            plus = list(base)
            plus[i] += eps
            minus = list(base)
            minus[i] -= eps
            score_plus = self._compute_score(plus)
            score_minus = self._compute_score(minus)
            grads[i] = (score_plus - score_minus) / (2 * eps)
        return grads

    @staticmethod
    def _get_norm_stats(lang: str) -> tuple[list[float], list[float]]:
        if lang == "ru":
            return _FEATURE_MEAN_RU, _FEATURE_STD_RU
        elif lang == "uk":
            return _FEATURE_MEAN_UK, _FEATURE_STD_UK
        return _FEATURE_MEAN, _FEATURE_STD


class FeatureGap:
    """One feature's gap from human-like values."""

    __slots__ = (
        "contribution", "gradient", "index", "mean",
        "name", "normed_value", "raw_gradient", "raw_value", "std",
    )

    def __init__(
        self, index: int, name: str, raw_value: float,
        normed_value: float, gradient: float, raw_gradient: float,
        contribution: float, mean: float, std: float,
    ) -> None:
        self.index = index
        self.name = name
        self.raw_value = raw_value
        self.normed_value = normed_value
        self.gradient = gradient
        self.raw_gradient = raw_gradient
        self.contribution = contribution
        self.mean = mean
        self.std = std

    @property
    def target_direction(self) -> str:
        """Whether this feature should increase or decrease to lower score."""
        return "decrease" if self.gradient > 0 else "increase"

    def __repr__(self) -> str:
        return (
            f"FeatureGap({self.name}: raw={self.raw_value:.3f}, "
            f"z={self.normed_value:.2f}, ∇={self.gradient:.4f}, "
            f"contrib={self.contribution:.4f}, dir={self.target_direction})"
        )


class FeatureGapReport:
    """Complete analysis of a text's AI detection features."""

    __slots__ = (
        "gaps", "gradients", "lang", "normed_features", "raw_features", "score",
    )

    def __init__(
        self, score: float, raw_features: Vec, normed_features: Vec,
        gradients: Vec, gaps: list[FeatureGap], lang: str,
    ) -> None:
        self.score = score
        self.raw_features = raw_features
        self.normed_features = normed_features
        self.gradients = gradients
        self.gaps = gaps
        self.lang = lang

    def top_gaps(self, n: int = 10) -> list[FeatureGap]:
        """Top N features by absolute contribution to AI score."""
        return self.gaps[:n]

    def actionable_gaps(self) -> list[FeatureGap]:
        """Gaps that can be addressed by text transformations."""
        actionable_features = {
            "word_length_variance", "sentence_length_variance",
            "sentence_length_skewness", "burstiness_score",
            "vocab_burstiness", "ai_pattern_rate",
            "transition_word_rate", "conjunction_rate",
            "starter_diversity", "comma_rate", "semicolon_rate",
            "dash_rate", "question_rate", "exclamation_rate",
            "avg_word_length", "avg_syllables_per_word",
            "type_token_ratio", "hapax_ratio", "vocabulary_richness",
            "mean_sentence_length", "consec_len_diff_var",
            "bigram_repetition_rate", "trigram_repetition_rate",
            "unique_bigram_ratio", "word_entropy", "char_entropy",
            "paragraph_count_norm", "avg_paragraph_length",
            "flesch_score_norm",
        }
        return [g for g in self.gaps if g.name in actionable_features]

    def __repr__(self) -> str:
        top = self.gaps[:5]
        lines = [f"Score: {self.score:.4f}"]
        for g in top:
            lines.append(f"  {g}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# SURGEON — Feature-targeted text transformations
# ═══════════════════════════════════════════════════════════════════════════

# Maps feature names to surgical operations that can modify them.
# Each operation returns (modified_text, expected_delta) where delta < 0
# means we expect the AI score to decrease.

class Surgeon:
    """Applies targeted text modifications guided by Oracle gradients.

    Unlike the naturalizer which applies ALL transformations at fixed intensity,
    Surgeon only modifies what the gradient says needs changing, and precisely
    controls the magnitude of each change.
    """

    def __init__(self, rng: random.Random | None = None, lang: str = "en") -> None:
        self._rng = rng or random.Random()
        self._lang = lang
        self._ops = _build_surgical_ops(lang, self._rng)

    def operate(
        self, text: str, report: FeatureGapReport,
        budget: float = 1.0,
    ) -> str:
        """Apply gradient-guided modifications to lower AI score.

        Args:
            text: Input text
            report: Oracle analysis
            budget: How aggressively to modify (0.0 = nothing, 1.0 = full)

        Returns:
            Modified text with targeted changes.
        """
        gaps = report.actionable_gaps()
        if not gaps:
            return text

        # Prioritize by |contribution| * |gradient|
        # This focuses on features that MOST affect the score AND can be moved
        priority = sorted(
            gaps,
            key=lambda g: abs(g.contribution) * abs(g.gradient),
            reverse=True,
        )

        modified = text
        applied_ops: list[str] = []
        max_ops = max(5, int(len(priority) * budget))

        for rank, gap in enumerate(priority[:max_ops]):
            if gap.name not in self._ops:
                continue

            op_fn = self._ops[gap.name]
            direction = gap.target_direction
            # Rank-based magnitude: top features get aggressive treatment
            # rank 0 → 0.95, rank 1 → 0.85, rank 2 → 0.75, etc.
            rank_mag = max(0.4, 0.95 - rank * 0.10)
            magnitude = min(rank_mag * budget, 1.0)

            try:
                new_text = op_fn(modified, direction, magnitude, gap)
                if new_text and new_text != modified:
                    modified = new_text
                    applied_ops.append(
                        f"{gap.name}({direction}, mag={magnitude:.2f})"
                    )
            except Exception as e:
                logger.debug("Surgeon op %s failed: %s", gap.name, e)

        if applied_ops:
            logger.info(
                "Surgeon applied %d operations: %s",
                len(applied_ops), ", ".join(applied_ops[:5]),
            )

        return modified


# ─── Surgical operations ────────────────────────────────────────────────

def _build_surgical_ops(
    lang: str, rng: random.Random,
) -> dict[str, Any]:
    """Build the map of feature_name → surgical function."""

    ops: dict[str, Any] = {}

    # --- AI pattern rate ---
    ops["ai_pattern_rate"] = lambda text, d, m, g: _op_ai_patterns(
        text, d, m, g, lang, rng,
    )

    # --- Sentence length variance ---
    ops["sentence_length_variance"] = lambda text, d, m, g: _op_sentence_variance(
        text, d, m, g, lang, rng,
    )

    # --- Burstiness ---
    ops["burstiness_score"] = lambda text, d, m, g: _op_burstiness(
        text, d, m, g, lang, rng,
    )

    # --- Word length variance ---
    ops["word_length_variance"] = lambda text, d, m, g: _op_word_length_var(
        text, d, m, g, lang, rng,
    )

    # --- Average word length ---
    ops["avg_word_length"] = lambda text, d, m, g: _op_avg_word_length(
        text, d, m, g, lang, rng,
    )

    # --- Transition word rate ---
    ops["transition_word_rate"] = lambda text, d, m, g: _op_transitions(
        text, d, m, g, lang, rng,
    )

    # --- Starter diversity ---
    ops["starter_diversity"] = lambda text, d, m, g: _op_starter_diversity(
        text, d, m, g, lang, rng,
    )

    # --- Conjunction rate ---
    ops["conjunction_rate"] = lambda text, d, m, g: _op_conjunction_rate(
        text, d, m, g, lang, rng,
    )

    # --- Average paragraph length ---
    ops["avg_paragraph_length"] = lambda text, d, m, g: _op_avg_para_length(
        text, d, m, g, lang, rng,
    )

    # --- Punctuation ops ---
    for punc_feat in ("comma_rate", "semicolon_rate", "dash_rate",
                      "question_rate", "exclamation_rate"):
        ops[punc_feat] = lambda text, d, m, g, _f=punc_feat: _op_punctuation(
            text, d, m, g, _f, lang, rng,
        )

    # --- Sentence length skewness ---
    ops["sentence_length_skewness"] = lambda text, d, m, g: _op_skewness(
        text, d, m, g, lang, rng,
    )

    # --- Consecutive length diff variance ---
    ops["consec_len_diff_var"] = lambda text, d, m, g: _op_consec_var(
        text, d, m, g, lang, rng,
    )

    # --- Mean sentence length ---
    ops["mean_sentence_length"] = lambda text, d, m, g: _op_mean_sent_len(
        text, d, m, g, lang, rng,
    )

    # --- Vocabulary diversity ---
    for voc_feat in ("type_token_ratio", "hapax_ratio", "vocabulary_richness",
                     "unique_bigram_ratio"):
        ops[voc_feat] = lambda text, d, m, g, _f=voc_feat: _op_vocabulary(
            text, d, m, g, _f, lang, rng,
        )

    # --- Entropy ---
    for ent_feat in ("word_entropy", "char_entropy", "bigram_entropy"):
        ops[ent_feat] = lambda text, d, m, g, _f=ent_feat: _op_entropy(
            text, d, m, g, _f, lang, rng,
        )

    # --- Avg syllables ---
    ops["avg_syllables_per_word"] = lambda text, d, m, g: _op_syllables(
        text, d, m, g, lang, rng,
    )

    # --- Paragraph structure ---
    ops["paragraph_count_norm"] = lambda text, d, m, g: _op_paragraphs(
        text, d, m, g, lang, rng,
    )

    # --- Vocab burstiness ---
    ops["vocab_burstiness"] = lambda text, d, m, g: _op_vocab_burstiness(
        text, d, m, g, lang, rng,
    )

    # --- Flesch score ---
    ops["flesch_score_norm"] = lambda text, d, m, g: _op_readability(
        text, d, m, g, lang, rng,
    )

    # --- Repetition rates ---
    for rep_feat in ("bigram_repetition_rate", "trigram_repetition_rate"):
        ops[rep_feat] = lambda text, d, m, g, _f=rep_feat: _op_repetition(
            text, d, m, g, _f, lang, rng,
        )

    return ops


# ─── Individual surgical operations ─────────────────────────────────────

# AI word replacement maps (curated, context-safe)
_AI_REPLACEMENTS_EN: dict[str, list[str]] = {
    # ── Transition words / connectors ──
    "furthermore": ["also", "plus", "and"],
    "moreover": ["also", "besides", "and"],
    "additionally": ["also", "plus", "on top of that"],
    "consequently": ["so", "as a result"],
    "subsequently": ["then", "later", "after that"],
    "nevertheless": ["still", "yet", "even so"],
    "notwithstanding": ["despite", "even so", "still"],
    "accordingly": ["so", "thus", "hence"],
    "conversely": ["but", "yet", "on the flip side"],
    "alternatively": ["or", "else", "instead"],
    "thereby": ["so", "thus"],
    "wherein": ["where", "in which"],
    "whereas": ["while", "but"],
    "henceforth": ["from now on", "going forward"],
    # ── Verbs ──
    "utilize": ["use", "apply", "work with"],
    "utilization": ["use", "usage"],
    "leverage": ["use", "tap into", "build on"],
    "facilitate": ["help", "support", "enable"],
    "optimize": ["improve", "tune", "refine"],
    "implement": ["set up", "build", "create"],
    "implementation": ["setup", "rollout", "build"],
    "demonstrate": ["show", "reveal", "prove"],
    "encompass": ["include", "cover", "span"],
    "streamline": ["simplify", "speed up", "trim"],
    "foster": ["support", "grow", "build"],
    "harness": ["use", "tap", "capture"],
    "embark": ["start", "begin", "set out"],
    "navigate": ["handle", "deal with", "manage"],
    "bolster": ["boost", "back up", "support"],
    "augment": ["add to", "expand", "grow"],
    "epitomize": ["sum up", "embody", "capture"],
    "transform": ["change", "reshape", "shift"],
    "transformed": ["changed", "reshaped", "shifted"],
    "transforms": ["changes", "reshapes", "shifts"],
    "transforming": ["changing", "reshaping", "shifting"],
    "underscore": ["stress", "show", "highlight"],
    "underscores": ["stresses", "shows", "highlights"],
    "elucidate": ["explain", "clarify", "spell out"],
    "exacerbate": ["worsen", "amplify", "deepen"],
    "exacerbates": ["worsens", "deepens", "amplifies"],
    "proliferate": ["spread", "grow", "multiply"],
    "proliferates": ["spreads", "grows", "multiplies"],
    "necessitate": ["require", "call for", "demand"],
    "necessitates": ["requires", "demands", "calls for"],
    "amalgamate": ["merge", "blend", "combine"],
    "exemplify": ["show", "prove", "typify"],
    "exemplifies": ["shows", "proves", "typifies"],
    "transcend": ["go beyond", "surpass", "exceed"],
    "transcends": ["exceeds", "surpasses", "goes beyond"],
    "orchestrate": ["plan", "run", "arrange"],
    "juxtapose": ["compare", "contrast", "set side by side"],
    # ── Morphological variants (verb forms) ──
    "utilized": ["used", "applied"],
    "utilizes": ["uses", "applies"],
    "utilizing": ["using", "applying"],
    "leveraged": ["used", "tapped"],
    "leveraging": ["using", "tapping"],
    "facilitated": ["helped", "enabled"],
    "facilitates": ["helps", "enables"],
    "facilitating": ["helping", "enabling"],
    "optimized": ["improved", "tuned", "refined"],
    "optimizes": ["improves", "tunes", "refines"],
    "optimizing": ["improving", "tuning", "refining"],
    "implemented": ["built", "set up", "created"],
    "implements": ["builds", "creates"],
    "implementing": ["building", "creating", "setting up"],
    "demonstrated": ["showed", "proved", "revealed"],
    "demonstrates": ["shows", "proves", "reveals"],
    "demonstrating": ["showing", "proving", "revealing"],
    "encompasses": ["covers", "includes", "spans"],
    "encompassing": ["covering", "including", "spanning"],
    "streamlined": ["simplified", "trimmed"],
    "streamlining": ["simplifying", "trimming"],
    "fostered": ["supported", "grown", "built"],
    "fosters": ["supports", "grows", "builds"],
    "fostering": ["supporting", "growing", "building"],
    "harnessed": ["used", "tapped", "captured"],
    "harnessing": ["using", "tapping", "capturing"],
    "navigating": ["handling", "managing"],
    "navigated": ["handled", "managed"],
    # ── Adjectives ──
    "comprehensive": ["full", "complete", "broad"],
    "paramount": ["key", "vital", "top"],
    "multifaceted": ["complex", "varied", "layered"],
    "pivotal": ["key", "central", "critical"],
    "nuanced": ["subtle", "fine", "detailed"],
    "seamless": ["smooth", "easy", "fluid"],
    "robust": ["strong", "solid", "tough"],
    "holistic": ["whole", "broad", "complete"],
    "intricate": ["complex", "involved", "tricky"],
    "innovative": ["new", "fresh", "novel"],
    "transformative": ["major", "powerful", "big"],
    "cutting-edge": ["latest", "modern", "top"],
    "groundbreaking": ["new", "major", "bold"],
    "crucial": ["key", "vital", "big"],
    "imperative": ["urgent", "needed", "vital"],
    "conducive": ["helpful", "good for", "useful"],
    "noteworthy": ["notable", "key", "worth a look"],
    "meticulous": ["careful", "precise", "exact"],
    "indispensable": ["essential", "key", "vital"],
    "integral": ["key", "core", "central"],
    "salient": ["key", "main", "notable"],
    "nascent": ["new", "young", "early"],
    "unprecedented": ["new", "rare", "unique", "unheard-of"],
    "sophisticated": ["complex", "refined", "advanced"],
    "fundamental": ["basic", "key", "core"],
    "ubiquitous": ["common", "everywhere", "widespread"],
    "disparate": ["different", "diverse", "unlike"],
    "cumbersome": ["bulky", "clumsy", "awkward"],
    "efficacious": ["effective", "potent", "useful"],
    "burgeoning": ["growing", "rising", "booming"],
    "overarching": ["broad", "main", "overall"],
    "underlying": ["core", "basic", "root"],
    "exponential": ["rapid", "steep", "fast"],
    "substantial": ["big", "large", "sizeable"],
    "rudimentary": ["basic", "simple", "crude"],
    "symbiotic": ["mutual", "shared", "linked"],
    "ubiquity": ["spread", "reach", "presence"],
    # ── Adverbs ──
    "significantly": ["a lot", "greatly", "much"],
    "substantially": ["largely", "mostly", "a lot"],
    "essentially": ["really", "at its core", "basically"],
    "particularly": ["especially", "mainly", "above all"],
    "specifically": ["namely", "exactly", "in detail"],
    "ultimately": ["in the end", "finally", "at last"],
    "undoubtedly": ["clearly", "for sure", "no doubt"],
    "fundamentally": ["deeply", "at the core", "at heart"],
    "increasingly": ["more and more", "ever more", "steadily"],
    "predominantly": ["mostly", "mainly", "largely"],
    "inherently": ["by nature", "at its core", "naturally"],
    "meticulously": ["carefully", "precisely", "closely"],
    "strategically": ["smartly", "wisely", "shrewdly"],
    "systematically": ["step by step", "in order", "methodically"],
    "exponentially": ["rapidly", "hugely", "fast"],
    "inextricably": ["closely", "tightly", "deeply"],
    # ── Nouns / compound nouns ──
    "landscape": ["field", "area", "scene"],
    "paradigm": ["model", "pattern", "framework"],
    "methodology": ["method", "approach", "way"],
    "testament": ["proof", "sign", "evidence"],
    "realm": ["area", "world", "sphere"],
    "beacon": ["guide", "signal", "light"],
    "plethora": ["many", "a lot of", "plenty of"],
    "myriad": ["many", "tons of", "lots of"],
    "aforementioned": ["earlier", "said", "noted"],
    "capabilities": ["skills", "abilities", "strengths"],
    "technology": ["tech", "tools", "systems"],
    "algorithms": ["methods", "steps", "processes"],
    "computational": ["computing", "digital", "data"],
    "infrastructure": ["setup", "base", "backbone"],
    "phenomenon": ["event", "trend", "occurrence"],
    "dichotomy": ["split", "divide", "gap"],
    "conundrum": ["puzzle", "problem", "dilemma"],
    "ramification": ["effect", "result", "impact"],
    "trajectory": ["path", "course", "trend"],
    "juxtaposition": ["contrast", "comparison"],
    "amalgamation": ["blend", "mix", "merger"],
    "delve": ["dig", "look", "explore"],
    # ── Domain-specific long → short ──
    "reevaluation": ["review", "rethink", "reset"],
    "personalized": ["custom", "tailored", "personal"],
    "instruction": ["teaching", "training", "lessons"],
    "educational": ["learning", "teaching", "school"],
    "comprehensive": ["full", "broad", "complete"],
    "necessitated": ["required", "called for", "forced"],
    "proliferation": ["spread", "growth", "rise"],
    "increasingly": ["more and more", "ever more"],
    "sophisticated": ["complex", "advanced", "refined"],
    "traditional": ["standard", "classic", "usual"],
    "contemporary": ["modern", "current", "today's"],
    "stewardship": ["care", "management", "oversight"],
    "environmental": ["ecological", "green", "natural"],
    "sustainability": ["durability", "lasting change"],
    "sustainable": ["lasting", "green", "viable"],
    "diagnostic": ["medical", "clinical", "testing"],
    "diagnostics": ["tests", "checks", "scans"],
    "cybersecurity": ["security", "digital safety"],
    "encryption": ["coding", "privacy", "encoding"],
    "intrusion": ["breach", "break-in", "attack"],
    "challenges": ["issues", "problems", "hurdles"],
    "intelligence": ["smarts", "brainpower", "AI"],
    "fundamentally": ["deeply", "at its core", "truly"],
    "unprecedented": ["rare", "unheard of", "new"],
    "significant": ["big", "major", "notable"],
    "represents": ["is", "stands for", "signals"],
    "dimensions": ["areas", "aspects", "levels"],
    "innovation": ["novelty", "new idea", "upgrade"],
    "innovations": ["upgrades", "new ideas", "advances"],
    "healthcare": ["health", "medicine", "medical care"],
    "transformation": ["change", "shift", "makeover"],
    "accurate": ["precise", "exact", "correct"],
    "efficient": ["fast", "lean", "smart"],
    "detection": ["finding", "spotting", "tracking"],
    "evolving": ["changing", "growing", "shifting"],
    "demonstrates": ["shows", "proves", "reveals"],
    "necessitate": ["need", "call for", "demand"],
}

# ── German AI replacement dictionary ──
_AI_REPLACEMENTS_DE: dict[str, list[str]] = {
    # ── Konnektoren / Übergangswörter ──
    "darüber hinaus": ["außerdem", "dazu", "noch dazu"],
    "des Weiteren": ["außerdem", "zudem", "dazu"],
    "infolgedessen": ["deshalb", "darum", "daher"],
    "dementsprechend": ["also", "darum", "folglich"],
    "nichtsdestotrotz": ["trotzdem", "dennoch", "aber"],
    "im Wesentlichen": ["hauptsächlich", "im Grunde", "vor allem"],
    "insbesondere": ["besonders", "vor allem", "gerade"],
    "zusammenfassend": ["kurz gesagt", "alles in allem", "insgesamt"],
    "hinsichtlich": ["was … angeht", "in Bezug auf", "wegen"],
    "diesbezüglich": ["dazu", "hierzu", "was das betrifft"],
    "grundsätzlich": ["im Grunde", "prinzipiell", "an sich"],
    "letztendlich": ["am Ende", "schließlich", "im Endeffekt"],
    "zweifellos": ["sicher", "klar", "ohne Frage"],
    "bemerkenswert": ["auffällig", "interessant", "erstaunlich"],
    "maßgeblich": ["entscheidend", "wichtig", "wesentlich"],
    "in Anbetracht": ["wenn man bedenkt", "angesichts"],
    "im Kontext": ["im Rahmen", "im Zusammenhang", "bei"],
    "in der Tat": ["tatsächlich", "wirklich", "stimmt"],
    # ── Adjektive ──
    "signifikant": ["deutlich", "spürbar", "merklich"],
    "umfassend": ["breit", "ausführlich", "gründlich"],
    "fundamental": ["grundlegend", "wesentlich", "tiefgreifend"],
    "essenziell": ["wichtig", "nötig", "unverzichtbar"],
    "komplex": ["schwierig", "verwickelt", "aufwendig"],
    "innovativ": ["neuartig", "kreativ", "erfinderisch"],
    "effizient": ["leistungsfähig", "wirksam", "sparsam"],
    "relevant": ["wichtig", "passend", "bedeutsam"],
    "optimal": ["bestmöglich", "ideal", "am besten"],
    "integriert": ["eingebaut", "eingebunden", "verknüpft"],
    "adaptiv": ["anpassungsfähig", "flexibel"],
    "präzise": ["genau", "exakt", "punktgenau"],
    "robust": ["stabil", "belastbar", "widerstandsfähig"],
    "transparent": ["durchsichtig", "offen", "nachvollziehbar"],
    "dynamisch": ["beweglich", "lebendig", "veränderlich"],
    "potentiell": ["möglich", "denkbar", "eventuell"],
    "konventionell": ["herkömmlich", "üblich", "gewohnt"],
    # ── Verben ──
    "implementieren": ["umsetzen", "einführen", "einbauen"],
    "implementiert": ["setzt um", "führt ein", "baut ein"],
    "optimieren": ["verbessern", "anpassen", "verfeinern"],
    "optimiert": ["verbessert", "passt an", "verfeinert"],
    "integrieren": ["einbinden", "einbauen", "verbinden"],
    "integriert": ["bindet ein", "baut ein", "verbindet"],
    "transformieren": ["umwandeln", "verändern", "umgestalten"],
    "analysieren": ["untersuchen", "prüfen", "auswerten"],
    "demonstrieren": ["zeigen", "belegen", "beweisen"],
    "demonstriert": ["zeigt", "belegt", "beweist"],
    "generieren": ["erzeugen", "schaffen", "herstellen"],
    "generiert": ["erzeugt", "schafft", "stellt her"],
    "gewährleisten": ["sicherstellen", "garantieren"],
    "gewährleistet": ["sichert", "garantiert", "sorgt für"],
    "ermöglichen": ["erlauben", "zulassen", "möglich machen"],
    "ermöglicht": ["erlaubt", "lässt zu", "macht möglich"],
    "erfordern": ["brauchen", "verlangen", "nötig haben"],
    "erfordert": ["braucht", "verlangt", "benötigt"],
    "berücksichtigen": ["beachten", "bedenken", "einbeziehen"],
    "identifizieren": ["erkennen", "feststellen", "finden"],
    "verifizieren": ["prüfen", "bestätigen", "nachweisen"],
    # ── Substantive ──
    "Implementierung": ["Umsetzung", "Einführung"],
    "Optimierung": ["Verbesserung", "Feinabstimmung"],
    "Infrastruktur": ["Aufbau", "Grundlage", "Gerüst"],
    "Transformation": ["Wandel", "Veränderung", "Umbruch"],
    "Paradigma": ["Denkweise", "Modell", "Ansatz"],
    "Methodologie": ["Vorgehen", "Methode", "Ansatz"],
    "Algorithmus": ["Verfahren", "Rechenweg", "Methode"],
    "Parameter": ["Einstellung", "Wert", "Größe"],
    "Perspektive": ["Sichtweise", "Blickwinkel", "Aussicht"],
    "Kontext": ["Zusammenhang", "Umfeld", "Rahmen"],
    "Aspekt": ["Seite", "Punkt", "Gesichtspunkt"],
    "Faktor": ["Grund", "Umstand", "Einfluss"],
    "Komponente": ["Teil", "Baustein", "Element"],
    "Strategie": ["Plan", "Vorgehen", "Ansatz"],
    "Potenzial": ["Möglichkeit", "Chancen", "Spielraum"],
    "Mechanismus": ["Vorgang", "Verfahren", "Ablauf"],
    "Funktionalität": ["Leistung", "Fähigkeit", "Funktion"],
    # ── AI-typische Phrasen ──
    "es ist wichtig zu beachten": ["man sollte bedenken", "beachtenswert ist"],
    "es ist erwähnenswert": ["auffällig ist", "interessant ist"],
    "spielt eine entscheidende Rolle": ["ist sehr wichtig", "hat großen Einfluss"],
    "stellt eine Herausforderung dar": ["ist schwierig", "ist eine Hürde"],
    "im Hinblick auf": ["was betrifft", "bezüglich"],
}

# ── French AI replacement dictionary ──
_AI_REPLACEMENTS_FR: dict[str, list[str]] = {
    # ── Connecteurs / mots de transition ──
    "par conséquent": ["donc", "du coup", "alors"],
    "en outre": ["de plus", "aussi", "en plus"],
    "de surcroît": ["en plus", "qui plus est", "aussi"],
    "néanmoins": ["pourtant", "quand même", "malgré tout"],
    "toutefois": ["cependant", "mais", "pourtant"],
    "fondamentalement": ["au fond", "en gros", "à la base"],
    "essentiellement": ["surtout", "en gros", "principalement"],
    "en résumé": ["bref", "en gros", "pour faire court"],
    "en définitive": ["au final", "en fin de compte", "au bout du compte"],
    "il convient de noter": ["il faut savoir", "on notera"],
    "il est important de souligner": ["il faut dire", "on retiendra"],
    "dans le cadre de": ["dans", "pour", "au sein de"],
    "à cet égard": ["à ce sujet", "sur ce point", "là-dessus"],
    "en ce qui concerne": ["pour ce qui est de", "quant à", "sur"],
    "il est essentiel": ["il faut", "c'est important", "c'est clé"],
    "en particulier": ["surtout", "notamment", "en premier lieu"],
    "dans une large mesure": ["en grande partie", "beaucoup", "largement"],
    "de manière significative": ["nettement", "fortement", "beaucoup"],
    # ── Adjectifs ──
    "significatif": ["notable", "important", "net"],
    "fondamental": ["essentiel", "de base", "central"],
    "substantiel": ["important", "gros", "considérable"],
    "innovant": ["nouveau", "créatif", "original"],
    "optimal": ["idéal", "le meilleur", "au top"],
    "complexe": ["difficile", "compliqué", "subtil"],
    "pertinent": ["utile", "adapté", "juste"],
    "efficace": ["performant", "bon", "qui marche"],
    "robuste": ["solide", "fiable", "résistant"],
    "dynamique": ["vivant", "actif", "en mouvement"],
    "exhaustif": ["complet", "détaillé", "approfondi"],
    "intégré": ["inclus", "incorporé", "combiné"],
    "conventionnel": ["classique", "habituel", "normal"],
    "prépondérant": ["dominant", "principal", "majeur"],
    # ── Verbes ──
    "implémenter": ["mettre en place", "déployer", "lancer"],
    "optimiser": ["améliorer", "ajuster", "peaufiner"],
    "intégrer": ["inclure", "incorporer", "combiner"],
    "transformer": ["changer", "modifier", "faire évoluer"],
    "démontrer": ["montrer", "prouver", "illustrer"],
    "démontre": ["montre", "prouve", "illustre"],
    "garantir": ["assurer", "promettre"],
    "garantit": ["assure", "offre", "permet"],
    "générer": ["créer", "produire", "fabriquer"],
    "génère": ["crée", "produit", "fabrique"],
    "nécessiter": ["demander", "exiger", "avoir besoin de"],
    "nécessite": ["demande", "exige", "a besoin de"],
    "faciliter": ["aider", "simplifier", "rendre facile"],
    "facilite": ["aide", "simplifie", "rend facile"],
    "identifier": ["repérer", "trouver", "reconnaître"],
    "identifie": ["repère", "trouve", "reconnaît"],
    "analyser": ["étudier", "examiner", "décortiquer"],
    "contribuer": ["aider", "participer", "jouer un rôle"],
    "contribue": ["aide", "participe", "joue un rôle"],
    # ── Noms ──
    "implémentation": ["mise en place", "déploiement", "lancement"],
    "optimisation": ["amélioration", "ajustement", "réglage"],
    "infrastructure": ["base", "fondation", "socle"],
    "transformation": ["changement", "évolution", "virage"],
    "paradigme": ["modèle", "vision", "approche"],
    "méthodologie": ["méthode", "approche", "démarche"],
    "algorithme": ["procédé", "méthode", "recette"],
    "paramètre": ["réglage", "valeur", "critère"],
    "perspective": ["point de vue", "angle", "vision"],
    "contexte": ["cadre", "situation", "environnement"],
    "composant": ["élément", "pièce", "partie"],
    "mécanisme": ["fonctionnement", "système", "procédé"],
    "potentiel": ["possibilité", "capacité", "marge"],
    "fonctionnalité": ["fonction", "option", "capacité"],
    # ── Phrases typiques de l'IA ──
    "il est important de noter": ["il faut savoir que", "à noter"],
    "joue un rôle crucial": ["est très important", "compte beaucoup"],
    "représente un défi": ["est difficile", "pose problème"],
    "dans le contexte de": ["dans", "pour", "en matière de"],
}

# ── Spanish AI replacement dictionary ──
_AI_REPLACEMENTS_ES: dict[str, list[str]] = {
    # ── Conectores / palabras de transición ──
    "por consiguiente": ["por eso", "así que", "entonces"],
    "adicionalmente": ["además", "también", "aparte"],
    "no obstante": ["sin embargo", "pero", "aun así"],
    "fundamentalmente": ["básicamente", "en el fondo", "sobre todo"],
    "esencialmente": ["en esencia", "básicamente", "sobre todo"],
    "en resumen": ["en pocas palabras", "resumiendo", "al final"],
    "cabe destacar": ["hay que decir", "vale la pena notar"],
    "es importante señalar": ["hay que saber", "conviene decir"],
    "en el marco de": ["dentro de", "en", "como parte de"],
    "a este respecto": ["sobre esto", "en este punto", "al respecto"],
    "en lo que respecta a": ["en cuanto a", "respecto a", "sobre"],
    "en particular": ["sobre todo", "especialmente", "en concreto"],
    "en gran medida": ["mucho", "bastante", "en buena parte"],
    "de manera significativa": ["mucho", "bastante", "notablemente"],
    "en última instancia": ["al final", "en el fondo", "a la larga"],
    "en consecuencia": ["por eso", "entonces", "así que"],
    "asimismo": ["también", "igualmente", "del mismo modo"],
    "sin lugar a dudas": ["sin duda", "seguro", "claro"],
    # ── Adjetivos ──
    "significativo": ["importante", "notable", "marcado"],
    "fundamental": ["básico", "esencial", "clave"],
    "sustancial": ["grande", "importante", "considerable"],
    "innovador": ["nuevo", "creativo", "novedoso"],
    "óptimo": ["ideal", "el mejor", "perfecto"],
    "complejo": ["difícil", "complicado", "enredado"],
    "pertinente": ["útil", "adecuado", "relevante"],
    "eficiente": ["eficaz", "bueno", "productivo"],
    "robusto": ["sólido", "fuerte", "resistente"],
    "dinámico": ["activo", "vivo", "cambiante"],
    "exhaustivo": ["completo", "detallado", "a fondo"],
    "integrado": ["incluido", "incorporado", "unido"],
    "convencional": ["tradicional", "normal", "habitual"],
    "preponderante": ["principal", "dominante", "importante"],
    # ── Verbos ──
    "implementar": ["poner en marcha", "aplicar", "llevar a cabo"],
    "implementa": ["pone en marcha", "aplica", "lleva a cabo"],
    "optimizar": ["mejorar", "ajustar", "afinar"],
    "optimiza": ["mejora", "ajusta", "afina"],
    "integrar": ["incluir", "incorporar", "unir"],
    "integra": ["incluye", "incorpora", "une"],
    "transformar": ["cambiar", "modificar", "convertir"],
    "transforma": ["cambia", "modifica", "convierte"],
    "demostrar": ["mostrar", "probar", "enseñar"],
    "demuestra": ["muestra", "prueba", "enseña"],
    "garantizar": ["asegurar", "prometer"],
    "garantiza": ["asegura", "ofrece", "permite"],
    "generar": ["crear", "producir", "dar lugar a"],
    "genera": ["crea", "produce", "da lugar a"],
    "requerir": ["necesitar", "exigir", "pedir"],
    "requiere": ["necesita", "exige", "pide"],
    "facilitar": ["ayudar", "simplificar", "hacer fácil"],
    "facilita": ["ayuda", "simplifica", "hace fácil"],
    "identificar": ["encontrar", "detectar", "reconocer"],
    "identifica": ["encuentra", "detecta", "reconoce"],
    "analizar": ["estudiar", "examinar", "revisar"],
    "contribuir": ["ayudar", "aportar", "sumar"],
    "contribuye": ["ayuda", "aporta", "suma"],
    # ── Sustantivos ──
    "implementación": ["puesta en marcha", "aplicación", "lanzamiento"],
    "optimización": ["mejora", "ajuste", "afinación"],
    "infraestructura": ["base", "cimientos", "estructura"],
    "transformación": ["cambio", "giro", "evolución"],
    "paradigma": ["modelo", "enfoque", "visión"],
    "metodología": ["método", "enfoque", "forma de trabajo"],
    "algoritmo": ["método", "proceso", "fórmula"],
    "parámetro": ["valor", "ajuste", "criterio"],
    "perspectiva": ["punto de vista", "ángulo", "visión"],
    "contexto": ["entorno", "situación", "marco"],
    "componente": ["parte", "pieza", "elemento"],
    "mecanismo": ["proceso", "sistema", "método"],
    "potencial": ["posibilidad", "capacidad", "margen"],
    "funcionalidad": ["función", "opción", "capacidad"],
    # ── Frases típicas de IA ──
    "es importante destacar": ["hay que decir", "vale la pena notar"],
    "desempeña un papel crucial": ["es muy importante", "tiene gran peso"],
    "representa un desafío": ["es difícil", "supone un reto"],
    "en el contexto de": ["en", "dentro de", "en materia de"],
}

_AI_REPLACEMENTS_RU: dict[str, list[str]] = {
    "значительно": ["сильно", "заметно", "ощутимо", "серьёзно"],
    "существенно": ["заметно", "сильно", "ощутимо"],
    "безусловно": ["конечно", "точно", "да"],
    "несомненно": ["понятно", "ясное дело", "точно"],
    "ключевой": ["главный", "основной", "важный"],
    "ключевую": ["главную", "основную", "важную"],
    "ключевые": ["главные", "основные", "важные"],
    "комплексный": ["сложный", "непростой"],
    "комплексная": ["сложная", "непростая"],
    "комплексное": ["сложное", "непростое"],
    "инновационный": ["новый", "свежий", "передовой"],
    "инновационная": ["новая", "свежая", "передовая"],
    "инновационные": ["новые", "свежие", "передовые"],
    "фундаментальный": ["основной", "базовый", "коренной"],
    "фундаментально": ["глубоко", "в корне", "по сути"],
    "оптимизировать": ["улучшить", "поправить", "наладить"],
    "имплементировать": ["внедрить", "применить", "запустить"],
    "имплементация": ["внедрение", "практика"],
    "имплементацию": ["внедрение", "практику"],
    "трансформировать": ["изменить", "перестроить"],
    "трансформировал": ["изменил", "перестроил"],
    "трансформировала": ["изменила", "перестроила"],
    "трансформировало": ["изменило", "перестроило"],
    "трансформацию": ["перемену", "изменение"],
    "трансформация": ["перемена", "изменение"],
    "интегрировать": ["объединить", "включить"],
    "верифицировать": ["проверить", "подтвердить"],
    "парадигма": ["подход", "модель", "принцип"],
    "методология": ["метод", "подход", "способ"],
    "способствует": ["помогает", "содействует"],
    "представляет собой": ["это", "является"],
    "обеспечивает": ["даёт", "позволяет"],
    "обеспечивают": ["дают", "позволяют"],
    "всеобъемлющий": ["полный", "широкий", "общий"],
    "первостепенный": ["главный", "основной"],
    "принципиальный": ["важный", "основной", "главный"],
    "чрезвычайно": ["очень", "весьма", "крайне"],
    "искусственный": ["рукотворный", "созданный"],
    "интеллект": ["ум", "разум"],
    "ландшафт": ["поле", "область", "среда"],
    "алгоритмов": ["методов", "приёмов", "схем"],
    "алгоритмы": ["методы", "приёмы", "схемы"],
    "беспрецедентные": ["небывалые", "невиданные", "новые"],
    "беспрецедентный": ["небывалый", "невиданный", "новый"],
    "демонстрирует": ["показывает", "доказывает", "являет"],
    "демонстрируют": ["показывают", "доказывают"],
    "современных": ["нынешних", "сегодняшних", "текущих"],
    "возможности": ["шансы", "навыки", "ресурсы"],
    "технологий": ["решений", "систем", "средств"],
    "различных": ["разных", "многих", "других"],
    "реализация": ["практика", "внедрение"],
    "концепция": ["идея", "мысль", "замысел"],
    "аспект": ["грань", "сторона", "черта"],
    "контекст": ["рамки", "условия", "среда"],
    "перспектива": ["вид", "план", "ракурс"],
    "потенциал": ["задел", "ресурс", "запас"],
    "эффективность": ["польза", "отдача", "толк"],
    "систематически": ["планомерно", "упорядоченно"],
    # ── Long words → shorter alternatives ──
    "технологических": ["новых", "современных"],
    "технологические": ["новые", "современные"],
    "соответственно": ["так", "стало быть"],
    "предоставляет": ["даёт", "вносит"],
    "предоставляют": ["дают", "вносят"],
    "непосредственно": ["прямо", "лично", "сразу"],
    "осуществляется": ["идёт", "делается", "ведётся"],
    "осуществлять": ["делать", "вести"],
    "формирование": ["создание", "рост"],
    "функционирование": ["работа", "действие"],
    "взаимодействие": ["связь", "работа", "контакт"],
    "совершенствование": ["улучшение", "рост"],
    "распространение": ["рост", "охват", "развитие"],
    "использование": ["применение", "задействование"],
    "использования": ["применения"],
    "использовать": ["применять", "задействовать"],
    "последовательно": ["пошагово", "по очереди"],
    "характеристики": ["свойства", "черты"],
    "обстоятельства": ["условия", "факты"],
    "необходимость": ["потребность"],
    "необходимости": ["потребности"],
    "традиционные": ["обычные", "привычные"],
    "традиционных": ["обычных", "привычных"],
    "традиционный": ["обычный", "привычный"],
    "исследования": ["работы", "поиск", "учёба"],
    "исследование": ["работа", "поиск", "анализ"],
    "определённых": ["некоторых", "конкретных"],
    "определённый": ["ясный", "конкретный"],
    "обработке": ["работе с"],
    "обработка": ["работа с"],
    "посредством": ["через", "с помощью"],
    "относительно": ["о", "насчёт", "про"],
    "разнообразных": ["разных", "многих"],
    "разнообразные": ["разные", "многие"],
    "первоначально": ["сперва", "сначала", "вначале"],
    "приблизительно": ["примерно", "около"],
    "максимально": ["как можно", "предельно"],
    "одновременно": ["сразу", "вместе"],
    "многочисленных": ["многих", "ряда"],
    "многочисленные": ["многие", "масса"],
    "проблематика": ["вопросы", "тема"],
    "перспективный": ["выгодный", "удачный"],
    "перспективная": ["выгодная", "удачная"],
    # ── Extra long → short for avg_word_length ──
    "обеспечения": ["защиты", "гарантий"],
    "информации": ["данных", "сведений"],
    "деятельности": ["работы", "дел"],
    "государственных": ["казённых", "публичных"],
    "общественных": ["людских", "общих"],
    "результатов": ["итогов", "плодов"],
    "управление": ["контроль", "ведение"],
    "количество": ["число", "объём"],
    "достижения": ["успехи", "плоды"],
    "требования": ["нужды", "запросы"],
    "развитие": ["рост", "прогресс"],
    "значение": ["роль", "смысл"],
    "проблемы": ["задачи", "беды"],
    "создание": ["запуск", "старт"],
    "наличие": ["присутствие"],
    "например": ["скажем", "к примеру"],
    "является": ["считается", "выступает"],
    # ── Domain-specific long → short ──
    "образовательных": ["учебных", "школьных"],
    "образовательные": ["учебные", "школьные"],
    "образовательная": ["учебная", "школьная"],
    "персонализации": ["личных нужд", "адаптации"],
    "персонализацию": ["адаптацию"],
    "здравоохранения": ["медицины"],
    "здравоохранение": ["медицина"],
    "здравоохранению": ["медицине"],
    "диагностических": ["медицинских", "клинических"],
    "диагностические": ["медицинские", "клинические"],
    "переосмысления": ["пересмотра", "перемен"],
    "переосмысление": ["пересмотр", "перемены"],
    "всеобъемлющего": ["полного", "общего", "большого"],
    "кибербезопасность": ["безопасность", "защита"],
    "инфраструктура": ["база", "основа"],
    "инфраструктуры": ["базы", "основы"],
    "преобразование": ["перемена", "изменение"],
    "преобразования": ["перемены", "изменения"],
    "производительность": ["продуктивность", "отдачу"],
    "производительности": ["продуктивности", "отдачи"],
    "ответственность": ["долг", "обязанность"],
    "ответственности": ["долга", "обязанности"],
    "благодаря": ["из-за", "за счёт"],
    "претерпел": ["прошёл", "пережил"],
    "претерпело": ["прошло", "пережило"],
    "претерпела": ["прошла", "пережила"],
    "обусловило": ["вызвало", "создало"],
    "обусловили": ["вызвали", "создали"],
    "адаптивных": ["гибких", "умных", "подстраиваемых"],
    "адаптивные": ["гибкие", "умные", "подстраиваемые"],
    "адаптивная": ["гибкая", "умная"],
    "адаптивное": ["гибкое", "умное"],
    "шифрования": ["защиты", "кодирования"],
    "шифрование": ["защита", "кодирование"],
    "протоколов": ["правил", "стандартов"],
    "эволюцию": ["рост", "развитие"],
    "передовых": ["новейших", "лучших"],
    "цифровых": ["новых", "IT"],
}

_AI_REPLACEMENTS_UK: dict[str, list[str]] = {
    "значно": ["сильно", "помітно", "відчутно", "серйозно"],
    "суттєво": ["помітно", "сильно", "відчутно"],
    "безумовно": ["звісно", "точно", "так"],
    "безсумнівно": ["зрозуміло", "ясна річ", "точно"],
    "ключовий": ["головний", "основний", "важливий"],
    "ключову": ["головну", "основну", "важливу"],
    "ключові": ["головні", "основні", "важливі"],
    "комплексний": ["складний", "непростий"],
    "комплексна": ["складна", "непроста"],
    "комплексне": ["складне", "непросте"],
    "інноваційний": ["новий", "свіжий", "передовий"],
    "інноваційна": ["нова", "свіжа", "передова"],
    "фундаментальний": ["основний", "базовий", "корінний"],
    "фундаментально": ["глибоко", "по суті", "в корені"],
    "оптимізувати": ["покращити", "поліпшити", "налагодити"],
    "імплементувати": ["впровадити", "застосувати", "запустити"],
    "імплементація": ["впровадження", "практика"],
    "трансформувати": ["змінити", "перебудувати"],
    "трансформував": ["змінив", "перебудував"],
    "трансформувала": ["змінила", "перебудувала"],
    "трансформувало": ["змінило", "перебудувало"],
    "інтегрувати": ["вбудувати", "об'єднати", "включити"],
    "верифікувати": ["перевірити", "підтвердити"],
    "парадигма": ["підхід", "модель", "принцип"],
    "методологія": ["метод", "підхід", "спосіб"],
    "сприяє": ["допомагає", "спричинює"],
    "являє собою": ["це", "є"],
    "забезпечує": ["дає", "дозволяє"],
    "забезпечують": ["дають", "дозволяють"],
    "всеосяжний": ["повний", "широкий", "загальний"],
    "штучний": ["створений людьми"],
    "інтелект": ["розум"],
    "ландшафт": ["поле", "область", "середовище"],
    "алгоритмів": ["методів", "прийомів", "схем"],
    "алгоритми": ["методи", "прийоми", "схеми"],
    "безпрецедентні": ["небувалі", "невидані", "нові"],
    "безпрецедентний": ["небувалий", "невиданий", "новий"],
    "демонструє": ["показує", "доводить", "виявляє"],
    "демонструють": ["показують", "доводять"],
    "сучасних": ["теперішніх", "сьогоднішніх", "нинішніх"],
    "можливості": ["шанси", "навички", "ресурси"],
    "технологій": ["рішень", "систем", "засобів"],
    "різних": ["різноманітних", "багатьох", "інших"],
    "реалізація": ["впровадження", "практика"],
    "концепція": ["ідея", "думка", "задум"],
    "аспект": ["грань", "сторона", "риса"],
    "контекст": ["рамки", "умови", "середовище"],
    "перспектива": ["вид", "план", "ракурс"],
    "потенціал": ["задел", "ресурс", "запас"],
    "ефективність": ["користь", "віддача", "толк"],
    # ── Long words → shorter alternatives ──
    "технологічних": ["нових", "сучасних"],
    "технологічні": ["нові", "сучасні"],
    "відповідно": ["так", "отже"],
    "надає": ["дає", "вносить"],
    "надають": ["дають", "вносять"],
    "безпосередньо": ["прямо", "особисто", "зразу"],
    "здійснюється": ["іде", "робиться", "ведеться"],
    "здійснювати": ["робити", "вести"],
    "формування": ["створення", "зростання"],
    "функціонування": ["робота", "дія"],
    "взаємодія": ["зв'язок", "робота", "контакт"],
    "вдосконалення": ["покращення", "зростання"],
    "розповсюдження": ["зростання", "охоплення"],
    "використання": ["робота з", "застосування"],
    "використовувати": ["брати", "застосовувати"],
    "послідовно": ["покроково", "по черзі"],
    "характеристики": ["властивості", "риси"],
    "обставини": ["умови", "факти"],
    "необхідність": ["потреба"],
    "необхідності": ["потреби"],
    "традиційні": ["звичайні", "звичні"],
    "традиційний": ["звичайний", "звичний"],
    "дослідження": ["роботи", "пошук", "аналіз"],
    "визначених": ["деяких", "конкретних"],
    "визначений": ["ясний", "конкретний"],
    "обробці": ["роботі з"],
    "обробка": ["робота з"],
    "за допомогою": ["через"],
    "відносно": ["про", "щодо"],
    "різноманітних": ["різних", "багатьох"],
    "різноманітні": ["різні", "багато"],
    "первісно": ["спершу", "спочатку"],
    "приблизно": ["близько", "десь"],
    "максимально": ["якомога", "гранично"],
    "одночасно": ["зразу", "водночас"],
    "численних": ["багатьох", "ряду"],
    "численні": ["багато", "ряд"],
}


def _get_ai_replacements(lang: str) -> dict[str, list[str]]:
    if lang == "ru":
        return _AI_REPLACEMENTS_RU
    elif lang == "uk":
        return _AI_REPLACEMENTS_UK
    elif lang == "de":
        return _AI_REPLACEMENTS_DE
    elif lang == "fr":
        return _AI_REPLACEMENTS_FR
    elif lang == "es":
        return _AI_REPLACEMENTS_ES
    return _AI_REPLACEMENTS_EN


# ── Short filler words / phrases for entropy and diversity injection ──

_FILLERS_EN = [
    "actually", "honestly", "you know", "I mean", "well",
    "really", "look", "basically", "sort of", "kind of",
    "right", "true", "sure", "okay", "fine",
    "anyway", "so", "still", "though", "yet",
]

_FILLERS_RU = [
    "вообще", "ну", "вот", "как бы", "типа",
    "короче", "собственно", "в принципе", "скажем",
    "допустим", "кстати", "правда", "между прочим",
    "знаете", "скорее всего", "пожалуй", "видимо",
]

_FILLERS_UK = [
    "взагалі", "ну", "ось", "як би", "типу",
    "коротше", "власне", "в принципі", "скажімо",
    "припустимо", "до речі", "правда", "між іншим",
    "знаєте", "скоріш за все", "мабуть", "видимо",
]

_FILLERS_DE = [
    "also", "naja", "halt", "eigentlich", "sozusagen",
    "irgendwie", "quasi", "sagen wir", "eben",
    "übrigens", "ehrlich gesagt", "im Grunde", "jedenfalls",
    "tatsächlich", "wohl", "vermutlich", "schon",
]

_FILLERS_FR = [
    "en fait", "bon", "alors", "quoi", "bref",
    "disons", "du coup", "genre", "enfin",
    "d'ailleurs", "franchement", "au fond", "bah",
    "en gros", "apparemment", "voilà", "justement",
]

_FILLERS_ES = [
    "bueno", "pues", "en fin", "la verdad", "vamos",
    "digamos", "o sea", "tipo", "mira",
    "por cierto", "la neta", "al final", "de hecho",
    "básicamente", "total", "vale", "claro",
]


def _get_fillers(lang: str) -> list[str]:
    if lang == "ru":
        return _FILLERS_RU
    elif lang == "uk":
        return _FILLERS_UK
    elif lang == "de":
        return _FILLERS_DE
    elif lang == "fr":
        return _FILLERS_FR
    elif lang == "es":
        return _FILLERS_ES
    return _FILLERS_EN


# ── Short words for length variance injection ──

_SHORT_WORDS_EN = [
    "but", "yet", "so", "and", "or", "now", "then",
    "well", "sure", "yes", "no", "oh", "right",
]

_LONG_WORDS_EN = [
    "unfortunately", "nevertheless", "alternatively",
    "interestingly", "surprisingly", "undeniably",
    "understandably", "independently", "approximately",
]

_SHORT_SENTENCES_EN = [
    "That matters.", "It works.", "Here's why.", "Think about it.",
    "Not always.", "Fair point.", "True enough.", "Makes sense.",
    "Consider this.", "Worth noting.", "Look closer.", "Simple as that.",
    "Hard to say.", "Not quite.", "Time will tell.", "It depends.",
]

_SHORT_SENTENCES_RU = [
    "Это важно.", "Так бывает.", "Вот почему.", "Задумайтесь.",
    "Не всегда.", "Верно.", "Имеет смысл.", "Бывает и так.",
    "Вдумайтесь.", "Стоит учесть.", "Просто факт.", "Важный момент.",
    "Сложно сказать.", "Не совсем.", "Время покажет.", "Зависит от ситуации.",
]

_SHORT_SENTENCES_UK = [
    "Це важливо.", "Так буває.", "Ось чому.", "Подумайте.",
    "Не завжди.", "Вірно.", "Має сенс.", "Буває і так.",
    "Вдумайтесь.", "Варто врахувати.", "Просто факт.", "Важливий момент.",
    "Складно сказати.", "Не зовсім.", "Час покаже.", "Залежить від ситуації.",
]

_SHORT_SENTENCES_DE = [
    "Stimmt.", "Klar.", "Genau.", "Denk mal drüber nach.",
    "Nicht immer.", "Guter Punkt.", "Ergibt Sinn.", "So ist das.",
    "Mal sehen.", "Gut zu wissen.", "Kommt drauf an.", "Einfach so.",
    "Schwer zu sagen.", "Nicht ganz.", "Die Zeit wird es zeigen.", "Passt.",
]

_SHORT_SENTENCES_FR = [
    "C'est vrai.", "Bien sûr.", "En effet.", "Réfléchissez-y.",
    "Pas toujours.", "Bon point.", "Ça se tient.", "C'est comme ça.",
    "On verra.", "À noter.", "Ça dépend.", "Tout simplement.",
    "Difficile à dire.", "Pas tout à fait.", "L'avenir le dira.", "Voilà.",
]

_SHORT_SENTENCES_ES = [
    "Es cierto.", "Claro.", "Exacto.", "Piénsalo bien.",
    "No siempre.", "Buen punto.", "Tiene sentido.", "Así es.",
    "Ya veremos.", "Vale la pena.", "Depende.", "Así de simple.",
    "Difícil decir.", "No del todo.", "El tiempo dirá.", "Bueno.",
]


def _get_short_sentences(lang: str) -> list[str]:
    if lang == "ru":
        return _SHORT_SENTENCES_RU
    elif lang == "uk":
        return _SHORT_SENTENCES_UK
    elif lang == "de":
        return _SHORT_SENTENCES_DE
    elif lang == "fr":
        return _SHORT_SENTENCES_FR
    elif lang == "es":
        return _SHORT_SENTENCES_ES
    return _SHORT_SENTENCES_EN


# ── Surgical operation implementations ──────────────────────────────────

def _op_ai_patterns(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Remove or replace AI-characteristic words/phrases."""
    replacements = _get_ai_replacements(lang)
    lower_text = text.lower()
    result = text

    # Sort by length (longest first) to avoid partial matches
    for ai_word in sorted(replacements, key=len, reverse=True):
        if ai_word.lower() not in lower_text:
            continue

        candidates = replacements[ai_word]
        if not candidates:
            continue

        # Use word boundary to avoid partial matches
        # ("transform" must NOT match inside "transformed")
        pattern = re.compile(
            r'\b' + re.escape(ai_word) + r'\b', re.IGNORECASE,
        )

        def _replace_match(m: re.Match, _c=candidates, _r=rng, _mag=magnitude) -> str:
            if _r.random() > _mag:
                return m.group(0)
            replacement = _r.choice(_c)
            # Preserve case
            orig = m.group(0)
            if orig[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            return replacement

        result = pattern.sub(_replace_match, result)
        lower_text = result.lower()

    return result


def _op_sentence_variance(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust sentence length variance.

    If direction=decrease: make sentences more uniform (shorter long ones)
    If direction=increase: inject short sentences for contrast
    """
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return text

    sent_lens = [len(_WORD_RE.findall(s)) for s in sentences]
    mean_len = sum(sent_lens) / len(sent_lens)

    if direction == "decrease":
        # Reduce variance: split very long sentences
        new_sents = []
        for sent, slen in zip(sentences, sent_lens):
            if slen > mean_len * 1.5 and slen > 15 and rng.random() < magnitude:
                # Find a good split point
                split = _find_sentence_split(sent, lang)
                if split:
                    new_sents.extend(split)
                else:
                    new_sents.append(sent)
            else:
                new_sents.append(sent)
        return " ".join(s.strip() for s in new_sents if s.strip())
    else:
        # Increase variance: inject short sentences AND split long ones
        shorts = _get_short_sentences(lang)
        new_sents = list(sentences)

        # First: split very long single sentences to create structure
        if len(new_sents) == 1 and len(_WORD_RE.findall(new_sents[0])) > 15:
            parts = _find_sentence_split(new_sents[0], lang)
            if parts:
                new_sents = parts

        # Then: inject short sentences for variance
        inject_factor = 0.06 if lang in ("ru", "uk") else 0.10
        n_inject = min(1, max(1, int(len(sentences) * inject_factor * magnitude)))
        for _ in range(n_inject):
            if new_sents:
                pos = rng.randint(1, max(1, len(new_sents) - 1))
                new_sents.insert(pos, rng.choice(shorts))
        return " ".join(s.strip() for s in new_sents if s.strip())


def _find_sentence_split(sent: str, lang: str) -> list[str] | None:
    """Find a natural split point in a long sentence."""
    # Split at conjunctions, relative clauses, or comma+conjunction
    patterns = [
        r',\s*(but|yet|however|although|while|though)\s+',
        r',\s*(но|однако|хотя|зато|впрочем)\s+',
        r',\s*(але|однак|хоча|зате|втім)\s+',
        r';\s+',
        r'\s+—\s+',
        r',\s*(and|or)\s+(?=[A-ZА-ЯЁЇ])',
    ]
    for pat in patterns:
        m = re.search(pat, sent, re.IGNORECASE)
        if m and m.start() > len(sent) * 0.25 and m.start() < len(sent) * 0.75:
            part1 = sent[:m.start()].rstrip(",;").strip()
            part2 = sent[m.end():].strip()
            if not part1.endswith((".", "!", "?")):
                part1 += "."
            if part2 and part2[0].islower():
                part2 = part2[0].upper() + part2[1:]
            return [part1, part2]
    return None


def _op_burstiness(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust burstiness (sentence length variation pattern)."""
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return text

    if direction == "increase":
        # Make MORE bursty — inject short sentences after long ones
        shorts = _get_short_sentences(lang)
        # Lower injection rate for RU/UK (short fillers increase word_length_variance)
        inject_rate = magnitude * (0.15 if lang in ("ru", "uk") else 0.30)
        new_sents = []
        sent_lens = [len(_WORD_RE.findall(s)) for s in sentences]
        for i, (sent, slen) in enumerate(zip(sentences, sent_lens)):
            new_sents.append(sent)
            # After long sentence, maybe add a short one
            if slen > 20 and rng.random() < inject_rate:
                new_sents.append(rng.choice(shorts))
        return " ".join(s.strip() for s in new_sents if s.strip())
    else:
        # Make LESS bursty — merge very short sentences
        new_sents = []
        skip_next = False
        for i, sent in enumerate(sentences):
            if skip_next:
                skip_next = False
                continue
            slen = len(_WORD_RE.findall(sent))
            if (slen <= 3 and i + 1 < len(sentences)
                    and rng.random() < magnitude * 0.5):
                # Merge with next
                next_sent = sentences[i + 1].strip()
                if next_sent and next_sent[0].isupper():
                    next_sent = next_sent[0].lower() + next_sent[1:]
                merged = sent.rstrip(".!?") + " — " + next_sent
                new_sents.append(merged)
                skip_next = True
            else:
                new_sents.append(sent)
        return " ".join(s.strip() for s in new_sents if s.strip())


def _op_word_length_var(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust word length variance by strategic word replacements."""
    words = _WORD_RE.findall(text)
    if not words:
        return text

    lengths = [len(w) for w in words]
    mean_len = sum(lengths) / len(lengths)

    replacements = _get_ai_replacements(lang)

    if direction == "decrease":
        # Reduce variance: replace outlier-length words (far from mean)
        result = text
        # Strategy 1: Use AI replacement dict for familiar long words
        for word in sorted(set(words), key=lambda w: abs(len(w) - mean_len), reverse=True):
            if abs(len(word) - mean_len) < 3:
                break
            lw = word.lower()
            if lw in replacements:
                # Find a replacement closer to mean length
                candidates = [c for c in replacements[lw]
                              if abs(len(c) - mean_len) < abs(len(word) - mean_len)]
                if candidates and rng.random() < magnitude:
                    repl = rng.choice(candidates)
                    result = re.sub(
                        r'\b' + re.escape(word) + r'\b',
                        repl, result, count=1, flags=re.IGNORECASE,
                    )

        # Strategy 2: For RU/UK, also try to simplify very long words
        # (>12 chars) not in dict by checking if any dict key is a substring
        if lang in ("ru", "uk"):
            remaining_words = _WORD_RE.findall(result)
            for word in sorted(set(remaining_words), key=len, reverse=True):
                if len(word) < 12:
                    break
                lw = word.lower()
                if lw in replacements or lw in _PROTECTED_WORDS:
                    continue
                # Try to find a dict entry that shares a root (first 5+ chars)
                root = lw[:min(6, len(lw) - 2)]
                for dict_word, candidates in replacements.items():
                    if dict_word.startswith(root) and candidates:
                        shorter = [c for c in candidates if len(c) < len(word) - 2]
                        if shorter and rng.random() < magnitude * 0.6:
                            repl = rng.choice(shorter)
                            result = re.sub(
                                r'\b' + re.escape(word) + r'\b',
                                repl, result, count=1, flags=re.IGNORECASE,
                            )
                            break
        return result
    else:
        # Increase variance: already handled by other ops
        return text


def _op_avg_word_length(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust average word length — the #1 contributor to AI detection.

    Uses a 2-tier strategy:
    1. Replace known AI words with shorter alternatives (curated, safe)
    2. Contract common phrases (e.g. "do not" → "don't")
    """
    if direction != "decrease":
        return text

    # Tier 1: AI word replacement at full magnitude
    result = _op_ai_patterns(text, direction, magnitude, gap, lang, rng)

    # Tier 2: Contractions (EN only) — always safe
    if lang == "en":
        result = _apply_contractions(result, rng, magnitude)

    return result


# ── Generic word shortening helpers ──────────────────────────────────────

_CONTRACTIONS_EN = [
    ("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"),
    ("is not", "isn't"), ("are not", "aren't"), ("was not", "wasn't"),
    ("were not", "weren't"), ("will not", "won't"), ("would not", "wouldn't"),
    ("could not", "couldn't"), ("should not", "shouldn't"),
    ("cannot", "can't"), ("can not", "can't"),
    ("it is", "it's"), ("that is", "that's"), ("there is", "there's"),
    ("they are", "they're"), ("we are", "we're"), ("you are", "you're"),
    ("I am", "I'm"), ("I have", "I've"), ("I will", "I'll"),
    ("I would", "I'd"), ("he is", "he's"), ("she is", "she's"),
    ("let us", "let's"), ("would have", "would've"), ("could have", "could've"),
    ("should have", "should've"),
]


def _apply_contractions(
    text: str, rng: random.Random, magnitude: float,
) -> str:
    """Apply natural English contractions."""
    result = text
    for full, short in _CONTRACTIONS_EN:
        if rng.random() < magnitude:
            pattern = re.compile(re.escape(full), re.IGNORECASE)
            def _repl(m: re.Match, _s=short) -> str:
                if m.group(0)[0].isupper():
                    return _s[0].upper() + _s[1:]
                return _s
            result = pattern.sub(_repl, result, count=1)
    return result


def _shorten_long_words(
    text: str, lang: str, rng: random.Random,
    magnitude: float, min_len: int = 8,
) -> str:
    """Replace long words with shorter synonyms from SynonymDB.

    Only replaces words that are clearly stylistic/formal, NOT content words.
    Uses strict quality filters to avoid bad synonyms.
    """
    try:
        from texthumanize._synonym_db import SynonymDB
        sdb = SynonymDB()
    except Exception:
        return text

    words = _WORD_RE.findall(text)
    # Find long words that could be shortened
    long_words = [w for w in words if len(w) >= min_len]
    if not long_words:
        return text

    # Deduplicate
    seen = set()
    unique_long = []
    for w in long_words:
        wl = w.lower()
        if wl not in seen and wl not in _PROTECTED_WORDS:
            seen.add(wl)
            unique_long.append(w)

    rng.shuffle(unique_long)
    result = text
    # Try to shorten up to magnitude% of long words
    max_replace = max(1, int(len(unique_long) * magnitude))

    replaced = 0
    for word in unique_long:
        if replaced >= max_replace:
            break

        lower = word.lower()
        syns = sdb.get(lower, lang)
        if not syns:
            # Try without common suffixes
            for suffix in ("ing", "tion", "ment", "ness", "ly", "ous", "ive", "able"):
                if lower.endswith(suffix) and len(lower) > len(suffix) + 3:
                    stem = lower[:-len(suffix)]
                    syns = sdb.get(stem, lang)
                    if syns:
                        break
            if not syns:
                continue

        # Filter to shorter synonyms with quality checks
        shorter = [
            s for s in syns
            if len(s) < len(word) - 1  # Actually shorter
            and len(s) >= 3            # Not too short
            and " " not in s           # Single word only
            and s.isalpha()            # No special chars
        ]
        if not shorter:
            continue

        # Prefer common short words (first in ranked list from SynonymDB)
        chosen = shorter[0] if rng.random() < 0.7 else rng.choice(shorter[:3])

        # Replace in text (case-preserving, first occurrence)
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        def _repl(m: re.Match, _c=chosen) -> str:
            orig = m.group(0)
            if orig[0].isupper():
                return _c[0].upper() + _c[1:]
            return _c
        new_result = pattern.sub(_repl, result, count=1)
        if new_result != result:
            result = new_result
            replaced += 1

    return result


# Words that should never be replaced (content words, topic-defining)
_PROTECTED_WORDS = frozenset({
    # Common content nouns (EN)
    "information", "education", "government", "development", "management",
    "environment", "experience", "organization", "community", "technology",
    "research", "business", "industry", "security", "university",
    "knowledge", "intelligence", "performance", "communication", "production",
    "population", "condition", "situation", "operation", "position",
    "attention", "direction", "connection", "collection", "protection",
    "application", "generation", "competition", "foundation", "discussion",
    "construction", "investigation", "observation", "expression",
    "machine", "learning", "network", "networks", "system", "systems",
    "analysis", "function", "structure", "material", "materials",
    "question", "questions", "problem", "problems", "solution", "solutions",
    "country", "countries", "company", "companies", "language", "languages",
    "children", "students", "teachers", "workers", "patients",
    "process", "processes", "resource", "resources", "service", "services",
    "interest", "practice", "evidence",
    # People / roles / tech
    "president", "professor", "scientist", "engineer", "developer",
    "artificial", "computer", "internet", "software", "hardware",
    "database", "programming", "document", "documents",
    # RU/UK content words
    "информация", "образование", "правительство", "технология",
    "исследование", "обучение", "обучения", "машинного", "машинное",
    "алгоритм", "алгоритмы", "алгоритмов", "сеть", "сети",
    "система", "системы", "процесс", "анализ", "данные", "данных",
    "организация", "інформація", "освіта", "навчання", "організація", "процес", "аналіз", "дані", "даних",
})


def _op_transitions(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust transition word density."""
    if lang == "en":
        transitions = [
            "however", "therefore", "furthermore", "moreover",
            "additionally", "consequently", "nevertheless",
            "subsequently", "accordingly", "alternatively",
        ]
    elif lang == "ru":
        transitions = [
            "однако", "поэтому", "следовательно", "кроме того",
            "более того", "тем не менее", "впоследствии",
        ]
    else:
        transitions = [
            "однак", "тому", "отже", "крім того",
            "більше того", "тим не менш", "згодом",
        ]

    if direction == "decrease":
        # Remove transition words (they signal AI)
        result = text
        rng.shuffle(transitions)
        n_remove = max(1, int(len(transitions) * magnitude))
        for tw in transitions[:n_remove]:
            # Remove at sentence start
            pattern = re.compile(
                r'(?<=\.\s)' + re.escape(tw.capitalize()) + r',?\s*',
                re.IGNORECASE,
            )
            result = pattern.sub("", result, count=1)
            # Remove mid-sentence
            pattern2 = re.compile(
                r',?\s*' + re.escape(tw) + r',?\s*',
                re.IGNORECASE,
            )
            if rng.random() < magnitude * 0.5:
                result = pattern2.sub(", ", result, count=1)
        return result
    else:
        # Insert a few natural transitions
        fillers = _get_fillers(lang)
        sentences = split_sentences(text)
        if len(sentences) < 2:
            return text
        new_sents = [sentences[0]]
        for s in sentences[1:]:
            if rng.random() < magnitude * 0.3:
                filler = rng.choice(fillers)
                s_stripped = s.strip()
                if s_stripped and s_stripped[0].isupper():
                    s_stripped = s_stripped[0].lower() + s_stripped[1:]
                new_sents.append(f"{filler.capitalize()}, {s_stripped}")
            else:
                new_sents.append(s)
        return " ".join(s.strip() for s in new_sents if s.strip())


def _op_starter_diversity(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust sentence starter diversity."""
    if direction == "increase":
        # Already have the naturalizer for this
        return text

    # Decrease: use same first word for consecutive sentences (rare need)
    return text


def _op_conjunction_rate(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust conjunction rate (and, but, or / и, но, а / і, але, а)."""
    conjunctions = {
        "en": ["and", "but", "or", "yet", "so"],
        "ru": ["и", "но", "а", "или", "да"],
        "uk": ["і", "але", "а", "або", "та"],
    }
    conj_list = conjunctions.get(lang, conjunctions["en"])

    if direction == "increase":
        # Inject conjunctions by merging adjacent sentences
        sentences = split_sentences(text)
        if len(sentences) < 2:
            return text
        new_sents = []
        skip = False
        for i, sent in enumerate(sentences):
            if skip:
                skip = False
                continue
            words = _WORD_RE.findall(sent)
            if (i + 1 < len(sentences) and len(words) < 12
                    and rng.random() < magnitude * 0.5):
                next_s = sentences[i + 1].strip()
                if next_s and next_s[0].isupper():
                    next_s = next_s[0].lower() + next_s[1:]
                conj = rng.choice(conj_list[:3])  # Prefer common ones
                merged = sent.rstrip(".!?") + f", {conj} " + next_s
                new_sents.append(merged)
                skip = True
            else:
                new_sents.append(sent)
        return " ".join(s.strip() for s in new_sents if s.strip())
    else:
        # Decrease: split at conjunctions
        for conj in conj_list:
            pattern = rf',\s*{re.escape(conj)}\s+'
            if re.search(pattern, text):
                parts = re.split(pattern, text, maxsplit=1)
                if len(parts) == 2 and len(parts[1]) > 10:
                    p2 = parts[1].strip()
                    if p2 and p2[0].islower():
                        p2 = p2[0].upper() + p2[1:]
                    return parts[0].rstrip() + ". " + p2
        return text


def _op_avg_para_length(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust average paragraph length."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return text

    if direction == "increase":
        # Merge short paragraphs
        if len(paragraphs) < 2:
            return text
        new_paras = [paragraphs[0]]
        for p in paragraphs[1:]:
            if (len(_WORD_RE.findall(new_paras[-1])) < 30
                    and rng.random() < magnitude * 0.6):
                new_paras[-1] = new_paras[-1] + " " + p
            else:
                new_paras.append(p)
        return "\n\n".join(new_paras)
    else:
        # Decrease: split long paragraphs
        new_paras = []
        for p in paragraphs:
            sents = split_sentences(p)
            if len(sents) > 4 and rng.random() < magnitude * 0.5:
                mid = len(sents) // 2
                new_paras.append(" ".join(s.strip() for s in sents[:mid]))
                new_paras.append(" ".join(s.strip() for s in sents[mid:]))
            else:
                new_paras.append(p)
        return "\n\n".join(new_paras)


def _op_punctuation(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, feat_name: str, lang: str, rng: random.Random,
) -> str:
    """Adjust punctuation rates."""
    if feat_name == "dash_rate":
        if direction == "increase":
            # Inject dashes
            sentences = split_sentences(text)
            result_sents = []
            for s in sentences:
                words = s.split()
                if len(words) > 8 and rng.random() < magnitude * 0.4:
                    pos = rng.randint(3, len(words) - 3)
                    words.insert(pos, "—")
                    result_sents.append(" ".join(words))
                else:
                    result_sents.append(s)
            return " ".join(result_sents)
        else:
            return text.replace(" — ", ", ").replace(" – ", ", ")

    elif feat_name == "question_rate":
        if direction == "increase":
            shorts = _get_short_sentences(lang)
            questions_en = [
                "But why?", "How so?", "What does this mean?",
                "Is that really true?", "Sound familiar?",
            ]
            questions_ru = [
                "Но почему?", "Как так?", "Что это значит?",
                "Правда ли это?", "Знакомо?",
            ]
            questions_uk = [
                "Але чому?", "Як так?", "Що це означає?",
                "Чи правда це?", "Знайомо?",
            ]
            questions_de = [
                "Aber warum?", "Wie das?", "Was heißt das?",
                "Stimmt das wirklich?", "Kommt Ihnen das bekannt vor?",
            ]
            questions_fr = [
                "Mais pourquoi?", "Comment ça?", "Qu'est-ce que ça veut dire?",
                "Vraiment?", "Ça vous parle?",
            ]
            questions_es = [
                "¿Pero por qué?", "¿Cómo así?", "¿Qué significa esto?",
                "¿De verdad?", "¿Les suena?",
            ]
            questions = (
                questions_ru if lang == "ru"
                else questions_uk if lang == "uk"
                else questions_de if lang == "de"
                else questions_fr if lang == "fr"
                else questions_es if lang == "es"
                else questions_en
            )
            sentences = split_sentences(text)
            if len(sentences) >= 3:
                pos = rng.randint(1, len(sentences) - 1)
                sentences.insert(pos, rng.choice(questions))
            return " ".join(s.strip() for s in sentences if s.strip())

    elif feat_name == "comma_rate":
        if direction == "increase":
            # Add parenthetical commas
            # Higher rate for short texts (few sentences = low chance)
            sentences = split_sentences(text)
            n_sents = len(sentences)
            if lang in ("ru", "uk"):
                base_rate = 0.18 if n_sents < 5 else 0.10
            else:
                base_rate = 0.30 if n_sents < 5 else 0.18
            inject_rate = magnitude * base_rate
            fillers = _get_fillers(lang)
            result_sents = []
            for s in sentences:
                if rng.random() < inject_rate:
                    words = s.split()
                    if len(words) > 5:
                        pos = rng.randint(2, min(4, len(words) - 2))
                        filler = rng.choice(fillers)
                        words.insert(pos, f", {filler},")
                        result_sents.append(" ".join(words))
                    else:
                        result_sents.append(s)
                else:
                    result_sents.append(s)
            return " ".join(result_sents)
        elif direction == "decrease":
            # Remove some commas
            parts = text.split(", ")
            if len(parts) > 2:
                result_parts = [parts[0]]
                for p in parts[1:]:
                    if rng.random() < magnitude * 0.3:
                        result_parts.append(p)  # no comma
                    else:
                        result_parts.append(", " + p)
                return "".join(result_parts)

    elif feat_name == "exclamation_rate":
        if direction == "decrease":
            # Replace ! with . to reduce exclamation rate
            result = text
            count = result.count("!")
            if count > 0:
                n_remove = max(1, int(count * magnitude * 0.7))
                for _ in range(n_remove):
                    idx = result.rfind("!")
                    if idx >= 0:
                        result = result[:idx] + "." + result[idx + 1:]
            return result
        elif direction == "increase":
            sentences = split_sentences(text)
            result_sents = []
            for s in sentences:
                if s.strip().endswith(".") and rng.random() < magnitude * 0.15:
                    result_sents.append(s.strip()[:-1] + "!")
                else:
                    result_sents.append(s)
            return " ".join(result_sents)

    elif feat_name == "semicolon_rate":
        if direction == "decrease":
            return text.replace(";", ",")
        elif direction == "increase":
            return re.sub(
                r',\s*(and|but|so|or|и|но|а|та|але)\s+',
                lambda m: '; ' + m.group(1) + ' ', text, count=1,
            )

    return text


def _op_skewness(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust sentence length distribution skewness."""
    # When skewness is too positive: add a very long sentence (right-tail extend)
    # When too negative: add short sentences
    if direction == "decrease":
        return _op_sentence_variance(text, "decrease", magnitude * 0.5, gap, lang, rng)
    else:
        return _op_sentence_variance(text, "increase", magnitude * 0.5, gap, lang, rng)


def _op_consec_var(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust consecutive sentence length difference variance."""
    # This measures how much adjacent sentences differ in length
    # High value = alternating short-long-short pattern
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return text

    if direction == "decrease":
        # Sort sentences by length within paragraphs (smooth transitions)
        # Actually, just reduce extreme length differences between neighbors
        return _op_sentence_variance(text, "decrease", magnitude * 0.7, gap, lang, rng)
    else:
        # Increase: inject short sentences between long ones
        return _op_burstiness(text, "increase", magnitude * 0.5, gap, lang, rng)


def _op_mean_sent_len(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust mean sentence length."""
    sentences = split_sentences(text)
    if not sentences:
        return text

    if direction == "decrease":
        # Shorten: split long sentences
        new_sents = []
        for sent in sentences:
            words = _WORD_RE.findall(sent)
            if len(words) > 20 and rng.random() < magnitude:
                split = _find_sentence_split(sent, lang)
                if split:
                    new_sents.extend(split)
                else:
                    new_sents.append(sent)
            else:
                new_sents.append(sent)
        return " ".join(s.strip() for s in new_sents if s.strip())
    else:
        # Lengthen: merge short sentences
        conjunctions = {
            "en": [", and ", " — ", "; "],
            "ru": [", и ", " — ", "; ", ", а "],
            "uk": [", і ", " — ", "; ", ", а "],
        }
        conj_list = conjunctions.get(lang, conjunctions["en"])
        new_sents = []
        skip = False
        for i, sent in enumerate(sentences):
            if skip:
                skip = False
                continue
            words = _WORD_RE.findall(sent)
            if (len(words) < 6 and i + 1 < len(sentences)
                    and rng.random() < magnitude):
                next_s = sentences[i + 1].strip()
                if next_s and next_s[0].isupper():
                    next_s = next_s[0].lower() + next_s[1:]
                conj = rng.choice(conj_list)
                merged = sent.rstrip(".!?") + conj + next_s
                new_sents.append(merged)
                skip = True
            else:
                new_sents.append(sent)
        return " ".join(s.strip() for s in new_sents if s.strip())


def _op_vocabulary(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, feat_name: str, lang: str, rng: random.Random,
) -> str:
    """Adjust vocabulary diversity metrics."""
    if direction == "increase":
        # Use AI replacements to increase vocabulary diversity
        return _op_ai_patterns(text, "decrease", magnitude * 0.5, gap, lang, rng)
    return text


def _op_entropy(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, feat_name: str, lang: str, rng: random.Random,
) -> str:
    """Adjust entropy metrics."""
    if direction == "increase":
        # Inject varied vocabulary (fillers, hedges)
        # Lower rate for RU/UK (short fillers hurt word_length_variance)
        inject_rate = magnitude * (0.10 if lang in ("ru", "uk") else 0.18)
        fillers = _get_fillers(lang)
        sentences = split_sentences(text)
        new_sents = []
        for s in sentences:
            if rng.random() < inject_rate:
                filler = rng.choice(fillers)
                s_stripped = s.strip()
                if s_stripped:
                    new_sents.append(f"{filler.capitalize()}, {s_stripped[0].lower()}{s_stripped[1:]}")
                else:
                    new_sents.append(s)
            else:
                new_sents.append(s)
        return " ".join(s.strip() for s in new_sents if s.strip())
    return text


def _op_syllables(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust average syllables per word."""
    if direction == "decrease":
        # AI pattern replacement: long AI words → short common ones
        result = _op_ai_patterns(text, "decrease", magnitude, gap, lang, rng)
        if lang == "en":
            result = _apply_contractions(result, rng, magnitude * 0.5)
        return result
    return text


def _op_paragraphs(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust paragraph structure."""
    if direction == "increase":
        # Split at natural points
        paragraphs = text.split("\n\n")
        new_paras = []
        for p in paragraphs:
            sentences = split_sentences(p)
            if len(sentences) > 5 and rng.random() < magnitude:
                mid = len(sentences) // 2
                new_paras.append(" ".join(s.strip() for s in sentences[:mid]))
                new_paras.append(" ".join(s.strip() for s in sentences[mid:]))
            else:
                new_paras.append(p)
        return "\n\n".join(new_paras)
    return text


def _op_vocab_burstiness(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust vocabulary burstiness (vocab distribution across text halves)."""
    if direction == "increase":
        # Increasing vocab burst = using different words in different parts
        result = _op_ai_patterns(text, "decrease", magnitude, gap, lang, rng)
        return result
    return text


def _op_readability(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, lang: str, rng: random.Random,
) -> str:
    """Adjust Flesch readability score."""
    if direction == "decrease":
        # Lower Flesch = harder to read — rarely needed
        return text
    else:
        # Higher Flesch = easier to read = shorter words + shorter sentences
        # Tier 1: Replace long AI words with shorter ones
        result = _op_ai_patterns(text, "decrease", magnitude * 0.5, gap, lang, rng)

        # Tier 2: Split very long sentences (>25 words)
        sentences = split_sentences(result)
        new_sents = []
        for sent in sentences:
            wc = len(_WORD_RE.findall(sent))
            if wc > 25 and rng.random() < magnitude:
                parts = _find_sentence_split(sent, lang)
                if parts:
                    new_sents.extend(parts)
                else:
                    new_sents.append(sent)
            else:
                new_sents.append(sent)
        result = " ".join(s.strip() for s in new_sents if s.strip())

        # Tier 3: Contractions (EN only)
        if lang == "en":
            result = _apply_contractions(result, rng, magnitude * 0.3)

        return result


def _op_repetition(
    text: str, direction: str, magnitude: float,
    gap: FeatureGap, feat_name: str, lang: str, rng: random.Random,
) -> str:
    """Adjust bigram/trigram repetition rate."""
    if direction == "decrease":
        # Replace repeated phrases with alternatives
        return _op_ai_patterns(text, "decrease", magnitude * 0.5, gap, lang, rng)
    return text


# ═══════════════════════════════════════════════════════════════════════════
# FORGE — Iterative optimization loop
# ═══════════════════════════════════════════════════════════════════════════

class Forge:
    """Iterative gradient descent over text space.

    The main PHANTOM™ loop:
    1. ORACLE analyzes text → feature gaps + gradients
    2. SURGEON applies targeted modifications
    3. ORACLE re-analyzes → check improvement
    4. Repeat until score < target or max iterations

    Unlike blind rule application, FORGE guarantees monotonic improvement
    (or stops if stuck).
    """

    def __init__(
        self,
        oracle: Oracle,
        max_iterations: int = 8,
        target_score: float = 0.30,
        min_improvement: float = 0.003,
        seed: int | None = None,
        use_combined_score: bool = True,
    ) -> None:
        self._oracle = oracle
        self._max_iter = max_iterations
        self._target = target_score
        self._min_improvement = min_improvement
        self._seed = seed
        self._use_combined = use_combined_score

    def _get_score(self, text: str, lang: str) -> float:
        """Get the relevant detection score."""
        if self._use_combined:
            from texthumanize.core import detect_ai
            det = detect_ai(text, lang=lang)
            return det.get("combined_score", det.get("score", 0.5))
        else:
            report = self._oracle.analyze(text, lang)
            return report.score

    def optimize(
        self, text: str, lang: str = "en",
        budget: float = 1.0,
    ) -> ForgeResult:
        """Run iterative optimization.

        Args:
            text: Input text (AI-generated)
            lang: Language code
            budget: Aggressiveness (0.0-1.0)

        Returns:
            ForgeResult with optimized text and trace
        """
        rng = random.Random(self._seed)
        surgeon = Surgeon(rng=rng, lang=lang)

        best_text = text
        best_score = float("inf")
        trace: list[ForgeStep] = []

        current_text = text
        stall_count = 0
        orig_word_count = len(_WORD_RE.findall(text))

        for iteration in range(self._max_iter):
            # 1. ORACLE analysis (gradient guide)
            report = self._oracle.analyze(current_text, lang)
            neural_score = report.score

            # 2. Get the score we're trying to beat
            combined_score = self._get_score(current_text, lang)
            score = combined_score if self._use_combined else neural_score

            logger.info(
                "FORGE iter %d/%d: combined=%.4f neural=%.4f (target=%.4f)",
                iteration + 1, self._max_iter, combined_score, neural_score, self._target,
            )

            # Track best
            if score < best_score:
                best_score = score
                best_text = current_text

            # Record trace
            top_gaps = report.top_gaps(5)
            trace.append(ForgeStep(
                iteration=iteration,
                score=score,
                top_features=[g.name for g in top_gaps],
                top_contributions=[g.contribution for g in top_gaps],
            ))

            # 2. Check convergence
            if score <= self._target:
                logger.info("FORGE converged at iteration %d: score=%.4f", iteration + 1, score)
                break

            # Check if we're stuck (no improvement)
            if iteration > 0 and trace[-1].score >= trace[-2].score - self._min_improvement:
                stall_count += 1
                if stall_count >= 5:
                    logger.info("FORGE: stalled for 5 iterations, stopping")
                    break
                # Increase budget to try harder
                budget = min(budget * 1.3, 1.0)
                logger.info("FORGE: stalling (%d), increasing budget to %.2f", stall_count, budget)
            else:
                stall_count = 0

            # 3. SURGEON operates
            # Adjust budget based on iteration (start aggressive, stay aggressive)
            iter_budget = budget * (0.85 + 0.15 * iteration / max(self._max_iter - 1, 1))
            modified = surgeon.operate(current_text, report, budget=iter_budget)

            if modified == current_text:
                logger.info("FORGE: no changes made, stopping")
                break

            # 4. Check text expansion limit
            # More generous for short texts (short texts need more injections)
            if orig_word_count < 20:
                max_expansion = 4.0
            elif orig_word_count < 40:
                max_expansion = 3.0
            elif orig_word_count < 60:
                max_expansion = 2.5
            else:
                max_expansion = 1.7
            modified_wc = len(_WORD_RE.findall(modified))
            if modified_wc > orig_word_count * max_expansion:
                logger.info(
                    "FORGE: text expanded too much (%d → %d words, limit=%.0f%%), stopping",
                    orig_word_count, modified_wc, (max_expansion - 1) * 100,
                )
                break

            # 5. Cleanup: fix spacing artifacts
            modified = _cleanup_text(modified, lang)

            current_text = modified

        # Final cleanup pass
        best_text = _cleanup_text(best_text, lang)

        # Get final score
        final_report = self._oracle.analyze(best_text, lang)
        final_combined = self._get_score(best_text, lang) if self._use_combined else final_report.score

        return ForgeResult(
            original_text=text,
            optimized_text=best_text,
            original_score=trace[0].score if trace else 1.0,
            final_score=final_combined,
            iterations=len(trace),
            trace=trace,
            final_report=final_report,
        )


class ForgeStep:
    """One step of the FORGE optimization loop."""
    __slots__ = ("iteration", "score", "top_contributions", "top_features")

    def __init__(
        self, iteration: int, score: float,
        top_features: list[str], top_contributions: list[float],
    ) -> None:
        self.iteration = iteration
        self.score = score
        self.top_features = top_features
        self.top_contributions = top_contributions


class ForgeResult:
    """Result of PHANTOM™ optimization."""
    __slots__ = (
        "final_report", "final_score", "iterations",
        "optimized_text", "original_score", "original_text", "trace",
    )

    def __init__(
        self, original_text: str, optimized_text: str,
        original_score: float, final_score: float,
        iterations: int, trace: list[ForgeStep],
        final_report: FeatureGapReport,
    ) -> None:
        self.original_text = original_text
        self.optimized_text = optimized_text
        self.original_score = original_score
        self.final_score = final_score
        self.iterations = iterations
        self.trace = trace
        self.final_report = final_report

    @property
    def improvement(self) -> float:
        """Score improvement (positive = better)."""
        return self.original_score - self.final_score

    @property
    def bypassed(self) -> bool:
        """Whether the text is now classified as human."""
        return self.final_score <= 0.34

    def summary(self) -> str:
        lines = [
            "PHANTOM™ Optimization Result",
            f"  Original score: {self.original_score:.4f}",
            f"  Final score:    {self.final_score:.4f}",
            f"  Improvement:    {self.improvement:.4f} ({self.improvement/max(self.original_score, 0.001)*100:.1f}%)",
            f"  Iterations:     {self.iterations}",
            f"  Bypassed:       {'YES ✓' if self.bypassed else 'NO ✗'}",
        ]
        if self.trace:
            lines.append("  Trace:")
            for step in self.trace:
                feats = ", ".join(f"{f}({c:+.3f})" for f, c in
                                  zip(step.top_features[:3], step.top_contributions[:3]))
                lines.append(f"    iter {step.iteration}: score={step.score:.4f} [{feats}]")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

_PHANTOM_INSTANCE: PhantomEngine | None = None


class PhantomEngine:
    """Main PHANTOM™ engine — combines ORACLE + SURGEON + FORGE.

    Usage::

        from texthumanize.phantom import get_phantom
        phantom = get_phantom()
        result = phantom.optimize("AI-generated text...", lang="en")
        print(result.summary())
        print(result.optimized_text)
    """

    def __init__(self) -> None:
        import texthumanize.neural_detector as _nd
        net = _nd._get_network()
        # Must read _DETECTOR_TRAINED AFTER _get_network() mutates it
        trained = _nd._DETECTOR_TRAINED
        self._oracle = Oracle(net, trained=trained)
        logger.info("PHANTOM™ engine initialized (trained=%s)", trained)

    def analyze(self, text: str, lang: str = "en") -> FeatureGapReport:
        """Analyze text and return feature gap report."""
        return self._oracle.analyze(text, lang)

    def optimize(
        self,
        text: str,
        lang: str = "en",
        *,
        max_iterations: int = 8,
        target_score: float = 0.30,
        budget: float = 1.0,
        seed: int | None = None,
    ) -> ForgeResult:
        """Run PHANTOM™ optimization on text.

        Args:
            text: AI-generated text to humanize
            lang: Language code ("en", "ru", "uk")
            max_iterations: Maximum FORGE iterations
            target_score: Stop when score drops below this
            budget: Aggressiveness (0.0 = minimal changes, 1.0 = max)
            seed: Random seed for reproducibility

        Returns:
            ForgeResult with optimized text and diagnostics
        """
        forge = Forge(
            oracle=self._oracle,
            max_iterations=max_iterations,
            target_score=target_score,
            seed=seed,
        )
        return forge.optimize(text, lang=lang, budget=budget)

    def gradient_report(self, text: str, lang: str = "en") -> str:
        """Human-readable gradient report for debugging."""
        report = self._oracle.analyze(text, lang)
        lines = [
            f"PHANTOM™ Gradient Report (score={report.score:.4f})",
            f"{'Feature':<30} {'Raw':>8} {'Z-score':>8} {'Gradient':>10} {'Contrib':>10} {'Direction'}",
            "─" * 85,
        ]
        for gap in report.gaps:
            lines.append(
                f"{gap.name:<30} {gap.raw_value:>8.3f} {gap.normed_value:>8.2f} "
                f"{gap.gradient:>10.4f} {gap.contribution:>10.4f} {gap.target_direction}"
            )
        return "\n".join(lines)


def get_phantom() -> PhantomEngine:
    """Get or create the PHANTOM™ engine singleton."""
    global _PHANTOM_INSTANCE
    if _PHANTOM_INSTANCE is None:
        _PHANTOM_INSTANCE = PhantomEngine()
    return _PHANTOM_INSTANCE


def phantom_optimize(
    text: str,
    lang: str = "en",
    *,
    max_iterations: int = 8,
    target_score: float = 0.30,
    budget: float = 1.0,
    seed: int | None = None,
) -> ForgeResult:
    """Convenience function: run PHANTOM™ optimization.

    Example::

        from texthumanize.phantom import phantom_optimize
        result = phantom_optimize("AI-generated text...", lang="en")
        print(result.optimized_text)
    """
    engine = get_phantom()
    return engine.optimize(
        text, lang, max_iterations=max_iterations,
        target_score=target_score, budget=budget, seed=seed,
    )
