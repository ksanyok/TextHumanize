"""Модуль стилевой натурализации текста.

Анализирует и корректирует характерные паттерны автоматически
сгенерированного текста, делая его стилистически ближе к текстам,
написанным человеком.

Основные направления обработки:

1. **Perplexity (перплексия)** — насколько предсказуем текст.
   Автотекст имеет низкую перплексию = высокую предсказуемость.
   Решение: вставить менее предсказуемые конструкции.

2. **Burstiness (вариативность)** — вариация длины предложений.
   Автотекст равномерен (10-20 слов). Живой текст — от 2 до 40 слов.
   Решение: создать естественный ритм.

3. **Coherence uniformity** — равномерная связность.
   Автотекст идеально связывает абзацы. Живой текст — не всегда.
   Решение: варьировать переходы.

4. **Vocabulary uniformity** — использование «безопасных» слов.
   Решение: использовать менее частотные синонимы.

5. **Sentence structure** — предпочтение SVO.
   Решение: инверсия, вставки, фрагменты.

6. **Context-aware replacement (WSD)** — проверка контекста
   перед заменой слова, чтобы не заменять омонимы в неверном значении.

6. **Perfect grammar** — отсутствие естественных конструкций.
   Решение: добавить живые обороты (не ошибки!).

Этот модуль — ключевой для стилевой натурализации текста.
"""

from __future__ import annotations

import logging
import random
import re
from collections import Counter

from texthumanize._replacement_data import (
    EN_EXTRA,
    RU_BOOSTERS_EXTRA,
    RU_EXPANDED,
    RU_PHRASE_EXTRA,
    UK_BOOSTERS_EXTRA,
    UK_EXPANDED,
    UK_PHRASE_EXTRA,
)
from texthumanize.collocation_engine import CollocEngine
from texthumanize.decancel import _is_replacement_safe
from texthumanize.segmenter import has_placeholder, skip_placeholder_sentence
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ─── Характерные стилевые паттерны автоматически сгенерированного текста ───

# Слова, которые AI использует значительно чаще людей (все языки)
_AI_OVERUSED_UNIVERSAL = {
    # Наречия-усилители
    "significantly", "substantially", "considerably", "remarkably",
    "exceptionally", "tremendously", "profoundly", "fundamentally",
    "essentially", "particularly", "specifically", "notably",
    "increasingly", "effectively", "ultimately", "consequently",
    # Прилагательные
    "comprehensive", "crucial", "pivotal", "paramount",
    "innovative", "robust", "seamless", "holistic",
    "cutting-edge", "state-of-the-art", "groundbreaking",
    "transformative", "synergistic", "multifaceted",
    # Глаголы
    "utilize", "leverage", "facilitate", "implement",
    "foster", "enhance", "streamline", "optimize",
    "underscore", "delve", "navigate", "harness",
    "exemplify", "spearhead", "revolutionize", "catalyze",
    # Фразы-связки
    "it is important to note", "it is worth mentioning",
    "in conclusion", "to summarize",
    "in today's world", "in the modern era",
    "plays a crucial role", "is of paramount importance",
}

# Русские AI-паттерны
_AI_OVERUSED_RU = {
    "значительно", "существенно", "чрезвычайно", "крайне",
    "безусловно", "несомненно", "неоспоримо",
    "комплексный", "всеобъемлющий", "инновационный",
    "ключевой", "основополагающий", "первостепенный",
    "фундаментальный", "принципиальный",
    "обеспечивает", "способствует", "представляет собой",
    "необходимо подчеркнуть", "следует отметить",
    "играет ключевую роль", "имеет первостепенное значение",
    "в современном мире", "на сегодняшний день",
    # Phase-2 additions
    "имплементировать", "оптимизировать", "генерировать",
    "трансформировать", "интегрировать", "верифицировать",
    "координировать", "стимулировать", "модернизировать",
    "парадигма", "методология", "инфраструктура",
    "трансформация", "имплементация", "диверсификация",
    "кардинально", "перманентно", "систематически",
    "беспрецедентный", "высокотехнологичный", "многоаспектный",
    "приоритетный", "релевантный", "когнитивный",
    "в рамках", "в контексте", "посредством",
    "тем не менее", "таким образом", "следовательно",
}

# Украинские AI-паттерны
_AI_OVERUSED_UK = {
    "значно", "суттєво", "надзвичайно", "вкрай",
    "безумовно", "безсумнівно", "незаперечно",
    "комплексний", "всеосяжний", "інноваційний",
    "ключовий", "основоположний", "першочерговий",
    "фундаментальний", "принциповий",
    "забезпечує", "сприяє", "являє собою",
    "необхідно підкреслити", "слід зазначити",
    "відіграє ключову роль", "має першочергове значення",
    "у сучасному світі", "на сьогоднішній день",
    # Phase-2 additions
    "імплементувати", "оптимізувати", "генерувати",
    "трансформувати", "інтегрувати", "верифікувати",
    "координувати", "стимулювати", "модернізувати",
    "парадигма", "методологія", "інфраструктура",
    "трансформація", "імплементація", "диверсифікація",
    "кардинально", "перманентно", "систематично",
    "безпрецедентний", "високотехнологічний", "багатоаспектний",
    "пріоритетний", "релевантний", "когнітивний",
    "у рамках", "в контексті", "за допомогою",
    "тим не менш", "таким чином", "відповідно",
}

# Замены для характерных слов автогенерации (язык → {слово → [замены]})
_AI_WORD_REPLACEMENTS = {
    "en": {
        "utilize": ["use", "apply", "work with"],
        "leverage": ["use", "take advantage of", "build on"],
        "facilitate": ["help", "make easier", "support"],
        "implement": ["set up", "put in place", "build"],
        "comprehensive": ["full", "complete", "thorough", "detailed"],
        "crucial": ["key", "important", "central", "major"],
        "pivotal": ["key", "important", "central"],
        "innovative": ["new", "fresh", "creative", "original"],
        "robust": ["strong", "solid", "reliable", "sturdy"],
        "seamless": ["smooth", "easy", "simple"],
        "enhance": ["improve", "boost", "strengthen"],
        "optimize": ["improve", "fine-tune", "tweak"],
        "significantly": ["a lot", "greatly", "by a good margin", "much"],
        "substantially": ["a lot", "greatly", "very much"],
        "consequently": ["so", "as a result", "because of this"],
        "furthermore": ["also", "on top of that", "plus"],
        "moreover": ["also", "besides", "and"],
        "nevertheless": ["still", "even so", "but"],
        "specifically": ["in particular", "especially", "mainly"],
        "effectively": ["well", "really", "in practice"],
        "ultimately": ["in the end", "at the end of the day"],
        "foster": ["encourage", "support", "build"],
        "streamline": ["simplify", "speed up", "clean up"],
        "underscore": ["highlight", "show", "point out"],
        "delve": ["dig into", "look into", "explore"],
        "navigate": ["work through", "deal with", "figure out"],
        "harness": ["use", "tap into", "make use of"],
        "paramount": ["very important", "top", "main"],
        "multifaceted": ["complex", "varied", "many-sided"],
        "holistic": ["overall", "full-picture", "broad"],
        # ── Inflected forms of already-covered base words ──
        "utilization": ["use", "usage", "application"],
        "leveraging": ["using", "building on", "drawing on"],
        "facilitates": ["helps", "supports", "enables"],
        "facilitation": ["help", "support", "assistance"],
        "optimization": ["improvement", "tuning", "fine-tuning"],
        "implementation": ["setup", "rollout", "execution"],
        "demonstrates": ["shows", "proves", "reveals"],
        "encompasses": ["covers", "includes", "spans"],
        "encompass": ["cover", "include", "span"],
        "constitutes": ["makes up", "is", "forms"],
        "necessitate": ["require", "call for", "need"],
        "necessitates": ["requires", "calls for", "needs"],
        "delving": ["digging into", "exploring", "looking into"],
        "fostering": ["encouraging", "building", "supporting"],
        "harnessing": ["using", "tapping into", "channeling"],
        "streamlined": ["simplified", "cleaned up", "lean"],
        "endeavors": ["tries", "attempts", "efforts"],
        "underscores": ["highlights", "shows", "points out"],
        "navigating": ["working through", "dealing with", "handling"],
        "unraveling": ["untangling", "figuring out", "breaking down"],
        # ── Formal connectors and adverbs ──
        "thereby": ["this way", "so", "in doing so"],
        "notwithstanding": ["despite", "even so", "regardless"],
        "whilst": ["while", "as"],
        "aforementioned": ["earlier", "above", "previous"],
        # ── Fancy adjectives/descriptors ──
        "nuanced": ["subtle", "layered", "detailed"],
        "intricate": ["complex", "detailed", "involved"],
        "pertinent": ["relevant", "related", "important"],
        "substantive": ["real", "meaningful", "solid"],
        "overarching": ["main", "broad", "overall"],
        "noteworthy": ["notable", "worth noting", "interesting"],
        "commendable": ["impressive", "praiseworthy", "admirable"],
        "meticulous": ["careful", "thorough", "precise"],
        "meticulously": ["carefully", "thoroughly", "with care"],
        "transformative": ["game-changing", "major", "powerful"],
        "cutting-edge": ["latest", "modern", "advanced"],
        "indispensable": ["essential", "vital", "necessary"],
        "invaluable": ["priceless", "extremely useful", "key"],
        "groundbreaking": ["pioneering", "novel", "breakthrough"],
        # ── AI-metaphor vocabulary ──
        "landscape": ["scene", "space", "field", "world"],
        "paradigm": ["model", "approach", "framework"],
        "synergy": ["teamwork", "combined effect", "collaboration"],
        "cornerstone": ["foundation", "basis", "core"],
        "tapestry": ["mix", "blend", "web"],
        "beacon": ["guide", "signal", "example"],
        "linchpin": ["key part", "backbone", "anchor"],
        "testament": ["proof", "sign", "evidence"],
        "realm": ["area", "field", "world", "domain"],
        "culmination": ["peak", "result", "climax"],
        "juxtaposition": ["contrast", "comparison", "side-by-side look"],
        "underpinning": ["basis", "foundation", "backbone"],
        # ── Formal verbs ──
        "adhere": ["stick to", "follow", "keep to"],
        "adherence": ["sticking to", "following", "commitment"],
        "delineate": ["outline", "describe", "lay out"],
        "delineates": ["outlines", "describes", "lays out"],
        "elucidate": ["explain", "clarify", "spell out"],
        "embark": ["start", "begin", "set out"],
        "spearhead": ["lead", "drive", "champion"],
        "unravel": ["untangle", "figure out", "break down"],
        # ── Additional word shortening ──
        # (highest-impact feature: avg_word_length Δ=+0.23 for EN)
        "capabilities": ["skills", "tools", "powers"],
        "recognition": ["spotting", "ID", "finding"],
        "integration": ["adding", "mixing", "blend"],
        "predictions": ["guesses", "calls", "bets"],
        "enhancement": ["boost", "lift", "gain"],
        "improvement": ["fix", "boost", "gain"],
        "information": ["info", "data", "facts"],
        "environment": ["setting", "space", "world"],
        "organization": ["group", "body", "firm"],
        "architecture": ["layout", "setup", "design"],
        "dramatically": ["hugely", "wildly", "a lot"],
        "applications": ["apps", "uses", "tools"],
        "opportunities": ["chances", "shots", "ways"],
        "requirements": ["needs", "rules", "specs"],
        "successfully": ["well", "with ease", "nicely"],
        "professionals": ["pros", "experts", "staff"],
        "traditionally": ["usually", "often", "before"],
        "understanding": ["grasp", "sense", "view"],
        "establishment": ["setup", "start", "founding"],
        "transformation": ["shift", "change", "switch"],
        "functionality": ["features", "tools", "uses"],
        "accessibility": ["access", "reach", "ease"],
        "sustainability": ["lasting", "green", "viable"],
        "challenges": ["issues", "hurdles", "snags"],
        "stakeholders": ["parties", "groups", "people"],
        "continuously": ["always", "non-stop", "still"],
        "accumulated": ["built up", "gathered", "saved"],
        # ── Academic vocabulary simplification ──
        # (reduces avg_word_length, avg_syllables, improves flesch_score)
        "sophisticated": ["complex", "advanced", "clever"],
        "methodology": ["method", "approach", "process"],
        "methodological": ["research", "study", "scientific"],
        "methodologies": ["methods", "approaches", "ways"],
        "interconnected": ["linked", "tied", "related"],
        "computational": ["computer", "digital", "data"],
        "operational": ["working", "daily", "practical"],
        "contemporary": ["modern", "current", "present"],
        "unprecedented": ["rare", "extreme", "record"],
        "approximately": ["about", "roughly", "around"],
        "predominantly": ["mostly", "mainly", "largely"],
        "fundamentally": ["basically", "at its core", "deeply"],
        "systematically": ["step by step", "in order", "carefully"],
        "characteristics": ["traits", "features", "qualities"],
        "infrastructure": ["setup", "system", "base"],
        "circumstances": ["conditions", "cases", "situations"],
        "communication": ["contact", "talk", "exchange"],
        "collaboration": ["teamwork", "joint work", "effort"],
        "determination": ["resolve", "grit", "drive"],
        "consideration": ["thought", "care", "attention"],
        "investigation": ["study", "look", "research"],
        "implications": ["effects", "results", "impact"],
        "perspectives": ["views", "angles", "takes"],
        "frameworks": ["models", "systems", "setups"],
        "parameters": ["settings", "factors", "variables"],
        "mechanisms": ["ways", "processes", "methods"],
        "disciplines": ["fields", "areas", "subjects"],
        "empirical": ["observed", "tested", "real"],
        "analytical": ["logical", "detailed", "careful"],
        "imperative": ["vital", "key", "pressing"],
        "significant": ["big", "major", "important"],
        "particularly": ["especially", "mainly", "notably"],
        "technological": ["tech", "digital", "modern"],
        "advancements": ["advances", "progress", "gains"],
        "convergence": ["meeting", "merging", "joining"],
        "interdisciplinary": ["cross-field", "mixed", "joint"],
        "algorithms": ["methods", "formulas", "programs"],
        "efficiency": ["speed", "output", "results"],
        "phenomena": ["events", "patterns", "things"],
        "rigorous": ["strict", "tough", "thorough"],
        "protocols": ["rules", "steps", "procedures"],
    },
    "ru": RU_EXPANDED,
    "uk": UK_EXPANDED,
    "de": {
        "implementieren": ["umsetzen", "einführen", "einrichten"],
        "Implementierung": ["Umsetzung", "Einführung"],
        "optimieren": ["verbessern", "anpassen", "verfeinern"],
        "Optimierung": ["Verbesserung", "Anpassung"],
        "signifikant": ["deutlich", "merklich", "spürbar"],
        "fundamental": ["grundlegend", "wesentlich", "elementar"],
        "innovativ": ["neu", "neuartig", "kreativ"],
        "umfassend": ["breit", "vollständig", "gründlich"],
        "umfassender": ["breiter", "vollständiger", "gründlicher"],
        "gewährleisten": ["sicherstellen", "sorgen für"],
        "sicherzustellen": ["zu sorgen", "zu gewährleisten"],
        "sicherstellen": ["sorgen", "gewährleisten"],
        "darüber hinaus": ["außerdem", "zudem", "dazu"],
        "nichtsdestotrotz": ["trotzdem", "aber", "dennoch"],
        "demzufolge": ["daher", "deshalb", "also"],
        "evaluieren": ["bewerten", "prüfen", "beurteilen"],
        "generieren": ["erzeugen", "erstellen", "schaffen"],
        "adressieren": ["angehen", "behandeln", "lösen"],
        "essentiell": ["wichtig", "nötig", "wesentlich"],
        "konsequent": ["folgerichtig", "durchgehend", "stetig"],
        "adäquat": ["passend", "angemessen", "geeignet"],
        "sukzessive": ["nach und nach", "schrittweise", "allmählich"],
        "inhärent": ["eigen", "innewohnend", "wesenseigen"],
        "primär": ["hauptsächlich", "vor allem", "in erster Linie"],
        "manifestieren": ["zeigen", "offenbaren", "deutlich machen"],
        # Noun forms often used in AI text
        "Berücksichtigung": ["Beachtung", "Rücksicht"],
        "sorgfältig": ["gründlich", "gewissenhaft", "genau"],
        "sorgfältige": ["gründliche", "genaue"],
        "angemessen": ["passend", "richtig", "geeignet"],
        "grundlegend": ["wesentlich", "elementar", "zentral"],
        "grundlegenden": ["wesentlichen", "zentralen", "wichtigen"],
        "verschiedener": ["unterschiedlicher", "diverser", "mehrerer"],
        "verschiedenen": ["unterschiedlichen", "diversen", "mehreren"],
        "bestehender": ["vorhandener", "aktueller", "bisheriger"],
        "erfordert": ["braucht", "verlangt", "benötigt"],
        "darstellt": ["bildet", "ist", "ausmacht"],
        "wesentlich": ["wichtig", "zentral", "bedeutend"],
    },
    "fr": {
        "implémenter": ["mettre en place", "réaliser", "installer"],
        "optimiser": ["améliorer", "ajuster", "perfectionner"],
        "significatif": ["notable", "important", "marquant"],
        "fondamental": ["essentiel", "de base", "central"],
        "innovant": ["nouveau", "novateur", "créatif"],
        "exhaustif": ["complet", "détaillé", "approfondi"],
        "garantir": ["assurer", "veiller à"],
        "en outre": ["de plus", "aussi", "par ailleurs"],
        "néanmoins": ["toutefois", "cependant", "mais"],
        "par conséquent": ["donc", "du coup", "ainsi"],
        "conceptualiser": ["penser", "imaginer", "concevoir"],
        "préconiser": ["recommander", "conseiller", "suggérer"],
        "appréhender": ["comprendre", "saisir", "cerner"],
        "substantiel": ["important", "considérable", "ample"],
        "primordial": ["essentiel", "capital", "vital"],
        "inhérent": ["propre", "naturel", "lié"],
        "adéquat": ["adapté", "convenable", "approprié"],
        "subséquent": ["suivant", "après", "ultérieur"],
        "préalable": ["avant", "premier", "initial"],
        "concrétiser": ["réaliser", "accomplir", "matérialiser"],
    },
    "es": {
        "implementar": ["poner en marcha", "llevar a cabo", "aplicar"],
        "optimizar": ["mejorar", "ajustar", "perfeccionar"],
        "significativo": ["notable", "importante", "destacado"],
        "fundamental": ["esencial", "básico", "central"],
        "innovador": ["nuevo", "novedoso", "creativo"],
        "exhaustivo": ["completo", "detallado", "amplio"],
        "garantizar": ["asegurar", "velar por"],
        "además": ["también", "aparte de eso", "igualmente"],
        "sin embargo": ["pero", "no obstante", "aun así"],
        "por consiguiente": ["por eso", "así que", "entonces"],
        "conceptualizar": ["pensar", "idear", "concebir"],
        "potenciar": ["fortalecer", "mejorar", "impulsar"],
        "coadyuvar": ["ayudar", "contribuir", "apoyar"],
        "paradigmático": ["ejemplar", "modelo", "típico"],
        "exponencial": ["rápido", "acelerado", "veloz"],
        "inherente": ["propio", "natural", "intrínseco"],
        "subsiguiente": ["siguiente", "posterior", "ulterior"],
        "primordial": ["esencial", "principal", "vital"],
        "multidimensional": ["variado", "complejo", "amplio"],
        "viabilizar": ["hacer posible", "permitir", "facilitar"],
    },
    "pl": {
        "implementować": ["wdrożyć", "wprowadzić", "zastosować"],
        "optymalizować": ["ulepszać", "poprawiać", "doskonalić"],
        "znacząco": ["wyraźnie", "odczuwalnie", "mocno"],
        "fundamentalny": ["podstawowy", "zasadniczy", "kluczowy"],
        "innowacyjny": ["nowy", "nowatorski", "twórczy"],
        "kompleksowy": ["pełny", "wszechstronny", "całościowy"],
        "ponadto": ["poza tym", "oprócz tego", "do tego"],
        "niemniej jednak": ["ale", "jednak", "mimo to"],
        "w konsekwencji": ["dlatego", "więc", "zatem"],
        "ewaluować": ["oceniać", "sprawdzać", "weryfikować"],
        "koordynować": ["organizować", "zarządzać", "kierować"],
        "dedykować": ["poświęcać", "przeznaczać", "przydzielać"],
        "kluczowy": ["główny", "najważniejszy", "centralny"],
        "zasadniczy": ["główny", "podstawowy", "istotny"],
        "adekwatny": ["odpowiedni", "stosowny", "właściwy"],
        "priorytetowy": ["najważniejszy", "główny", "pilny"],
        "komplementarny": ["uzupełniający", "dodatkowy", "wspierający"],
        "determinować": ["określać", "wyznaczać", "decydować"],
    },
    "pt": {
        "implementar": ["pôr em prática", "realizar", "aplicar"],
        "otimizar": ["melhorar", "ajustar", "aperfeiçoar"],
        "significativo": ["notável", "importante", "expressivo"],
        "fundamental": ["essencial", "básico", "central"],
        "inovador": ["novo", "criativo", "original"],
        "abrangente": ["completo", "amplo", "detalhado"],
        "além disso": ["também", "por outro lado", "mais ainda"],
        "no entanto": ["mas", "porém", "contudo"],
        "consequentemente": ["por isso", "assim", "então"],
        "viabilizar": ["possibilitar", "tornar possível", "facilitar"],
        "operacionalizar": ["pôr em prática", "executar", "realizar"],
        "primordial": ["essencial", "principal", "vital"],
        "inerente": ["próprio", "natural", "intrínseco"],
        "paradigmático": ["exemplar", "modelo", "típico"],
        "contundente": ["forte", "decisivo", "claro"],
        "exponencial": ["rápido", "acelerado", "intenso"],
        "subsequente": ["seguinte", "posterior", "ulterior"],
        "exaustivo": ["completo", "detalhado", "minucioso"],
    },
    "it": {
        "implementare": ["mettere in atto", "realizzare", "applicare"],
        "ottimizzare": ["migliorare", "perfezionare", "affinare"],
        "significativo": ["notevole", "importante", "rilevante"],
        "fondamentale": ["essenziale", "basilare", "centrale"],
        "innovativo": ["nuovo", "creativo", "originale"],
        "esaustivo": ["completo", "dettagliato", "approfondito"],
        "inoltre": ["in più", "anche", "per di più"],
        "tuttavia": ["ma", "però", "eppure"],
        "di conseguenza": ["quindi", "perciò", "così"],
        "determinare": ["stabilire", "decidere", "fissare"],
        "concretizzare": ["realizzare", "mettere in pratica", "attuare"],
        "primario": ["principale", "primo", "essenziale"],
        "inerente": ["proprio", "legato", "connesso"],
        "preponderante": ["principale", "dominante", "maggiore"],
        "imprescindibile": ["necessario", "essenziale", "irrinunciabile"],
        "onnicomprensivo": ["completo", "totale", "globale"],
        "paradigmatico": ["esemplare", "tipico", "modello"],
        "finalizzare": ["concludere", "finire", "completare"],
    },
}

# Merge expanded dictionaries from _replacement_data module
_AI_WORD_REPLACEMENTS["en"].update(EN_EXTRA)

# Фразовые паттерны AI (для замены целиком)
_AI_PHRASE_PATTERNS = {
    "en": {
        "it is important to note that": ["notably,", "keep in mind:", "worth knowing:"],
        "it is worth mentioning that": ["interestingly,", "by the way,", "also,"],
        "in today's world": ["today", "these days", "right now", "currently"],
        "in the modern era": ["nowadays", "today", "at this point"],
        "plays a crucial role": ["matters a lot", "is really important", "is central"],
        "is of paramount importance": ["is very important", "really matters"],
        "in order to": ["to"],
        "due to the fact that": ["because", "since"],
        "at the end of the day": ["really", "when it comes down to it"],
        "a wide range of": ["many", "various", "different"],
        "it goes without saying": ["clearly", "obviously"],
        "in light of": ["given", "considering", "because of"],
        "on the other hand": ["then again", "but", "at the same time"],
        "as a matter of fact": ["actually", "in fact", "really"],
        # --- New patterns (inspired by humano + GPTZero signals) ---
        "it should be noted that": ["one thing:", "keep in mind —"],
        "it is essential to": ["you need to", "the key is to"],
        "it is crucial that": ["what matters is", "the priority is"],
        "this serves as a testament to": ["this shows", "this proves"],
        "this underscores the importance of": ["this highlights", "this shows why"],
        "needless to say": ["obviously", "of course"],
        "with that being said": ["all the same,", "still,"],
        "it is evident that": ["clearly,", "you can see —"],
        "for the purpose of": ["for", "to"],
        "in the process of": ["while"],
        "has the potential to": ["can", "might", "could"],
        "is capable of": ["can"],
        "take into consideration": ["consider", "keep in mind"],
        "a significant number of": ["many", "plenty of", "quite a few"],
        "the vast majority of": ["most", "nearly all"],
        "despite the fact that": ["even though", "although"],
        "in the event that": ["if"],
        "at this point in time": ["now", "right now"],
        "prior to": ["before"],
        "subsequent to": ["after"],
        "in close proximity to": ["near", "close to"],
        "is indicative of": ["shows", "points to", "signals"],
        "serves as an example of": ["is a good example of", "shows"],
    },
    "ru": {
        "необходимо подчеркнуть": ["стоит сказать", "отметим"],
        "следует отметить": ["заметим", "стоит сказать", "скажем"],
        "играет ключевую роль": ["очень важен", "центральный"],
        "имеет первостепенное значение": ["очень важно", "критически важно"],
        "в современном мире": ["сегодня", "сейчас", "в наше время"],
        "на сегодняшний день": ["сейчас", "сегодня", "пока"],
        "в целях обеспечения": ["чтобы", "для того чтобы"],
        "в рамках данного": ["здесь", "в этом"],
        "широкий спектр": ["много", "разные", "целый ряд"],
        "не подлежит сомнению": ["ясно", "очевидно", "понятно"],
        "с учётом того что": ["учитывая", "раз", "поскольку"],
        # --- New patterns ---
        "представляет собой": ["это", "является", "выступает"],
        "в значительной степени": ["во многом", "сильно", "заметно"],
        "в контексте данного": ["тут", "здесь", "в этом"],
        "является неотъемлемой частью": ["входит в", "часть", "неразрывно связан с"],
        "оказывает существенное влияние": ["сильно влияет", "влияет", "сказывается на"],
        "в процессе реализации": ["при выполнении", "во время", "в ходе"],
        "с точки зрения": ["если смотреть на", "по части"],
        "целесообразно отметить": ["стоит сказать", "добавим"],
        "тот факт, что": ["то, что"],
        "исходя из вышеизложенного": ["итого", "резюмируя", "в итоге"],
    },
    "uk": {
        "необхідно підкреслити": ["варто сказати", "зазначимо"],
        "слід зазначити": ["зазначимо", "варто сказати", "скажемо"],
        "відіграє ключову роль": ["дуже важливий", "центральний"],
        "має першочергове значення": ["дуже важливо", "критично важливо"],
        "у сучасному світі": ["сьогодні", "зараз", "у наш час"],
        "на сьогоднішній день": ["зараз", "сьогодні", "поки"],
    },
    "de": {
        "es ist festzustellen": ["es zeigt sich", "klar ist"],
        "in Anbetracht der Tatsache": ["angesichts", "weil"],
        "zum Zwecke der": ["für", "um zu"],
        "es lässt sich konstatieren": ["man sieht", "es zeigt sich"],
        "von großer Bedeutung": ["wichtig", "bedeutend"],
        "eine zentrale Rolle spielen": ["wichtig sein", "zentral sein"],
        "im Hinblick auf": ["für", "bezüglich", "was betrifft"],
        "aufgrund der Tatsache": ["weil", "da", "denn"],
        "ist es wesentlich": ["ist es wichtig", "sollte man"],
        "stellt einen grundlegenden Aspekt dar": [
            "ist ein wichtiger Punkt", "ist zentral", "spielt eine wichtige Rolle",
        ],
        "einen grundlegenden Aspekt": ["einen wichtigen Punkt", "eine Kernfrage"],
        "unter Berücksichtigung": ["mit Blick auf", "angesichts"],
        "in Bezug auf": ["zu", "bei", "was betrifft"],
        "darüber hinaus ist es": ["außerdem ist es", "zudem sollte man"],
        "Darüber hinaus ist": ["Außerdem ist", "Zudem ist"],
        "Zudem stellt": ["Und", "Außerdem bildet", "Dazu kommt:"],
    },
    "fr": {
        "il convient de noter": ["notons que", "on remarque que"],
        "force est de constater": ["on voit que", "clairement"],
        "dans le cadre de": ["dans", "pendant", "lors de"],
        "de manière significative": ["nettement", "clairement", "beaucoup"],
        "joue un rôle crucial": ["est très important", "compte beaucoup"],
        "revêt une importance": ["est important", "compte"],
        "il est à souligner": ["soulignons", "important :"],
        "en vue de": ["pour", "afin de"],
    },
    "es": {
        "es menester señalar": ["cabe decir", "vale notar"],
        "en el marco de": ["dentro de", "en", "durante"],
        "de manera significativa": ["mucho", "claramente", "bastante"],
        "desempeña un papel crucial": ["es muy importante", "es clave"],
        "reviste especial importancia": ["es importante", "importa mucho"],
        "resulta imprescindible": ["es necesario", "hace falta"],
        "con el objetivo de": ["para", "con el fin de"],
        "en lo que respecta a": ["en cuanto a", "sobre"],
    },
    "it": {
        "è doveroso sottolineare": ["va detto", "bisogna dire"],
        "nell'ambito di": ["in", "dentro", "durante"],
        "in maniera significativa": ["molto", "parecchio", "nettamente"],
        "riveste un ruolo cruciale": ["è molto importante", "conta molto"],
        "risulta necessario": ["bisogna", "serve", "occorre"],
        "per quanto concerne": ["per quanto riguarda", "riguardo a"],
        "al fine di": ["per", "allo scopo di"],
        "assume un'importanza": ["è importante", "conta"],
    },
    "pl": {
        "należy podkreślić": ["warto powiedzieć", "zaznaczmy"],
        "w odniesieniu do": ["wobec", "co do", "jeśli chodzi o"],
        "odgrywa kluczową rolę": ["jest bardzo ważny", "ma duże znaczenie"],
        "ma fundamentalne znaczenie": ["jest bardzo ważne", "jest kluczowe"],
        "w istotny sposób": ["znacznie", "dużo", "bardzo"],
        "mając na uwadze": ["biorąc pod uwagę", "z uwagi na"],
        "w ramach": ["w", "podczas", "w obrębie"],
        "w zakresie": ["w", "pod względem", "co do"],
    },
    "pt": {
        "importa referir": ["vale notar", "cabe dizer"],
        "no âmbito de": ["em", "dentro de", "durante"],
        "de forma significativa": ["muito", "bastante", "claramente"],
        "desempenha um papel crucial": ["é muito importante", "é central"],
        "torna-se imprescindível": ["é preciso", "é necessário"],
        "no que diz respeito a": ["quanto a", "sobre"],
        "com o objetivo de": ["para", "a fim de"],
        "reveste-se de importância": ["é importante", "importa"],
    },
}

# Merge expanded phrase patterns
_AI_PHRASE_PATTERNS["ru"].update(RU_PHRASE_EXTRA)
_AI_PHRASE_PATTERNS["uk"].update(UK_PHRASE_EXTRA)

# Вставки для повышения перплексии (естественные «человеческие» конструкции)
_PERPLEXITY_BOOSTERS = {
    "en": {
        "hedges": [
            "probably", "likely", "I think", "seems like",
            "arguably", "in a way", "sort of", "more or less",
        ],
        "discourse_markers": [
            "well", "honestly", "actually", "basically",
            "look", "thing is", "anyway", "I mean",
        ],
        "parenthetical": [
            "(though not always)",
            "(at least in theory)",
            "(or close to it)",
            "(give or take)",
            "(more on that later)",
            "(if we're being honest)",
        ],
        "rhetorical_questions": [
            "But why does this matter?",
            "So what does that mean?",
            "What's the takeaway?",
            "Sounds familiar?",
        ],
        "fragments": [
            "Not always.",
            "Not quite.",
            "Fair enough.",
            "And for good reason.",
            "No surprise there.",
            "A big deal.",
            "The bottom line?",
        ],
    },
    "ru": {
        "hedges": [
            "наверное", "скорее всего", "похоже", "думаю",
            "пожалуй", "в каком-то смысле", "отчасти",
        ],
        "discourse_markers": [
            "ну", "вообще-то", "на самом деле", "в общем",
            "если честно", "проще говоря", "грубо говоря",
            "так сказать", "к слову",
        ],
        "parenthetical": [
            "(хотя не всегда)",
            "(по крайней мере в теории)",
            "(или около того)",
            "(плюс-минус)",
            "(об этом позже)",
            "(если быть честным)",
        ],
        "rhetorical_questions": [
            "Но почему это важно?",
            "И что это значит?",
            "Какой вывод?",
            "Знакомо?",
            "В чём суть?",
        ],
        "fragments": [
            "Не всегда.",
            "Не совсем.",
            "Логично.",
            "И не зря.",
            "Неудивительно.",
            "Это важно.",
            "Суть вот в чём.",
        ],
    },
    "uk": {
        "hedges": [
            "напевно", "скоріше за все", "схоже", "думаю",
            "мабуть", "певною мірою", "частково",
        ],
        "discourse_markers": [
            "ну", "взагалі-то", "насправді", "загалом",
            "якщо чесно", "простіше кажучи", "грубо кажучи",
            "так би мовити", "до речі",
        ],
        "parenthetical": [
            "(хоча не завжди)",
            "(принаймні в теорії)",
            "(або близько до того)",
            "(плюс-мінус)",
            "(про це пізніше)",
        ],
        "rhetorical_questions": [
            "Але чому це важливо?",
            "І що це означає?",
            "Який висновок?",
            "Знайомо?",
        ],
        "fragments": [
            "Не завжди.",
            "Не зовсім.",
            "Логічно.",
            "І не дарма.",
            "Це важливо.",
        ],
    },
    "de": {
        "hedges": ["wahrscheinlich", "vermutlich", "wohl", "irgendwie",
                   "möglicherweise", "unter Umständen", "gewissermaßen"],
        "discourse_markers": ["naja", "eigentlich", "im Grunde", "ehrlich gesagt",
                              "genau genommen", "streng genommen", "nebenbei"],
        "parenthetical": [
            "(wenn man so will)",
            "(zumindest theoretisch)",
            "(mehr oder weniger)",
            "(immerhin)",
        ],
        "rhetorical_questions": [
            "Aber warum ist das wichtig?",
            "Was bedeutet das nun?",
            "Klingt bekannt?",
        ],
        "fragments": ["Nicht immer.", "Logisch.", "Kein Wunder.",
                      "Und das aus gutem Grund.", "Gut so.", "Eben."],
    },
    "fr": {
        "hedges": ["probablement", "sans doute", "peut-être", "en quelque sorte",
                   "vraisemblablement", "d'une certaine manière", "apparemment"],
        "discourse_markers": ["bon", "en fait", "franchement", "disons",
                              "avouons-le", "soit dit en passant", "au passage"],
        "parenthetical": [
            "(du moins en théorie)",
            "(ou presque)",
            "(à peu de chose près)",
            "(soyons honnêtes)",
        ],
        "rhetorical_questions": [
            "Mais pourquoi est-ce important ?",
            "Et alors, que retenir ?",
            "Ça vous dit quelque chose ?",
        ],
        "fragments": ["Pas toujours.", "Logique.", "C'est normal.",
                      "Et pour cause.", "En un mot.", "Voilà."],
    },
    "es": {
        "hedges": ["probablemente", "seguramente", "quizás", "en cierto modo",
                   "posiblemente", "de alguna manera", "aparentemente"],
        "discourse_markers": ["bueno", "la verdad", "o sea", "digamos",
                              "a decir verdad", "es más", "eso sí"],
        "parenthetical": [
            "(al menos en teoría)",
            "(o casi)",
            "(más o menos)",
            "(seamos honestos)",
        ],
        "rhetorical_questions": [
            "¿Pero por qué importa?",
            "¿Y qué significa eso?",
            "¿Suena familiar?",
        ],
        "fragments": ["No siempre.", "Lógico.", "Normal.",
                      "Y con razón.", "En una palabra.", "Claro."],
    },
    "it": {
        "hedges": ["probabilmente", "forse", "in un certo senso", "pare",
                   "verosimilmente", "in qualche modo", "apparentemente"],
        "discourse_markers": ["beh", "in realtà", "diciamo", "onestamente",
                              "tra l'altro", "a proposito", "per così dire"],
        "parenthetical": [
            "(almeno in teoria)",
            "(o quasi)",
            "(più o meno)",
            "(a ben vedere)",
        ],
        "rhetorical_questions": [
            "Ma perché è importante?",
            "E cosa significa?",
            "Suona familiare?",
        ],
        "fragments": ["Non sempre.", "Logico.", "Normale.",
                      "E a ragione.", "In una parola.", "Ecco."],
    },
    "pl": {
        "hedges": ["prawdopodobnie", "zapewne", "być może", "w pewnym sensie",
                   "przypuszczalnie", "poniekąd", "najwyraźniej"],
        "discourse_markers": ["no", "tak naprawdę", "powiedzmy", "szczerze mówiąc",
                              "w gruncie rzeczy", "nawiasem mówiąc", "zresztą"],
        "parenthetical": [
            "(przynajmniej w teorii)",
            "(lub prawie)",
            "(mniej więcej)",
            "(bądź co bądź)",
        ],
        "rhetorical_questions": [
            "Ale dlaczego to ważne?",
            "I co to oznacza?",
            "Brzmi znajomo?",
        ],
        "fragments": ["Nie zawsze.", "Logiczne.", "Normalne.",
                      "I słusznie.", "Jednym słowem.", "Właśnie."],
    },
    "pt": {
        "hedges": ["provavelmente", "talvez", "de certa forma", "aparentemente",
                   "possivelmente", "de alguma maneira", "supostamente"],
        "discourse_markers": ["bom", "na verdade", "digamos", "sinceramente",
                              "aliás", "por sinal", "a propósito"],
        "parenthetical": [
            "(pelo menos em teoria)",
            "(ou quase)",
            "(mais ou menos)",
            "(sejamos honestos)",
        ],
        "rhetorical_questions": [
            "Mas por que isso importa?",
            "E o que isso significa?",
            "Soa familiar?",
        ],
        "fragments": ["Nem sempre.", "Lógico.", "Normal.",
                      "E com razão.", "Em uma palavra.", "Pois é."],
    },
}

# Merge expanded perplexity boosters for RU/UK
for _category, _items in RU_BOOSTERS_EXTRA.items():
    _PERPLEXITY_BOOSTERS["ru"].setdefault(_category, []).extend(_items)
for _category, _items in UK_BOOSTERS_EXTRA.items():
    _PERPLEXITY_BOOSTERS["uk"].setdefault(_category, []).extend(_items)
# De-duplicate lists
for _lang_data in _PERPLEXITY_BOOSTERS.values():
    for _cat in _lang_data:
        _lang_data[_cat] = list(dict.fromkeys(_lang_data[_cat]))

# ─── Semantic Intensity Clusters ────────────────────────────────
# Замена «very/really + adj» → одно ёмкое слово.
# Это уменьшает word-count и повышает лексическую плотность — признак
# человеческого текста.  Сортировано по частоте в AI-тексте.
_INTENSITY_CLUSTERS: dict[str, list[tuple[str, list[str]]]] = {
    "en": [
        # (паттерн regex, варианты замены)
        (r"\bvery good\b", ["excellent", "great", "superb"]),
        (r"\bvery bad\b", ["terrible", "awful", "dreadful"]),
        (r"\bvery big\b", ["huge", "massive", "enormous"]),
        (r"\bvery small\b", ["tiny", "minuscule", "compact"]),
        (r"\bvery important\b", ["crucial", "vital", "key"]),
        (r"\bvery difficult\b", ["tough", "grueling", "daunting"]),
        (r"\bvery easy\b", ["effortless", "simple", "a breeze"]),
        (r"\bvery fast\b", ["rapid", "lightning-fast", "swift"]),
        (r"\bvery slow\b", ["sluggish", "glacial", "plodding"]),
        (r"\bvery old\b", ["ancient", "aged", "antique"]),
        (r"\bvery new\b", ["brand-new", "fresh", "cutting-edge"]),
        (r"\bvery hot\b", ["scorching", "blazing", "boiling"]),
        (r"\bvery cold\b", ["freezing", "frigid", "icy"]),
        (r"\bvery happy\b", ["thrilled", "ecstatic", "overjoyed"]),
        (r"\bvery sad\b", ["heartbroken", "devastated", "miserable"]),
        (r"\bvery tired\b", ["exhausted", "drained", "worn out"]),
        (r"\bvery hungry\b", ["starving", "famished", "ravenous"]),
        (r"\bvery beautiful\b", ["stunning", "gorgeous", "breathtaking"]),
        (r"\bvery ugly\b", ["hideous", "ghastly", "unsightly"]),
        (r"\bvery quiet\b", ["silent", "hushed", "muted"]),
        (r"\bvery loud\b", ["deafening", "thunderous", "blaring"]),
        (r"\bvery rich\b", ["wealthy", "affluent", "loaded"]),
        (r"\bvery poor\b", ["destitute", "impoverished", "broke"]),
        (r"\bvery strong\b", ["powerful", "mighty", "robust"]),
        (r"\bvery weak\b", ["feeble", "frail", "fragile"]),
        (r"\bvery bright\b", ["brilliant", "radiant", "dazzling"]),
        (r"\bvery dark\b", ["pitch-black", "dim", "murky"]),
        (r"\bvery scared\b", ["terrified", "petrified", "panic-stricken"]),
        (r"\bvery angry\b", ["furious", "livid", "enraged"]),
        (r"\bvery simple\b", ["straightforward", "basic", "elementary"]),
        (r"\bvery complex\b", ["intricate", "elaborate", "convoluted"]),
        (r"\breally good\b", ["excellent", "outstanding", "top-notch"]),
        (r"\breally bad\b", ["terrible", "horrible", "atrocious"]),
        (r"\breally big\b", ["massive", "gigantic", "colossal"]),
        (r"\breally important\b", ["essential", "critical", "paramount"]),
        (r"\breally difficult\b", ["extremely tough", "really hard", "a real challenge"]),
        (r"\bextremely important\b", ["absolutely vital", "mission-critical", "essential"]),
        (r"\bhighly significant\b", ["pivotal", "game-changing", "landmark"]),
        (r"\bvery interesting\b", ["fascinating", "captivating", "gripping"]),
        (r"\bvery effective\b", ["highly potent", "remarkably efficient", "spot-on"]),
    ],
    "ru": [
        (r"\bочень хорош(?:ий|ая|ее|ие)\b", ["отличн\\1", "превосходн\\1", "великолепн\\1"]),
        (r"\bочень плох(?:ой|ая|ое|ие)\b", ["ужасн\\1", "отвратительн\\1"]),
        (r"\bочень больш(?:ой|ая|ое|ие)\b", ["огромн\\1", "колоссальн\\1", "гигантск\\1"]),
        (r"\bочень маленьк(?:ий|ая|ое|ие)\b", ["крошечн\\1", "миниатюрн\\1"]),
        (r"\bочень важн(?:ый|ая|ое|ые)\b", ["ключев\\1", "критическ\\1"]),
        (r"\bочень сложн(?:ый|ая|ое|ые)\b", ["крайне непрост\\1", "головоломн\\1"]),
        (r"\bочень быстр(?:ый|ая|ое|ые)\b", ["молниеносн\\1", "стремительн\\1"]),
        (r"\bочень медленн(?:ый|ая|ое|ые)\b", ["черепаш\\1", "вял\\1"]),
        (r"\bочень красив(?:ый|ая|ое|ые)\b", ["потрясающ\\1", "великолепн\\1"]),
        (r"\bочень странн(?:ый|ая|ое|ые)\b", ["диковинн\\1", "причудлив\\1"]),
        (r"\bочень интересн(?:ый|ая|ое|ые)\b", ["увлекательн\\1", "захватывающ\\1"]),
    ],
    "uk": [
        (r"\bдуже гарн(?:ий|а|е|і)\b", ["чудов\\1", "прекрасн\\1", "розкішн\\1"]),
        (r"\bдуже поган(?:ий|а|е|і)\b", ["жахлив\\1", "огидн\\1"]),
        (r"\bдуже велик(?:ий|а|е|і)\b", ["величезн\\1", "колосальн\\1"]),
        (r"\bдуже маленьк(?:ий|а|е|і)\b", ["крихітн\\1", "мініатюрн\\1"]),
        (r"\bдуже важлив(?:ий|а|е|і)\b", ["ключов\\1", "критичн\\1"]),
        (r"\bдуже складн(?:ий|а|е|і)\b", ["вкрай непрост\\1", "заплутан\\1"]),
        (r"\bдуже швидк(?:ий|а|е|і)\b", ["блискавичн\\1", "стрімк\\1"]),
        (r"\bдуже цікав(?:ий|а|е|і)\b", ["захопливо цікав\\1", "вражаюч\\1"]),
    ],
}


class TextNaturalizer:
    """Модуль стилевой натурализации текста.

    Работает на уровне текста целиком (не пословно).
    Применяется ПОСЛЕ основных трансформаций.
    """

    def __init__(
        self,
        lang: str = "ru",
        profile: str = "web",
        intensity: int = 60,
        seed: int | None = None,
    ):
        self.lang = lang
        self.profile = profile
        self.intensity = intensity
        self.rng = random.Random(seed)
        self.changes: list[dict[str, str]] = []

        # Морфологический движок для согласования форм
        from texthumanize.morphology import get_morphology
        self._morph = get_morphology(lang)

        # Загружаем данные для языка (или пустые)
        self._replacements = _AI_WORD_REPLACEMENTS.get(lang, {})
        self._phrase_patterns = _AI_PHRASE_PATTERNS.get(lang, {})
        self._boosters = _PERPLEXITY_BOOSTERS.get(lang, {})

        # Lang pack для sentence_starters и т.д.
        from texthumanize.lang import get_lang_pack
        self.pack = get_lang_pack(lang)

    def process(self, text: str) -> str:
        """Применить натурализацию к тексту.

        Args:
            text: Текст (уже прошедший базовую обработку).

        Returns:
            Текст со стилистически естественными характеристиками.
        """
        self.changes = []

        if not text or len(text.strip()) < 30:
            return text

        prob = self.intensity / 100.0

        # 1. Замена AI-характерных фраз (regex на полном тексте — безопасно)
        text = self._replace_ai_phrases(text, prob)

        # 2. Замена AI-характерных слов (regex на полном тексте — безопасно)
        text = self._replace_ai_words(text, prob)

        # 2a. Удаление transition-стартеров предложений (самый сильный
        # сигнал для нейродетектора — feature 27 ai_pattern_rate и
        # feature 34 transition_word_rate)
        text = self._delete_transition_starters(text, prob)

        # 2b. Semantic intensity clusters — замена «very + adj» одним
        # более выразительным прилагательным (идея из humano).
        # EN: "very good" → "excellent", RU: "очень хороший" → "отличный"
        text = self._collapse_intensity_clusters(text, prob)

        # 3-5: Эти методы используют split_sentences + join → обрабатываем
        # каждый абзац/строку отдельно, чтобы не разрушать структуру
        text = self._per_paragraph(text, self._inject_burstiness, prob)

        if self.profile in ("chat", "web"):
            text = self._per_paragraph(text, self._boost_perplexity, prob)
        elif self.intensity >= 30:
            # Лёгкий перплексивный буст для формальных профилей —
            # вставляем 1-2 риторических вопроса и фрагмента
            text = self._per_paragraph(text, self._light_perplexity_boost, prob)

        text = self._per_paragraph(text, self._vary_sentence_structure, prob)

        # 5a. Инъекция тире (em-dash) — высокоимпактная фича в нейродетекторе
        # dash_rate: EN Δ=-0.12, RU Δ=-0.26, UK Δ=-0.28
        if self.intensity >= 25:
            text = self._per_paragraph(text, self._inject_dashes, prob)

        # 5b. Разбивка длинных абзацев (avg_paragraph_length: UK Δ=+0.32)
        if self.intensity >= 30:
            text = self._split_long_paragraphs(text)

        # 6. Контрактива — перенесена в sentence_restructurer.inject_contractions()
        # (75+ паттернов vs 15 здесь); не дублируем.

        return text

    # ─── Paragraph-safe wrapper ────────────────────────────────

    def _per_paragraph(
        self,
        text: str,
        fn: object,
        *args: object,
    ) -> str:
        """Применить *fn* к каждой непустой строке независимо.

        Сохраняет структуру абзацев/списков: строки, разделённые ``\\n``,
        обрабатываются по отдельности и не склеиваются друг с другом.
        """
        lines = text.split('\n')
        result: list[str] = []
        for line in lines:
            if line.strip():
                result.append(fn(line, *args))  # type: ignore[operator]
            else:
                result.append(line)
        return '\n'.join(result)

    def _replace_ai_phrases(self, text: str, prob: float) -> str:
        """Заменить фразовые AI-паттерны."""
        if not self._phrase_patterns:
            return text

        for phrase, replacements in self._phrase_patterns.items():
            if self.rng.random() > prob:
                continue

            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            matches = list(pattern.finditer(text))

            for match in reversed(matches):
                if self.rng.random() > prob:
                    continue

                if has_placeholder(text[max(0, match.start()-5):match.end()+5]):
                    continue

                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Сохраняем регистр
                if original[0].isupper() and replacement[0].islower():
                    replacement = replacement[0].upper() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]
                self.changes.append({
                    "type": "naturalize_phrase",
                    "original": original,
                    "replacement": replacement,
                })
                break  # Одна замена на фразу

        return text

    def _replace_ai_words(self, text: str, prob: float) -> str:
        """Заменить слова, характерные для автогенерации.

        Uses collocation engine for context-aware synonym selection
        when multiple replacement candidates are available.
        """
        if not self._replacements:
            return text

        replaced = 0
        max_replacements = max(10, len(text.split()) // 8)
        colloc = CollocEngine(lang=self.lang)

        for word, replacements in self._replacements.items():
            if replaced >= max_replacements:
                break

            if self.rng.random() > min(0.95, prob * 1.1):
                continue

            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))

            if not matches:
                continue

            # Заменяем первое вхождение
            match = matches[0]

            if has_placeholder(text[max(0, match.start()-5):match.end()+5]):
                continue

            # Collocation-aware synonym selection:
            # extract context words around the match for scoring
            # Use wider context window (200 chars) for better collocation matching
            ctx_start = max(0, match.start() - 200)
            ctx_end = min(len(text), match.end() + 200)
            ctx_text = text[ctx_start:match.start()] + text[match.end():ctx_end]
            ctx_words = re.findall(r'[\w]+', ctx_text.lower())

            if len(replacements) > 1 and ctx_words:
                replacement = colloc.best_synonym(
                    word, replacements, ctx_words,
                )
            else:
                replacement = self.rng.choice(replacements)

            # Context guard: проверяем, безопасна ли замена в контексте
            if not _is_replacement_safe(
                word, text, match.start(), match.end(),
                replacement=replacement,
            ):
                continue

            original = match.group(0)

            # Морфологическое согласование: подбираем форму синонима
            if self.lang in ("ru", "uk", "en", "de"):
                replacement = self._morph.find_synonym_form(
                    original.lower(), replacement,
                )

            # Сохраняем регистр
            if original.isupper():
                replacement = replacement.upper()
            elif original[0].isupper() and replacement[0].islower():
                replacement = replacement[0].upper() + replacement[1:]

            text = text[:match.start()] + replacement + text[match.end():]
            replaced += 1
            self.changes.append({
                "type": "naturalize_word",
                "original": original,
                "replacement": replacement,
            })

        return text

    # ── Transition starters — deletion/simplification ──────────

    # These sentence-initial transition phrases are the #1 AI signal.
    # Removing them entirely (not replacing) has the strongest effect
    # on neural feature 27 (ai_pattern_rate, LR w=-2.10) and
    # feature 34 (transition_word_rate, LR w=-0.45).
    _TRANSITION_STARTERS_EN: list[str] = [
        "Furthermore, ", "Moreover, ", "Additionally, ",
        "Consequently, ", "Subsequently, ", "Nevertheless, ",
        "Nonetheless, ", "Accordingly, ", "Conversely, ",
        "Importantly, ", "Significantly, ", "Essentially, ",
        "Fundamentally, ", "Ultimately, ", "Indeed, ",
        "Notably, ", "Evidently, ", "Undoubtedly, ",
        "It is important to note that ", "It should be noted that ",
        "It is worth mentioning that ", "It is noteworthy that ",
    ]

    _TRANSITION_STARTERS_RU: list[str] = [
        "Кроме того, ", "Более того, ", "Помимо этого, ",
        "Следовательно, ", "Тем не менее, ", "Вместе с тем, ",
        "В связи с этим, ", "Таким образом, ", "Безусловно, ",
        "Несомненно, ", "Очевидно, ", "Существенно, ",
        "Важно отметить, что ", "Следует отметить, что ",
        "Необходимо отметить, что ", "Стоит упомянуть, что ",
        "Следует подчеркнуть, что ", "Важно понимать, что ",
        "Прежде всего, ", "В первую очередь, ", "В целом, ",
        "В частности, ", "На сегодняшний день, ",
    ]

    _TRANSITION_STARTERS_UK: list[str] = [
        "Крім того, ", "Більше того, ", "Окрім цього, ",
        "Відповідно, ", "Тим не менш, ", "Разом з тим, ",
        "У зв'язку з цим, ", "Таким чином, ", "Безумовно, ",
        "Безсумнівно, ", "Очевидно, ", "Суттєво, ",
        "Важливо зазначити, що ", "Слід зазначити, що ",
        "Необхідно зазначити, що ", "Варто зазначити, що ",
        "Слід підкреслити, що ", "Важливо розуміти, що ",
        "Насамперед, ", "У першу чергу, ", "Загалом, ",
        "Зокрема, ", "На сьогоднішній день, ",
    ]

    def _delete_transition_starters(self, text: str, prob: float) -> str:
        """Delete AI-characteristic sentence-initial transition phrases.

        Instead of replacing them, outright deletion is more effective
        because it eliminates the AI signal entirely.
        """
        if self.lang == "en":
            starters = self._TRANSITION_STARTERS_EN
        elif self.lang == "ru":
            starters = self._TRANSITION_STARTERS_RU
        elif self.lang == "uk":
            starters = self._TRANSITION_STARTERS_UK
        else:
            return text

        deleted = 0
        max_deletes = max(2, int(len(text.split('.')) * 0.35))

        for starter in starters:
            if deleted >= max_deletes:
                break
            if self.rng.random() > prob * 0.8:
                continue
            if starter in text:
                # After deletion, capitalize the next character
                idx = text.index(starter)
                after = text[idx + len(starter):]
                if after and after[0].islower():
                    after = after[0].upper() + after[1:]
                text = text[:idx] + after
                deleted += 1
                self.changes.append({
                    "type": "naturalize_delete_transition",
                    "original": starter.strip(),
                    "replacement": "(deleted)",
                })

        return text

    # ─── Semantic intensity clusters ──────────────────────────

    def _collapse_intensity_clusters(self, text: str, prob: float) -> str:
        """Collapse «very/really + adjective» into a single vivid word.

        Reduces word-count and raises lexical density — both are
        human-text markers.  E.g. "very good" → "excellent".
        """
        clusters = _INTENSITY_CLUSTERS.get(self.lang)
        if not clusters:
            return text

        replacements = 0
        max_replacements = max(2, int(len(text) / 400))

        for pattern, alternatives in clusters:
            if replacements >= max_replacements:
                break
            if self.rng.random() > prob * 0.6:
                continue
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                original = m.group(0)
                replacement = self.rng.choice(alternatives)
                # For RU/UK patterns with backrefs, apply sub directly
                if "\\" in replacement:
                    text = re.sub(pattern, replacement, text,
                                  count=1, flags=re.IGNORECASE)
                else:
                    # Preserve original capitalization
                    if original[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    text = text[:m.start()] + replacement + text[m.end():]
                replacements += 1
                self.changes.append({
                    "type": "naturalize_intensity_cluster",
                    "original": original,
                    "replacement": replacement,
                })

        return text

    def _inject_burstiness(self, text: str, prob: float) -> str:
        """Внедрить вариативность длины предложений.

        Ключевой метод натурализации: однообразие длины предложений —
        характерный признак автоматически сгенерированного текста.
        """
        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 3:
            return text

        lengths = [len(s.split()) for s in sentences]
        avg = sum(lengths) / len(lengths) if lengths else 0
        if avg == 0:
            return text

        # CV — коэффициент вариации
        variance = sum((sl - avg) ** 2 for sl in lengths) / len(lengths)
        cv = (variance ** 0.5) / avg

        # Если вариативность уже хорошая — не трогаем
        if cv > 0.6:
            return text

        # Более агрессивный порог split для RU/UK (слова длиннее → меньше слов в предложении)
        split_threshold = 16 if self.lang in ("ru", "uk") else 20

        result = list(sentences)
        modified = False

        for i in range(len(result)):
            sent = result[i]
            words = sent.split()
            wlen = len(words)

            # Стратегия 1: Разбить длинные предложения
            if wlen > split_threshold and self.rng.random() < prob * 0.7:
                split = self._smart_split(sent)
                if split:
                    result[i] = split
                    modified = True
                    self.changes.append({
                        "type": "naturalize_burstiness",
                        "description": f"Разбивка предложения ({wlen} → 2 части)",
                    })

            # Стратегия 2: Объединить два коротких (< 8 слов каждое)
            elif (wlen <= 6 and i + 1 < len(result)
                  and len(result[i + 1].split()) <= 8
                  and not re.search(r'(?:^|\n)\d+[.)]\s?', sent)
                  and not re.search(r'(?:^|\n)\d+[.)]\s?', result[i + 1])
                  and not re.search(r'\d+[.)]$', sent.rstrip())
                  and not re.search(r'\d+[.)]$', result[i + 1].rstrip())
                  and self.rng.random() < prob * 0.5):
                # Объединяем через тире или запятую
                first = sent.rstrip().rstrip('.!?')
                second = result[i + 1]
                if second and second[0].isupper() and not has_placeholder(second):
                    second = second[0].lower() + second[1:]
                connector = self.rng.choice([' — ', ', и ', ', '])
                if self.lang == "en":
                    connector = self.rng.choice([' — ', ', and ', ', '])
                result[i] = first + connector + second
                result[i + 1] = ''
                modified = True
                self.changes.append({
                    "type": "naturalize_burstiness",
                    "description": "Объединение коротких предложений",
                })

            # Стратегия 3: Вставить короткий фрагмент для разбивки
            # монотонности (3 подряд "средних" предложения)
            # Cap probability at 0.20 to prevent over-insertion of
            # discourse fragments which themselves become AI signals.
            elif (i >= 2 and wlen > 8
                  and abs(wlen - avg) < avg * 0.25
                  and abs(len(result[i-1].split()) - avg) < avg * 0.25
                  and abs(len(result[i-2].split()) - avg) < avg * 0.25
                  and self.rng.random() < min(prob * 0.35, 0.20)):
                fragment = self._get_burstiness_fragment()
                if fragment:
                    result[i] = fragment + " " + sent
                    modified = True
                    self.changes.append({
                        "type": "naturalize_burstiness",
                        "description": "Вставка фрагмента перед монотонным предложением",
                    })

        if modified:
            return ' '.join(s for s in result if s.strip())
        return text

    def _get_burstiness_fragment(self) -> str:
        """Получить короткий дискурсивный фрагмент для cadence."""
        if self.lang == "ru":
            fragments = [
                "Вот что важно.", "К слову.", "Однако.",
                "И это не всё.", "Суть в другом.",
                "Но.", "А впрочем.", "Проще говоря.",
            ]
        elif self.lang == "uk":
            fragments = [
                "Ось що важливо.", "До речі.", "Однак.",
                "І це не все.", "Суть в іншому.",
                "Але.", "А втім.", "Простіше кажучи.",
            ]
        else:
            fragments = [
                "Here's the thing.", "Worth noting.", "That said.",
                "Actually.", "In short.", "But wait.",
                "Key point.", "Makes sense.",
            ]
        return self.rng.choice(fragments)

    def _smart_split(self, sentence: str) -> str | None:
        """Умная разбивка предложения для burstiness."""
        words = sentence.split()
        if len(words) < 14:
            return None

        mid = len(sentence) // 2

        # Приоритет: точка с запятой > запятая перед союзом > просто запятая
        best = None
        best_dist = len(sentence)

        # Ищем ; рядом с серединой
        for m in re.finditer(r';\s', sentence):
            left_w = len(sentence[:m.start()].split())
            right_w = len(sentence[m.end():].split())
            if left_w >= 5 and right_w >= 4:
                dist = abs(m.start() - mid)
                if dist < best_dist:
                    best_dist = dist
                    best = m.start()

        # Ищем , перед союзом
        if best is None:
            for pattern in [r',\s+(?:и|а|но|или|что|который|где|когда)',
                           r',\s+(?:and|but|or|which|where|when|that)',
                           r',\s+(?:und|aber|oder|dass)',
                           r',\s+(?:et|mais|ou|que|qui)',
                           r',\s+(?:y|pero|o|que|donde)']:
                for m in re.finditer(pattern, sentence, re.IGNORECASE):
                    left_w = len(sentence[:m.start()].split())
                    right_w = len(sentence[m.end():].split())
                    if left_w >= 5 and right_w >= 4:
                        dist = abs(m.start() - mid)
                        if dist < best_dist:
                            best_dist = dist
                            best = m.start()

        # Ищем просто запятую
        if best is None:
            for m in re.finditer(r',\s', sentence):
                left_w = len(sentence[:m.start()].split())
                right_w = len(sentence[m.end():].split())
                if left_w >= 5 and right_w >= 4:
                    dist = abs(m.start() - mid)
                    if dist < best_dist:
                        best_dist = dist
                        best = m.start()

        if best is not None:
            part1 = sentence[:best].rstrip().rstrip(',;') + '.'
            rest = sentence[best + 1:].lstrip()
            # Пропускаем запятую/; и пробелы
            rest = re.sub(r'^[,;\s]+', '', rest)
            if rest and rest[0].islower():
                rest = rest[0].upper() + rest[1:]
            return f"{part1} {rest}"

        return None

    # ─── Em-dash injection ──────────────────────────────────

    def _inject_dashes(self, text: str, prob: float) -> str:
        """Вставить тире (em-dashes) — одна из самых чувствительных фич нейродетектора.

        dash_rate: EN Δ=-0.12, RU Δ=-0.26, UK Δ=-0.28 (lower=more AI).
        AI текст почти не использует тире. Люди — постоянно.
        """
        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 2:
            return text

        result = list(sentences)
        injected = 0
        max_injections = max(1, len(sentences) // 3)

        for i in range(len(result)):
            if injected >= max_injections:
                break
            sent = result[i]
            words = sent.split()
            if len(words) < 8:
                continue

            # Стратегия 1 (40%): Заменить запятую перед союзом на тире
            if self.rng.random() < prob * 0.4:
                new_sent = self._comma_to_dash(sent)
                if new_sent != sent:
                    result[i] = new_sent
                    injected += 1
                    self.changes.append({
                        "type": "dash_injection",
                        "description": "Замена запятой на тире перед союзом",
                    })
                    continue

            # Стратегия 2 (30%): Вставить вводное тире (parenthetical)
            if self.rng.random() < prob * 0.3:
                aside_sent = self._insert_dash_aside(sent)
                if aside_sent and aside_sent != sent:
                    result[i] = aside_sent
                    injected += 1
                    self.changes.append({
                        "type": "dash_injection",
                        "description": "Вставка вводной фразы с тире",
                    })

        if injected > 0:
            return ' '.join(result)
        return text

    def _comma_to_dash(self, sent: str) -> str:
        """Заменить одну запятую+союз на тире."""
        if self.lang in ("ru", "uk"):
            patterns = [
                (r',\s+(и|а|но)\s+', r' — \1 '),
                (r',\s+(що|что)\s+', r' — \1 '),
            ]
        else:
            patterns = [
                (r',\s+(and|but|or)\s+', r' — \1 '),
                (r',\s+(which|where)\s+', r' — \1 '),
            ]
        for pat, repl in patterns:
            new = re.sub(pat, repl, sent, count=1)
            if new != sent:
                return new
        return sent

    def _insert_dash_aside(self, sent: str) -> str | None:
        """Вставить вводную фразу в тирах внутри предложения."""
        # Guard: skip if sentence already contains an em-dash aside
        if "\u2014" in sent:
            return None
        words = sent.split()
        if len(words) < 10:
            return None

        if self.lang == "ru":
            asides = [
                "— что важно —", "— между прочим —", "— к слову —",
                "— как ни странно —", "— надо сказать —",
                "— и это ключевое —", "— по сути —",
            ]
        elif self.lang == "uk":
            asides = [
                "— що важливо —", "— між іншим —", "— до речі —",
                "— як не дивно —", "— треба сказати —",
                "— і це ключове —", "— по суті —",
            ]
        else:
            asides = [
                "— surprisingly —", "— to be fair —", "— interestingly —",
                "— in a way —", "— arguably —", "— at least in part —",
                "— and this matters —",
            ]

        aside = self.rng.choice(asides)
        # Вставляем на 1/3 предложения
        pos = len(words) // 3
        if pos < 2:
            pos = 2
        words.insert(pos, aside)
        return ' '.join(words)

    # ─── Light perplexity boost for formal profiles ──────────

    def _light_perplexity_boost(self, text: str, prob: float) -> str:
        """Лёгкий перплексивный буст для формальных профилей.

        Вставляет 1-2 элемента (риторический вопрос, фрагмент) чтобы
        поднять question_rate и token entropy. Не агрессивный как полный
        _boost_perplexity, подходит для formal/docs/blog/seo.
        """
        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 3:
            return text

        result = list(sentences)
        inserted = 0

        # Вставить 1 риторический вопрос
        if self.rng.random() < prob * 0.6:
            if self.lang == "ru":
                questions = [
                    "Но почему это важно?", "И что это значит на практике?",
                    "Какой из этого вывод?", "Что стоит за этим?",
                ]
            elif self.lang == "uk":
                questions = [
                    "Але чому це важливо?", "І що це означає на практиці?",
                    "Який з цього висновок?", "Що стоїть за цим?",
                ]
            else:
                questions = [
                    "But why does this matter?", "So what does that mean in practice?",
                    "What's the takeaway here?", "And what comes next?",
                ]
            q = self.rng.choice(questions)
            # Вставляем после 2/3 текста
            pos = max(1, 2 * len(result) // 3)
            result.insert(pos, q)
            inserted += 1
            self.changes.append({
                "type": "light_perplexity",
                "description": f"Вставлен риторический вопрос: {q}",
            })

        if inserted > 0:
            return ' '.join(result)
        return text

    # ─── Paragraph splitting ────────────────────────────────

    def _split_long_paragraphs(self, text: str) -> str:
        """Разбить длинные абзацы на более короткие.

        avg_paragraph_length: UK Δ=+0.32, RU Δ=+0.24 (higher=more AI).
        AI генерирует монолитные абзацы. Люди чаще ставят переносы.
        """
        paragraphs = text.split('\n')
        result = []
        for para in paragraphs:
            if not para.strip():
                result.append(para)
                continue
            sentences = split_sentences(para, lang=self.lang)
            if len(sentences) >= 5:
                # Разбиваем примерно пополам
                mid = len(sentences) // 2
                p1 = ' '.join(sentences[:mid])
                p2 = ' '.join(sentences[mid:])
                result.append(p1)
                result.append('')  # Пустая строка — разделение абзацев
                result.append(p2)
                self.changes.append({
                    "type": "paragraph_split",
                    "description": f"Разбивка абзаца ({len(sentences)} → 2 части)",
                })
            else:
                result.append(para)
        return '\n'.join(result)

    def _boost_perplexity(self, text: str, prob: float) -> str:
        """Повысить перплексию через человеческие конструкции.

        Вставляет хеджинг, дискурсивные маркеры, риторические вопросы,
        фрагменты, вводные конструкции — элементы, повышающие
        естественную «непредсказуемость» текста.
        """
        if not self._boosters:
            return text

        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 5:
            return text

        result = list(sentences)
        insertions = 0
        max_insertions = max(1, len(sentences) // 6)

        # Стратегия 1: Вставить дискурсивные маркеры
        discourse = self._boosters.get("discourse_markers", [])
        if discourse and self.rng.random() < prob * 0.5:
            # Выбираем случайное предложение (не первое и не последнее)
            candidates = [
                c for c in range(2, len(result) - 1)
                if not skip_placeholder_sentence(result[c])
            ]
            if candidates:
                idx = self.rng.choice(candidates)
                marker = self.rng.choice(discourse)
                words = result[idx].split()
                if len(words) > 4:
                    # Вставляем в начало предложения (безопасно —
                    # не разбивает составные конструкции типа "Поки що")
                    if words[0][0].isupper():
                        words[0] = words[0][0].lower() + words[0][1:]
                    cap_marker = marker[0].upper() + marker[1:]
                    result[idx] = f"{cap_marker}, " + ' '.join(words)
                    insertions += 1
                    self.changes.append({
                        "type": "naturalize_perplexity",
                        "description": f"Дискурсивный маркер: {marker}",
                    })

        # Стратегия 2: Вставить хеджинг
        hedges = self._boosters.get("hedges", [])
        if hedges and insertions < max_insertions and self.rng.random() < prob * 0.4:
            candidates = [
                c for c in range(3, len(result) - 1)
                if not skip_placeholder_sentence(result[c])
            ]
            if candidates:
                idx = self.rng.choice(candidates)
                hedge = self.rng.choice(hedges)
                words = result[idx].split()
                if len(words) > 5:
                    # Вставляем в начало предложения
                    if words[0][0].isupper():
                        words[0] = words[0][0].lower() + words[0][1:]
                    if hedge[0].islower():
                        hedge = hedge[0].upper() + hedge[1:]
                    result[idx] = f"{hedge}, " + ' '.join(words)
                    insertions += 1
                    self.changes.append({
                        "type": "naturalize_perplexity",
                        "description": f"Хеджинг: {hedge}",
                    })

        # Стратегия 3: Вставить фрагмент или риторический вопрос
        fragments = self._boosters.get("fragments", [])
        questions = self._boosters.get("rhetorical_questions", [])
        inserts = fragments + questions

        if inserts and insertions < max_insertions and self.rng.random() < prob * 0.3:
            candidates = [
                c for c in range(3, len(result))
                if not skip_placeholder_sentence(result[c])
            ]
            if candidates:
                idx = self.rng.choice(candidates)
                insert = self.rng.choice(inserts)
                # Вставляем ПЕРЕД предложением
                result.insert(idx, insert)
                insertions += 1
                self.changes.append({
                    "type": "naturalize_perplexity",
                    "description": f"Фрагмент/вопрос: {insert}",
                })

        # Стратегия 4: Вводная конструкция в скобках
        parens = self._boosters.get("parenthetical", [])
        if parens and insertions < max_insertions and self.rng.random() < prob * 0.25:
            candidates = [
                c for c in range(2, len(result) - 1)
                if not skip_placeholder_sentence(result[c])
            ]
            if candidates:
                idx = self.rng.choice(candidates)
                paren = self.rng.choice(parens)
                sent = result[idx]
                # Добавляем перед точкой в конце
                if sent.rstrip().endswith('.'):
                    sent = sent.rstrip()[:-1] + ' ' + paren + '.'
                elif sent.rstrip().endswith(('!', '?')):
                    end_char = sent.rstrip()[-1]
                    sent = sent.rstrip()[:-1] + ' ' + paren + end_char
                else:
                    sent = sent + ' ' + paren
                result[idx] = sent
                insertions += 1
                self.changes.append({
                    "type": "naturalize_perplexity",
                    "description": f"Вводная конструкция: {paren}",
                })

        if insertions > 0:
            return ' '.join(result)
        return text

    def _vary_sentence_structure(self, text: str, prob: float) -> str:
        """Варьировать структуру предложений.

        AI предпочитает Subject-Verb-Object. Люди используют
        инверсию, вводные обороты, сложные конструкции.
        """
        if prob < 0.3:
            return text

        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 4:
            return text

        modified = False
        result = list(sentences)

        # Проверяем: начинаются ли предложения одинаково
        starts = [s.split()[0].lower().rstrip('.,;:') if s.split() else '' for s in sentences]
        start_counts = Counter(starts)
        repeated_starts = {s: c for s, c in start_counts.items() if c >= 3 and s}

        # Вводные обороты для вставки
        introductory = {
            "en": ["Interestingly,", "In practice,", "As expected,",
                   "Notably,", "In many cases,", "More specifically,",
                   "At the same time,", "On reflection,", "In reality,"],
            "ru": ["Интересно, что", "На практике", "Как ожидалось,",
                   "В частности,", "Во многих случаях", "Более того,",
                   "Одновременно с этим", "В действительности",
                   "По сути,", "Стоит заметить, что"],
            "uk": ["Цікаво, що", "На практиці", "Як і очікувалось,",
                   "Зокрема,", "У багатьох випадках", "Більш того,",
                   "Водночас", "Насправді", "По суті,"],
        }
        intros = introductory.get(self.lang, introductory.get("en", []))

        # 1. Исправляем повторяющиеся начала
        if repeated_starts:
            for start_word, count in repeated_starts.items():
                fixed = 0
                for i in range(len(result)):
                    words = result[i].split()
                    if not words:
                        continue
                    if skip_placeholder_sentence(result[i]):
                        continue
                    if words[0].lower().rstrip('.,;:') != start_word:
                        continue
                    if fixed == 0:
                        fixed += 1
                        continue  # Первое пропускаем

                    if self.rng.random() > prob:
                        fixed += 1
                        continue

                    sent_text = result[i]

                    # Стратегия 1: Добавить вводный оборот
                    if self.rng.random() < 0.4 and intros:
                        intro = self.rng.choice(intros)
                        lower_start = sent_text[0].lower() + sent_text[1:]
                        result[i] = f"{intro} {lower_start}"
                        modified = True
                        self.changes.append({
                            "type": "naturalize_structure",
                            "detail": f"add_introductory_phrase '{intro}'",
                        })

                    # Стратегия 2: Инверсия (перенос обстоятельства вперёд)
                    elif len(words) > 6:
                        # Ищем наречие или PP в конце
                        last_word = words[-1].rstrip('.!?')
                        punct = sent_text[-1] if sent_text[-1] in '.!?' else '.'

                        # EN: слово на -ly → наречие, выносим
                        if (self.lang == "en" and last_word.endswith("ly")
                                and len(last_word) > 4):
                            front = last_word[0].upper() + last_word[1:] + ","
                            rest_words = words[:-1]
                            rest_words[0] = rest_words[0][0].lower() + rest_words[0][1:]
                            rest = " ".join(rest_words)
                            result[i] = f"{front} {rest}{punct}"
                            modified = True
                            self.changes.append({
                                "type": "naturalize_structure",
                                "detail": f"adverb_fronting '{last_word}'",
                            })

                        # RU/UK: вынос обстоятельственного оборота
                        elif self.lang in ("ru", "uk") and len(words) > 7:
                            # Если предложение содержит запятую — перебрасываем
                            # часть после запятой в начало
                            comma_idx = sent_text.rfind(',')
                            if comma_idx > len(sent_text) // 2:
                                part_after = sent_text[comma_idx + 1:].strip().rstrip('.!?')
                                part_before = sent_text[:comma_idx].strip()
                                if len(part_after.split()) >= 2:
                                    front = part_after[0].upper() + part_after[1:]
                                    part_before = part_before[0].lower() + part_before[1:]
                                    result[i] = f"{front}, {part_before}{punct}"
                                    modified = True
                                    self.changes.append({
                                        "type": "naturalize_structure",
                                        "detail": "clause_fronting",
                                    })

                    # Стратегия 3: Использовать sentence_starter замену
                    elif self.rng.random() < 0.5:
                        starters = self.pack.get("sentence_starters", {})
                        first_word = words[0].rstrip('.,;:')
                        if starters.get(first_word):
                            new_start = self.rng.choice(starters[first_word])
                            rest = " ".join(words[1:])
                            result[i] = f"{new_start} {rest}"
                            modified = True
                            self.changes.append({
                                "type": "naturalize_structure",
                                "detail": f"sentence_starter '{first_word}' → '{new_start}'",
                            })

                    fixed += 1
                    if fixed >= count:
                        break

        # 2. Иногда вставляем короткий фрагмент между длинными предложениями
        if len(result) > 3 and self.rng.random() < prob * 0.5:
            fragments = {
                "en": ["A key point.", "Worth noting.", "Not always.",
                       "But not only.", "And yet.", "A small detail."],
                "ru": ["Важный момент.", "Стоит учесть.", "Но не всегда.",
                       "И это не всё.", "Небольшое уточнение.", "Вот в чём дело."],
                "uk": ["Важливий момент.", "Варто врахувати.", "Але не завжди.",
                       "І це не все.", "Невелике уточнення.", "Ось у чому справа."],
            }
            frags = fragments.get(self.lang, fragments.get("en", []))
            if frags:
                # Вставляем между двумя длинными предложениями
                for i in range(1, len(result) - 1):
                    words_prev = len(result[i - 1].split())
                    words_curr = len(result[i].split())
                    if words_prev > 15 and words_curr > 15 and self.rng.random() < 0.3:
                        fragment = self.rng.choice(frags)
                        result.insert(i, fragment)
                        modified = True
                        self.changes.append({
                            "type": "naturalize_structure",
                            "detail": f"insert_fragment '{fragment}'",
                        })
                        break  # Один фрагмент за вызов

        if modified:
            return ' '.join(result)

        return text

    def _apply_contractions(self, text: str, prob: float) -> str:
        """Применить сокращения для английского (don't, isn't, etc.)."""
        if prob < 0.3:
            return text

        contractions = {
            "do not": "don't",
            "does not": "doesn't",
            "did not": "didn't",
            "is not": "isn't",
            "are not": "aren't",
            "was not": "wasn't",
            "were not": "weren't",
            "would not": "wouldn't",
            "could not": "couldn't",
            "should not": "shouldn't",
            "will not": "won't",
            "can not": "can't",
            "cannot": "can't",
            "have not": "haven't",
            "has not": "hasn't",
            "had not": "hadn't",
            "it is": "it's",
            "that is": "that's",
            "there is": "there's",
            "what is": "what's",
            "who is": "who's",
            "I am": "I'm",
            "I have": "I've",
            "I will": "I'll",
            "I would": "I'd",
            "we are": "we're",
            "we have": "we've",
            "we will": "we'll",
            "they are": "they're",
            "they have": "they've",
            "they will": "they'll",
            "you are": "you're",
            "you have": "you've",
            "you will": "you'll",
            "he is": "he's",
            "she is": "she's",
            "let us": "let's",
        }

        for full, short in contractions.items():
            if self.rng.random() > prob * 0.7:
                continue

            pattern = re.compile(r'\b' + re.escape(full) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))
            for match in reversed(matches):
                if self.rng.random() > prob:
                    continue

                original = match.group(0)
                replacement = short
                # Сохраняем регистр начала
                if original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]
                self.changes.append({
                    "type": "naturalize_contraction",
                    "original": original,
                    "replacement": replacement,
                })
                break  # Одна замена за паттерн

        return text
