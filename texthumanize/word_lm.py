"""Word-level language model for perplexity computation.

Unigram/bigram model with pre-built frequency tables for
14 languages. Replaces character-trigram perplexity with
real word-level measurement.

Usage:
    from texthumanize.word_lm import WordLanguageModel

    lm = WordLanguageModel(lang="en")
    pp = lm.perplexity("The quick brown fox jumps")
    score = lm.naturalness_score("Some text here")
"""

from __future__ import annotations

import math
import re
from typing import Any

# ── Frequency tables ──────────────────────────────────────
# Top unigram frequencies (word → probability).
# Sources: Google n-grams, Wikipedia word counts.

_EN_UNI: dict[str, float] = {
    "the": 0.069, "be": 0.036, "to": 0.026,
    "of": 0.025, "and": 0.023, "a": 0.021,
    "in": 0.019, "that": 0.010, "have": 0.009,
    "i": 0.008, "it": 0.008, "for": 0.008,
    "not": 0.006, "on": 0.006, "with": 0.006,
    "he": 0.005, "as": 0.005, "you": 0.005,
    "do": 0.005, "at": 0.004, "this": 0.004,
    "but": 0.004, "his": 0.003, "by": 0.003,
    "from": 0.003, "they": 0.003, "we": 0.003,
    "say": 0.002, "her": 0.002, "she": 0.002,
    "or": 0.002, "an": 0.002, "will": 0.002,
    "my": 0.002, "one": 0.002, "all": 0.002,
    "would": 0.002, "there": 0.002, "their": 0.002,
    "what": 0.001, "so": 0.001, "up": 0.001,
    "out": 0.001, "if": 0.001, "about": 0.001,
    "who": 0.001, "get": 0.001, "which": 0.001,
    "go": 0.001, "me": 0.001, "when": 0.001,
    "make": 0.001, "can": 0.001, "like": 0.001,
    "time": 0.001, "no": 0.001, "just": 0.001,
    "him": 0.001, "know": 0.001, "take": 0.001,
    "people": 0.0009, "into": 0.0009,
    "year": 0.0009, "your": 0.0009,
    "good": 0.0008, "some": 0.0008,
    "could": 0.0008, "them": 0.0008,
    "see": 0.0008, "other": 0.0008,
    "than": 0.0008, "then": 0.0008,
    "now": 0.0007, "look": 0.0007,
    "only": 0.0007, "come": 0.0007,
    "its": 0.0007, "over": 0.0007,
    "think": 0.0007, "also": 0.0007,
    "back": 0.0007, "after": 0.0007,
    "use": 0.0006, "two": 0.0006,
    "how": 0.0006, "our": 0.0006,
    "work": 0.0006, "first": 0.0006,
    "well": 0.0006, "way": 0.0006,
    "even": 0.0006, "new": 0.0006,
    "want": 0.0005, "because": 0.0005,
    "any": 0.0005, "these": 0.0005,
    "give": 0.0005, "day": 0.0005,
    "most": 0.0005, "us": 0.0005,
    "is": 0.008, "are": 0.003,
    "was": 0.004, "were": 0.001,
    "been": 0.001, "being": 0.0004,
    "has": 0.002, "had": 0.002,
    "should": 0.0006,
    "may": 0.0005, "might": 0.0004,
    "must": 0.0004, "shall": 0.0002,
    "very": 0.0005, "much": 0.0004,
    "more": 0.0007, "many": 0.0004,
    "such": 0.0004, "each": 0.0003,
    "own": 0.0003, "same": 0.0003,
    "while": 0.0004, "where": 0.0004,
    "before": 0.0004, "between": 0.0003,
    "still": 0.0004, "through": 0.0004,
    "long": 0.0003, "great": 0.0003,
    "small": 0.0002, "large": 0.0002,
    "never": 0.0003, "always": 0.0003,
    "those": 0.0003, "both": 0.0003,
    "life": 0.0003, "world": 0.0003,
    "hand": 0.0003, "high": 0.0003,
    "part": 0.0003, "place": 0.0003,
    "case": 0.0003, "point": 0.0003,
    "group": 0.0002, "number": 0.0003,
    "however": 0.0003, "system": 0.0002,
    "end": 0.0002,
    "during": 0.0003, "away": 0.0002,
    "under": 0.0003, "last": 0.0003,
    "right": 0.0003, "old": 0.0003,
    "big": 0.0002, "few": 0.0003,
    "left": 0.0002, "man": 0.0003,
    "found": 0.0002, "head": 0.0002,
    "house": 0.0002, "country": 0.0002,
    "school": 0.0002, "state": 0.0002,
    "family": 0.0002, "water": 0.0002,
    "city": 0.0002, "since": 0.0003,
    "home": 0.0002, "thing": 0.0003,
    "name": 0.0002, "another": 0.0002,
    "need": 0.0003,
    "again": 0.0003, "seem": 0.0002,
    "help": 0.0002, "show": 0.0002,
    "turn": 0.0002, "move": 0.0002,
    "live": 0.0002, "find": 0.0003,
    "here": 0.0003, "something": 0.0002,
    "tell": 0.0002, "keep": 0.0002,
    "let": 0.0002, "begin": 0.0002,
    "though": 0.0002, "too": 0.0003,
    "child": 0.0002, "side": 0.0002,
    "call": 0.0002, "different": 0.0002,
    "put": 0.0002, "read": 0.0002,
    "ask": 0.0002, "change": 0.0002,
    "play": 0.0002, "run": 0.0002,
    "without": 0.0002, "against": 0.0002,
    "important": 0.0002, "until": 0.0002,
    "start": 0.0002, "try": 0.0002,
    "fact": 0.0002, "already": 0.0002,
    "problem": 0.0002, "enough": 0.0002,
    "often": 0.0002, "result": 0.0002,
    "quite": 0.0002, "rather": 0.0002,
    "really": 0.0002, "almost": 0.0002,
    "among": 0.0002, "example": 0.0002,
    "several": 0.0002, "area": 0.0001,
    "power": 0.0002, "far": 0.0002,
    "perhaps": 0.0001, "company": 0.0001,
    "possible": 0.0001, "best": 0.0002,
    "next": 0.0002, "level": 0.0001,
}

_EN_BI: dict[tuple[str, str], float] = {
    ("of", "the"): 0.0035, ("in", "the"): 0.0030,
    ("to", "the"): 0.0015, ("on", "the"): 0.0010,
    ("to", "be"): 0.0012, ("it", "is"): 0.0010,
    ("it", "was"): 0.0008, ("i", "have"): 0.0005,
    ("do", "not"): 0.0006, ("will", "be"): 0.0005,
    ("for", "the"): 0.0008, ("at", "the"): 0.0006,
    ("with", "the"): 0.0005, ("from", "the"): 0.0004,
    ("and", "the"): 0.0006, ("by", "the"): 0.0004,
    ("this", "is"): 0.0005, ("that", "the"): 0.0004,
    ("he", "was"): 0.0004, ("she", "was"): 0.0003,
    ("there", "is"): 0.0003, ("there", "are"): 0.0003,
    ("has", "been"): 0.0004, ("have", "been"): 0.0003,
    ("can", "be"): 0.0003, ("would", "be"): 0.0002,
    ("i", "am"): 0.0003, ("i", "was"): 0.0003,
    ("as", "a"): 0.0003, ("such", "as"): 0.0002,
    ("one", "of"): 0.0003, ("part", "of"): 0.0002,
    ("out", "of"): 0.0002, ("some", "of"): 0.0002,
    ("all", "the"): 0.0002, ("a", "lot"): 0.0002,
    ("going", "to"): 0.0002, ("used", "to"): 0.0002,
    ("able", "to"): 0.0002, ("want", "to"): 0.0002,
    ("need", "to"): 0.0002, ("have", "to"): 0.0003,
    ("had", "been"): 0.0002, ("would", "have"): 0.0002,
    ("could", "have"): 0.0002, ("should", "have"): 0.0001,
    ("did", "not"): 0.0003, ("was", "not"): 0.0002,
    ("is", "not"): 0.0002, ("are", "not"): 0.0002,
    ("not", "be"): 0.0001, ("not", "have"): 0.0001,
    ("may", "be"): 0.0002, ("might", "be"): 0.0001,
    ("so", "that"): 0.0001, ("in", "order"): 0.0001,
    ("as", "well"): 0.0002, ("well", "as"): 0.0001,
    ("more", "than"): 0.0002, ("less", "than"): 0.0001,
    ("most", "of"): 0.0001, ("each", "other"): 0.0001,
    ("up", "to"): 0.0001, ("a", "new"): 0.0002,
    ("the", "first"): 0.0002, ("the", "same"): 0.0002,
    ("at", "least"): 0.0002, ("the", "most"): 0.0001,
    ("the", "world"): 0.0001, ("new", "york"): 0.0001,
    ("it", "has"): 0.0002, ("they", "are"): 0.0003,
    ("we", "have"): 0.0002, ("you", "can"): 0.0002,
    ("i", "think"): 0.0002, ("i", "know"): 0.0002,
    ("he", "had"): 0.0002, ("she", "had"): 0.0001,
    ("they", "had"): 0.0002, ("they", "were"): 0.0002,
    ("we", "are"): 0.0002, ("you", "are"): 0.0002,
    ("he", "is"): 0.0002, ("who", "is"): 0.0001,
    ("what", "is"): 0.0002, ("that", "is"): 0.0002,
    ("which", "is"): 0.0001, ("there", "was"): 0.0003,
    ("there", "were"): 0.0002, ("when", "the"): 0.0001,
    ("if", "you"): 0.0002, ("if", "the"): 0.0001,
    ("but", "the"): 0.0001, ("but", "i"): 0.0001,
    ("but", "it"): 0.0001, ("and", "i"): 0.0001,
    ("and", "it"): 0.0001, ("and", "a"): 0.0001,
}

_RU_UNI: dict[str, float] = {
    "в": 0.032, "и": 0.028, "не": 0.018,
    "на": 0.016, "что": 0.013, "я": 0.011,
    "с": 0.010, "он": 0.009, "а": 0.008,
    "как": 0.007, "это": 0.007, "по": 0.006,
    "но": 0.005, "она": 0.005, "к": 0.005,
    "за": 0.004, "от": 0.004, "его": 0.004,
    "все": 0.004, "так": 0.003, "они": 0.003,
    "же": 0.003, "у": 0.003, "бы": 0.003,
    "из": 0.003, "мы": 0.003, "для": 0.003,
    "вы": 0.002, "при": 0.002, "ее": 0.002,
    "нет": 0.002, "уже": 0.002, "мне": 0.002,
    "вот": 0.002, "был": 0.003, "было": 0.002,
    "быть": 0.002, "есть": 0.002, "этот": 0.002,
    "тот": 0.002, "свой": 0.002, "весь": 0.002,
    "который": 0.002, "только": 0.002,
    "можно": 0.002, "надо": 0.001,
    "себя": 0.001, "когда": 0.001,
    "если": 0.001, "будет": 0.001,
    "были": 0.001, "нас": 0.001,
    "них": 0.001, "чем": 0.001,
    "где": 0.001, "тут": 0.001,
    "очень": 0.001, "даже": 0.001,
    "после": 0.001, "до": 0.001,
    "без": 0.001, "между": 0.001,
    "потом": 0.001, "ещё": 0.001,
    "раз": 0.001, "сам": 0.001,
    "может": 0.001, "нужно": 0.001,
    "об": 0.001, "через": 0.001,
    "день": 0.001, "время": 0.001,
    "год": 0.001, "дело": 0.001,
    "жизнь": 0.001, "рука": 0.001,
    "место": 0.001, "человек": 0.001,
    "стал": 0.001, "такой": 0.001,
    "другой": 0.001, "новый": 0.001,
    "первый": 0.001, "большой": 0.001,
    "хороший": 0.0008, "один": 0.001,
    "два": 0.0008, "три": 0.0005,
    "много": 0.0008, "мало": 0.0005,
    "говорить": 0.001, "знать": 0.001,
    "думать": 0.0008, "делать": 0.0008,
    "видеть": 0.0007, "хотеть": 0.0007,
    "идти": 0.0007, "стоять": 0.0006,
    "дать": 0.0006, "работа": 0.0006,
    "слово": 0.0006, "дом": 0.0006,
    "глаз": 0.0005, "голова": 0.0005,
    "тоже": 0.0008, "также": 0.0007,
    "потому": 0.0006, "однако": 0.0005,
    "всегда": 0.0006, "никогда": 0.0004,
    "часто": 0.0004, "сейчас": 0.0005,
    "теперь": 0.0005, "здесь": 0.0005,
    "там": 0.0006, "тогда": 0.0005,
    "более": 0.0005, "менее": 0.0003,
    "каждый": 0.0004, "должен": 0.0005,
    "сказать": 0.0008, "стать": 0.0006,
    "именно": 0.0004, "просто": 0.0005,
    "наш": 0.0005, "ваш": 0.0003,
    "мой": 0.0004, "свою": 0.0003,
    "того": 0.0004, "чтобы": 0.001,
    "перед": 0.0005, "вместе": 0.0003,
    "конечно": 0.0003, "правда": 0.0003,
    "лучше": 0.0003, "снова": 0.0003,
    "против": 0.0003, "вокруг": 0.0002,
    "стране": 0.0003, "город": 0.0003,
    "система": 0.0003, "развитие": 0.0003,
    "данный": 0.0003, "следует": 0.0003,
    "является": 0.0004, "процесс": 0.0002,
    "результат": 0.0002, "случай": 0.0003,
    "вопрос": 0.0003, "образ": 0.0003,
    "общий": 0.0002, "главный": 0.0003,
    "значение": 0.0002, "сторона": 0.0002,
}

_RU_BI: dict[tuple[str, str], float] = {
    ("в", "том"): 0.0010, ("в", "этом"): 0.0008,
    ("на", "то"): 0.0006, ("не", "может"): 0.0004,
    ("не", "было"): 0.0005, ("не", "только"): 0.0005,
    ("из", "них"): 0.0003, ("в", "которой"): 0.0003,
    ("в", "которых"): 0.0003, ("с", "тем"): 0.0003,
    ("для", "того"): 0.0003, ("то", "что"): 0.0005,
    ("то", "есть"): 0.0003, ("так", "как"): 0.0003,
    ("потому", "что"): 0.0003, ("может", "быть"): 0.0004,
    ("и", "не"): 0.0004, ("но", "и"): 0.0003,
    ("это", "не"): 0.0003, ("он", "не"): 0.0003,
    ("я", "не"): 0.0003, ("что", "он"): 0.0002,
    ("что", "это"): 0.0002, ("на", "него"): 0.0002,
    ("от", "того"): 0.0002, ("до", "сих"): 0.0002,
    ("все", "это"): 0.0002, ("было", "бы"): 0.0002,
    ("одним", "из"): 0.0001, ("все", "еще"): 0.0002,
    ("кроме", "того"): 0.0002, ("таким", "образом"): 0.0002,
    ("в", "целом"): 0.0001, ("на", "самом"): 0.0002,
    ("самом", "деле"): 0.0002, ("тем", "более"): 0.0001,
    ("более", "того"): 0.0001, ("имеет", "значение"): 0.0001,
    ("в", "первую"): 0.0001, ("к", "тому"): 0.0001,
    ("тому", "же"): 0.0001, ("по", "мнению"): 0.0001,
    ("что", "не"): 0.0002, ("я", "думаю"): 0.0001,
    ("он", "был"): 0.0003, ("она", "была"): 0.0002,
    ("они", "были"): 0.0002, ("мы", "не"): 0.0002,
}

# ── Compact models for other languages ────────────────────
_UK_UNI: dict[str, float] = {
    "і": 0.028, "в": 0.025, "не": 0.018,
    "на": 0.015, "що": 0.012, "я": 0.010,
    "з": 0.010, "він": 0.008, "а": 0.008,
    "як": 0.007, "це": 0.007, "по": 0.005,
    "але": 0.005, "вона": 0.004, "до": 0.005,
    "за": 0.004, "від": 0.004, "його": 0.004,
    "всі": 0.003, "так": 0.003, "вони": 0.003,
    "ж": 0.003, "у": 0.003, "б": 0.003,
    "із": 0.002, "ми": 0.003, "для": 0.003,
    "ви": 0.002, "при": 0.002, "її": 0.002,
    "ні": 0.002, "вже": 0.002, "мені": 0.002,
    "ось": 0.001, "був": 0.003, "було": 0.002,
    "бути": 0.002, "є": 0.002, "цей": 0.002,
    "той": 0.002, "свій": 0.002, "весь": 0.002,
    "який": 0.002, "тільки": 0.002,
    "можна": 0.001, "треба": 0.001,
    "себе": 0.001, "коли": 0.001,
    "якщо": 0.001, "буде": 0.001,
    "були": 0.001, "нас": 0.001,
    "них": 0.001, "ніж": 0.001,
    "де": 0.001, "тут": 0.001,
    "дуже": 0.001, "навіть": 0.001,
    "після": 0.001, "між": 0.001,
    "також": 0.001, "ще": 0.001,
    "час": 0.001, "рік": 0.001,
    "людина": 0.001, "може": 0.001,
}

_DE_UNI: dict[str, float] = {
    "die": 0.035, "der": 0.033, "und": 0.028,
    "in": 0.019, "den": 0.012, "von": 0.010,
    "zu": 0.010, "das": 0.010, "mit": 0.009,
    "sich": 0.007, "des": 0.007, "auf": 0.006,
    "für": 0.005, "ist": 0.005, "im": 0.005,
    "dem": 0.005, "nicht": 0.005, "ein": 0.005,
    "eine": 0.004, "als": 0.004, "auch": 0.004,
    "es": 0.004, "an": 0.004, "er": 0.004,
    "hat": 0.003, "aus": 0.003, "sie": 0.004,
    "nach": 0.003, "wird": 0.003, "bei": 0.003,
    "einer": 0.003, "um": 0.002, "am": 0.002,
    "sind": 0.002, "noch": 0.002, "wie": 0.002,
    "einem": 0.002, "über": 0.002, "so": 0.002,
    "zum": 0.002, "war": 0.002, "haben": 0.002,
    "nur": 0.002, "oder": 0.002, "aber": 0.002,
    "vor": 0.002, "zur": 0.002, "bis": 0.001,
    "mehr": 0.001, "durch": 0.001, "man": 0.001,
    "dann": 0.001, "da": 0.001, "sein": 0.001,
    "sehr": 0.001, "schon": 0.001, "wenn": 0.001,
    "kann": 0.001, "ich": 0.002, "wir": 0.001,
    "was": 0.001, "werden": 0.001, "alle": 0.001,
}

_FR_UNI: dict[str, float] = {
    "de": 0.036, "la": 0.024, "le": 0.020,
    "et": 0.018, "les": 0.015, "des": 0.012,
    "en": 0.011, "un": 0.010, "du": 0.008,
    "une": 0.008, "que": 0.007, "est": 0.006,
    "dans": 0.006, "qui": 0.006, "par": 0.005,
    "pour": 0.005, "au": 0.005, "il": 0.005,
    "sur": 0.004, "ce": 0.004, "pas": 0.004,
    "plus": 0.003, "ne": 0.004, "se": 0.003,
    "son": 0.003, "avec": 0.003, "on": 0.003,
    "sa": 0.002, "ses": 0.002, "mais": 0.003,
    "comme": 0.002, "nous": 0.002, "vous": 0.002,
    "tout": 0.002, "elle": 0.002, "aux": 0.002,
    "été": 0.002, "ont": 0.002, "bien": 0.002,
    "aussi": 0.002, "cette": 0.002, "entre": 0.001,
    "ces": 0.001, "où": 0.001, "sont": 0.002,
    "peut": 0.001, "fait": 0.001, "même": 0.001,
    "si": 0.001, "deux": 0.001, "tous": 0.001,
    "après": 0.001, "leur": 0.001, "temps": 0.001,
    "très": 0.001, "ans": 0.001, "avant": 0.001,
    "autres": 0.001, "sous": 0.001, "dont": 0.001,
    "encore": 0.001, "eux": 0.001, "juste": 0.0008,
}

_ES_UNI: dict[str, float] = {
    "de": 0.040, "la": 0.024, "que": 0.020,
    "el": 0.018, "en": 0.016, "y": 0.014,
    "a": 0.012, "los": 0.010, "del": 0.008,
    "se": 0.007, "las": 0.006, "por": 0.006,
    "un": 0.006, "para": 0.005, "con": 0.005,
    "no": 0.005, "una": 0.005, "su": 0.004,
    "al": 0.003, "es": 0.004, "lo": 0.003,
    "como": 0.003, "más": 0.003, "pero": 0.003,
    "sus": 0.002, "le": 0.002, "ya": 0.002,
    "o": 0.002, "este": 0.002, "si": 0.002,
    "porque": 0.001, "esta": 0.002, "entre": 0.001,
    "cuando": 0.001, "muy": 0.001, "sin": 0.001,
    "sobre": 0.001, "también": 0.001, "me": 0.001,
    "hasta": 0.001, "hay": 0.001, "donde": 0.001,
    "quien": 0.001, "desde": 0.001, "todo": 0.001,
    "nos": 0.001, "durante": 0.001, "todos": 0.001,
    "uno": 0.001, "les": 0.001, "ni": 0.001,
    "contra": 0.0008, "otros": 0.0008,
    "ese": 0.0008, "eso": 0.0008,
    "ante": 0.0007, "ellos": 0.0008,
    "sido": 0.0008, "parte": 0.0008,
    "después": 0.0008, "bien": 0.0007,
    "ahora": 0.0007, "cada": 0.0007,
    "nuevo": 0.0006, "tiempo": 0.0006,
}

_IT_UNI: dict[str, float] = {
    "di": 0.035, "e": 0.028, "il": 0.020,
    "la": 0.018, "che": 0.015, "in": 0.013,
    "un": 0.010, "per": 0.009, "è": 0.008,
    "del": 0.007, "non": 0.007, "una": 0.006,
    "a": 0.006, "le": 0.005, "con": 0.005,
    "si": 0.005, "da": 0.004, "i": 0.004,
    "lo": 0.004, "al": 0.003, "ha": 0.003,
    "dei": 0.003, "nel": 0.003, "alla": 0.003,
    "più": 0.002, "come": 0.002, "su": 0.002,
    "anche": 0.002, "ma": 0.002, "sono": 0.002,
    "degli": 0.002, "questo": 0.002,
    "delle": 0.002, "se": 0.002,
    "tra": 0.001, "sua": 0.001,
    "suo": 0.001, "quando": 0.001,
    "stato": 0.001, "essere": 0.001,
    "tutto": 0.001, "ancora": 0.001,
    "poi": 0.001, "già": 0.001,
    "molto": 0.001, "dove": 0.001,
}

_PL_UNI: dict[str, float] = {
    "i": 0.028, "w": 0.025, "nie": 0.018,
    "na": 0.015, "z": 0.012, "że": 0.010,
    "do": 0.009, "to": 0.008, "się": 0.008,
    "jest": 0.006, "jak": 0.005, "ale": 0.005,
    "o": 0.005, "co": 0.004, "tak": 0.004,
    "po": 0.004, "za": 0.004, "od": 0.003,
    "ten": 0.003, "już": 0.003, "był": 0.003,
    "by": 0.003, "tylko": 0.002, "jego": 0.002,
    "jej": 0.002, "ich": 0.002, "tego": 0.002,
    "może": 0.002, "tym": 0.002, "czy": 0.002,
    "przed": 0.001, "też": 0.001,
    "kiedy": 0.001, "sobie": 0.001,
    "jeszcze": 0.001, "który": 0.001,
    "dla": 0.001, "przy": 0.001,
    "bardzo": 0.001, "dobrze": 0.001,
    "więc": 0.001, "jednak": 0.001,
    "potem": 0.001, "teraz": 0.001,
}

_PT_UNI: dict[str, float] = {
    "de": 0.040, "a": 0.024, "o": 0.020,
    "que": 0.018, "e": 0.016, "do": 0.012,
    "da": 0.011, "em": 0.009, "um": 0.008,
    "para": 0.007, "é": 0.006, "com": 0.006,
    "não": 0.005, "uma": 0.005, "os": 0.005,
    "no": 0.004, "se": 0.004, "na": 0.004,
    "por": 0.004, "mais": 0.003, "as": 0.003,
    "dos": 0.003, "como": 0.003, "mas": 0.003,
    "foi": 0.002, "ao": 0.002, "ele": 0.002,
    "das": 0.002, "tem": 0.002, "à": 0.002,
    "seu": 0.002, "sua": 0.002, "ou": 0.002,
    "ser": 0.001, "quando": 0.001,
    "muito": 0.001, "há": 0.001,
    "nos": 0.001, "já": 0.001,
    "está": 0.001, "eu": 0.001,
    "também": 0.001, "só": 0.001,
    "pelo": 0.001, "pela": 0.001,
}

_AR_UNI: dict[str, float] = {
    "في": 0.025, "من": 0.022, "على": 0.015,
    "إلى": 0.012, "أن": 0.012, "هذا": 0.008,
    "التي": 0.008, "الذي": 0.006, "ما": 0.006,
    "عن": 0.006, "لا": 0.006, "هذه": 0.005,
    "بين": 0.004, "كان": 0.005, "قد": 0.004,
    "ذلك": 0.004, "عند": 0.003, "لم": 0.003,
    "بعد": 0.003, "كل": 0.003, "هو": 0.004,
    "هي": 0.003, "أو": 0.003, "حتى": 0.002,
    "لأن": 0.002, "تم": 0.002, "ثم": 0.002,
    "أي": 0.002, "قبل": 0.002, "أكثر": 0.002,
    "يمكن": 0.002, "مع": 0.003, "فقط": 0.001,
    "كما": 0.002, "أيضا": 0.001, "دون": 0.001,
    "خلال": 0.001, "حيث": 0.001, "مثل": 0.001,
    "جدا": 0.001, "لكن": 0.002, "ليس": 0.001,
}

_ZH_UNI: dict[str, float] = {
    "的": 0.040, "是": 0.015, "了": 0.012,
    "在": 0.012, "不": 0.010, "和": 0.008,
    "有": 0.008, "我": 0.008, "他": 0.006,
    "这": 0.006, "中": 0.005, "人": 0.005,
    "们": 0.004, "大": 0.004, "来": 0.004,
    "上": 0.004, "个": 0.004, "到": 0.004,
    "说": 0.003, "就": 0.003, "会": 0.003,
    "也": 0.003, "地": 0.003, "出": 0.003,
    "对": 0.003, "要": 0.003, "能": 0.003,
    "以": 0.003, "为": 0.003, "时": 0.002,
    "年": 0.002, "可": 0.002, "都": 0.002,
    "把": 0.002, "那": 0.002, "你": 0.002,
    "她": 0.002, "着": 0.002, "过": 0.002,
    "被": 0.001, "从": 0.002, "而": 0.002,
}

_JA_UNI: dict[str, float] = {
    "の": 0.030, "に": 0.020, "は": 0.018,
    "を": 0.015, "た": 0.012, "が": 0.012,
    "で": 0.010, "て": 0.010, "と": 0.009,
    "し": 0.007, "れ": 0.006, "さ": 0.005,
    "ある": 0.005, "いる": 0.005, "も": 0.005,
    "する": 0.004, "から": 0.004, "な": 0.004,
    "こと": 0.004, "ない": 0.004, "この": 0.003,
    "その": 0.003, "よう": 0.003, "まで": 0.002,
    "です": 0.003, "ます": 0.003, "それ": 0.002,
    "これ": 0.002, "など": 0.002, "また": 0.002,
    "ため": 0.002, "もの": 0.002, "だ": 0.002,
    "ので": 0.001, "でも": 0.001, "だけ": 0.001,
    "より": 0.001, "ここ": 0.001, "あり": 0.001,
    "いう": 0.001, "なる": 0.001, "られ": 0.001,
}

_KO_UNI: dict[str, float] = {
    "의": 0.020, "이": 0.015, "는": 0.015,
    "을": 0.012, "를": 0.010, "에": 0.012,
    "가": 0.010, "로": 0.008,
    "에서": 0.006, "와": 0.005, "한": 0.005,
    "있다": 0.005, "하다": 0.005, "것": 0.004,
    "수": 0.004, "이다": 0.004, "대": 0.003,
    "또": 0.003, "그": 0.003, "위": 0.002,
    "등": 0.003, "및": 0.002, "않다": 0.002,
    "되다": 0.003, "중": 0.002, "대한": 0.002,
    "때": 0.002, "후": 0.002, "더": 0.002,
    "같다": 0.001, "만": 0.002, "보다": 0.001,
    "들": 0.002, "아니다": 0.001, "모든": 0.001,
    "이러한": 0.001, "통해": 0.001, "위해": 0.001,
    "매우": 0.001, "다른": 0.001, "새로운": 0.001,
}

_TR_UNI: dict[str, float] = {
    "bir": 0.020, "ve": 0.018, "bu": 0.012,
    "da": 0.010, "de": 0.010, "için": 0.008,
    "ile": 0.007, "olan": 0.005, "olarak": 0.005,
    "gibi": 0.004, "daha": 0.004, "çok": 0.004,
    "en": 0.004, "kadar": 0.003, "ya": 0.003,
    "o": 0.003, "ne": 0.003, "var": 0.003,
    "yok": 0.002, "ama": 0.003, "ancak": 0.002,
    "sonra": 0.002, "önce": 0.002, "her": 0.002,
    "ben": 0.002, "sen": 0.002, "biz": 0.001,
    "siz": 0.001, "onlar": 0.001, "şey": 0.002,
    "zaman": 0.002, "iç": 0.001, "üzere": 0.001,
    "tarafından": 0.001, "göre": 0.001,
    "arasında": 0.001, "karşı": 0.001,
    "yalnız": 0.001, "sadece": 0.001,
    "bile": 0.001, "hep": 0.001,
    "böyle": 0.001, "öyle": 0.001,
}

# ── Language model registry ───────────────────────────────
_UNIGRAMS: dict[str, dict[str, float]] = {
    "en": _EN_UNI, "ru": _RU_UNI, "uk": _UK_UNI,
    "de": _DE_UNI, "fr": _FR_UNI, "es": _ES_UNI,
    "it": _IT_UNI, "pl": _PL_UNI, "pt": _PT_UNI,
    "ar": _AR_UNI, "zh": _ZH_UNI, "ja": _JA_UNI,
    "ko": _KO_UNI, "tr": _TR_UNI,
}

_BIGRAMS: dict[str, dict[tuple[str, str], float]] = {
    "en": _EN_BI, "ru": _RU_BI,
}

_LAMBDA = 0.4  # bigram interpolation weight
_SMOOTH = 1e-8  # Laplace smoothing floor

_TOK_RE = re.compile(r"[\w'']+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization."""
    return [w.lower() for w in _TOK_RE.findall(text)]


class WordLanguageModel:
    """Word-level unigram/bigram language model.

    Computes perplexity, burstiness, and naturalness for
    14 languages using pre-built frequency tables.
    """

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang if lang in _UNIGRAMS else "en"
        self._uni = _UNIGRAMS[self.lang]
        self._bi = _BIGRAMS.get(self.lang, {})
        # total mass for normalization
        self._uni_total = sum(self._uni.values())
        self._bi_total = sum(self._bi.values()) or 1.0
        self._vocab_size = len(self._uni) + 1

    # ── Core probability ──────────────────────────────────

    def _p_uni(self, word: str) -> float:
        """Smoothed unigram probability."""
        freq = self._uni.get(word, 0.0)
        return (freq + _SMOOTH) / (
            self._uni_total + _SMOOTH * self._vocab_size
        )

    def _p_bi(self, w1: str, w2: str) -> float:
        """Smoothed bigram probability."""
        if not self._bi:
            return self._p_uni(w2)
        freq = self._bi.get((w1, w2), 0.0)
        # Normalize by w1 frequency
        w1_freq = self._uni.get(w1, _SMOOTH)
        return (freq + _SMOOTH) / (
            w1_freq + _SMOOTH * self._vocab_size
        )

    def _p_interp(self, w_prev: str, w: str) -> float:
        """Interpolated probability."""
        return (
            _LAMBDA * self._p_bi(w_prev, w)
            + (1 - _LAMBDA) * self._p_uni(w)
        )

    # ── Perplexity ────────────────────────────────────────

    def perplexity(self, text: str) -> float:
        """Word-level perplexity of the text.

        Lower values = more predictable (AI-like).
        Typical human: 50-200, AI: 20-60.
        """
        tokens = _tokenize(text)
        if len(tokens) < 2:
            return 0.0
        log_sum = 0.0
        for i in range(1, len(tokens)):
            p = self._p_interp(tokens[i - 1], tokens[i])
            log_sum += math.log(max(p, 1e-20))
        n = len(tokens) - 1
        return math.exp(-log_sum / n) if n > 0 else 0.0

    def sentence_perplexity(self, sentence: str) -> float:
        """Perplexity for a single sentence."""
        return self.perplexity(sentence)

    def per_word_surprise(
        self, text: str,
    ) -> list[tuple[str, float]]:
        """Return (word, surprise_bits) for each word."""
        tokens = _tokenize(text)
        if len(tokens) < 2:
            return [(t, 0.0) for t in tokens]
        result: list[tuple[str, float]] = [
            (tokens[0], 0.0),
        ]
        for i in range(1, len(tokens)):
            p = self._p_interp(tokens[i - 1], tokens[i])
            bits = -math.log2(max(p, 1e-20))
            result.append((tokens[i], bits))
        return result

    # ── Burstiness ────────────────────────────────────────

    def burstiness(self, text: str) -> float:
        """Perplexity variance across sentences.

        Higher = more human-like variation.
        """
        sents = re.split(r"[.!?]+\s+", text.strip())
        sents = [s for s in sents if len(s.split()) >= 3]
        if len(sents) < 2:
            return 0.0
        pps = [self.sentence_perplexity(s) for s in sents]
        mean_pp = sum(pps) / len(pps)
        if mean_pp == 0:
            return 0.0
        variance = sum(
            (p - mean_pp) ** 2 for p in pps
        ) / len(pps)
        # Coefficient of variation
        return math.sqrt(variance) / max(mean_pp, 1e-10)

    # ── Naturalness score ─────────────────────────────────

    def naturalness_score(self, text: str) -> dict[str, Any]:
        """Full naturalness analysis.

        Returns:
            dict with: perplexity, burstiness, variance,
            naturalness (0-100), verdict.
        """
        tokens = _tokenize(text)
        if len(tokens) < 5:
            return {
                "perplexity": 0.0,
                "burstiness": 0.0,
                "variance": 0.0,
                "naturalness": 50,
                "verdict": "unknown",
            }

        pp = self.perplexity(text)
        burst = self.burstiness(text)

        # Sentence perplexities for variance
        sents = re.split(r"[.!?]+\s+", text.strip())
        sents = [s for s in sents if len(s.split()) >= 3]
        if len(sents) >= 2:
            pps = [
                self.sentence_perplexity(s) for s in sents
            ]
            mean_pp = sum(pps) / len(pps)
            var = sum(
                (p - mean_pp) ** 2 for p in pps
            ) / len(pps)
        else:
            var = 0.0

        # Score computation
        score = 0

        # Perplexity in human range (50-300): +35
        if 40 <= pp <= 400:
            score += 35
        elif 20 <= pp < 40:
            score += 15  # Borderline low
        elif pp > 400:
            score += 25  # Somewhat high but variable
        # Very low PP (<20) = likely AI → +0

        # Burstiness (human > 0.3): +30
        if burst > 0.5:
            score += 30
        elif burst > 0.3:
            score += 20
        elif burst > 0.15:
            score += 10

        # Variance: +20
        if var > 100:
            score += 20
        elif var > 30:
            score += 12
        elif var > 10:
            score += 6

        # No extremely low PP windows: +15
        if sents and len(sents) >= 2:
            pps_list = [
                self.sentence_perplexity(s)
                for s in sents
            ]
            low_count = sum(
                1 for p in pps_list if p < 15
            )
            ratio = low_count / len(pps_list)
            if ratio < 0.1:
                score += 15
            elif ratio < 0.3:
                score += 8
        else:
            score += 10

        score = max(0, min(100, score))

        if score >= 65:
            verdict = "human"
        elif score >= 35:
            verdict = "mixed"
        else:
            verdict = "ai"

        return {
            "perplexity": round(pp, 2),
            "burstiness": round(burst, 4),
            "variance": round(var, 2),
            "naturalness": score,
            "verdict": verdict,
        }


# ── Convenience functions ─────────────────────────────────

def word_perplexity(
    text: str, lang: str = "en",
) -> float:
    """Compute word-level perplexity."""
    return WordLanguageModel(lang=lang).perplexity(text)


def word_naturalness(
    text: str, lang: str = "en",
) -> dict[str, Any]:
    """Full naturalness analysis."""
    return WordLanguageModel(lang=lang).naturalness_score(
        text,
    )
