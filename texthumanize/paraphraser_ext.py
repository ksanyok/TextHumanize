"""Расширенный модуль семантического перефразирования.

Предоставляет 15+ синтаксических трансформаций для глубокого
перефразирования предложений без ML-зависимостей:

1.  Clause reorder (Although X, Y → Y, although X)
2.  Passive → Active (EN)
3.  Active → Passive (EN)
4.  Sentence split
5.  Sentence merge
6.  Adverb / PP fronting
7.  Nominalization ↔ Verbalization
8.  It-cleft (EN: "X did Y" → "It was X that did Y")
9.  Topicalization ("I like apples" → "Apples, I like")
10. There-insertion ("A problem exists" → "There is a problem")
11. Gerund ↔ Infinitive (EN: "to do" → "doing")
12. Relative clause → participle (EN: "who is running" → "running")
13. Apposition reorder
14. Coordination → subordination
15. Subject–complement swap (for linking verbs)
16. Conditional inversion (EN: "If you need" → "Should you need")

Все трансформации — rule-based, zero-dependency.
Каждая возвращает (result, description, confidence).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from texthumanize.sentence_split import split_sentences


# ═══════════════════════════════════════════════════════════════
#  Data classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class TransformResult:
    """Single sentence transformation result."""
    original: str
    transformed: str
    kind: str  # e.g. "clause_reorder", "passive_to_active"
    confidence: float  # 0..1


@dataclass
class ParaphraseReport:
    """Full paraphrase report for a text."""
    original: str
    paraphrased: str
    transforms: list[TransformResult] = field(default_factory=list)
    confidence: float = 1.0


# ═══════════════════════════════════════════════════════════════
#  Clause reorder patterns
# ═══════════════════════════════════════════════════════════════

_CLAUSE_REORDER = {
    "en": [
        (re.compile(r'^(Although|Though|Even though|While|Whereas)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Because|Since|As)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')} {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(If)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')} if {m.group(2).strip()}"),
        (re.compile(r'^(When|Whenever|Once)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')} {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Before|After|Until)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')} {m.group(1).lower()} {m.group(2).strip()}"),
    ],
    "ru": [
        (re.compile(r'^(Хотя|Несмотря на то,? что)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Поскольку|Так как|Потому что)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Если)\s+(.+?),\s+(то\s+)?(.+)$', re.I),
         lambda m: f"{m.group(4).strip().rstrip('.!?')}, если {m.group(2).strip()}"),
        (re.compile(r'^(Когда|Пока|После того как)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(До того как|Прежде чем)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
    ],
    "uk": [
        (re.compile(r'^(Хоча|Незважаючи на те,? що)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Оскільки|Тому що)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Якщо)\s+(.+?),\s+(то\s+)?(.+)$', re.I),
         lambda m: f"{m.group(4).strip().rstrip('.!?')}, якщо {m.group(2).strip()}"),
        (re.compile(r'^(Коли|Після того як|Перш ніж)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
    ],
    "de": [
        (re.compile(r'^(Obwohl|Obgleich|Obschon)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Weil|Da)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Wenn|Falls)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
    ],
    "fr": [
        (re.compile(r"^(Bien que|Même si|Quoique)\s+(.+?),\s+(.+)$", re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r"^(Puisque|Parce que|Comme)\s+(.+?),\s+(.+)$", re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
    ],
    "es": [
        (re.compile(r'^(Aunque|A pesar de que)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
        (re.compile(r'^(Porque|Ya que|Como)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3).strip().rstrip('.!?')}, {m.group(1).lower()} {m.group(2).strip()}"),
    ],
}


# ═══════════════════════════════════════════════════════════════
#  Passive ↔ Active patterns (EN only)
# ═══════════════════════════════════════════════════════════════

_PASSIVE_BY_RE = re.compile(
    r'^(The\s+)?(.+?)\s+(was|were|is|are|has been|have been|had been)\s+'
    r'(\w+ed)\s+by\s+(.+?)([.!?]?)$',
    re.IGNORECASE,
)

# Active → Passive: "John wrote the book" → "The book was written by John"
_ACTIVE_SVO_RE = re.compile(
    r'^([A-ZА-ЯІЇЄҐ]\w+(?:\s+\w+)?)\s+'   # subject (1-2 words)
    r'(\w+(?:ed|s|es|d))\s+'                 # verb past/3ps
    r'(the\s+|a\s+|an\s+)?'                  # optional article
    r'(.+?)([.!?]?)$',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
#  EN Contractions → full / full → contractions
# ═══════════════════════════════════════════════════════════════

_EN_IRREGULAR_PAST = {
    "wrote": "written", "ate": "eaten", "took": "taken",
    "gave": "given", "saw": "seen", "made": "made",
    "found": "found", "told": "told", "built": "built",
    "brought": "brought", "caught": "caught", "chose": "chosen",
    "drove": "driven", "grew": "grown", "knew": "known",
    "led": "led", "lost": "lost", "read": "read",
    "ran": "run", "sent": "sent", "sold": "sold",
    "set": "set", "spent": "spent", "thought": "thought",
    "understood": "understood", "won": "won",
}


# ═══════════════════════════════════════════════════════════════
#  Nominalization map
# ═══════════════════════════════════════════════════════════════

_NOM_MAP = {
    "en": {
        "decide": "decision", "conclude": "conclusion",
        "develop": "development", "improve": "improvement",
        "analyze": "analysis", "investigate": "investigation",
        "implement": "implementation", "evaluate": "evaluation",
        "consider": "consideration", "recommend": "recommendation",
        "observe": "observation", "explain": "explanation",
        "describe": "description", "suggest": "suggestion",
        "discuss": "discussion", "produce": "production",
        "reduce": "reduction", "introduce": "introduction",
        "transform": "transformation", "create": "creation",
        "demonstrate": "demonstration", "participate": "participation",
        "organize": "organization", "connect": "connection",
        "permit": "permission", "react": "reaction",
        "communicate": "communication", "contribute": "contribution",
        "distribute": "distribution", "educate": "education",
        "eliminate": "elimination", "generate": "generation",
        "inform": "information", "motivate": "motivation",
        "regulate": "regulation", "select": "selection",
    },
    "ru": {
        "решать": "решение", "развивать": "развитие",
        "анализировать": "анализ", "улучшать": "улучшение",
        "исследовать": "исследование", "внедрять": "внедрение",
        "оценивать": "оценка", "рекомендовать": "рекомендация",
        "обсуждать": "обсуждение", "производить": "производство",
        "сокращать": "сокращение", "создавать": "создание",
        "описывать": "описание", "объяснять": "объяснение",
        "предлагать": "предложение", "участвовать": "участие",
    },
    "uk": {
        "вирішувати": "рішення", "розвивати": "розвиток",
        "аналізувати": "аналіз", "покращувати": "покращення",
        "досліджувати": "дослідження", "впроваджувати": "впровадження",
        "оцінювати": "оцінка", "рекомендувати": "рекомендація",
        "обговорювати": "обговорення", "виробляти": "виробництво",
        "скорочувати": "скорочення", "створювати": "створення",
    },
}

_VERB_MAP = {
    lang: {v: k for k, v in mapping.items()}
    for lang, mapping in _NOM_MAP.items()
}


# ═══════════════════════════════════════════════════════════════
#  Split / Merge connectors
# ═══════════════════════════════════════════════════════════════

_SPLIT_CONJ = {
    "en": [", and ", ", but ", ", so ", ", yet ", "; however, ", "; moreover, ",
           "; therefore, ", "; furthermore, ", "; in addition, "],
    "ru": [", и ", ", но ", ", а ", ", поэтому ", "; однако ", "; кроме того, ",
           ", следовательно, ", "; при этом "],
    "uk": [", і ", ", але ", ", а ", ", тому ", "; однак ", "; крім того, ",
           "; при цьому "],
    "de": [", und ", ", aber ", ", doch ", "; jedoch ", "; außerdem "],
    "fr": [", et ", ", mais ", "; cependant, ", "; de plus, "],
    "es": [", y ", ", pero ", "; sin embargo, ", "; además, "],
}

_MERGE_CONN = {
    "en": ["and", "while also", "and at the same time", "moreover"],
    "ru": ["и при этом", "причём", "а также", "и вместе с тем"],
    "uk": ["і при цьому", "причому", "а також", "і водночас"],
    "de": ["und dabei", "und zugleich", "wobei"],
    "fr": ["tout en", "et en même temps", "et par ailleurs"],
    "es": ["y al mismo tiempo", "además de", "y a la vez"],
}


# ═══════════════════════════════════════════════════════════════
#  It-cleft patterns (EN-only)
# ═══════════════════════════════════════════════════════════════

# "John solved the problem" → "It was John who solved the problem"
_IT_CLEFT_RE = re.compile(
    r'^([A-Z]\w+)\s+([\w]+(?:ed|s|es)?)\s+(.+?)([.!?]?)$',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
#  There-insertion (EN existential)
# ═══════════════════════════════════════════════════════════════

# "A problem exists" → "There is a problem"
_EXISTENTIAL_VERBS = {"exists", "existed", "remain", "remains", "remained",
                      "appear", "appears", "appeared", "arise", "arises", "arose"}

# ═══════════════════════════════════════════════════════════════
#  Relative clause → participial (EN)
# ═══════════════════════════════════════════════════════════════

# "who is running" → "running"
# "that was built" → "built"
_REL_TO_PARTICIPLE = re.compile(
    r',?\s*(?:who|which|that)\s+(?:is|are|was|were)\s+(\w+ing|\w+ed)\b',
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════
#  Gerund ↔ Infinitive (EN)
# ═══════════════════════════════════════════════════════════════

_GERUND_TO_INF_VERBS = {"start", "begin", "continue", "prefer", "like",
                         "love", "hate", "try", "intend", "attempt"}
_GERUND_RE = re.compile(r'\b(start|begin|continue|prefer|like|love|hate|try|'
                         r'intend|attempt)(?:s|ed)?\s+(\w+)ing\b', re.I)
_INF_RE = re.compile(r'\b(start|begin|continue|prefer|like|love|hate|try|'
                      r'intend|attempt)(?:s|ed)?\s+to\s+(\w+)\b', re.I)


# ═══════════════════════════════════════════════════════════════
#  Conditional inversion (EN)
# ═══════════════════════════════════════════════════════════════

# "If you need help, ..." → "Should you need help, ..."
_COND_INVERSION_RE = re.compile(
    r'^If\s+(?:you|we|they)\s+(need|want|have|require|decide|choose)\b(.+?),'
    r'\s*(.+)$',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
#  Engine
# ═══════════════════════════════════════════════════════════════

class SemanticParaphraser:
    """Rule-based semantic paraphraser with 16 transform types.

    Transforms sentences syntactically while preserving meaning.
    No external ML dependencies — everything is pattern-based.
    """

    def __init__(
        self,
        lang: str = "en",
        intensity: float = 0.5,
        seed: int | None = None,
    ):
        self.lang = lang
        self.intensity = max(0.0, min(1.0, intensity))
        self.rng = random.Random(seed)
        self.changes: list[TransformResult] = []

        # Pre-load per-language data
        self._clause_pats = _CLAUSE_REORDER.get(lang, [])
        self._split_conj = _SPLIT_CONJ.get(lang, [])
        self._merge_conn = _MERGE_CONN.get(lang, [])
        self._nom = _NOM_MAP.get(lang, {})
        self._verb = _VERB_MAP.get(lang, {})

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def process(self, text: str) -> str:
        """Paraphrase text for the humanisation pipeline.

        Preserves paragraph structure (processes each paragraph
        independently).
        """
        self.changes = []
        if not text or len(text.strip()) < 20:
            return text

        lines = text.split('\n')
        result: list[str] = []
        for line in lines:
            # Skip lines containing segmenter placeholders
            if '\x00THZ_' in line or not line.strip():
                result.append(line)
            else:
                result.append(self._process_paragraph(line))
        return '\n'.join(result)

    def paraphrase(self, text: str) -> ParaphraseReport:
        """Full paraphrase with detailed report."""
        self.changes = []
        processed = self.process(text)
        conf = (sum(t.confidence for t in self.changes) / len(self.changes)
                if self.changes else 1.0)
        return ParaphraseReport(
            original=text,
            paraphrased=processed,
            transforms=list(self.changes),
            confidence=conf,
        )

    # ──────────────────────────────────────────────────────────
    #  Internal: per-paragraph processing
    # ──────────────────────────────────────────────────────────

    def _process_paragraph(self, para: str) -> str:
        """Process a single paragraph (no newlines)."""
        sentences = split_sentences(para, lang=self.lang)
        if not sentences:
            return para

        result: list[str] = []
        max_transforms = max(1, int(len(sentences) * self.intensity))
        n_transforms = 0

        for i, sent in enumerate(sentences):
            if n_transforms >= max_transforms:
                result.append(sent)
                continue

            if self.rng.random() > self.intensity:
                result.append(sent)
                continue

            transformed, kind, conf = self._try_transform(sent, i, sentences)
            if transformed != sent:
                result.append(transformed)
                n_transforms += 1
                self.changes.append(TransformResult(
                    original=sent,
                    transformed=transformed,
                    kind=kind,
                    confidence=conf,
                ))
            else:
                result.append(sent)

        # Try merge adjacent short sentences
        if n_transforms < max_transforms and len(result) >= 3:
            result = self._try_merge_pass(result)

        return ' '.join(result)

    # ──────────────────────────────────────────────────────────
    #  Transform dispatcher
    # ──────────────────────────────────────────────────────────

    def _try_transform(
        self, sent: str, idx: int, all_sents: list[str],
    ) -> tuple[str, str, float]:
        """Try all applicable transforms in randomized order."""
        transforms = [
            self._try_clause_reorder,
            self._try_passive_to_active,
            self._try_active_to_passive,
            self._try_sentence_split,
            self._try_fronting,
            self._try_nom_swap,
            self._try_it_cleft,
            self._try_there_insertion,
            self._try_relative_to_participle,
            self._try_gerund_infinitive_swap,
            self._try_conditional_inversion,
            self._try_apposition_reorder,
            self._try_coord_to_subord,
        ]

        self.rng.shuffle(transforms)

        for fn in transforms:
            result, kind, conf = fn(sent)
            if result != sent and len(result.strip()) > 5:
                return result, kind, conf

        return sent, "no_change", 1.0

    # ──────────────────────────────────────────────────────────
    #  1. Clause reorder
    # ──────────────────────────────────────────────────────────

    def _try_clause_reorder(self, sent: str) -> tuple[str, str, float]:
        bare = sent.rstrip('.!?')
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        for pattern, replacement_fn in self._clause_pats:
            m = pattern.match(bare)
            if m:
                try:
                    new = replacement_fn(m) + punct
                    new = new[0].upper() + new[1:]
                    return new, "clause_reorder", 0.9
                except (IndexError, AttributeError):
                    continue
        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  2. Passive → Active (EN)
    # ──────────────────────────────────────────────────────────

    def _try_passive_to_active(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        m = _PASSIVE_BY_RE.match(sent.strip())
        if not m:
            return sent, "", 0.0

        obj = m.group(2).strip()
        verb_pp = m.group(4)
        subj = m.group(5).strip().rstrip('.!?')
        punct = m.group(6) or "."

        active = f"{subj} {verb_pp} the {obj.lower()}{punct}"
        active = active[0].upper() + active[1:]
        return active, "passive_to_active", 0.7

    # ──────────────────────────────────────────────────────────
    #  3. Active → Passive (EN)
    # ──────────────────────────────────────────────────────────

    def _try_active_to_passive(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        words = sent.rstrip('.!?').split()
        if len(words) < 4 or len(words) > 10:
            return sent, "", 0.0
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        m = _ACTIVE_SVO_RE.match(sent.strip())
        if not m:
            return sent, "", 0.0

        subj = m.group(1).strip()
        verb = m.group(2).strip().lower()
        _article = m.group(3) or ""
        obj = m.group(4).strip().rstrip('.!?')

        # Skip if object contains adverbs or prepositions (too complex)
        obj_words = obj.split()
        if any(w.lower().endswith("ly") for w in obj_words) or len(obj_words) > 4:
            return sent, "", 0.0

        # Get past participle
        pp = _EN_IRREGULAR_PAST.get(verb)
        if pp is None:
            if verb.endswith("ed"):
                pp = verb
            else:
                return sent, "", 0.0

        # Determine aux
        aux = "was"
        result = f"The {obj.lower()} {aux} {pp} by {subj}{punct}"
        result = result[0].upper() + result[1:]
        return result, "active_to_passive", 0.65

    # ──────────────────────────────────────────────────────────
    #  4. Sentence split
    # ──────────────────────────────────────────────────────────

    def _try_sentence_split(self, sent: str) -> tuple[str, str, float]:
        if len(sent.split()) < 12:
            return sent, "", 0.0

        lower = sent.lower()
        for conj in self._split_conj:
            if conj.lower() in lower:
                idx = lower.index(conj.lower())
                part1 = sent[:idx].strip()
                part2 = sent[idx + len(conj):].strip()

                if len(part1.split()) >= 4 and len(part2.split()) >= 4:
                    if not part1.endswith(('.', '!', '?')):
                        part1 += '.'
                    if part2 and part2[0].islower():
                        part2 = part2[0].upper() + part2[1:]
                    return f"{part1} {part2}", "sentence_split", 0.8

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  5. Sentence merge (pass over list of sentences)
    # ──────────────────────────────────────────────────────────

    def _try_merge_pass(self, sentences: list[str]) -> list[str]:
        """Try to merge two adjacent short sentences."""
        if not self._merge_conn or len(sentences) < 3:
            return sentences

        result = list(sentences)
        for i in range(len(result) - 1):
            s1 = result[i]
            s2 = result[i + 1]
            if (s1 and s2
                    and len(s1.split()) <= 8
                    and len(s2.split()) <= 8
                    and self.rng.random() < self.intensity * 0.3):

                # Strip punctuation from first
                first = s1.rstrip().rstrip('.!?')
                second = s2.strip()
                if second and second[0].isupper():
                    second = second[0].lower() + second[1:]

                conn = self.rng.choice(self._merge_conn)
                merged = f"{first}, {conn} {second}"
                result[i] = merged
                result[i + 1] = ''

                self.changes.append(TransformResult(
                    original=f"{s1} | {s2}",
                    transformed=merged,
                    kind="sentence_merge",
                    confidence=0.75,
                ))
                break  # one merge per pass

        return [s for s in result if s.strip()]

    # ──────────────────────────────────────────────────────────
    #  6. Adverb / PP fronting
    # ──────────────────────────────────────────────────────────

    def _try_fronting(self, sent: str) -> tuple[str, str, float]:
        words = sent.rstrip('.!?').split()
        if len(words) < 5:
            return sent, "", 0.0
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        if self.lang == "en":
            last = words[-1].lower()
            if last.endswith("ly") and len(last) > 4:
                front = last[0].upper() + last[1:]
                rest = " ".join(words[:-1])
                rest = rest[0].lower() + rest[1:]
                return f"{front}, {rest}{punct}", "adverb_fronting", 0.8

            # Prepositional phrase at end: "... in the garden" → "In the garden, ..."
            for prep in ("in", "on", "at", "from", "with", "during", "after", "before"):
                for j in range(len(words) - 2, max(2, len(words) // 2), -1):
                    if words[j].lower() == prep:
                        pp_part = " ".join(words[j:])
                        main_part = " ".join(words[:j]).rstrip(',;')
                        front = pp_part[0].upper() + pp_part[1:]
                        main_part = main_part[0].lower() + main_part[1:]
                        return f"{front}, {main_part}{punct}", "pp_fronting", 0.75
                break  # only check last PP

        elif self.lang in ("ru", "uk"):
            # Move temporal adverb from end to start
            temporal_ru = {"сегодня", "вчера", "завтра", "потом", "сначала",
                           "наконец", "недавно", "раньше", "обычно", "иногда"}
            temporal_uk = {"сьогодні", "вчора", "завтра", "потім", "спочатку",
                           "нарешті", "нещодавно", "раніше", "зазвичай", "іноді"}
            temporal = temporal_ru if self.lang == "ru" else temporal_uk
            last = words[-1].lower().rstrip('.,;:!?')
            if last in temporal:
                front = last[0].upper() + last[1:]
                rest = " ".join(words[:-1])
                rest = rest[0].lower() + rest[1:]
                return f"{front} {rest}{punct}", "temporal_fronting", 0.8

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  7. Nominalization ↔ Verbalization
    # ──────────────────────────────────────────────────────────

    def _try_nom_swap(self, sent: str) -> tuple[str, str, float]:
        """Nominalization swap — only EN, only safe patterns.

        "the development of X" → "developing X"
        "the analysis of Y"   → "analyzing Y"
        Disabled for RU/UK as it requires full morphological generation.
        """
        if self.lang != "en":
            return sent, "", 0.0

        words = sent.split()
        if len(words) < 5:
            return sent, "", 0.0

        # Pattern: "the <noun> of ..." → "... <verb>-ing ..."
        for i, word in enumerate(words[:-2]):
            w_lower = word.lower().rstrip('.,;:!?')
            if (w_lower in self._verb
                    and i > 0
                    and words[i - 1].lower() in ("the", "a", "an")
                    and i + 1 < len(words)
                    and words[i + 1].lower() == "of"):
                verb = self._verb[w_lower]
                # Form gerund
                if verb.endswith("e"):
                    gerund = verb[:-1] + "ing"
                else:
                    gerund = verb + "ing"
                # Remove "the <noun> of" → replace with gerund
                new_words = words[:i - 1] + [gerund] + words[i + 2:]
                result = " ".join(new_words)
                if result and result[0].islower():
                    result = result[0].upper() + result[1:]
                return result, "verbalization", 0.65

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  8. It-cleft (EN)
    # ──────────────────────────────────────────────────────────

    def _try_it_cleft(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        words = sent.rstrip('.!?').split()
        if len(words) < 4 or len(words) > 10:
            return sent, "", 0.0
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        m = _IT_CLEFT_RE.match(sent.strip())
        if not m:
            return sent, "", 0.0

        subj = m.group(1)
        verb = m.group(2)
        rest = m.group(3).rstrip('.!?')

        # Only for past tense verbs
        if not verb.lower().endswith(("ed", "te", "ew", "ld")):
            return sent, "", 0.0

        cleft = f"It was {subj} who {verb} {rest}{punct}"
        return cleft, "it_cleft", 0.7

    # ──────────────────────────────────────────────────────────
    #  9. There-insertion (EN)
    # ──────────────────────────────────────────────────────────

    def _try_there_insertion(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        words = sent.rstrip('.!?').split()
        if len(words) < 3 or len(words) > 8:
            return sent, "", 0.0
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        # "A problem exists" → "There is a problem"
        last = words[-1].lower()
        if last in _EXISTENTIAL_VERBS:
            subj_part = " ".join(words[:-1])
            if subj_part.lower().startswith(("a ", "an ", "some ", "many ", "several ")):
                verb_form = "is" if last.endswith("s") and not last.endswith("es") else "are"
                if last in ("existed", "remained", "appeared", "arose"):
                    verb_form = "was"
                result = f"There {verb_form} {subj_part.lower()}{punct}"
                result = result[0].upper() + result[1:]
                return result, "there_insertion", 0.7

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  10. Relative clause → participial (EN)
    # ──────────────────────────────────────────────────────────

    def _try_relative_to_participle(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        m = _REL_TO_PARTICIPLE.search(sent)
        if m:
            participle = m.group(1)
            start = sent[:m.start()]
            end = sent[m.end():]
            # ", running" or just " running"
            result = f"{start.rstrip(',')} {participle}{end}"
            if result.strip() and len(result.split()) > 3:
                return result, "relative_to_participle", 0.75
        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  11. Gerund ↔ Infinitive swap (EN)
    # ──────────────────────────────────────────────────────────

    def _try_gerund_infinitive_swap(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        # Gerund → Infinitive
        m = _GERUND_RE.search(sent)
        if m:
            verb_main = m.group(1)
            verb_base = m.group(2)
            replacement = f"{verb_main} to {verb_base}"
            result = sent[:m.start()] + replacement + sent[m.end():]
            return result, "gerund_to_infinitive", 0.8

        # Infinitive → Gerund
        m = _INF_RE.search(sent)
        if m:
            verb_main = m.group(1)
            verb_base = m.group(2)
            gerund = verb_base + "ing"
            if verb_base.endswith("e"):
                gerund = verb_base[:-1] + "ing"
            replacement = f"{verb_main} {gerund}"
            result = sent[:m.start()] + replacement + sent[m.end():]
            return result, "infinitive_to_gerund", 0.8

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  12. Conditional inversion (EN)
    # ──────────────────────────────────────────────────────────

    def _try_conditional_inversion(self, sent: str) -> tuple[str, str, float]:
        if self.lang != "en":
            return sent, "", 0.0

        m = _COND_INVERSION_RE.match(sent)
        if m:
            verb = m.group(1)
            rest_cond = m.group(2).strip()
            main_clause = m.group(3).strip()
            result = f"Should you {verb} {rest_cond}, {main_clause}"
            result = result[0].upper() + result[1:]
            return result, "conditional_inversion", 0.75

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  13. Apposition reorder
    # ──────────────────────────────────────────────────────────

    def _try_apposition_reorder(self, sent: str) -> tuple[str, str, float]:
        """Move apposition (parenthetical) to sentence start.

        "Python, a popular language, is used widely."
        → "A popular language, Python is used widely."
        """
        # Match: "X, <apposition>, <rest>"
        m = re.match(
            r'^(\w+(?:\s+\w+)?),\s+(a\s+.+?|an\s+.+?|the\s+.+?),\s+(.+)$',
            sent, re.I,
        )
        if m and self.lang == "en":
            name = m.group(1)
            appos = m.group(2)
            rest = m.group(3)
            result = f"{appos[0].upper()}{appos[1:]}, {name} {rest}"
            return result, "apposition_reorder", 0.7

        return sent, "", 0.0

    # ──────────────────────────────────────────────────────────
    #  14. Coordination → Subordination
    # ──────────────────────────────────────────────────────────

    def _try_coord_to_subord(self, sent: str) -> tuple[str, str, float]:
        """Convert "X and Y" to "X, which Y" or "Since X, Y".

        Only for compound sentences with "and" / "и" / "і".
        """
        if self.lang == "en":
            m = re.match(r'^(.+?),?\s+and\s+(.+)$', sent.rstrip('.!?'), re.I)
            if m and len(m.group(1).split()) >= 4 and len(m.group(2).split()) >= 4:
                punct = sent[-1] if sent and sent[-1] in '.!?' else '.'
                part1 = m.group(1).strip()
                part2 = m.group(2).strip()
                if part2 and part2[0].isupper():
                    part2 = part2[0].lower() + part2[1:]

                # Choose subordination type
                connector = self.rng.choice([
                    f"{part1}, which {part2}",
                    f"{part1}. Additionally, {part2[0].upper()}{part2[1:]}",
                    f"{part1}; moreover, {part2}",
                ])
                return f"{connector}{punct}", "coord_to_subord", 0.65

        elif self.lang in ("ru", "uk"):
            conj = " и " if self.lang == "ru" else " і "
            parts = sent.rstrip('.!?').split(conj, 1)
            if len(parts) == 2 and len(parts[0].split()) >= 4 and len(parts[1].split()) >= 4:
                punct = sent[-1] if sent and sent[-1] in '.!?' else '.'
                part1 = parts[0].strip()
                part2 = parts[1].strip()
                if part2 and part2[0].isupper():
                    part2 = part2[0].lower() + part2[1:]

                conns = {
                    "ru": [f"{part1}, при этом {part2}",
                           f"{part1}. Вместе с тем {part2[0].upper()}{part2[1:]}"],
                    "uk": [f"{part1}, при цьому {part2}",
                           f"{part1}. Водночас {part2[0].upper()}{part2[1:]}"],
                }
                connected = self.rng.choice(conns.get(self.lang, conns["ru"]))
                return f"{connected}{punct}", "coord_to_subord", 0.65

        return sent, "", 0.0
