"""Sentence-level restructuring engine for deep humanization.

Targets the structural patterns that AI detectors key on:
1. Contraction injection (don't, it's, we're — huge human signal)
2. Sentence-length distribution reshaping (log-normal target)
3. Sentence-order perturbation within paragraphs
4. Register mixing (formal → informal vocabulary within text)
5. Self-correction patterns ("or rather", "well, actually")
6. Rhetorical question generation from statements
7. Cleft / existential / topicalization transforms

Zero external dependencies — all rule-based.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Optional

from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  1. Contraction injection (EN) — highest impact for detection
# ═══════════════════════════════════════════════════════════════

_CONTRACTION_MAP: dict[str, str] = {
    "do not": "don't",
    "does not": "doesn't",
    "did not": "didn't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "will not": "won't",
    "would not": "wouldn't",
    "could not": "couldn't",
    "should not": "shouldn't",
    "can not": "can't",
    "cannot": "can't",
    "shall not": "shan't",
    "it is": "it's",
    "it has": "it's",
    "that is": "that's",
    "that has": "that's",
    "there is": "there's",
    "there has": "there's",
    "what is": "what's",
    "what has": "what's",
    "who is": "who's",
    "who has": "who's",
    "where is": "where's",
    "when is": "when's",
    "how is": "how's",
    "I am": "I'm",
    "I have": "I've",
    "I will": "I'll",
    "I would": "I'd",
    "I had": "I'd",
    "you are": "you're",
    "you have": "you've",
    "you will": "you'll",
    "you would": "you'd",
    "you had": "you'd",
    "we are": "we're",
    "we have": "we've",
    "we will": "we'll",
    "we would": "we'd",
    "we had": "we'd",
    "they are": "they're",
    "they have": "they've",
    "they will": "they'll",
    "they would": "they'd",
    "they had": "they'd",
    "he is": "he's",
    "he has": "he's",
    "he will": "he'll",
    "he would": "he'd",
    "she is": "she's",
    "she has": "she's",
    "she will": "she'll",
    "she would": "she'd",
    "let us": "let's",
}

# Build compiled regexes — case-insensitive, word-boundary
_CONTRACTION_PATTERNS: list[tuple[re.Pattern[str], str, str]] = []
for _full, _short in _CONTRACTION_MAP.items():
    _pat = re.compile(
        r'\b' + re.escape(_full) + r'\b',
        re.IGNORECASE,
    )
    _CONTRACTION_PATTERNS.append((_pat, _full, _short))


def inject_contractions(
    text: str,
    probability: float = 0.75,
    rng: random.Random | None = None,
) -> str:
    """Replace formal expansions with contractions.

    Args:
        text: Input English text.
        probability: Probability of replacing each match (0-1).
        rng: Optional seeded random instance for determinism.

    Returns:
        Text with natural contractions injected.
    """
    if rng is None:
        rng = random.Random()

    for pat, full, short in _CONTRACTION_PATTERNS:
        def _replacer(m: re.Match, _short: str = short) -> str:
            if rng.random() > probability:
                return m.group()
            orig = m.group()
            # Preserve original capitalization
            if orig[0].isupper():
                return _short[0].upper() + _short[1:]
            return _short
        text = pat.sub(_replacer, text)

    return text


# ═══════════════════════════════════════════════════════════════
#  2. Sentence-length distribution reshaping
# ═══════════════════════════════════════════════════════════════

# Target: log-normal distribution with CV >= 0.50
# - Short sentences (3-7 words): ~20% of text
# - Medium sentences (8-18 words): ~50%
# - Long sentences (19-30 words): ~25%
# - Very long (30+): ~5%

_SPLIT_CONJUNCTIONS_EN = [
    ", which ", ", and ", ", but ", "; ", ", so ",
    ", yet ", ", while ", ", whereas ", " — ",
    ", although ", ", however ", ", therefore ",
]

_SPLIT_CONJUNCTIONS_RU = [
    ", который ", ", которая ", ", которое ", ", которые ",
    ", и ", ", но ", "; ", ", а ",
    ", однако ", ", поэтому ", ", хотя ",
    ", причём ", ", при этом ", " — ",
    ", так как ", ", потому что ", ", ведь ",
]

_SPLIT_CONJUNCTIONS_UK = [
    ", який ", ", яка ", ", яке ", ", які ",
    ", і ", ", але ", "; ", ", а ",
    ", однак ", ", тому ", ", хоча ",
    ", причому ", ", при цьому ", " — ",
    ", бо ", ", тому що ", ", адже ",
]

_SPLIT_CONJUNCTIONS = {
    "en": _SPLIT_CONJUNCTIONS_EN,
    "ru": _SPLIT_CONJUNCTIONS_RU,
    "uk": _SPLIT_CONJUNCTIONS_UK,
}

_SHORT_FRAGMENTS_EN = [
    "Right.", "True.", "Not quite.", "Fair point.", "No doubt.",
    "Exactly.", "In theory.", "Sometimes.", "Hopefully.", "Perhaps.",
    "Debatable.", "Obviously.", "Clearly.", "Well, sort of.",
    "More or less.", "Hard to say.", "It depends.", "Maybe.",
    "Not always.", "Good point.", "That said.", "Interesting.",
]

_SHORT_FRAGMENTS_RU = [
    "Верно.", "Точно.", "Не совсем.", "Логично.", "Без сомнений.",
    "Именно.", "В теории.", "Иногда.", "Надеюсь.", "Возможно.",
    "Спорно.", "Очевидно.", "Ясное дело.", "Ну, как бы да.",
    "Примерно так.", "Трудно сказать.", "Зависит от ситуации.", "Может быть.",
    "Не всегда.", "Хороший аргумент.", "При этом.", "Интересно.",
    "Факт.", "Вот так.", "Бывает.", "А что поделаешь.", "Увы.",
    "Но нет.", "Само собой.", "И правда.",
]

_SHORT_FRAGMENTS_UK = [
    "Вірно.", "Точно.", "Не зовсім.", "Логічно.", "Без сумнівів.",
    "Саме так.", "В теорії.", "Іноді.", "Сподіваюсь.", "Можливо.",
    "Спірно.", "Очевидно.", "Ясна річ.", "Ну, приблизно так.",
    "Приблизно.", "Важко сказати.", "Залежить від ситуації.", "Може бути.",
    "Не завжди.", "Гарний аргумент.", "При цьому.", "Цікаво.",
    "Факт.", "Ось так.", "Буває.", "А що вдієш.", "На жаль.",
    "Але ні.", "Само собою.", "І справді.",
]

_SHORT_FRAGMENTS = {
    "en": _SHORT_FRAGMENTS_EN,
    "ru": _SHORT_FRAGMENTS_RU,
    "uk": _SHORT_FRAGMENTS_UK,
}


def reshape_sentence_lengths(
    text: str,
    lang: str = "en",
    target_cv: float = 0.55,
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Reshape sentence-length distribution toward human-like CV.

    Splits overly uniform sentences and occasionally inserts short
    fragments to increase coefficient of variation.
    """
    if lang not in _SPLIT_CONJUNCTIONS:
        return text  # Unsupported language

    if rng is None:
        rng = random.Random()

    sentences = split_sentences(text, lang)
    if len(sentences) < 3:
        return text

    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return text

    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    cv = (variance ** 0.5) / mean_len

    if cv >= target_cv:
        return text  # Already has enough variation

    result: list[str] = []

    for i, sent in enumerate(sentences):
        wc = len(sent.split())

        # Strategy 1: Split long uniform sentences
        if wc >= 22 and rng.random() < intensity * 0.6:
            parts = _try_split_at_conjunction(sent, lang, rng)
            if parts:
                result.extend(parts)
                continue

        # Strategy 2: Insert short fragment after medium sentences
        # to create variety
        if (
            wc >= 12
            and wc <= 20
            and i < len(sentences) - 1
            and rng.random() < intensity * 0.2
        ):
            result.append(sent)
            result.append(rng.choice(_SHORT_FRAGMENTS.get(lang, _SHORT_FRAGMENTS_EN)))
            continue

        result.append(sent)

    return " ".join(result)


def _try_split_at_conjunction(
    sent: str, lang: str, rng: random.Random,
) -> list[str] | None:
    """Try to split a sentence at a conjunction point."""
    words = sent.split()
    wc = len(words)
    if wc < 15:
        return None

    conj_list = _SPLIT_CONJUNCTIONS.get(lang, _SPLIT_CONJUNCTIONS_EN)

    # Find best split point (in middle third)
    best_pos = -1
    best_conj = ""
    min_third = wc // 3
    max_third = 2 * wc // 3

    for conj in conj_list:
        idx = sent.find(conj)
        if idx == -1:
            continue
        # Count words before the conjunction
        words_before = len(sent[:idx].split())
        if min_third <= words_before <= max_third:
            if best_pos == -1 or abs(words_before - wc // 2) < abs(best_pos - wc // 2):
                best_pos = words_before
                best_conj = conj

    if best_pos == -1:
        return None

    idx = sent.find(best_conj)
    first = sent[:idx].strip()
    second = sent[idx + len(best_conj):].strip()

    # Ensure both parts have content
    if len(first.split()) < 4 or len(second.split()) < 4:
        return None

    # End first with period
    if not first.endswith(('.', '!', '?')):
        first = first.rstrip(',;') + '.'

    # Capitalize second
    if second and second[0].islower():
        second = second[0].upper() + second[1:]

    # Ensure second ends with punctuation
    if not second.endswith(('.', '!', '?')):
        second = second + '.'

    return [first, second]


# ═══════════════════════════════════════════════════════════════
#  3. Sentence-order perturbation
# ═══════════════════════════════════════════════════════════════

def perturb_sentence_order(
    text: str,
    lang: str = "en",
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Slightly shuffle sentence order within paragraphs.

    Only swaps adjacent sentences (not random shuffle) to
    maintain partial coherence. Skips first and last sentences.
    """
    if rng is None:
        rng = random.Random()

    paragraphs = text.split("\n\n")
    result_paras: list[str] = []

    for para in paragraphs:
        sentences = split_sentences(para.strip(), lang)
        if len(sentences) < 4:
            result_paras.append(para)
            continue

        # Swap adjacent non-first/non-last sentences with some probability
        new_sents = list(sentences)
        for i in range(1, len(new_sents) - 2):
            if rng.random() < intensity * 0.25:
                new_sents[i], new_sents[i + 1] = new_sents[i + 1], new_sents[i]

        result_paras.append(" ".join(new_sents))

    return "\n\n".join(result_paras)


# ═══════════════════════════════════════════════════════════════
#  4. Register mixing (formal → informal)
# ═══════════════════════════════════════════════════════════════

_FORMAL_TO_INFORMAL_EN: dict[str, list[str]] = {
    "utilize": ["use", "go with"],
    "implement": ["set up", "put in place", "roll out"],
    "demonstrate": ["show", "prove"],
    "facilitate": ["help", "make easier"],
    "subsequently": ["then", "after that", "later"],
    "consequently": ["so", "as a result"],
    "nevertheless": ["still", "even so", "but"],
    "furthermore": ["also", "plus", "on top of that"],
    "approximately": ["about", "around", "roughly"],
    "sufficient": ["enough"],
    "insufficient": ["not enough"],
    "endeavor": ["try", "attempt"],
    "commence": ["start", "begin", "kick off"],
    "terminate": ["end", "stop", "wrap up"],
    "acquire": ["get", "pick up"],
    "ascertain": ["find out", "figure out"],
    "comprehend": ["understand", "get"],
    "numerous": ["many", "a lot of", "plenty of"],
    "substantial": ["big", "major", "significant"],
    "minimal": ["small", "tiny", "minor"],
    "optimal": ["best", "ideal"],
    "predominant": ["main", "biggest"],
    "equivalent": ["same", "equal"],
    "inevitable": ["bound to happen", "unavoidable"],
    "preliminary": ["early", "initial", "first"],
    "prior to": ["before"],
    "in addition to": ["besides", "on top of"],
    "with respect to": ["about", "regarding"],
    "in the event that": ["if"],
    "for the purpose of": ["to", "for"],
    "in spite of the fact that": ["even though", "despite"],
    "at the present time": ["now", "right now", "currently"],
    "in the near future": ["soon"],
    "a significant number of": ["many", "lots of"],
    "on a daily basis": ["every day", "daily"],
    "in close proximity to": ["near", "close to"],
}

_FORMAL_TO_INFORMAL_RU: dict[str, list[str]] = {
    "осуществлять": ["делать", "проводить"],
    "реализовывать": ["делать", "проводить", "воплощать"],
    "имплементировать": ["внедрять", "вводить"],
    "оптимизировать": ["улучшать", "настраивать"],
    "генерировать": ["создавать", "выдавать"],
    "трансформировать": ["менять", "преобразовывать"],
    "интегрировать": ["встраивать", "объединять"],
    "верифицировать": ["проверять", "подтверждать"],
    "валидировать": ["проверять", "одобрять"],
    "координировать": ["согласовывать", "организовывать"],
    "стимулировать": ["поощрять", "побуждать"],
    "модернизировать": ["обновлять", "улучшать"],
    "систематизировать": ["упорядочить", "разложить по полочкам"],
    "структурировать": ["организовать", "упорядочить"],
    "аккумулировать": ["накопить", "собрать"],
    "нивелировать": ["сгладить", "убрать"],
    "максимизировать": ["увеличить", "поднять"],
    "минимизировать": ["уменьшить", "сократить"],
    "фундаментально": ["в корне", "по сути"],
    "принципиально": ["в корне", "по-настоящему"],
    "систематически": ["регулярно", "методично"],
    "перманентно": ["постоянно", "всё время"],
    "существенно": ["заметно", "ощутимо", "сильно"],
    "безусловно": ["конечно", "точно"],
    "несомненно": ["конечно", "точно"],
    "в настоящее время": ["сейчас", "на данный момент"],
    "в рамках": ["в пределах", "в ходе"],
    "посредством": ["при помощи", "через"],
    "вследствие": ["из-за", "по причине"],
    "с целью": ["чтобы", "для того чтобы"],
    "представляет собой": ["является", "это"],
    "в значительной степени": ["во многом", "сильно"],
    "тем не менее": ["но", "однако"],
    "таким образом": ["итак", "так что"],
    "следовательно": ["а значит", "стало быть"],
}

_FORMAL_TO_INFORMAL_UK: dict[str, list[str]] = {
    "здійснювати": ["робити", "проводити"],
    "реалізовувати": ["робити", "проводити", "втілювати"],
    "імплементувати": ["впроваджувати", "вводити"],
    "оптимізувати": ["поліпшувати", "налаштовувати"],
    "генерувати": ["створювати", "видавати"],
    "трансформувати": ["змінювати", "перетворювати"],
    "інтегрувати": ["вбудовувати", "об'єднувати"],
    "верифікувати": ["перевіряти", "підтверджувати"],
    "валідувати": ["перевіряти", "ухвалювати"],
    "координувати": ["узгоджувати", "організовувати"],
    "стимулювати": ["заохочувати", "спонукати"],
    "модернізувати": ["оновлювати", "поліпшувати"],
    "систематизувати": ["упорядкувати", "розкласти по поличках"],
    "структурувати": ["організувати", "упорядкувати"],
    "акумулювати": ["накопичити", "зібрати"],
    "нівелювати": ["згладити", "прибрати"],
    "максимізувати": ["збільшити", "підняти"],
    "мінімізувати": ["зменшити", "скоротити"],
    "фундаментально": ["докорінно", "по суті"],
    "принципово": ["докорінно", "по-справжньому"],
    "систематично": ["регулярно", "методично"],
    "перманентно": ["постійно", "весь час"],
    "суттєво": ["помітно", "відчутно", "сильно"],
    "безумовно": ["звичайно", "точно"],
    "безсумнівно": ["звичайно", "точно"],
    "наразі": ["зараз", "на даний момент"],
    "у рамках": ["в межах", "у ході"],
    "за допомогою": ["через", "при допомозі"],
    "внаслідок": ["через", "з причини"],
    "з метою": ["щоб", "для того щоб"],
    "являє собою": ["є", "це"],
    "значною мірою": ["багато в чому", "сильно"],
    "тим не менш": ["але", "однак"],
    "таким чином": ["отже", "тож"],
    "відповідно": ["значить", "як наслідок"],
}

_FORMAL_TO_INFORMAL_ALL = {
    "en": _FORMAL_TO_INFORMAL_EN,
    "ru": _FORMAL_TO_INFORMAL_RU,
    "uk": _FORMAL_TO_INFORMAL_UK,
}

_FORMAL_TO_INFORMAL_RE: dict[str, list[tuple[re.Pattern[str], list[str]]]] = {}
for _lang_code, _map in _FORMAL_TO_INFORMAL_ALL.items():
    _FORMAL_TO_INFORMAL_RE[_lang_code] = [
        (re.compile(r'\b' + re.escape(k) + r'\b', re.IGNORECASE), v)
        for k, v in _map.items()
    ]


def mix_register(
    text: str,
    lang: str = "en",
    probability: float = 0.3,
    rng: random.Random | None = None,
) -> str:
    """Replace some formal vocabulary with informal equivalents.

    Only fires for a fraction of matches to create natural register
    variation (not uniformly formal or informal).
    """
    if lang not in _FORMAL_TO_INFORMAL_RE:
        return text

    if rng is None:
        rng = random.Random()

    for pat, replacements in _FORMAL_TO_INFORMAL_RE[lang]:
        def _replacer(m: re.Match, _repls: list[str] = replacements) -> str:
            if rng.random() > probability:
                return m.group()
            replacement = rng.choice(_repls)
            orig = m.group()
            if orig[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            return replacement
        text = pat.sub(_replacer, text)

    return text


# ═══════════════════════════════════════════════════════════════
#  5. Self-correction & discourse markers
# ═══════════════════════════════════════════════════════════════

_SELF_CORRECTION_PATTERNS = [
    "— or rather, ",
    " — well, ",
    " (or maybe ",
    ", actually ",
]

_DISCOURSE_STARTERS_EN = [
    "Look, ", "OK so ", "The thing is, ", "Honestly, ",
    "Here's the deal: ", "I mean, ", "So basically, ",
    "Now, ", "See, ", "Truth is, ", "Point is, ",
    "Funny enough, ", "Turns out, ", "Real talk: ",
    "For what it's worth, ",
]

_DISCOURSE_STARTERS_RU = [
    "Слушайте, ", "Ну вот, ", "Дело в том, что ", "Честно говоря, ",
    "Вот что важно: ", "То есть ", "Проще говоря, ",
    "Так вот, ", "Смотрите, ", "Правда в том, что ", "Суть вот в чём: ",
    "Забавно, но ", "Оказывается, ", "Если по-честному: ",
    "Как ни крути, ", "Кстати, ", "Между прочим, ",
    "Надо сказать, ", "Знаете что, ", "А вообще, ",
    "Ну и ", "К слову, ", "Вот что интересно: ",
]

_DISCOURSE_STARTERS_UK = [
    "Слухайте, ", "Ну ось, ", "Справа в тому, що ", "Чесно кажучи, ",
    "Ось що важливо: ", "Тобто ", "Простіше кажучи, ",
    "Так ось, ", "Дивіться, ", "Правда в тому, що ", "Суть ось у чому: ",
    "Кумедно, але ", "Виявляється, ", "Якщо чесно: ",
    "Як не крути, ", "До речі, ", "Між іншим, ",
    "Треба сказати, ", "Знаєте що, ", "А взагалі, ",
    "Ну і ", "До слова, ", "Ось що цікаво: ",
]

_DISCOURSE_STARTERS = {
    "en": _DISCOURSE_STARTERS_EN,
    "ru": _DISCOURSE_STARTERS_RU,
    "uk": _DISCOURSE_STARTERS_UK,
}


def inject_discourse_markers(
    text: str,
    lang: str = "en",
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Insert human-like discourse markers at sentence beginnings.

    Only inserts in ~15-25% of sentences to maintain natural feel.
    """
    starters = _DISCOURSE_STARTERS.get(lang)
    if starters is None:
        return text

    if rng is None:
        rng = random.Random()

    sentences = split_sentences(text, lang)
    if len(sentences) < 3:
        return text

    result: list[str] = []
    insertions = 0
    max_insertions = max(1, int(len(sentences) * 0.25))

    for i, sent in enumerate(sentences):
        # Skip first sentence and already-marked sentences
        if i == 0 or insertions >= max_insertions:
            result.append(sent)
            continue

        # Check if sentence already starts with a discourse marker
        lower_start = sent[:20].lower()
        if any(lower_start.startswith(m.lower().rstrip()) for m in starters):
            result.append(sent)
            continue

        if rng.random() < intensity * 0.2:
            marker = rng.choice(starters)
            # Lowercase the sentence start after marker
            if sent and sent[0].isupper():
                sent = sent[0].lower() + sent[1:]
            result.append(marker + sent)
            insertions += 1
        else:
            result.append(sent)

    return " ".join(result)


# ═══════════════════════════════════════════════════════════════
#  6. Cleft & existential transforms
# ═══════════════════════════════════════════════════════════════

# "X causes Y" → "It is X that causes Y"
_CLEFT_PATTERN = re.compile(
    r'^(The |A |An |This |That |These |Those |Our |Their )'
    r'(\w+(?:\s+\w+)?)\s+'
    r'(is|are|was|were|has|have|had|can|could|will|would|should|must|may|might)\s+'
    r'(.+)$',
    re.IGNORECASE,
)

# "There are many X that Y" → "Many X that Y exist"
_EXISTENTIAL_PATTERN = re.compile(
    r'^There\s+(is|are|was|were)\s+(a\s+|an\s+|many\s+|several\s+|numerous\s+|some\s+)?(.+?)(\.|!|\?)?$',
    re.IGNORECASE,
)


def apply_cleft_transform(sent: str, rng: random.Random) -> Optional[str]:
    """Transform "The X verb Y" → "It is the X that verb Y"."""
    m = _CLEFT_PATTERN.match(sent.strip())
    if not m:
        return None

    det = m.group(1).strip()
    subj = m.group(2)
    verb = m.group(3)
    rest = m.group(4)

    # Don't cleft very short sentences
    if len(sent.split()) < 8:
        return None

    clefted = f"It {verb} {det.lower()}{subj} that {rest}"
    if not clefted.endswith(('.', '!', '?')):
        clefted += '.'
    return clefted


def apply_existential_transform(sent: str, rng: random.Random) -> Optional[str]:
    """Transform "There are many X" → "Many X exist"."""
    m = _EXISTENTIAL_PATTERN.match(sent.strip())
    if not m:
        return None

    copula = m.group(1).lower()
    quantifier = (m.group(2) or "").strip()
    rest = m.group(3).strip()
    punct = m.group(4) or "."

    if len(rest.split()) < 3:
        return None

    # Choose appropriate verb
    if copula in ("is", "are"):
        verb = "exist" if copula == "are" else "exists"
    elif copula in ("was", "were"):
        verb = "existed"
    else:
        return None

    if quantifier:
        result = f"{quantifier.capitalize()}{rest} {verb}{punct}"
    else:
        result = f"{rest[0].upper()}{rest[1:]} {verb}{punct}"
    return result


# ═══════════════════════════════════════════════════════════════
#  7. Rhetorical question generation
# ═══════════════════════════════════════════════════════════════

_QUESTION_TRIGGERS_EN = {
    "important": "But why does this matter?",
    "significant": "Why is this significant?",
    "crucial": "So why is this crucial?",
    "essential": "Why is this essential?",
    "challenge": "But what's the real challenge here?",
    "problem": "So what's the actual problem?",
    "benefit": "What's the real benefit though?",
    "advantage": "But what advantage does this give us?",
    "solution": "So what's the solution?",
    "difference": "What difference does it make?",
    "impact": "But what's the real impact?",
    "result": "And what was the result?",
}

_QUESTION_TRIGGERS_RU = {
    "важн": "Но почему это вообще важно?",
    "значител": "Почему это имеет значение?",
    "ключев": "Так почему это ключевой момент?",
    "необходим": "А почему это необходимо?",
    "проблем": "Так в чём же реальная проблема?",
    "вызов": "Но в чём тут сложность?",
    "преимущ": "Какое преимущество это даёт?",
    "выгод": "А в чём тут выгода?",
    "решени": "Так какое же решение?",
    "разниц": "Какая тут разница?",
    "влияни": "Но какое реальное влияние?",
    "результат": "И каков результат?",
    "эффект": "Но какой от этого эффект?",
    "причин": "Но в чём причина?",
}

_QUESTION_TRIGGERS_UK = {
    "важлив": "Але чому це взагалі важливо?",
    "значн": "Чому це має значення?",
    "ключов": "Так чому це ключовий момент?",
    "необхідн": "А чому це необхідно?",
    "проблем": "Так у чому ж справжня проблема?",
    "виклик": "Але в чому тут складність?",
    "переваг": "Яку перевагу це дає?",
    "вигод": "А в чому тут вигода?",
    "рішенн": "Так яке ж рішення?",
    "різниц": "Яка тут різниця?",
    "вплив": "Але який реальний вплив?",
    "результат": "І який результат?",
    "ефект": "Але який від цього ефект?",
    "причин": "Але в чому причина?",
}

_QUESTION_TRIGGERS = {
    "en": _QUESTION_TRIGGERS_EN,
    "ru": _QUESTION_TRIGGERS_RU,
    "uk": _QUESTION_TRIGGERS_UK,
}


def inject_rhetorical_questions(
    text: str,
    lang: str = "en",
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Insert rhetorical questions before sentences about key concepts."""
    triggers = _QUESTION_TRIGGERS.get(lang)
    if triggers is None:
        return text

    if rng is None:
        rng = random.Random()

    sentences = split_sentences(text, lang)
    if len(sentences) < 4:
        return text

    result: list[str] = []
    questions_added = 0
    max_questions = max(1, int(len(sentences) * 0.15))

    for i, sent in enumerate(sentences):
        if i == 0 or questions_added >= max_questions:
            result.append(sent)
            continue

        lower = sent.lower()
        for trigger, question in triggers.items():
            if (
                trigger in lower
                and rng.random() < intensity * 0.15
                and questions_added < max_questions
            ):
                result.append(question)
                questions_added += 1
                break

        result.append(sent)

    return " ".join(result)


# ═══════════════════════════════════════════════════════════════
#  Dash & punctuation injection
# ═══════════════════════════════════════════════════════════════

# Patterns: ", and " / ", but " / ", which " can become " — "
_DASH_TARGETS_EN = re.compile(
    r",\s+(and|but|which|or)\s+",
    re.IGNORECASE,
)

_DASH_TARGETS_RU = re.compile(
    r",\s+(и|но|а|или|однако|который|которая|которое|которые|что|хотя)\s+",
    re.IGNORECASE,
)

_DASH_TARGETS_UK = re.compile(
    r",\s+(і|але|а|або|однак|який|яка|яке|які|що|хоча)\s+",
    re.IGNORECASE,
)

_DASH_TARGETS_ALL = {
    "en": _DASH_TARGETS_EN,
    "ru": _DASH_TARGETS_RU,
    "uk": _DASH_TARGETS_UK,
}


def inject_dashes(
    text: str,
    lang: str = "en",
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Replace some comma-conjunction patterns with em-dash variants.

    Targets `dash_rate` feature in the neural/stat detectors.
    """
    pattern = _DASH_TARGETS_ALL.get(lang)
    if pattern is None:
        return text
    if rng is None:
        rng = random.Random()

    def _dash_replacer(m: re.Match) -> str:
        conj = m.group(1)
        if rng.random() < intensity * 0.35:
            # 50% chance: em-dash only, 50%: em-dash + conjunction
            if rng.random() < 0.5:
                return f" \u2014 {conj} "
            return " \u2014 "
        return m.group(0)

    return pattern.sub(_dash_replacer, text)


# Also inject parenthetical asides with dashes
_ASIDE_EN = [
    " \u2014 at least for now",
    " \u2014 or so it seems",
    " \u2014 surprisingly enough",
    " \u2014 in a way",
    " \u2014 to some extent",
]

_ASIDE_RU = [
    " \u2014 по крайней мере пока",
    " \u2014 во всяком случае",
    " \u2014 как ни странно",
    " \u2014 в каком-то смысле",
    " \u2014 до некоторой степени",
    " \u2014 если можно так выразиться",
    " \u2014 что характерно",
    " \u2014 надо заметить",
]

_ASIDE_UK = [
    " \u2014 принаймні поки що",
    " \u2014 у будь-якому разі",
    " \u2014 як не дивно",
    " \u2014 у певному сенсі",
    " \u2014 до певної міри",
    " \u2014 якщо можна так сказати",
    " \u2014 що характерно",
    " \u2014 треба зауважити",
]

_ASIDE_ALL = {
    "en": _ASIDE_EN,
    "ru": _ASIDE_RU,
    "uk": _ASIDE_UK,
}


def inject_parenthetical_dashes(
    text: str,
    lang: str = "en",
    rng: random.Random | None = None,
    intensity: float = 0.5,
) -> str:
    """Inject parenthetical asides marked by em-dashes.

    Human writers frequently use em-dashes for asides.
    """
    asides = _ASIDE_ALL.get(lang)
    if asides is None:
        return text
    if rng is None:
        rng = random.Random()

    sentences = split_sentences(text, lang)
    if len(sentences) < 3:
        return text

    result: list[str] = []
    injected = 0
    max_inject = max(1, int(len(sentences) * 0.15))

    for sent in sentences:
        if injected < max_inject and rng.random() < intensity * 0.12:
            aside = rng.choice(asides)
            if sent.endswith("."):
                sent = sent[:-1] + aside + "."
                injected += 1
        result.append(sent)

    return " ".join(result)


# ═══════════════════════════════════════════════════════════════
#  Master restructure function
# ═══════════════════════════════════════════════════════════════

class SentenceRestructurer:
    """Orchestrates all sentence restructuring transforms.

    Designed to deeply restructure EN text to reduce AI detection.
    Applies transforms based on intensity (0-100).
    """

    def __init__(
        self,
        lang: str = "en",
        intensity: int = 50,
        seed: int | None = None,
    ):
        self.lang = lang
        self.intensity = intensity
        self._rng = random.Random(seed)
        self.changes: list[dict[str, str]] = []

    def process(self, text: str) -> str:
        """Apply all restructuring transforms.

        Preserves paragraph structure by processing each paragraph
        independently and rejoining with original separators.

        Returns:
            Restructured text.
        """
        if not text or not text.strip():
            return text

        self.changes = []
        prob = self.intensity / 100.0

        # Split into paragraphs, preserving separators
        parts = re.split(r'(\n\s*\n)', text)
        # parts = [para1, sep1, para2, sep2, para3, ...]
        processed_parts: list[str] = []
        for part in parts:
            # Separators (whitespace-only between paragraphs) — keep as-is
            if not part.strip():
                processed_parts.append(part)
                continue
            # Process each paragraph through the transforms
            processed_parts.append(
                self._process_paragraph(part, prob)
            )

        return "".join(processed_parts)

    def _process_paragraph(self, text: str, prob: float) -> str:
        """Apply all restructuring transforms to a single paragraph."""

        # 1. Contractions (highest impact, always apply for EN)
        if self.lang == "en" and prob >= 0.15:
            before = text
            text = inject_contractions(text, probability=min(0.9, prob * 1.2), rng=self._rng)
            if text != before:
                self._record_change("contraction_injection", "Injected natural contractions")

        # 2. Register mixing (formal → informal vocabulary)
        if prob >= 0.25:
            before = text
            text = mix_register(
                text, self.lang,
                probability=min(0.5, prob * 0.6),
                rng=self._rng,
            )
            if text != before:
                self._record_change("register_mixing", "Mixed formal/informal register")

        # 3. Sentence-length reshaping
        if prob >= 0.3:
            before = text
            text = reshape_sentence_lengths(
                text, self.lang,
                target_cv=0.35,
                rng=self._rng,
                intensity=prob,
            )
            if text != before:
                self._record_change("length_reshaping", "Reshaped sentence-length distribution")

        # 4. Discourse markers (medium intensity)
        if prob >= 0.35:
            before = text
            text = inject_discourse_markers(
                text, self.lang,
                rng=self._rng,
                intensity=prob,
            )
            if text != before:
                self._record_change("discourse_markers", "Added human-like discourse markers")

        # 5. Rhetorical questions (higher intensity)
        if prob >= 0.45:
            before = text
            text = inject_rhetorical_questions(
                text, self.lang,
                rng=self._rng,
                intensity=prob,
            )
            if text != before:
                self._record_change("rhetorical_questions", "Inserted rhetorical questions")

        # 6. Sentence order perturbation (high intensity only)
        if prob >= 0.6:
            before = text
            text = perturb_sentence_order(
                text, self.lang,
                rng=self._rng,
                intensity=prob * 0.3,  # Gentle even at high intensity
            )
            if text != before:
                self._record_change("sentence_reorder", "Perturbed sentence order for naturalness")

        # 7. Structural transforms (cleft, existential) — per sentence
        if self.lang == "en" and prob >= 0.35:
            text = self._apply_structural_transforms(text, prob)

        # 8. Dash injection (comma→em-dash for punctuation variety)
        if prob >= 0.25:
            before = text
            text = inject_dashes(text, self.lang, rng=self._rng, intensity=prob)
            if text != before:
                self._record_change("dash_injection", "Replaced commas with em-dashes for variety")

        # 9. Parenthetical asides with dashes
        if prob >= 0.50:
            before = text
            text = inject_parenthetical_dashes(text, self.lang, rng=self._rng, intensity=prob)
            if text != before:
                self._record_change("parenthetical_dashes", "Added parenthetical asides with em-dashes")

        return text

    def _record_change(self, change_type: str, description: str) -> None:
        """Record a change, avoiding duplicates for same type."""
        for c in self.changes:
            if c["type"] == change_type:
                return
        self.changes.append({"type": change_type, "description": description})

    def _apply_structural_transforms(self, text: str, prob: float) -> str:
        """Apply cleft and existential transforms to individual sentences."""
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 3:
            return text

        result: list[str] = []
        transforms = 0
        max_transforms = max(1, int(len(sentences) * 0.2))

        for sent in sentences:
            if transforms >= max_transforms:
                result.append(sent)
                continue

            # Try cleft transform
            if self._rng.random() < prob * 0.15:
                clefted = apply_cleft_transform(sent, self._rng)
                if clefted:
                    result.append(clefted)
                    transforms += 1
                    continue

            # Try existential transform
            if self._rng.random() < prob * 0.2:
                existential = apply_existential_transform(sent, self._rng)
                if existential:
                    result.append(existential)
                    transforms += 1
                    continue

            result.append(sent)

        if transforms > 0:
            self.changes.append({
                "type": "structural_transform",
                "description": f"Applied {transforms} structural transforms (cleft/existential)",
            })

        return " ".join(result)
