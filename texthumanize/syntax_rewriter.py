"""Rule-based sentence-level syntax rewriter.

Transforms sentence structure to increase naturalness:
- Active <-> passive voice
- Clause inversion (front/back swap)
- Nominalization <-> verbification
- Parenthetical insertion
- Gerund conversion
- Topic-comment reordering
- Enumeration reordering

Usage:
    from texthumanize.syntax_rewriter import SyntaxRewriter

    rw = SyntaxRewriter(lang="en")
    variants = rw.rewrite(
        "The system processes data efficiently."
    )
"""

from __future__ import annotations

import logging
import random
import re
from typing import Optional

from texthumanize.pos_tagger import POSTagger

logger = logging.getLogger(__name__)

# ─── Irregular verb table (EN) ─────────────────────────────
# {base_form: past_participle}
_EN_IRREGULAR: dict[str, str] = {
    "arise": "arisen",
    "awake": "awoken",
    "be": "been",
    "bear": "borne",
    "beat": "beaten",
    "become": "become",
    "begin": "begun",
    "bend": "bent",
    "bet": "bet",
    "bind": "bound",
    "bite": "bitten",
    "bleed": "bled",
    "blow": "blown",
    "break": "broken",
    "breed": "bred",
    "bring": "brought",
    "build": "built",
    "burn": "burnt",
    "burst": "burst",
    "buy": "bought",
    "catch": "caught",
    "choose": "chosen",
    "cling": "clung",
    "come": "come",
    "cost": "cost",
    "creep": "crept",
    "cut": "cut",
    "deal": "dealt",
    "dig": "dug",
    "do": "done",
    "draw": "drawn",
    "dream": "dreamt",
    "drink": "drunk",
    "drive": "driven",
    "eat": "eaten",
    "fall": "fallen",
    "feed": "fed",
    "feel": "felt",
    "fight": "fought",
    "find": "found",
    "flee": "fled",
    "fly": "flown",
    "forbid": "forbidden",
    "forget": "forgotten",
    "forgive": "forgiven",
    "freeze": "frozen",
    "get": "gotten",
    "give": "given",
    "go": "gone",
    "grind": "ground",
    "grow": "grown",
    "hang": "hung",
    "have": "had",
    "hear": "heard",
    "hide": "hidden",
    "hit": "hit",
    "hold": "held",
    "hurt": "hurt",
    "keep": "kept",
    "kneel": "knelt",
    "know": "known",
    "lay": "laid",
    "lead": "led",
    "lean": "leant",
    "leap": "leapt",
    "learn": "learnt",
    "leave": "left",
    "lend": "lent",
    "let": "let",
    "lie": "lain",
    "light": "lit",
    "lose": "lost",
    "make": "made",
    "mean": "meant",
    "meet": "met",
    "mistake": "mistaken",
    "mow": "mown",
    "overcome": "overcome",
    "overtake": "overtaken",
    "pay": "paid",
    "prove": "proven",
    "put": "put",
    "quit": "quit",
    "read": "read",
    "ride": "ridden",
    "ring": "rung",
    "rise": "risen",
    "run": "run",
    "say": "said",
    "see": "seen",
    "seek": "sought",
    "sell": "sold",
    "send": "sent",
    "set": "set",
    "sew": "sewn",
    "shake": "shaken",
    "shed": "shed",
    "shine": "shone",
    "shoot": "shot",
    "show": "shown",
    "shrink": "shrunk",
    "shut": "shut",
    "sing": "sung",
    "sink": "sunk",
    "sit": "sat",
    "sleep": "slept",
    "slide": "slid",
    "sow": "sown",
    "speak": "spoken",
    "speed": "sped",
    "spend": "spent",
    "spill": "spilt",
    "spin": "spun",
    "spit": "spat",
    "split": "split",
    "spread": "spread",
    "spring": "sprung",
    "stand": "stood",
    "steal": "stolen",
    "stick": "stuck",
    "sting": "stung",
    "stink": "stunk",
    "stride": "stridden",
    "strike": "struck",
    "strive": "striven",
    "swear": "sworn",
    "sweep": "swept",
    "swim": "swum",
    "swing": "swung",
    "take": "taken",
    "teach": "taught",
    "tear": "torn",
    "tell": "told",
    "think": "thought",
    "throw": "thrown",
    "tread": "trodden",
    "understand": "understood",
    "undertake": "undertaken",
    "upset": "upset",
    "wake": "woken",
    "wear": "worn",
    "weave": "woven",
    "weep": "wept",
    "win": "won",
    "wind": "wound",
    "withdraw": "withdrawn",
    "withstand": "withstood",
    "wring": "wrung",
    "write": "written",
}

# Reverse lookup: past_participle → base
_EN_PP_TO_BASE: dict[str, str] = {
    v: k for k, v in _EN_IRREGULAR.items()
}

# ─── Irregular past simple (EN) ────────────────────────────
_EN_PAST_SIMPLE: dict[str, str] = {
    "arise": "arose",
    "awake": "awoke",
    "be": "was",
    "bear": "bore",
    "beat": "beat",
    "become": "became",
    "begin": "began",
    "bend": "bent",
    "bet": "bet",
    "bite": "bit",
    "bleed": "bled",
    "blow": "blew",
    "break": "broke",
    "bring": "brought",
    "build": "built",
    "burn": "burnt",
    "burst": "burst",
    "buy": "bought",
    "catch": "caught",
    "choose": "chose",
    "come": "came",
    "cost": "cost",
    "cut": "cut",
    "deal": "dealt",
    "dig": "dug",
    "do": "did",
    "draw": "drew",
    "drink": "drank",
    "drive": "drove",
    "eat": "ate",
    "fall": "fell",
    "feed": "fed",
    "feel": "felt",
    "fight": "fought",
    "find": "found",
    "fly": "flew",
    "forget": "forgot",
    "forgive": "forgave",
    "freeze": "froze",
    "get": "got",
    "give": "gave",
    "go": "went",
    "grow": "grew",
    "hang": "hung",
    "have": "had",
    "hear": "heard",
    "hide": "hid",
    "hit": "hit",
    "hold": "held",
    "hurt": "hurt",
    "keep": "kept",
    "know": "knew",
    "lay": "laid",
    "lead": "led",
    "leave": "left",
    "lend": "lent",
    "let": "let",
    "lie": "lay",
    "light": "lit",
    "lose": "lost",
    "make": "made",
    "mean": "meant",
    "meet": "met",
    "pay": "paid",
    "put": "put",
    "quit": "quit",
    "read": "read",
    "ride": "rode",
    "ring": "rang",
    "rise": "rose",
    "run": "ran",
    "say": "said",
    "see": "saw",
    "seek": "sought",
    "sell": "sold",
    "send": "sent",
    "set": "set",
    "shake": "shook",
    "shed": "shed",
    "shine": "shone",
    "shoot": "shot",
    "show": "showed",
    "shrink": "shrank",
    "shut": "shut",
    "sing": "sang",
    "sink": "sank",
    "sit": "sat",
    "sleep": "slept",
    "speak": "spoke",
    "spend": "spent",
    "spin": "spun",
    "stand": "stood",
    "steal": "stole",
    "swim": "swam",
    "swing": "swung",
    "take": "took",
    "teach": "taught",
    "tear": "tore",
    "tell": "told",
    "think": "thought",
    "throw": "threw",
    "understand": "understood",
    "wake": "woke",
    "wear": "wore",
    "win": "won",
    "write": "wrote",
}

# ─── Nominalization → verb mapping ─────────────────────────
_EN_NOMINALIZATION: dict[str, str] = {
    "investigation": "investigate",
    "implementation": "implement",
    "evaluation": "evaluate",
    "application": "apply",
    "creation": "create",
    "production": "produce",
    "distribution": "distribute",
    "examination": "examine",
    "exploration": "explore",
    "presentation": "present",
    "regulation": "regulate",
    "consideration": "consider",
    "observation": "observe",
    "demonstration": "demonstrate",
    "explanation": "explain",
    "generation": "generate",
    "celebration": "celebrate",
    "organization": "organize",
    "preparation": "prepare",
    "transformation": "transform",
    "installation": "install",
    "determination": "determine",
    "administration": "administer",
    "communication": "communicate",
    "classification": "classify",
    "modification": "modify",
    "verification": "verify",
    "specification": "specify",
    "optimization": "optimize",
    "development": "develop",
    "improvement": "improve",
    "movement": "move",
    "achievement": "achieve",
    "agreement": "agree",
    "arrangement": "arrange",
    "assessment": "assess",
    "assignment": "assign",
    "attachment": "attach",
    "engagement": "engage",
    "enhancement": "enhance",
    "establishment": "establish",
    "management": "manage",
    "measurement": "measure",
    "replacement": "replace",
    "requirement": "require",
    "settlement": "settle",
    "statement": "state",
    "treatment": "treat",
    "maintenance": "maintain",
    "performance": "perform",
    "attendance": "attend",
    "occurrence": "occur",
    "acceptance": "accept",
    "appearance": "appear",
    "assistance": "assist",
    "compliance": "comply",
    "dependence": "depend",
    "existence": "exist",
    "governance": "govern",
    "guidance": "guide",
    "insurance": "insure",
    "persistence": "persist",
    "preference": "prefer",
    "reference": "refer",
    "reliance": "rely",
    "resistance": "resist",
    "tolerance": "tolerate",
    "analysis": "analyze",
    "synthesis": "synthesize",
    "diagnosis": "diagnose",
    "emphasis": "emphasize",
    "hypothesis": "hypothesize",
    "removal": "remove",
    "approval": "approve",
    "arrival": "arrive",
    "denial": "deny",
    "disposal": "dispose",
    "proposal": "propose",
    "refusal": "refuse",
    "renewal": "renew",
    "revival": "revive",
    "survival": "survive",
    "withdrawal": "withdraw",
}

# ─── Subordinating conjunctions ─────────────────────────────
_EN_SUB_CONJ = {
    "although", "though", "even though",
    "while", "whereas", "when", "whenever",
    "if", "unless", "because", "since",
    "after", "before", "until", "once",
    "as soon as", "as long as", "so that",
    "in order that", "provided that",
}

_RU_SUB_CONJ = {
    "хотя", "хоть", "хотя и",
    "когда", "пока", "если",
    "потому что", "так как", "поскольку",
    "после того как", "перед тем как",
    "до того как", "как только",
    "несмотря на то что",
    "в то время как", "тогда как",
    "чтобы", "для того чтобы",
    "если бы", "пока не",
}

_UK_SUB_CONJ = {
    "хоча", "хоч", "хоча й",
    "коли", "поки", "якщо",
    "тому що", "бо", "оскільки",
    "після того як", "перед тим як",
    "до того як", "як тільки",
    "незважаючи на те що",
    "в той час як", "тоді як",
    "щоб", "для того щоб",
    "якби", "поки не",
}

_DE_SUB_CONJ = {
    "obwohl", "obgleich", "obschon",
    "wenn", "als", "falls", "sofern",
    "weil", "da", "nachdem", "bevor",
    "während", "solange", "sobald",
    "bis", "damit", "sodass",
    "seitdem", "ehe", "indem",
}

# ─── English auxiliary verbs ────────────────────────────────
_EN_AUX = {
    "is", "are", "was", "were", "am",
    "has", "have", "had",
    "will", "would", "shall", "should",
    "can", "could", "may", "might",
    "must", "do", "does", "did",
    "being", "been",
}

# ─── Russian passive auxiliaries ────────────────────────────
_RU_PASSIVE_AUX = {
    "был", "была", "было", "были",
    "будет", "будут", "будем",
}

# ─── Tokenizer ──────────────────────────────────────────────
_WORD_RE = re.compile(
    r"[A-Za-z\u00C0-\u024F\u0400-\u04FF"
    r"\u0500-\u052F\u1E00-\u1EFF\u00DF'\-]+"
    r"|[^\s]"
)

_SENT_SPLIT_RE = re.compile(
    r'(?<=[.!?])\s+'
)

# ─── Helpers ────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Split text into word and punctuation tokens."""
    return _WORD_RE.findall(text)

def _capitalize_first(s: str) -> str:
    """Capitalize the first character only."""
    if not s:
        return s
    return s[0].upper() + s[1:]

def _lower_first(s: str) -> str:
    """Lower-case the first character only."""
    if not s:
        return s
    return s[0].lower() + s[1:]

def _strip_trailing_punct(s: str) -> tuple[str, str]:
    """Separate trailing sentence punctuation."""
    s = s.rstrip()
    if s and s[-1] in ".!?":
        return s[:-1].rstrip(), s[-1]
    return s, ""

def _join_tokens(tokens: list[str]) -> str:
    """Join tokens back into text with spacing."""
    if not tokens:
        return ""
    parts: list[str] = [tokens[0]]
    for tok in tokens[1:]:
        if tok in ".,;:!?)]}\"'" or (parts and parts[-1] in "([{\"'"):
            parts.append(tok)
        else:
            parts.append(" " + tok)
    return "".join(parts)

# Verbs that do NOT double final consonant
_NO_DOUBLE = {
    "develop", "open", "listen", "offer",
    "enter", "happen", "visit", "cover",
    "deliver", "consider", "discover",
    "remember", "order", "wander",
    "whisper", "suffer", "differ",
    "gather", "master", "answer",
    "number", "wonder", "encounter",
    "recover", "render", "murder",
    "plaster", "foster", "alter",
    "monitor", "power", "color",
    "flavor", "honor", "labor",
    "favor", "humor", "harbor",
    "limit", "profit", "target",
    "market", "budget", "benefit",
    "credit", "edit", "audit",
    "deposit", "exhibit", "inherit",
    "orbit", "permit", "prohibit",
    "travel", "cancel", "model",
    "channel", "signal", "total",
    "focus", "process", "witness",
    "broadcast", "forecast",
}

def _get_past_participle_en(verb: str) -> str:
    """Get EN past participle for a verb."""
    low = verb.lower()
    if low in _EN_IRREGULAR:
        return _EN_IRREGULAR[low]
    # Regular verbs
    if low.endswith("e"):
        return low + "d"
    if low.endswith("y") and len(low) > 2 and low[-2:] not in (
        "ay", "ey", "oy", "uy",
    ):
        return low[:-1] + "ied"
    # CVC doubling (only for short monosyllables)
    if (
        len(low) > 2
        and low[-1] not in "aeiouxyw"
        and low[-2] in "aeiou"
        and low[-3] not in "aeiou"
        and low not in _NO_DOUBLE
    ):
        return low + low[-1] + "ed"
    return low + "ed"

def _get_past_simple_en(verb: str) -> str:
    """Get EN past simple for a verb."""
    low = verb.lower()
    if low in _EN_PAST_SIMPLE:
        return _EN_PAST_SIMPLE[low]
    return _get_past_participle_en(low)

def _get_gerund_en(verb: str) -> str:
    """Get EN gerund (-ing form) for a verb."""
    low = verb.lower()
    if low == "be":
        return "being"
    if low == "have":
        return "having"
    if low == "die":
        return "dying"
    if low == "lie":
        return "lying"
    if low == "tie":
        return "tying"
    if low.endswith("ie"):
        return low[:-2] + "ying"
    if low.endswith("ee"):
        return low + "ing"
    if low.endswith("e") and len(low) > 2:
        return low[:-1] + "ing"
    if (
        len(low) > 2
        and low[-1] not in "aeiouxyw"
        and low[-2] in "aeiou"
        and low[-3] not in "aeiou"
        and low not in _NO_DOUBLE
    ):
        return low + low[-1] + "ing"
    return low + "ing"

def _base_from_3s(verb: str) -> str:
    """Recover EN base form from 3rd person -s."""
    low = verb.lower()
    if low.endswith("ies") and len(low) > 4:
        return low[:-3] + "y"
    if low.endswith(("shes", "ches", "xes", "sses")):
        return low[:-2]
    if low.endswith("zes") and len(low) > 4:
        return low[:-2]
    if low.endswith("ses") and len(low) > 4:
        return low[:-1]
    if low.endswith("s"):
        return low[:-1]
    return low

def _is_vowel(ch: str) -> bool:
    return ch.lower() in "aeiou"

# ─── detect be-forms ────────────────────────────────────────

_EN_BE_FORMS = {
    "is", "are", "was", "were", "am",
    "be", "been", "being",
}

_EN_HAVE_FORMS = {
    "has", "have", "had", "having",
}

def _pick_be_form(
    subject: str, tense: str = "present",
) -> str:
    """Pick 'is/are/was/were' based on subject."""
    low = subject.lower().strip()
    plural_prons = {"they", "we", "you"}
    singular_prons = {"he", "she", "it", "i"}
    if tense == "past":
        if low in plural_prons or low.endswith("s"):
            return "were"
        return "was"
    # present
    if low in plural_prons:
        return "are"
    if low == "i":
        return "am"
    if low in singular_prons:
        return "is"
    if low.endswith("s") and not low.endswith("ss"):
        return "are"
    return "is"

# ═══════════════════════════════════════════════════════════
# SyntaxRewriter
# ═══════════════════════════════════════════════════════════

class SyntaxRewriter:
    """Rule-based sentence-level syntax rewriter.

    Generates structural variants of sentences
    without changing meaning.

    Parameters
    ----------
    lang : str
        Language code: 'en', 'ru', 'uk', 'de'.
    seed : int | None
        Random seed for deterministic output.
    """

    __slots__ = ("_lang", "_rng", "_tagger")

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self._lang = lang.lower().strip()
        self._tagger = POSTagger(lang=self._lang)
        self._rng = random.Random(seed)

    # ── Public API ────────────────────────────────────────

    @property
    def lang(self) -> str:
        """Return the language code."""
        return self._lang

    def rewrite(
        self,
        sentence: str,
        max_variants: int = 3,
    ) -> list[str]:
        """Generate structural variants of *sentence*.

        Returns up to *max_variants* distinct rewrites.
        If no transformation applies, returns ``[]``.
        """
        if not sentence or not sentence.strip():
            return []

        methods = [
            self.active_to_passive,
            self.passive_to_active,
            self.invert_clauses,
            self.front_adverbial,
            self.reorder_enumeration,
            self._nominalization_to_verb,
            self._gerund_conversion,
            self._split_sentence,
        ]

        variants: list[str] = []
        seen = {sentence.strip()}
        for method in methods:
            if len(variants) >= max_variants:
                break
            try:
                result = method(sentence)
            except Exception:
                continue
            if result and result.strip() not in seen:
                variants.append(result.strip())
                seen.add(result.strip())
        return variants[:max_variants]

    def rewrite_random(self, sentence: str) -> str:
        """Pick one random structural variant.

        Returns original if no transform applies.
        Skips sentences containing placeholders (\x00, THZ_).
        """
        # Skip sentences with placeholders
        if '\x00' in sentence or 'THZ_' in sentence or 'THZ ' in sentence:
            return sentence
        variants = self.rewrite(
            sentence, max_variants=8
        )
        if not variants:
            return sentence
        return self._rng.choice(variants)

    # ── Active → Passive ─────────────────────────────────

    def active_to_passive(
        self, sentence: str,
    ) -> Optional[str]:
        """Convert active voice to passive voice.

        Returns ``None`` if not applicable.
        """
        if self._lang == "en":
            return self._en_active_to_passive(sentence)
        if self._lang == "ru":
            return self._ru_active_to_passive(sentence)
        if self._lang == "uk":
            return self._uk_active_to_passive(sentence)
        if self._lang == "de":
            return self._de_active_to_passive(sentence)
        return None

    # ── Passive → Active ─────────────────────────────────

    def passive_to_active(
        self, sentence: str,
    ) -> Optional[str]:
        """Convert passive voice to active voice.

        Returns ``None`` if not applicable.
        """
        if self._lang == "en":
            return self._en_passive_to_active(sentence)
        if self._lang == "ru":
            return self._ru_passive_to_active(sentence)
        if self._lang == "de":
            return self._de_passive_to_active(sentence)
        return None

    # ── Clause Inversion ─────────────────────────────────

    def invert_clauses(
        self, sentence: str,
    ) -> Optional[str]:
        """Swap main and subordinate clauses.

        Returns ``None`` if not applicable.
        """
        if self._lang == "en":
            return self._invert_with_conj(
                sentence, _EN_SUB_CONJ,
            )
        if self._lang == "ru":
            return self._invert_with_conj(
                sentence, _RU_SUB_CONJ,
            )
        if self._lang == "uk":
            return self._invert_with_conj(
                sentence, _UK_SUB_CONJ,
            )
        if self._lang == "de":
            return self._invert_with_conj(
                sentence, _DE_SUB_CONJ,
            )
        return None

    # ── Front Adverbial ──────────────────────────────────

    def front_adverbial(
        self, sentence: str,
    ) -> Optional[str]:
        """Move adverbial to sentence start.

        Returns ``None`` if not applicable.
        """
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        tokens = _tokenize(body)
        if len(tokens) < 4:
            return None

        tags = self._tagger.tag(body)

        # Strategy 1: Move trailing prepositional phrase
        result = self._front_prep_phrase(
            tokens, tags, punct,
        )
        if result:
            return result

        # Strategy 2: Move single adverb
        result = self._front_single_adverb(
            tokens, tags, punct,
        )
        if result:
            return result

        return None

    # ── Enumeration Reorder ──────────────────────────────

    def reorder_enumeration(
        self, sentence: str,
    ) -> Optional[str]:
        """Reorder items in an enumeration.

        Returns ``None`` if not applicable.
        """
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )

        # Pattern: "X, Y, and Z" or "X, Y and Z"
        # Also: "X, Y, or Z"
        # Items must be single words or short phrases
        m = re.search(
            r'(?:^|[\s,;:])'
            r'(\w+(?:\s+\w+){0,3}?)'
            r',\s+'
            r'(\w+(?:\s+\w+){0,3}?)'
            r',?\s*'
            r'(and|or|und|и|та|і|oder)\s+'
            r'(\w+(?:\s+\w+){0,3}?)\s*$',
            body,
            re.IGNORECASE,
        )
        if not m:
            return None

        # Walk back to find the real start of the
        # first enum item (after a verb or colon)
        raw_a = m.group(1).strip()
        raw_b = m.group(2).strip()
        conj = m.group(3)
        raw_c = m.group(4).strip()

        # If first item is multi-word, trim prefix
        # by taking only last N words matching other
        # items' length
        max_words = max(
            len(raw_b.split()), len(raw_c.split()),
        )
        a_words = raw_a.split()
        if len(a_words) > max_words + 1:
            prefix_part = " ".join(
                a_words[:-(max_words)]
            )
            item_a = " ".join(
                a_words[-(max_words):]
            )
            extra_prefix = body[:m.start()].strip()
            if extra_prefix:
                prefix = (
                    extra_prefix + " " + prefix_part
                )
            else:
                prefix = prefix_part
        else:
            prefix = body[:m.start()].strip()
            item_a = raw_a

        item_b = raw_b
        item_c = raw_c

        items = [item_a, item_b, item_c]
        if any(len(it.split()) > 5 for it in items):
            return None

        # Rotate items
        rotated = [items[2], items[0], items[1]]

        new_enum = (
            f"{rotated[0]}, {rotated[1]}, "
            f"{conj} {rotated[2]}"
        )
        if prefix:
            result = f"{prefix} {new_enum}"
        else:
            result = new_enum
        result = _capitalize_first(result)
        if punct:
            result += punct
        return result

    # ═══════════════════════════════════════════════════════
    # English implementations
    # ═══════════════════════════════════════════════════════

    def _en_active_to_passive(
        self, sentence: str,
    ) -> Optional[str]:
        """EN: Subject Verb Object → Object be PP by Subj."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        tags = self._tagger.tag(body)
        if len(tags) < 3:
            return None

        words = [w for w, _ in tags]
        pos = [t for _, t in tags]

        # Find main verb (skip auxiliaries)
        verb_idx = None
        aux_idx = None
        for i, (w, t) in enumerate(tags):
            low_w = w.lower()
            if t == "VERB" and i > 0:
                if low_w in _EN_AUX:
                    aux_idx = i
                    continue
                verb_idx = i
                break

        # Fallback: if no verb found, look for
        # NOUN-tagged word after subject that
        # could be a verb (e.g. "processes")
        if verb_idx is None:
            for i in range(1, len(tags) - 1):
                w, t = tags[i]
                low_w = w.lower()
                if t != "NOUN":
                    continue
                # Previous must be NOUN/PRON/X
                pt = pos[i - 1]
                if pt not in (
                    "NOUN", "PRON", "X",
                ):
                    continue
                # Next must exist
                nt = pos[i + 1]
                if nt in (
                    "NOUN", "X", "ADJ", "ADV",
                    "DET", "NUM",
                ):
                    # Check if word could be a verb
                    base = _base_from_3s(low_w)
                    if (
                        base != low_w
                        and low_w.endswith("s")
                        and len(low_w) > 3
                    ):
                        verb_idx = i
                        break

        if verb_idx is None:
            return None

        # Subject = tokens before aux or verb
        first_v = (
            aux_idx if aux_idx is not None
            else verb_idx
        )
        subj_tokens = words[:first_v]
        if not subj_tokens:
            return None

        # Check for auxiliary before verb
        aux = None
        tense = "present"
        if aux_idx is not None:
            aux = words[aux_idx].lower()
            if aux in ("was", "were", "did"):
                tense = "past"
            elif aux in (
                "has", "have", "had",
            ):
                tense = "perfect"
        elif verb_idx >= 2:
            prev_w = words[verb_idx - 1].lower()
            if prev_w in _EN_AUX:
                aux = prev_w
                subj_tokens = words[
                    :verb_idx - 1
                ]
                if prev_w in (
                    "was", "were", "did",
                ):
                    tense = "past"
                elif prev_w in (
                    "has", "have", "had",
                ):
                    tense = "perfect"

        # Object = tokens after verb
        # Separate trailing modifiers (ADV, PREP phrases)
        obj_idx_start = verb_idx + 1
        obj_toks: list[str] = []
        mod_toks: list[str] = []
        in_modifier = False
        for j in range(obj_idx_start, len(tags)):
            w_j, t_j = tags[j]
            if not in_modifier and t_j in (
                "NOUN", "DET", "ADJ", "NUM", "X",
            ):
                obj_toks.append(w_j)
            else:
                in_modifier = True
                mod_toks.append(w_j)

        if not obj_toks:
            # Fall back to simple split
            obj_toks = words[verb_idx + 1:]
            mod_toks = []

        if not obj_toks:
            return None

        obj_text = " ".join(obj_toks).strip()
        mod_text = " ".join(mod_toks).strip()
        if not obj_text or len(obj_text) < 2:
            return None

        verb_base = words[verb_idx].lower()

        # Recover base from 3rd person -s
        if verb_base.endswith("s") and not aux:
            verb_base = _base_from_3s(verb_base)
            tense = "present"

        # Recover base from past tense
        past_to_base = {
            v: k for k, v in _EN_PAST_SIMPLE.items()
        }
        if verb_base in past_to_base and not aux:
            verb_base = past_to_base[verb_base]
            tense = "past"

        # Also check -ed regular past
        if (
            verb_base.endswith("ed")
            and not aux
            and verb_base not in _EN_IRREGULAR
        ):
            if verb_base.endswith("ied"):
                verb_base = verb_base[:-3] + "y"
            elif verb_base.endswith("ed"):
                candidate = verb_base[:-2]
                if candidate and len(candidate) > 1:
                    verb_base = candidate
            tense = "past"

        pp = _get_past_participle_en(verb_base)
        subj_text = " ".join(subj_tokens)
        if not subj_text:
            return None

        be = _pick_be_form(obj_text, tense)

        # Build: "Obj be PP [modifier] by Subj"
        passive = (
            f"{_capitalize_first(obj_text)} "
            f"{be} {pp}"
        )
        if mod_text:
            passive += f" {mod_text}"
        passive += (
            f" by {_lower_first(subj_text)}"
        )
        result = passive.rstrip()
        if punct:
            result += punct
        return result

    def _en_passive_to_active(
        self, sentence: str,
    ) -> Optional[str]:
        """EN: Object be PP by Subject → Subj V Obj."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        # Pattern: ... was/were/is/are PP by ...
        m = re.search(
            r'\b(was|were|is|are|am|has been'
            r'|have been|had been)\s+'
            r'(\w+(?:ed|en|wn|ht|lt|pt|ft|nt|ld'
            r'|id|ot|un|ug|et|ut|it|ck|ng|ne'
            r'|de|te|se|ze|ke|ve|rn))'
            r'\s+by\s+',
            body,
            re.IGNORECASE,
        )
        if not m:
            return None

        obj_text = body[:m.start()].strip()
        be_form = m.group(1).lower()
        pp = m.group(2).lower()
        agent = body[m.end():].strip()

        if not obj_text or not agent:
            return None

        # Determine tense
        if be_form in ("was", "were", "had been"):
            tense = "past"
        else:
            tense = "present"

        # Recover base verb from PP
        if pp in _EN_PP_TO_BASE:
            base = _EN_PP_TO_BASE[pp]
        elif pp.endswith("ed"):
            base = pp[:-2] if len(pp) > 4 else pp[:-1]
            if not base:
                base = pp
        else:
            base = pp

        # Conjugate
        if tense == "past":
            verb = _get_past_simple_en(base)
        else:
            # Simple present, match subject
            low_agent = agent.lower().strip()
            words_a = low_agent.split()
            first_a = words_a[0] if words_a else ""
            if first_a in (
                "he", "she", "it",
            ) or (
                not first_a.endswith("s")
                and first_a not in ("i", "we", "they", "you")
            ):
                # 3rd person singular
                if base.endswith(
                    ("sh", "ch", "x", "ss", "o"),
                ):
                    verb = base + "es"
                elif (
                    base.endswith("y")
                    and not base.endswith(
                        ("ay", "ey", "oy", "uy")
                    )
                ):
                    verb = base[:-1] + "ies"
                else:
                    verb = base + "s"
            else:
                verb = base

        result = (
            f"{_capitalize_first(agent)} "
            f"{verb} {_lower_first(obj_text)}"
        )
        result = result.rstrip()
        if punct:
            result += punct
        return result

    # ═══════════════════════════════════════════════════════
    # Russian implementations
    # ═══════════════════════════════════════════════════════

    def _ru_active_to_passive(
        self, sentence: str,
    ) -> Optional[str]:
        """RU: Subj + Verb + Obj → Obj + был + PP + Subj.

        Simplified approach using pattern matching.
        """
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        tags = self._tagger.tag(body)
        if len(tags) < 3:
            return None

        words = [w for w, _ in tags]

        # Find verb
        verb_idx = None
        for i, (_w, t) in enumerate(tags):
            if t == "VERB" and i > 0:
                verb_idx = i
                break
        if verb_idx is None:
            return None

        subj = " ".join(words[:verb_idx])
        verb = words[verb_idx]
        obj_parts = words[verb_idx + 1:]
        if not subj or not obj_parts:
            return None
        obj_text = " ".join(obj_parts)

        # Build passive participle (simplified)
        pp = self._ru_make_passive_pp(verb)
        if not pp:
            return None

        # Pick aux based on PP ending (which encodes
        # the gender/number of the new subject)
        aux = self._ru_aux_from_pp(pp)

        result = (
            f"{_capitalize_first(obj_text)} "
            f"{aux} {pp} "
            f"{_lower_first(subj)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    @staticmethod
    def _ru_make_passive_pp(verb: str) -> Optional[str]:
        """Build RU passive past participle."""
        low = verb.lower()
        # -ать → -ан(а/о/ы)
        if low.endswith("ал") or low.endswith("ала"):
            stem = re.sub(r'ала?$', '', low)
            return stem + "ана"
        if low.endswith("ать"):
            stem = low[:-3]
            return stem + "ана"
        # -ить → -ен(а/о/ы)
        if low.endswith("ил") or low.endswith("ила"):
            stem = re.sub(r'ила?$', '', low)
            return stem + "ена"
        if low.endswith("ить"):
            stem = low[:-3]
            return stem + "ена"
        # -овать → -ован(а)
        if low.endswith("овал") or low.endswith("овала"):
            stem = re.sub(r'овала?$', '', low)
            return stem + "ована"
        if low.endswith("овать"):
            stem = low[:-5]
            return stem + "ована"
        # -еть → -ена
        if low.endswith("ел") or low.endswith("ела"):
            stem = re.sub(r'ела?$', '', low)
            return stem + "ена"
        if low.endswith("еть"):
            stem = low[:-3]
            return stem + "ена"
        return None

    @staticmethod
    def _ru_pick_passive_aux(obj_text: str) -> str:
        """Choose была/был/было/были for RU passive."""
        low = obj_text.lower().strip()
        last_word = low.split()[-1] if low.split() else ""
        if last_word.endswith("а") or last_word.endswith("я"):
            return "была"
        if last_word.endswith("о") or last_word.endswith("е"):
            return "было"
        if last_word.endswith(("ы", "и")):
            return "были"
        return "был"

    @staticmethod
    def _ru_aux_from_pp(pp: str) -> str:
        """Pick RU passive aux matching the PP ending."""
        low = pp.lower()
        if low.endswith("ана") or low.endswith("ена"):
            return "была"
        if low.endswith("ано") or low.endswith("ено"):
            return "было"
        if low.endswith(("аны", "ены")):
            return "были"
        return "был"

    def _ru_passive_to_active(
        self, sentence: str,
    ) -> Optional[str]:
        """RU: convert passive to active voice."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        # Pattern: Obj + был/была/было/были + PP + agent
        m = re.search(
            r'^(.+?)\s+'
            r'(был[аои]?)\s+'
            r'(\S+(?:ан[аоы]?|ен[аоы]?'
            r'|ован[аоы]?))\s+'
            r'(.+)$',
            body,
            re.IGNORECASE,
        )
        if not m:
            return None

        obj_text = m.group(1).strip()
        pp = m.group(3)
        agent = m.group(4).strip()

        # Recover verb (simplified)
        low_pp = pp.lower()
        if "ован" in low_pp:
            stem = re.sub(r'ован[аоы]?$', '', low_pp)
            verb = stem + "овал"
        elif "ан" in low_pp:
            stem = re.sub(r'ан[аоы]?$', '', low_pp)
            verb = stem + "ал"
        elif "ен" in low_pp:
            stem = re.sub(r'ен[аоы]?$', '', low_pp)
            verb = stem + "ил"
        else:
            return None

        # Determine verb ending from agent gender
        low_agent = agent.lower().strip()
        last_a = low_agent.split()[-1] if low_agent else ""
        if (
            last_a.endswith("а")
            or last_a.endswith("я")
        ) and (verb.endswith("ал") or verb.endswith("ил")):
            verb = verb + "а"

        result = (
            f"{_capitalize_first(agent)} "
            f"{verb} {_lower_first(obj_text)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    # ═══════════════════════════════════════════════════════
    # Ukrainian implementations
    # ═══════════════════════════════════════════════════════

    def _uk_active_to_passive(
        self, sentence: str,
    ) -> Optional[str]:
        """UK: Subj + Verb + Obj → Obj + був + PP + Subj."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        tags = self._tagger.tag(body)
        if len(tags) < 3:
            return None

        words = [w for w, _ in tags]

        verb_idx = None
        for i, (_w, t) in enumerate(tags):
            if t == "VERB" and i > 0:
                verb_idx = i
                break
        if verb_idx is None:
            return None

        subj = " ".join(words[:verb_idx])
        verb = words[verb_idx]
        obj_parts = words[verb_idx + 1:]
        if not subj or not obj_parts:
            return None
        obj_text = " ".join(obj_parts)

        pp = self._uk_make_passive_pp(verb)
        if not pp:
            return None

        aux = self._uk_pick_passive_aux(obj_text)

        result = (
            f"{_capitalize_first(obj_text)} "
            f"{aux} {pp} "
            f"{_lower_first(subj)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    @staticmethod
    def _uk_make_passive_pp(verb: str) -> Optional[str]:
        """Build UK passive past participle."""
        low = verb.lower()
        if low.endswith("ав") or low.endswith("ала"):
            stem = re.sub(r'а[вл]а?$', '', low)
            return stem + "ана"
        if low.endswith("ати"):
            stem = low[:-3]
            return stem + "ана"
        if low.endswith("ив") or low.endswith("ила"):
            stem = re.sub(r'и[вл]а?$', '', low)
            return stem + "ена"
        if low.endswith("ити"):
            stem = low[:-3]
            return stem + "ена"
        if low.endswith("ував") or low.endswith("увала"):
            stem = re.sub(r'ува[вл]а?$', '', low)
            return stem + "увана"
        if low.endswith("увати"):
            stem = low[:-5]
            return stem + "увана"
        return None

    @staticmethod
    def _uk_pick_passive_aux(obj_text: str) -> str:
        """Choose була/був/було/були for UK passive."""
        low = obj_text.lower().strip()
        last = low.split()[-1] if low.split() else ""
        if last.endswith("а") or last.endswith("я"):
            return "була"
        if last.endswith("о") or last.endswith("е"):
            return "було"
        if last.endswith(("и", "і")):
            return "були"
        return "був"

    # ═══════════════════════════════════════════════════════
    # German implementations
    # ═══════════════════════════════════════════════════════

    def _de_active_to_passive(
        self, sentence: str,
    ) -> Optional[str]:
        """DE: Subj + Verb + Obj → Obj + wurde + PP + von.

        German passive uses 'wurde' + Partizip II.
        """
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        tags = self._tagger.tag(body)
        if len(tags) < 3:
            return None

        words = [w for w, _ in tags]

        # German V2: verb is usually at position 1
        verb_idx = None
        for i, (_w, t) in enumerate(tags):
            if t == "VERB" and i > 0:
                verb_idx = i
                break
        if verb_idx is None:
            return None

        subj = " ".join(words[:verb_idx])
        verb = words[verb_idx]
        obj_parts = words[verb_idx + 1:]
        if not subj or not obj_parts:
            return None
        obj_text = " ".join(obj_parts)

        # Build Partizip II
        pp = self._de_make_partizip2(verb)

        result = (
            f"{_capitalize_first(obj_text)} "
            f"wurde {pp} von "
            f"{_lower_first(subj)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    @staticmethod
    def _de_make_partizip2(verb: str) -> str:
        """Build German Partizip II (simplified)."""
        low = verb.lower()
        # Already a participle? ge-...-t/en
        if low.startswith("ge"):
            return low
        # -ieren → -iert (no ge- prefix)
        if low.endswith("ieren"):
            return low[:-2] + "t"
        if low.endswith("iert"):
            return low
        if low.endswith("ierte"):
            return low[:-1]
        # Strong: stem + ge-...-en (simplified)
        # Weak: ge- + stem + -t
        if low.endswith("en"):
            stem = low[:-2]
        elif low.endswith("n"):
            stem = low[:-1]
        elif low.endswith("t"):
            # Possibly conjugated already
            stem = low[:-1]
            if stem.endswith("e"):
                stem = stem[:-1]
        elif low.endswith("te"):
            stem = low[:-2]
        else:
            stem = low
        return "ge" + stem + "t"

    def _de_passive_to_active(
        self, sentence: str,
    ) -> Optional[str]:
        """DE: Obj wurde PP von Subj → Subj V Obj."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        m = re.search(
            r'^(.+?)\s+'
            r'(?:wurde|wurden|wird|werden)\s+'
            r'(\S+)\s+'
            r'von\s+(.+)$',
            body,
            re.IGNORECASE,
        )
        if not m:
            return None

        obj_text = m.group(1).strip()
        pp = m.group(2).strip()
        agent = m.group(3).strip()

        # Recover infinitive from Partizip II
        low_pp = pp.lower()
        if low_pp.startswith("ge"):
            stem = low_pp[2:]
            if stem.endswith("t"):
                verb = stem[:-1] + "en"
            elif stem.endswith("en"):
                verb = stem
            else:
                verb = stem + "en"
        elif low_pp.endswith("iert"):
            verb = low_pp[:-1] + "en"
        else:
            verb = low_pp + "en"

        # German V2: verb second
        result = (
            f"{_capitalize_first(agent)} "
            f"{verb} {_lower_first(obj_text)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    # ═══════════════════════════════════════════════════════
    # Clause inversion (all languages)
    # ═══════════════════════════════════════════════════════

    def _invert_with_conj(
        self,
        sentence: str,
        conjunctions: set,
    ) -> Optional[str]:
        """Swap subordinate + main clause around comma."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        low = body.lower()

        # Case 1: subordinate clause at the start
        # "Although X, Y" → "Y, although X"
        for conj in sorted(
            conjunctions, key=len, reverse=True,
        ):
            if low.startswith(conj + " "):
                clen = len(conj)
                rest = body[clen:].strip()
                comma_idx = rest.find(",")
                if comma_idx == -1:
                    continue
                sub_clause = rest[:comma_idx].strip()
                main_clause = rest[comma_idx + 1:].strip()
                if not main_clause:
                    continue
                # Preserve original case of conjunction
                orig_conj = body[:clen]
                result = (
                    f"{_capitalize_first(main_clause)}"
                    f", {orig_conj.lower()} "
                    f"{sub_clause}"
                )
                if punct:
                    result = result.rstrip() + punct
                return result

        # Case 2: subordinate clause at the end
        # "Y, although X" → "Although X, Y"
        for conj in sorted(
            conjunctions, key=len, reverse=True,
        ):
            patt = re.compile(
                r'^(.+?),\s*'
                + re.escape(conj)
                + r'\s+(.+)$',
                re.IGNORECASE,
            )
            m = patt.match(body)
            if m:
                main_clause = m.group(1).strip()
                sub_clause = m.group(2).strip()
                if not sub_clause:
                    continue
                result = (
                    f"{_capitalize_first(conj)} "
                    f"{sub_clause}, "
                    f"{_lower_first(main_clause)}"
                )
                if punct:
                    result = result.rstrip() + punct
                return result

        # Case 3: no comma — conjunction mid-sentence
        # "They went outside because it stopped"
        # → "Because it stopped, they went outside"
        for conj in sorted(
            conjunctions, key=len, reverse=True,
        ):
            patt = re.compile(
                r'^(.+?)\s+'
                + re.escape(conj)
                + r'\s+(.+)$',
                re.IGNORECASE,
            )
            m = patt.match(body)
            if m:
                main_clause = m.group(1).strip()
                sub_clause = m.group(2).strip()
                if (
                    len(main_clause.split()) < 2
                    or len(sub_clause.split()) < 2
                ):
                    continue
                result = (
                    f"{_capitalize_first(conj)} "
                    f"{sub_clause}, "
                    f"{_lower_first(main_clause)}"
                )
                if punct:
                    result = result.rstrip() + punct
                return result

        return None

    # ═══════════════════════════════════════════════════════
    # Front adverbial helpers
    # ═══════════════════════════════════════════════════════

    def _front_prep_phrase(
        self,
        tokens: list[str],
        tags: list[tuple[str, str]],
        punct: str,
    ) -> Optional[str]:
        """Move a trailing prepositional phrase to front."""
        pos = [t for _, t in tags]

        # Find last PREP in the sentence
        prep_idx = None
        for i in range(len(pos) - 1, 0, -1):
            if pos[i] == "PREP":
                prep_idx = i
                break
        if prep_idx is None:
            return None

        # Prep phrase must be at least 2 tokens
        # and start after halfway
        if prep_idx < len(tokens) // 2:
            return None
        pp_tokens = tokens[prep_idx:]
        if len(pp_tokens) < 2:
            return None

        main_tokens = tokens[:prep_idx]
        if len(main_tokens) < 2:
            return None

        pp_text = _join_tokens(pp_tokens)
        main_text = _join_tokens(main_tokens)

        result = (
            f"{_capitalize_first(pp_text)}, "
            f"{_lower_first(main_text)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    def _front_single_adverb(
        self,
        tokens: list[str],
        tags: list[tuple[str, str]],
        punct: str,
    ) -> Optional[str]:
        """Move a single adverb to sentence front."""
        pos = [t for _, t in tags]

        # Find an ADV that is NOT the first token
        adv_idx = None
        for i in range(1, len(pos)):
            if pos[i] == "ADV" and i < len(tokens) - 1:
                adv_idx = i
                break
        if adv_idx is None:
            return None

        adverb = tokens[adv_idx]
        rest = tokens[:adv_idx] + tokens[adv_idx + 1:]
        if len(rest) < 2:
            return None

        rest_text = _join_tokens(rest)
        result = (
            f"{_capitalize_first(adverb)}, "
            f"{_lower_first(rest_text)}"
        )
        if punct:
            result = result.rstrip() + punct
        return result

    # ═══════════════════════════════════════════════════════
    # Nominalization → Verb
    # ═══════════════════════════════════════════════════════

    def _nominalization_to_verb(
        self, sentence: str,
    ) -> Optional[str]:
        """Convert 'the X-tion of Y' → 'X-ing Y'."""
        if self._lang != "en":
            return self._nom_generic(sentence)

        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        # Pattern: "the <nominalization> of <NP>"
        m = re.search(
            r'\b[Tt]he\s+(\w+)\s+of\s+(.+?)(?:\s*$)',
            body,
        )
        if not m:
            return None

        nom = m.group(1).lower()
        np_text = m.group(2).strip()

        # Explicit lookup
        verb = _EN_NOMINALIZATION.get(nom)

        # Suffix-based fallback
        if not verb:
            verb = self._nom_suffix_to_verb(nom)
        if not verb:
            return None

        gerund = _get_gerund_en(verb)
        prefix = body[:m.start()].strip()
        suffix = ""

        new_phrase = f"{gerund} {np_text}"
        if prefix:
            result = f"{prefix} {new_phrase}"
        else:
            result = _capitalize_first(new_phrase)

        if suffix:
            result += " " + suffix
        if punct:
            result = result.rstrip() + punct
        return result

    @staticmethod
    def _nom_suffix_to_verb(nom: str) -> Optional[str]:
        """Derive verb from nominalization suffix."""
        low = nom.lower()
        # -ization → -ize
        if low.endswith("ization"):
            return low[:-7] + "ize"
        # -isation → -ise
        if low.endswith("isation"):
            return low[:-7] + "ise"
        # -ication → -icate (rare) or -ify
        if low.endswith("ification"):
            return low[:-9] + "ify"
        # -ation → -ate
        if low.endswith("ation") and len(low) > 6:
            return low[:-5] + "ate"
        # -tion → remove (less reliable)
        if low.endswith("tion") and len(low) > 6:
            stem = low[:-4]
            if stem.endswith("c"):
                return stem + "e"
            if stem.endswith("u"):
                return stem + "te"
            return stem + "e"
        # -ment → remove
        if low.endswith("ment") and len(low) > 6:
            return low[:-4]
        # -ance/-ence → various
        if low.endswith("ance") and len(low) > 6:
            return low[:-4]
        if low.endswith("ence") and len(low) > 6:
            return low[:-4]
        # -al → remove
        if low.endswith("al") and len(low) > 5:
            return low[:-2] + "e"
        return None

    def _nom_generic(
        self, sentence: str,
    ) -> Optional[str]:
        """Nominalization for non-EN (placeholder)."""
        return None

    # ═══════════════════════════════════════════════════════
    # Gerund conversion
    # ═══════════════════════════════════════════════════════

    def _gerund_conversion(
        self, sentence: str,
    ) -> Optional[str]:
        """Convert 'Subj V1, Subj V2' → 'V1-ing, Subj V2'.

        Works by detecting two clauses sharing a subject.
        """
        if self._lang != "en":
            return self._gerund_generic(sentence)

        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        # Split into two sentences
        parts = _SENT_SPLIT_RE.split(body, maxsplit=1)
        if len(parts) < 2:
            # Try splitting at comma
            comma_idx = body.find(",")
            if comma_idx == -1:
                return None
            parts = [
                body[:comma_idx],
                body[comma_idx + 1:],
            ]

        s1 = parts[0].strip().rstrip(".")
        s2 = parts[1].strip().rstrip(".")
        if not s1 or not s2:
            return None

        tags1 = self._tagger.tag(s1)
        tags2 = self._tagger.tag(s2)
        if len(tags1) < 2 or len(tags2) < 2:
            return None

        words1 = [w for w, _ in tags1]
        words2 = [w for w, _ in tags2]

        # Check if subjects match (first word or two)
        subj1 = words1[0].lower()
        subj2 = words2[0].lower()

        if subj1 != subj2:
            # Also try "he/she/it/they" == original subj
            pron_map = {
                "he", "she", "it", "they",
                "we", "i", "you",
            }
            if subj2 not in pron_map:
                return None

        # Find verb in first clause
        v_idx1 = None
        for i, (_w, t) in enumerate(tags1):
            if t == "VERB" and i > 0:
                v_idx1 = i
                break
        if v_idx1 is None:
            return None

        verb1 = words1[v_idx1].lower()
        # Skip auxiliaries
        if verb1 in _EN_AUX:
            return None

        gerund = _get_gerund_en(verb1)
        rest1 = _join_tokens(words1[v_idx1 + 1:])

        # Build: "Having/Gerund ... , subj ..."
        gerund_phrase = _capitalize_first(gerund)
        if rest1:
            gerund_phrase += " " + rest1

        # Use second clause as main
        main = _join_tokens(words2)
        if subj2.lower() == subj1.lower():
            main = _capitalize_first(main)
        else:
            main = _lower_first(main)

        result = f"{gerund_phrase}, {main}"
        if punct:
            result = result.rstrip() + punct
        return result

    def _gerund_generic(
        self, sentence: str,
    ) -> Optional[str]:
        """Gerund conversion for non-EN."""
        if self._lang != "ru":
            return None
        return self._ru_deeprichastie(sentence)

    def _ru_deeprichastie(
        self, sentence: str,
    ) -> Optional[str]:
        """RU: combine with деепричастие.

        "Он открыл дверь. Он вошёл." →
        "Открыв дверь, он вошёл."
        """
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        parts = _SENT_SPLIT_RE.split(body, maxsplit=1)
        if len(parts) < 2:
            return None

        s1 = parts[0].strip().rstrip(".")
        s2 = parts[1].strip().rstrip(".")
        if not s1 or not s2:
            return None

        tags1 = self._tagger.tag(s1)
        if len(tags1) < 2:
            return None

        words1 = [w for w, _ in tags1]

        verb_idx = None
        for i, (_w, t) in enumerate(tags1):
            if t == "VERB" and i > 0:
                verb_idx = i
                break
        if verb_idx is None:
            return None

        verb = words1[verb_idx].lower()
        # Build деепричастие (simplified)
        deep = self._ru_make_deeprichastie(verb)
        if not deep:
            return None

        rest1 = " ".join(words1[verb_idx + 1:])
        dp_phrase = _capitalize_first(deep)
        if rest1:
            dp_phrase += " " + rest1

        result = f"{dp_phrase}, {_lower_first(s2)}"
        if punct:
            result = result.rstrip() + punct
        return result

    @staticmethod
    def _ru_make_deeprichastie(
        verb: str,
    ) -> Optional[str]:
        """Build RU деепричастие (совершенный вид)."""
        low = verb.lower()
        # Past perfective: -ал → -ав
        if low.endswith("ал"):
            return low[:-2] + "ав"
        if low.endswith("ала"):
            return low[:-3] + "ав"
        # -ил → -ив
        if low.endswith("ил"):
            return low[:-2] + "ив"
        if low.endswith("ила"):
            return low[:-3] + "ив"
        # -ел → -ев
        if low.endswith("ел"):
            return low[:-2] + "ев"
        if low.endswith("ела"):
            return low[:-3] + "ев"
        return None

    # ═══════════════════════════════════════════════════════
    # Sentence splitting
    # ═══════════════════════════════════════════════════════

    def _split_sentence(
        self, sentence: str,
    ) -> Optional[str]:
        """Split long sentence at conjunction boundary."""
        body, punct = _strip_trailing_punct(
            sentence.strip()
        )
        if not punct:
            punct = "."

        words = body.split()
        if len(words) < 15:
            return None

        # Try splitting at coordinating conjunctions
        split_words = self._get_split_words()
        best_idx = None
        best_dist = 0
        for i, w in enumerate(words):
            if w.lower().rstrip(",") in split_words:
                dist = min(i, len(words) - i)
                if dist > best_dist and dist >= 4:
                    best_dist = dist
                    best_idx = i

        if best_idx is None:
            return None

        conj = words[best_idx].lower().rstrip(",")
        first_half = " ".join(words[:best_idx])
        second_half = " ".join(
            words[best_idx + 1:]
        )
        first_half = first_half.rstrip(",").strip()
        second_half = second_half.strip()

        if not first_half or not second_half:
            return None

        # Add transition based on conjunction
        transitions = {
            "and": "Also,",
            "but": "However,",
            "yet": "Nevertheless,",
            "however": "Meanwhile,",
            "which": "It",
            "that": "This",
            "и": "Также",
            "а": "При этом",
            "но": "Однако",
            "und": "Außerdem",
            "aber": "Jedoch",
            "та": "Також",
            "але": "Проте",
            "і": "Також",
        }
        trans = transitions.get(conj, "")

        s1 = _capitalize_first(first_half) + punct
        if trans:
            s2 = (
                f"{trans} "
                f"{_lower_first(second_half)}"
            )
        else:
            s2 = _capitalize_first(second_half)
        s2 = s2.rstrip() + punct

        return f"{s1} {s2}"

    def _get_split_words(self) -> set:
        """Get conjunction words suitable for splitting."""
        if self._lang == "en":
            return {
                "and", "but", "yet", "however",
                "which", "although",
            }
        if self._lang == "ru":
            return {
                "и", "а", "но", "однако",
                "который", "хотя",
            }
        if self._lang == "uk":
            return {
                "і", "та", "але", "однак",
                "який", "хоча",
            }
        if self._lang == "de":
            return {
                "und", "aber", "jedoch", "doch",
                "obwohl",
            }
        return {"and", "but"}

    # ── repr ──────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SyntaxRewriter(lang={self._lang!r})"
        )
