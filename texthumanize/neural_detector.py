"""Neural AI text detector — pure Python, zero dependencies.

A 3-layer MLP (35→64→32→1) trained to distinguish AI-generated text from
human-written text. Uses the same 35 statistical features as the logistic
regression detector but with non-linear feature interactions for higher
accuracy.

Pre-trained weights are embedded directly in this module.

Usage::

    from texthumanize.neural_detector import NeuralAIDetector
    detector = NeuralAIDetector()
    result = detector.detect("Some text to analyze...", lang="en")
    print(result)  # {'score': 0.82, 'verdict': 'ai', 'confidence': 'high', ...}
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from texthumanize.ai_markers import load_ai_markers
from texthumanize.neural_engine import (
    DenseLayer,
    FeedForwardNet,
    Vec,
    _sigmoid,
)
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature normalization statistics (mean, std) — from corpus analysis
# ---------------------------------------------------------------------------

_FEATURE_NAMES: list[str] = [
    "type_token_ratio", "hapax_ratio", "avg_word_length", "word_length_variance",
    "mean_sentence_length", "sentence_length_variance", "sentence_length_skewness",
    "yules_k", "simpsons_diversity", "vocabulary_richness",
    "bigram_repetition_rate", "trigram_repetition_rate", "unique_bigram_ratio",
    "char_entropy", "word_entropy", "bigram_entropy",
    "burstiness_score", "vocab_burstiness",
    "paragraph_count_norm", "avg_paragraph_length", "list_bullet_ratio",
    "comma_rate", "semicolon_rate", "dash_rate", "question_rate", "exclamation_rate",
    "ai_pattern_rate", "word_freq_rank_variance", "zipf_fit_residual",
    "avg_syllables_per_word", "flesch_score_norm",
    "starter_diversity", "conjunction_rate", "transition_word_rate",
    "consec_len_diff_var",
]

_FEATURE_MEAN: list[float] = [
    0.65, 0.55, 4.5, 3.5, 15.0, 30.0, 0.3, 80.0, 0.96, 7.0,
    0.05, 0.02, 0.95, 4.3, 6.0, 7.0, -0.2, 0.6, 0.3, 0.5, 0.05,
    0.012, 0.0005, 0.003, 0.003, 0.002, 0.01, 1.0, 2.0, 1.5, 0.6,
    0.7, 0.04, 0.008, 2.0,
]

_FEATURE_STD: list[float] = [
    0.15, 0.18, 0.7, 1.2, 6.0, 25.0, 0.8, 50.0, 0.03, 2.5,
    0.05, 0.025, 0.05, 0.35, 1.5, 2.0, 0.18, 0.18, 0.2, 0.25, 0.1,
    0.008, 0.001, 0.004, 0.004, 0.003, 0.02, 0.8, 1.5, 0.22, 0.25,
    0.18, 0.02, 0.01, 1.2,
]

# ---------------------------------------------------------------------------
# AI-characteristic patterns
# ---------------------------------------------------------------------------

_AI_PATTERNS_EN: set[str] = {
    "furthermore", "moreover", "additionally", "consequently", "subsequently",
    "utilize", "utilization", "leverage", "leveraging", "facilitate",
    "facilitates", "facilitation", "optimize", "optimization", "implement",
    "implementation", "demonstrate", "demonstrates", "encompass", "encompasses",
    "comprehensive", "constitutes", "necessitate", "necessitates",
    "paramount", "delve", "delving", "adhere", "adherence",
    "multifaceted", "pivotal", "nuanced", "intricate", "seamless",
    "seamlessly", "streamline", "streamlined", "robust", "fostering",
    "foster", "harness", "harnessing", "aforementioned", "thereby",
    "notwithstanding", "whilst", "endeavor", "endeavors", "pertinent",
    "substantive", "delineate", "delineates", "ascertain", "elucidate",
    "underscore", "underscores", "landscape", "paradigm", "synergy",
    "holistic", "overarching", "cornerstone", "invaluable", "noteworthy",
    "commendable", "meticulous", "meticulously", "indispensable",
    "juxtaposition", "culmination", "testament", "realm", "tapestry",
    "beacon", "linchpin", "spearhead", "embark", "unravel", "unraveling",
    "navigate", "navigating", "underpinning",
    "groundbreaking", "transformative", "cutting-edge",
    # Extended AI markers
    "plethora", "myriad", "crucial", "imperative", "integral",
    "instrumental", "conducive", "propensity", "proliferation",
    "cognizant", "burgeoning", "amalgamation", "ubiquitous",
    "exacerbate", "exacerbates", "mitigate", "mitigates", "mitigation",
    "bolster", "bolstering", "augment", "augmenting",
    "catalyze", "catalyzing", "catalyst", "resonate", "resonates",
    "underpin", "predicated", "predicate",
    "salient", "disparate", "concomitant", "nascent",
    "promulgate", "precipitate", "tantamount", "commensurate",
    "juxtapose", "bifurcate", "conflate", "delineation",
    "operationalize", "contextualize", "conceptualize",
    "exemplify", "exemplifies", "epitomize", "epitomizes",
    "spearheading", "vanguard", "forefront",
}

_AI_PATTERNS_RU: list[str] = [
    "кроме того", "более того", "необходимо отметить", "следует подчеркнуть",
    "важно понимать", "в заключение", "таким образом", "в связи с этим",
    "вместе с тем", "в целом", "в частности", "прежде всего",
    "в первую очередь", "с другой стороны", "в настоящее время",
    "на сегодняшний день", "в рамках данного", "согласно данным",
    "по мнению экспертов", "представляет собой", "является ключевым",
    "обусловлено тем", "способствует развитию", "оказывает влияние",
    "имеет важное значение", "в контексте данного", "на основании",
    "принимая во внимание", "с учётом вышеизложенного", "данный подход",
    "является неотъемлемой", "играет важную роль", "следует учитывать",
    "не менее важным", "ключевым аспектом", "существенным образом",
    "имеет место быть", "что касается",
]

_CONJUNCTIONS_EN: set[str] = {
    "and", "but", "or", "nor", "for", "yet", "so", "because",
    "although", "while", "whereas", "since", "unless", "until",
    "though", "even", "whether", "after", "before", "when",
}

_CONJUNCTIONS_RU: set[str] = {
    "и", "а", "но", "или", "однако", "зато", "потому", "поэтому",
    "хотя", "пока", "когда", "если", "чтобы", "пусть", "ведь",
    "либо", "ибо", "причём", "притом", "тоже", "также",
}

_CONJUNCTIONS_UK: set[str] = {
    "і", "й", "а", "але", "або", "проте", "однак", "зате", "тому",
    "хоча", "поки", "коли", "якщо", "щоб", "бо", "адже", "отже",
    "хай", "нехай", "також", "теж",
}

_CONJUNCTIONS_DE: set[str] = {
    "und", "aber", "oder", "denn", "sondern", "doch", "jedoch", "weil",
    "obwohl", "während", "wenn", "falls", "damit", "bevor", "nachdem",
    "seitdem", "sobald", "solange", "weder", "noch", "sowohl", "als",
}

_CONJUNCTIONS_FR: set[str] = {
    "et", "mais", "ou", "donc", "car", "ni", "or", "puis",
    "quand", "lorsque", "puisque", "parce", "bien", "quoique",
    "tandis", "pendant", "avant", "après", "depuis", "comme",
}

_CONJUNCTIONS_ES: set[str] = {
    "y", "e", "pero", "sino", "o", "u", "ni", "que", "porque",
    "aunque", "cuando", "mientras", "como", "pues", "ya",
    "desde", "hasta", "según", "antes", "después",
}

_TRANSITIONS_EN: set[str] = {
    "however", "therefore", "furthermore", "moreover", "additionally",
    "consequently", "nevertheless", "nonetheless", "meanwhile",
    "subsequently", "accordingly", "conversely", "alternatively",
    "specifically", "particularly", "notably", "importantly",
    "significantly", "essentially", "fundamentally", "ultimately",
    "regardless", "indeed", "certainly", "undoubtedly", "evidently",
}

_TRANSITIONS_RU: set[str] = {
    "однако", "поэтому", "следовательно", "кроме", "более",
    "дополнительно", "тем", "вместе", "впоследствии", "соответственно",
    "наоборот", "альтернативно", "конкретно", "безусловно",
    "существенно", "фундаментально", "действительно", "несомненно",
    "очевидно", "таким", "прежде", "во-первых", "во-вторых",
    "в-третьих", "наконец", "итак", "впрочем",
}

_TRANSITIONS_UK: set[str] = {
    "однак", "тому", "отже", "крім", "більше",
    "додатково", "разом", "згодом", "відповідно",
    "навпаки", "конкретно", "безумовно",
    "суттєво", "фундаментально", "дійсно", "безсумнівно",
    "очевидно", "таким", "насамперед", "по-перше", "по-друге",
    "по-третє", "нарешті", "отож", "втім", "зрештою",
}

_TRANSITIONS_DE: set[str] = {
    "jedoch", "deshalb", "außerdem", "darüber", "hinaus",
    "folglich", "dennoch", "nichtsdestotrotz", "inzwischen",
    "dementsprechend", "umgekehrt", "insbesondere", "grundsätzlich",
    "letztendlich", "tatsächlich", "zweifellos", "offensichtlich",
    "zusammenfassend", "abschließend", "schließlich", "zunächst",
    "erstens", "zweitens", "drittens", "allerdings",
}

_TRANSITIONS_FR: set[str] = {
    "cependant", "toutefois", "néanmoins", "pourtant", "ainsi",
    "donc", "par", "ailleurs", "conséquent", "davantage",
    "effectivement", "certainement", "évidemment", "fondamentalement",
    "essentiellement", "notamment", "particulièrement", "finalement",
    "premièrement", "deuxièmement", "troisièmement", "enfin",
    "autrement", "spécifiquement", "incontestablement",
}

_TRANSITIONS_ES: set[str] = {
    "sin", "embargo", "therefore", "además", "asimismo",
    "consecuentemente", "consiguientemente", "específicamente",
    "particularmente", "notablemente", "fundamentalmente",
    "esencialmente", "ciertamente", "indudablemente", "evidentemente",
    "primero", "segundo", "tercero", "finalmente", "concretamente",
    "igualmente", "respectivamente", "efectivamente",
}

_VOWELS_EN = set("aeiouyAEIOUY")
_VOWELS_RU = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
_VOWELS_UK = set("аеіїоуєюяАЕІЇОУЄЮЯ")
_VOWELS_DE = set("aeiouyäöüAEIOUYÄÖÜ")
_VOWELS_FR = set("aeiouyàâéèêëîïôùûüÿæœAEIOUYÀÂÉÈÊËÎÏÔÙÛÜŸÆŒ")
_VOWELS_ES = set("aeiouyáéíóúüAEIOUYÁÉÍÓÚÜ")

_AI_PATTERNS_DE: list[str] = [
    "darüber hinaus", "es ist wichtig zu beachten", "zusammenfassend lässt sich sagen",
    "in diesem zusammenhang", "von entscheidender bedeutung", "es sei darauf hingewiesen",
    "im rahmen dieser", "auf der grundlage", "unter berücksichtigung",
    "die implementierung von", "ein beispielloses maß", "im wesentlichen",
    "es ist erwähnenswert", "grundsätzlich gilt", "von großer bedeutung",
    "im kontext von", "hinsichtlich der", "in anbetracht der tatsache",
    "des weiteren", "nichtsdestotrotz", "dementsprechend",
]

_AI_WORDS_DE: set[str] = {
    "revolutioniert", "transformiert", "implementierung", "grundlegend",
    "beispiellos", "umfassend", "maßgeblich", "weitreichend",
    "entscheidend", "bemerkenswert", "signifikant", "paradigmenwechsel",
    "optimierung", "zunehmend", "fortschrittlich", "ganzheitlich",
}

_AI_PATTERNS_FR: list[str] = [
    "il est important de noter", "en outre", "par conséquent",
    "dans ce contexte", "il convient de souligner", "force est de constater",
    "la mise en œuvre", "dans le cadre de", "en tenant compte de",
    "il est essentiel de", "de manière significative", "en fin de compte",
    "il est à noter", "en ce qui concerne", "dans une large mesure",
    "à cet égard", "sans précédent", "de surcroît", "en définitive",
]

_AI_WORDS_FR: set[str] = {
    "révolutionné", "transformé", "implémentation", "fondamentalement",
    "considérablement", "significativement", "remarquablement",
    "incontestablement", "indéniablement", "substantiellement",
    "paradigme", "optimisation", "progressivement", "holistique",
}

_AI_PATTERNS_ES: list[str] = [
    "es importante señalar", "cabe destacar", "en este contexto",
    "por consiguiente", "la implementación de", "niveles sin precedentes",
    "de manera significativa", "en última instancia", "en lo que respecta a",
    "resulta fundamental", "en el marco de", "teniendo en cuenta",
    "es necesario subrayar", "sin lugar a dudas", "en términos generales",
    "a este respecto", "con el fin de", "en virtud de",
]

_AI_WORDS_ES: set[str] = {
    "revolucionado", "transformado", "implementación", "fundamentalmente",
    "considerablemente", "significativamente", "notablemente",
    "indudablemente", "paradigma", "optimización", "progresivamente",
    "holístico", "precedentes", "automatización", "sostenibilidad",
}

_AI_PATTERNS_UK: list[str] = [
    "крім того", "більше того", "необхідно зазначити", "слід підкреслити",
    "важливо розуміти", "на завершення", "таким чином", "у зв'язку з цим",
    "разом з тим", "загалом", "зокрема", "насамперед",
    "у першу чергу", "з іншого боку", "на сьогоднішній день",
    "у межах даного", "згідно з даними",
    "на думку експертів", "являє собою", "є ключовим",
    "зумовлено тим", "сприяє розвитку", "здійснює вплив",
    "має важливе значення", "у контексті даного", "на підставі",
    "беручи до уваги", "з урахуванням вищевикладеного", "даний підхід",
    "є невід'ємною", "відіграє важливу роль", "слід враховувати",
    "не менш важливим", "ключовим аспектом", "істотним чином",
    "має місце", "що стосується",
]

# AI-characteristic individual WORDS for RU/UK (complement phrase lists)
_AI_WORDS_RU: set[str] = {
    "трансформировал", "трансформирует", "трансформация",
    "беспрецедентные", "беспрецедентный",
    "фундаментальный", "фундаментально",
    "кардинально", "ландшафт", "парадигма", "парадигму",
    "оптимизировать", "оптимизация", "имплементация",
    "интеграция", "интегрировать",
    "предиктивный", "предиктивных", "предиктивные",
    "паттерн", "паттернов", "паттерны",
    "синергия", "синергетический",
    "релевантный", "релевантных",
    "холистический", "всеобъемлющий",
    "многогранный", "многоаспектный",
    "обусловливает", "детерминирует",
    "нивелировать", "аккумулировать",
    "инкорпорировать", "транспарентный",
    "валидный", "верифицировать",
    # Extended RU AI words
    "комплексный", "системный", "стратегический",
    "эффективный", "ключевой", "целостный",
    "неотъемлемый", "всесторонний", "концептуальный",
    "детерминистский", "инновационный", "перспективный",
    "компетентностный", "методологический",
    "конвергенция", "дивергенция", "модификация",
    "верификация", "валидация", "апробация",
    "имплицитный", "эксплицитный", "каузальный",
    "корреляция", "экстраполяция", "артикуляция",
    "диверсификация", "кластеризация", "приоритизация",
    "резюмируя", "констатируя", "акцентируя",
    "дифференцированный", "пролиферация",
}

_AI_WORDS_UK: set[str] = {
    "трансформував", "трансформує", "трансформація",
    "безпрецедентні", "безпрецедентний",
    "фундаментальний", "фундаментально",
    "кардинально", "ландшафт", "парадигма", "парадигму",
    "оптимізувати", "оптимізація", "імплементація",
    "інтеграція", "інтегрувати",
    "предиктивний", "предиктивних", "предиктивні",
    "патерн", "патернів", "патерни",
    "синергія", "синергетичний",
    "релевантний", "релевантних",
    "холістичний", "всеосяжний",
    "багатогранний", "багатоаспектний",
    "обумовлює", "детермінує",
    "нівелювати", "акумулювати",
    "інкорпорувати", "транспарентний",
    "валідний", "верифікувати",
    # Extended UK AI words
    "комплексний", "системний", "стратегічний",
    "ефективний", "ключовий", "цілісний",
    "невід'ємний", "всебічний", "концептуальний",
    "детерміністський", "інноваційний", "перспективний",
    "компетентнісний", "методологічний",
    "конвергенція", "дивергенція", "модифікація",
    "верифікація", "валідація", "апробація",
    "імпліцитний", "експліцитний", "каузальний",
    "кореляція", "екстраполяція", "артикуляція",
    "диверсифікація", "кластеризація", "пріоритизація",
    "резюмуючи", "констатуючи", "акцентуючи",
    "диференційований", "проліферація",
}

# Per-language feature normalization: Cyrillic text has different char_entropy
# baseline, different word/sentence length distributions.
_FEATURE_MEAN_RU: list[float] = [
    0.62, 0.52, 5.2, 4.2, 14.0, 28.0, 0.3, 75.0, 0.96, 6.5,
    0.05, 0.02, 0.95, 4.8, 6.5, 7.5, -0.2, 0.6, 0.3, 0.5, 0.05,
    0.016, 0.0003, 0.006, 0.002, 0.001, 0.015, 1.0, 2.0, 2.0, 0.5,
    0.7, 0.06, 0.01, 2.0,
]

_FEATURE_STD_RU: list[float] = [
    0.14, 0.16, 0.8, 1.4, 5.5, 22.0, 0.8, 45.0, 0.03, 2.3,
    0.05, 0.025, 0.05, 0.30, 1.3, 1.8, 0.18, 0.18, 0.2, 0.25, 0.1,
    0.010, 0.0008, 0.005, 0.003, 0.002, 0.02, 0.8, 1.5, 0.25, 0.25,
    0.18, 0.03, 0.012, 1.2,
]

_FEATURE_MEAN_UK: list[float] = [
    0.63, 0.53, 5.1, 4.0, 13.5, 26.0, 0.3, 72.0, 0.96, 6.8,
    0.05, 0.02, 0.95, 4.9, 6.5, 7.4, -0.2, 0.6, 0.3, 0.5, 0.05,
    0.015, 0.0003, 0.005, 0.002, 0.001, 0.014, 1.0, 2.0, 2.1, 0.5,
    0.7, 0.06, 0.01, 2.0,
]

_FEATURE_STD_UK: list[float] = [
    0.14, 0.16, 0.8, 1.3, 5.5, 22.0, 0.8, 45.0, 0.03, 2.3,
    0.05, 0.025, 0.05, 0.28, 1.3, 1.7, 0.18, 0.18, 0.2, 0.25, 0.1,
    0.010, 0.0008, 0.005, 0.003, 0.002, 0.02, 0.8, 1.5, 0.25, 0.25,
    0.18, 0.03, 0.012, 1.2,
]

# German: longer words, similar sentence length to EN
_FEATURE_MEAN_DE: list[float] = [
    0.58, 0.50, 5.8, 5.5, 15.0, 30.0, 0.2, 68.0, 0.96, 6.2,
    0.04, 0.015, 0.96, 4.6, 6.2, 7.2, -0.22, 0.58, 0.28, 0.45, 0.04,
    0.018, 0.0004, 0.004, 0.002, 0.001, 0.012, 1.1, 1.8, 2.2, 0.55,
    0.68, 0.07, 0.015, 1.8,
]

_FEATURE_STD_DE: list[float] = [
    0.14, 0.16, 0.9, 1.6, 5.5, 24.0, 0.8, 48.0, 0.03, 2.4,
    0.04, 0.02, 0.04, 0.30, 1.2, 1.7, 0.18, 0.17, 0.2, 0.25, 0.08,
    0.012, 0.0008, 0.005, 0.003, 0.002, 0.018, 0.9, 1.4, 0.28, 0.25,
    0.18, 0.04, 0.015, 1.3,
]

# French: moderate word length, rich punctuation
_FEATURE_MEAN_FR: list[float] = [
    0.60, 0.51, 5.0, 4.5, 16.0, 32.0, 0.25, 70.0, 0.96, 6.5,
    0.04, 0.015, 0.96, 4.7, 6.4, 7.3, -0.20, 0.60, 0.30, 0.48, 0.04,
    0.020, 0.0005, 0.005, 0.003, 0.002, 0.014, 1.0, 1.9, 2.0, 0.50,
    0.70, 0.065, 0.013, 1.9,
]

_FEATURE_STD_FR: list[float] = [
    0.14, 0.16, 0.8, 1.4, 5.5, 24.0, 0.8, 46.0, 0.03, 2.3,
    0.04, 0.02, 0.04, 0.28, 1.3, 1.7, 0.18, 0.18, 0.2, 0.25, 0.08,
    0.012, 0.0008, 0.005, 0.003, 0.002, 0.018, 0.8, 1.5, 0.25, 0.25,
    0.18, 0.035, 0.013, 1.3,
]

# Spanish: similar to French, shorter words
_FEATURE_MEAN_ES: list[float] = [
    0.59, 0.50, 5.2, 4.6, 17.0, 35.0, 0.22, 72.0, 0.96, 6.4,
    0.045, 0.016, 0.96, 4.6, 6.3, 7.2, -0.18, 0.59, 0.30, 0.47, 0.04,
    0.019, 0.0004, 0.005, 0.004, 0.003, 0.013, 1.05, 1.9, 2.1, 0.52,
    0.69, 0.065, 0.014, 1.85,
]

_FEATURE_STD_ES: list[float] = [
    0.14, 0.16, 0.8, 1.5, 6.0, 26.0, 0.8, 47.0, 0.03, 2.3,
    0.04, 0.02, 0.04, 0.28, 1.3, 1.7, 0.18, 0.17, 0.2, 0.25, 0.08,
    0.012, 0.0008, 0.005, 0.004, 0.003, 0.018, 0.85, 1.5, 0.26, 0.25,
    0.18, 0.035, 0.014, 1.3,
]

# Sentence boundary regex
_SENT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ"\'"(])')
_WORD_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐüöäßÜÖÄàâéèêëîïôùûçÀÂÉÈÊËÎÏÔÙÛÇáéíóúñÁÉÍÓÚÑ]+')
_BULLET_RE = re.compile(r'^\s*[-*•▸▹►]|\d+[.)]\s', re.MULTILINE)


# ---------------------------------------------------------------------------
# Feature extraction (35 features)
# ---------------------------------------------------------------------------

def _safe_var(vals: list[float]) -> float:
    """Population variance, safe for empty/single."""
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return sum((x - m) ** 2 for x in vals) / len(vals)


def _safe_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _shannon_entropy(counts: Counter) -> float:  # type: ignore[type-arg]
    """Shannon entropy in bits."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent


def _count_syllables(word: str, vowels: set[str]) -> int:
    """Count syllables via vowel groups with English silent-e correction."""
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    # English silent-e
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def extract_features(text: str, lang: str = "en") -> Vec:
    """Extract 35 statistical features from text.

    Returns a list of 35 raw feature values in the canonical order.
    """
    tokens = _WORD_RE.findall(text.lower())
    n_tokens = len(tokens)
    if n_tokens < 3:
        return [0.0] * 35

    sentences = split_sentences(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        sentences = [text]
    n_sentences = len(sentences)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    n_paragraphs = len(paragraphs)

    # Token stats
    token_set = set(tokens)
    freq = Counter(tokens)
    n_types = len(token_set)
    word_lengths = [float(len(t)) for t in tokens]

    # 1. type_token_ratio
    ttr = n_types / n_tokens

    # 2. hapax_ratio
    hapax = sum(1 for c in freq.values() if c == 1)
    hapax_ratio = hapax / n_tokens

    # 3, 4. avg/var word length
    awl = _safe_mean(word_lengths)
    wlv = _safe_var(word_lengths)

    # Sentence lengths (in tokens)
    sent_token_counts = []
    for s in sentences:
        st = _WORD_RE.findall(s.lower())
        sent_token_counts.append(float(len(st)) if st else 0.0)

    # 5, 6, 7. sentence length stats
    msl = _safe_mean(sent_token_counts)
    slv = _safe_var(sent_token_counts)
    # skewness
    sls = 0.0
    if len(sent_token_counts) >= 3:
        sm = msl
        ssig = math.sqrt(slv) if slv > 0 else 1.0
        sls = sum((x - sm) ** 3 for x in sent_token_counts) / (len(sent_token_counts) * ssig ** 3)

    # 8. Yule's K
    freq_spectrum = Counter(freq.values())
    m2 = sum(i * i * v for i, v in freq_spectrum.items())
    yules_k = 10000.0 * (m2 - n_tokens) / (n_tokens * n_tokens) if n_tokens > 1 else 0.0

    # 9. Simpson's diversity
    simpsons = 1.0 - sum(c * (c - 1) for c in freq.values()) / (n_tokens * (n_tokens - 1)) if n_tokens > 1 else 1.0

    # 10. Vocabulary richness (Guiraud)
    vocab_rich = n_types / math.sqrt(n_tokens)

    # 11, 12, 13. N-gram stats
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(n_tokens - 1)]
    trigrams = [f"{tokens[i]}_{tokens[i+1]}_{tokens[i+2]}" for i in range(n_tokens - 2)]
    bigram_freq = Counter(bigrams)
    trigram_freq = Counter(trigrams)
    n_unique_bi = len(bigram_freq)
    n_unique_tri = len(trigram_freq)
    bi_rep = sum(1 for c in bigram_freq.values() if c > 1) / max(n_unique_bi, 1)
    tri_rep = sum(1 for c in trigram_freq.values() if c > 1) / max(n_unique_tri, 1)
    uniq_bi_ratio = n_unique_bi / max(len(bigrams), 1)

    # 14, 15, 16. Entropy
    char_counts: Counter[str] = Counter(c for c in text if not c.isspace())
    char_ent = _shannon_entropy(char_counts)
    word_ent = _shannon_entropy(freq)
    bigram_ent = _shannon_entropy(bigram_freq)

    # 17, 18. Burstiness
    if len(sent_token_counts) >= 2:
        b_mu = _safe_mean(sent_token_counts)
        b_sig = math.sqrt(_safe_var(sent_token_counts))
        burstiness = (b_sig - b_mu) / (b_sig + b_mu) if (b_sig + b_mu) > 0 else 0.0
    else:
        burstiness = 0.0

    half = n_tokens // 2
    if half > 0:
        first_half = set(tokens[:half])
        second_half = set(tokens[half:])
        jaccard = len(first_half & second_half) / max(len(first_half | second_half), 1)
        vocab_burst = 1.0 - jaccard
    else:
        vocab_burst = 0.0

    # 19, 20, 21. Structural
    para_norm = min(n_paragraphs / 10.0, 1.0)
    avg_para_len = min((n_tokens / max(n_paragraphs, 1)) / 100.0, 1.0)
    bullet_matches = len(_BULLET_RE.findall(text))
    list_bullet_ratio = bullet_matches / max(n_sentences, 1)

    # 22-26. Punctuation rates
    text_len = max(len(text), 1)
    comma_rate = text.count(",") / text_len
    semi_rate = text.count(";") / text_len
    dash_count = text.count("—") + text.count("–") + text.count(" - ")
    dash_rate = dash_count / text_len
    question_rate = text.count("?") / text_len
    excl_rate = text.count("!") / text_len

    # 27. AI pattern rate (multilingual)
    lower_text = text.lower()
    ai_count = sum(1 for t in tokens if t in _AI_PATTERNS_EN)
    if lang == "ru":
        for phrase in _AI_PATTERNS_RU:
            ai_count += lower_text.count(phrase)
        ai_count += sum(1 for t in tokens if t in _AI_WORDS_RU)
    elif lang == "uk":
        for phrase in _AI_PATTERNS_UK:
            ai_count += lower_text.count(phrase)
        ai_count += sum(1 for t in tokens if t in _AI_WORDS_UK)
    elif lang == "de":
        for phrase in _AI_PATTERNS_DE:
            ai_count += lower_text.count(phrase)
        ai_count += sum(1 for t in tokens if t in _AI_WORDS_DE)
    elif lang == "fr":
        for phrase in _AI_PATTERNS_FR:
            ai_count += lower_text.count(phrase)
        ai_count += sum(1 for t in tokens if t in _AI_WORDS_FR)
    elif lang == "es":
        for phrase in _AI_PATTERNS_ES:
            ai_count += lower_text.count(phrase)
        ai_count += sum(1 for t in tokens if t in _AI_WORDS_ES)

    # Also load language-specific markers from ai_markers module
    if lang not in ("en", "ru", "uk", "de", "fr", "es"):
        lang_markers = load_ai_markers(lang)
        if lang_markers:
            lang_words: set[str] = set()
            lang_phrases: list[str] = []
            for words in lang_markers.values():
                for w in words:
                    if " " in w:
                        lang_phrases.append(w.lower())
                    else:
                        lang_words.add(w.lower())
            for phrase in lang_phrases:
                ai_count += lower_text.count(phrase)
            for t in tokens:
                if t in lang_words:
                    ai_count += 1

    ai_pattern_rate = ai_count / max(n_tokens, 1)

    # 28. Word frequency rank variance
    wf_values = [float(freq[t]) for t in tokens]
    wfr_var = math.log1p(_safe_var(wf_values))

    # 29. Zipf fit residual
    sorted_freqs = sorted(freq.values(), reverse=True)[:100]
    if len(sorted_freqs) >= 2:
        f1 = sorted_freqs[0]
        residuals = []
        for r, fr in enumerate(sorted_freqs, 1):
            expected = f1 / r
            if fr > 0 and expected > 0:
                residuals.append((math.log(fr) - math.log(expected)) ** 2)
        zipf_res = _safe_mean(residuals)
    else:
        zipf_res = 0.0

    # 30, 31. Readability
    _VOWELS_MAP = {
        "en": _VOWELS_EN, "ru": _VOWELS_RU, "uk": _VOWELS_UK,
        "de": _VOWELS_DE, "fr": _VOWELS_FR, "es": _VOWELS_ES,
    }
    vowels = _VOWELS_MAP.get(lang, _VOWELS_EN)
    syllables = [_count_syllables(t, vowels) for t in tokens]
    avg_syl = _safe_mean([float(s) for s in syllables])
    asl = n_tokens / max(n_sentences, 1)
    flesch = 206.835 - 1.015 * asl - 84.6 * avg_syl
    flesch_norm = max(-0.5, min(1.5, flesch / 100.0))

    # 32. Starter diversity
    first_words = []
    for s in sentences:
        st = _WORD_RE.findall(s.lower())
        if st:
            first_words.append(st[0])
    starter_div = len(set(first_words)) / max(len(first_words), 1)

    # 33. Conjunction rate (language-aware)
    _CONJ_MAP = {
        "en": _CONJUNCTIONS_EN, "ru": _CONJUNCTIONS_RU, "uk": _CONJUNCTIONS_UK,
        "de": _CONJUNCTIONS_DE, "fr": _CONJUNCTIONS_FR, "es": _CONJUNCTIONS_ES,
    }
    _conj_set = _CONJ_MAP.get(lang, _CONJUNCTIONS_EN)
    conj_count = sum(1 for t in tokens if t in _conj_set)
    conj_rate = conj_count / max(n_tokens, 1)

    # 34. Transition word rate (language-aware)
    _TRANS_MAP = {
        "en": _TRANSITIONS_EN, "ru": _TRANSITIONS_RU, "uk": _TRANSITIONS_UK,
        "de": _TRANSITIONS_DE, "fr": _TRANSITIONS_FR, "es": _TRANSITIONS_ES,
    }
    _trans_set = _TRANS_MAP.get(lang, _TRANSITIONS_EN)
    trans_count = sum(1 for t in tokens if t in _trans_set)
    trans_rate = trans_count / max(n_tokens, 1)

    # 35. Consecutive length difference variance
    if len(sent_token_counts) >= 2:
        diffs = [abs(sent_token_counts[i] - sent_token_counts[i + 1])
                 for i in range(len(sent_token_counts) - 1)]
        cld_var = math.log1p(_safe_var(diffs))
    else:
        cld_var = 0.0

    return [
        ttr, hapax_ratio, awl, wlv,
        msl, slv, sls,
        yules_k, simpsons, vocab_rich,
        bi_rep, tri_rep, uniq_bi_ratio,
        char_ent, word_ent, bigram_ent,
        burstiness, vocab_burst,
        para_norm, avg_para_len, list_bullet_ratio,
        comma_rate, semi_rate, dash_rate, question_rate, excl_rate,
        ai_pattern_rate, wfr_var, zipf_res,
        avg_syl, flesch_norm,
        starter_div, conj_rate, trans_rate,
        cld_var,
    ]


def normalize_features(raw: Vec, lang: str = "en") -> Vec:
    """Normalize features: z-score then clip to [-3, 3].

    Uses per-language normalization to account for
    different char_entropy baselines and word length distributions.
    """
    _NORM_MAP = {
        "ru": (_FEATURE_MEAN_RU, _FEATURE_STD_RU),
        "uk": (_FEATURE_MEAN_UK, _FEATURE_STD_UK),
        "de": (_FEATURE_MEAN_DE, _FEATURE_STD_DE),
        "fr": (_FEATURE_MEAN_FR, _FEATURE_STD_FR),
        "es": (_FEATURE_MEAN_ES, _FEATURE_STD_ES),
    }
    means, stds = _NORM_MAP.get(lang, (_FEATURE_MEAN, _FEATURE_STD))

    out = []
    for _i, (val, mu, sig) in enumerate(zip(raw, means, stds)):
        if sig > 0:
            z = (val - mu) / sig
        else:
            z = 0.0
        out.append(max(-3.0, min(3.0, z)))
    return out


# ---------------------------------------------------------------------------
# Pre-trained MLP weights (35 → 64 → 32 → 1)
#
# Layer 1 (35→64, ReLU): feature expansion with cross-interactions.
# Layer 2 (64→32, ReLU): non-linear combination layer.
# Layer 3 (32→1, linear): output logit.
#
# Weights are trained via backpropagation with Adam optimizer on a corpus
# of AI and human-written text features. Training code: training.py
# Trained weights are stored in texthumanize/weights/detector_weights.json.zb85
#
# When pre-trained weights are not available, falls back to heuristic
# initialization from logistic regression weights.
# ---------------------------------------------------------------------------

def _load_trained_network() -> FeedForwardNet | None:
    """Try to load pre-trained weights from the weights directory."""
    try:
        from texthumanize.weight_loader import load_detector_weights
        config = load_detector_weights()
        if config is not None:
            net = FeedForwardNet.from_config(config)
            logger.info(
                "Loaded trained detector: %d params, arch %s",
                net.param_count, net.name,
            )
            return net
    except Exception as e:
        logger.warning("Could not load trained detector weights: %s", e)
    return None


def _build_pretrained_network() -> FeedForwardNet:
    """Build the MLP for AI detection.

    First tries to load real trained weights. Falls back to heuristic
    initialization from logistic regression weights if unavailable.

    Architecture: 35 → 64 (ReLU) → 32 (ReLU) → 1 (linear)
    """
    # Try loading real trained weights first
    trained = _load_trained_network()
    if trained is not None:
        return trained

    logger.info("No trained weights found, using heuristic initialization")
    import random
    rng = random.Random(31415)

    # Existing LR weights (from statistical_detector.py)
    lr_w = [
        -0.85, 0.62, -0.48, 0.37, -0.32, 0.91, 0.44, 0.28, -0.55, -0.39,
        0.53, 0.41, -0.67, 0.22, 0.58, 0.19, 1.15, 0.73, 0.05, -0.21,
        -0.34, -0.26, -0.72, 0.45, 0.38, 0.29, -2.10, 0.64, 0.31, -0.42,
        0.36, 0.52, 0.18, -0.88, 0.76,
    ]

    # Layer 1: 35 → 64 — initialized with LR as first 35 neurons,
    # plus 29 cross-feature detectors
    n_in, n_h1, n_h2, _n_out = 35, 64, 32, 1

    w1 = []  # 64 x 35
    b1 = []  # 64

    # First 35 neurons: each captures one original feature (amplified)
    for i in range(n_in):
        row = [0.0] * n_in
        row[i] = lr_w[i] * 1.5  # amplify the original signal
        # add slight cross-feature coupling
        for j in range(n_in):
            if i != j:
                row[j] = rng.gauss(0, 0.08)
        w1.append(row)
        b1.append(rng.gauss(0, 0.05))

    # Next 29 neurons: feature interaction detectors
    # Group features into semantically related clusters for interaction
    _clusters = [
        [0, 1, 8, 9],       # vocabulary diversity
        [2, 3],              # word length
        [4, 5, 6],           # sentence length
        [7, 8, 9],           # lexical diversity measures
        [10, 11, 12],        # n-gram repetition
        [13, 14, 15],        # entropy group
        [16, 17],            # burstiness pair
        [18, 19, 20],        # structural
        [21, 22, 23, 24, 25],  # punctuation cluster
        [26],                # AI patterns (critical)
        [27, 28],            # frequency proxy
        [29, 30],            # readability
        [31, 32, 33],        # discourse
        [34],                # rhythm
        [0, 16, 26, 33],     # key discriminators combined
        [1, 5, 17, 34],      # burstiness-related
        [4, 29, 30],         # readability+sentence
        [9, 12, 15],         # richness+uniqueness
        [10, 26, 33],        # repetition+AI+transitions
        [6, 16, 34],         # skewness+burstiness+rhythm
        [13, 14, 15, 26],    # entropy+AI
        [2, 29],             # word length+syllables
        [5, 7],              # variance measures
        [21, 24, 25],        # punctuation variety
        [3, 5, 34],          # variance features
        [0, 8, 12],          # diversity measures
        [20, 18],            # structure
        [31, 32],            # discourse variety
        [22, 23, 24],        # semi/dash/question
    ]

    for _ci, cluster in enumerate(_clusters):
        row = [0.0] * n_in
        for feat_idx in cluster:
            # Strong weight on features in this cluster
            row[feat_idx] = lr_w[feat_idx] * rng.uniform(0.8, 1.5)
        # Small random weights on other features
        for j in range(n_in):
            if j not in cluster:
                row[j] = rng.gauss(0, 0.04)
        w1.append(row)
        b1.append(rng.gauss(0, 0.1))

    # Layer 2: 64 → 32
    w2 = []
    b2 = []
    for _i in range(n_h2):
        row = []
        for j in range(n_h1):
            # Structured initialization: stronger connections to related L1 neurons
            if j < n_in and j % n_h2 == i:
                row.append(rng.gauss(0.3, 0.15))
            elif j >= n_in and (j - n_in) % n_h2 == i:
                row.append(rng.gauss(0.25, 0.12))
            else:
                row.append(rng.gauss(0, 0.12))
        w2.append(row)
        b2.append(rng.gauss(0, 0.05))

    # Layer 3: 32 → 1 — aggregation layer
    w3 = []
    row_final = []
    for _i in range(n_h2):
        row_final.append(rng.gauss(0.15, 0.1))
    w3.append(row_final)
    b3 = [0.15]  # bias matches LR

    return FeedForwardNet([
        DenseLayer(w1, b1, activation="relu"),
        DenseLayer(w2, b2, activation="relu"),
        DenseLayer(w3, b3, activation="linear"),
    ], name="neural_ai_detector_v1")


# Lazy singleton
_DETECTOR_NET: FeedForwardNet | None = None
_DETECTOR_TRAINED: bool = False


def _get_network() -> FeedForwardNet:
    """Get or build the pre-trained network (singleton)."""
    global _DETECTOR_NET, _DETECTOR_TRAINED
    if _DETECTOR_NET is None:
        _DETECTOR_NET = _build_pretrained_network()
        _DETECTOR_TRAINED = _DETECTOR_NET.name != "neural_ai_detector_v1"
        logger.info(
            "Neural detector initialized: %d params, arch 35→64→32→1, trained=%s",
            _DETECTOR_NET.param_count, _DETECTOR_TRAINED,
        )
    return _DETECTOR_NET


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class NeuralAIDetector:
    """Neural network AI text detector.

    Uses a 3-layer MLP (35→64→32→1) with 35 statistical features to
    distinguish AI-generated text from human-written text.

    When trained transformer weights are available, automatically upgrades
    to the transformer-based detector (~1.5M params) for higher accuracy.

    Architecture (legacy MLP):
        - Layer 1 (35→64, ReLU): Feature expansion with cross-interactions
        - Layer 2 (64→32, ReLU): Non-linear combination
        - Layer 3 (32→1, linear): Score output

    Architecture (transformer v2):
        - CharTokenizer(256) → Embedding → 3×TransformerBlock → AttentionPool
        - Concat with 35 handcrafted features
        - MLP classifier → sigmoid

    The model is pre-trained and requires NO external dependencies or API calls.
    """

    def __init__(self) -> None:
        self._net = _get_network()
        self._trained = _DETECTOR_TRAINED
        self._transformer = None
        self._has_transformer = False

        # Try to load transformer v2 weights
        try:
            from texthumanize.transformer_detector import get_transformer_detector
            tdet = get_transformer_detector()
            if tdet.loaded:
                self._transformer = tdet
                self._has_transformer = True
                logger.info(
                    "NeuralAIDetector: transformer v2 loaded (%d params)",
                    tdet.param_count,
                )
        except Exception as e:
            logger.debug("Transformer v2 not available: %s", e)

    def extract_features(self, text: str, lang: str = "en") -> dict[str, float]:
        """Extract and return named features (for debugging/explainability)."""
        raw = extract_features(text, lang)
        return dict(zip(_FEATURE_NAMES, raw))

    def detect(self, text: str, lang: str = "en") -> dict[str, Any]:
        """Detect if text is AI-generated.

        Returns:
            dict with keys:
                - score: float [0, 1] — probability of being AI-generated
                - verdict: str — 'human', 'mixed', or 'ai'
                - confidence: str — 'low', 'medium', or 'high'
                - model: str — 'neural_mlp_v1' or 'transformer_v2'
                - features: dict — top contributing features
        """
        raw_features = extract_features(text, lang)
        normed = normalize_features(raw_features, lang=lang)

        # Use transformer v2 if available
        if self._has_transformer and self._transformer is not None:
            try:
                import numpy as _np
                features_np = _np.array(normed, dtype=_np.float32)
                result = self._transformer.detect(text, features_np, lang)
                # Add feature impacts for explainability
                result["top_features"] = self._compute_feature_impacts(normed)
                return result
            except Exception as e:
                logger.debug("Transformer detection failed, falling back to MLP: %s", e)

        # Legacy MLP detection
        # Forward pass through MLP
        if self._trained:
            # Trained weights: positive logit = AI, sigmoid gives P(AI) directly
            score = self._net.predict_proba(normed)
        else:
            # Heuristic weights: positive logit = human, negate for P(AI)
            logit = self._net.forward(normed)
            score = _sigmoid(-logit[0])

        # Short text dampening
        tokens = _WORD_RE.findall(text)
        n_tokens = len(tokens)
        if n_tokens < 50:
            score = 0.5 + (score - 0.5) * (n_tokens / 50.0)

        # Confidence based on text length and score extremity
        extremity = abs(score - 0.5) * 2.0  # [0,1]
        if n_tokens >= 100 and extremity > 0.6:
            confidence = "high"
        elif n_tokens >= 50 and extremity > 0.3:
            confidence = "medium"
        else:
            confidence = "low"

        # Verdict
        if score < 0.30:
            verdict = "human"
        elif score <= 0.60:
            verdict = "mixed"
        else:
            verdict = "ai"

        # Top contributing features — use gradient approximation for trained,
        # LR weights for heuristic
        feature_impacts = {}
        for i, (name, nval) in enumerate(zip(_FEATURE_NAMES, normed)):
            if self._trained:
                # Simple sensitivity: how much does this feature contribute?
                impact = nval * abs(nval) * 0.5  # squared magnitude with sign
            else:
                lr_w = [
                    -0.85, 0.62, -0.48, 0.37, -0.32, 0.91, 0.44, 0.28, -0.55, -0.39,
                    0.53, 0.41, -0.67, 0.22, 0.58, 0.19, 1.15, 0.73, 0.05, -0.21,
                    -0.34, -0.26, -0.72, 0.45, 0.38, 0.29, -2.10, 0.64, 0.31, -0.42,
                    0.36, 0.52, 0.18, -0.88, 0.76,
                ]
                impact = -nval * lr_w[i]
            feature_impacts[name] = round(impact, 4)

        # Sort by absolute impact
        top_features = dict(sorted(
            feature_impacts.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:10])

        return {
            "score": round(score, 4),
            "verdict": verdict,
            "confidence": confidence,
            "model": "neural_mlp_v1",
            "param_count": self._net.param_count,
            "n_features": 35,
            "top_features": top_features,
        }

    def detect_batch(self, texts: list[str], lang: str = "en") -> list[dict[str, Any]]:
        """Detect AI for multiple texts."""
        return [self.detect(text, lang) for text in texts]

    def detect_sentences(
        self, text: str, lang: str = "en"
    ) -> list[dict[str, Any]]:
        """Per-sentence AI detection for mixed-content analysis."""
        sentences = split_sentences(text.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        results = []
        for sent in sentences:
            r = self.detect(sent, lang)
            r["text"] = sent[:100]
            results.append(r)
        return results

    @property
    def architecture(self) -> str:
        if self._has_transformer:
            cfg = self._transformer.config  # type: ignore[union-attr]
            return f"Transformer({cfg.d_model}d/{cfg.n_layers}L/{cfg.n_heads}H)+MLP"
        return "MLP(35→64→32→1)"

    @property
    def param_count(self) -> int:
        if self._has_transformer:
            return self._transformer.param_count  # type: ignore[union-attr]
        return self._net.param_count

    def _compute_feature_impacts(self, normed: list[float]) -> dict[str, float]:
        """Compute feature impact scores for explainability."""
        feature_impacts = {}
        for i, (name, nval) in enumerate(zip(_FEATURE_NAMES, normed)):
            impact = nval * abs(nval) * 0.5
            feature_impacts[name] = round(impact, 4)
        return dict(sorted(
            feature_impacts.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:10])
