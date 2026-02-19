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

import random
import re
from collections import Counter

from texthumanize.decancel import _is_replacement_safe
from texthumanize.sentence_split import split_sentences

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
    },
    "ru": {
        "значительно": ["заметно", "ощутимо", "сильно", "намного"],
        "существенно": ["заметно", "ощутимо", "серьёзно"],
        "чрезвычайно": ["очень", "крайне", "сильно"],
        "безусловно": ["конечно", "да", "точно"],
        "несомненно": ["конечно", "понятно", "точно"],
        "комплексный": ["сложный", "многогранный", "разносторонний"],
        "всеобъемлющий": ["полный", "широкий", "общий"],
        "инновационный": ["новый", "свежий", "передовой", "современный"],
        "ключевой": ["главный", "основной", "центральный"],
        "основополагающий": ["основной", "главный", "базовый"],
        "первостепенный": ["главный", "важнейший", "основной"],
        "фундаментальный": ["основной", "базовый", "коренной"],
        "обеспечивает": ["даёт", "создаёт", "позволяет"],
        "способствует": ["помогает", "ведёт к", "влияет на"],
    },
    "uk": {
        "значно": ["помітно", "відчутно", "сильно", "набагато"],
        "суттєво": ["помітно", "відчутно", "серйозно"],
        "надзвичайно": ["дуже", "вкрай", "сильно"],
        "безумовно": ["звичайно", "так", "точно"],
        "безсумнівно": ["звичайно", "зрозуміло", "точно"],
        "комплексний": ["складний", "багатогранний", "різнобічний"],
        "всеосяжний": ["повний", "широкий", "загальний"],
        "інноваційний": ["новий", "свіжий", "передовий", "сучасний"],
        "ключовий": ["головний", "основний", "центральний"],
        "основоположний": ["основний", "головний", "базовий"],
        "першочерговий": ["головний", "найважливіший", "основний"],
        "фундаментальний": ["основний", "базовий", "корінний"],
        "забезпечує": ["дає", "створює", "дозволяє"],
        "сприяє": ["допомагає", "веде до", "впливає на"],
    },
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

        # 3-5: Эти методы используют split_sentences + join → обрабатываем
        # каждый абзац/строку отдельно, чтобы не разрушать структуру
        text = self._per_paragraph(text, self._inject_burstiness, prob)

        if self.profile in ("chat", "web"):
            text = self._per_paragraph(text, self._boost_perplexity, prob)

        text = self._per_paragraph(text, self._vary_sentence_structure, prob)

        # 6. Контрактива (regex — безопасно)
        if self.lang == "en" and self.profile in ("chat", "web"):
            text = self._apply_contractions(text, prob)

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
        """Заменить слова, характерные для автогенерации."""
        if not self._replacements:
            return text

        replaced = 0
        max_replacements = max(5, len(text.split()) // 20)

        for word, replacements in self._replacements.items():
            if replaced >= max_replacements:
                break

            if self.rng.random() > prob * 0.8:
                continue

            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))

            if not matches:
                continue

            # Заменяем первое вхождение
            match = matches[0]

            original = match.group(0)
            replacement = self.rng.choice(replacements)

            # Context guard: проверяем, безопасна ли замена в контексте
            if not _is_replacement_safe(
                word, text, match.start(), match.end(),
                replacement=replacement,
            ):
                continue

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

    def _inject_burstiness(self, text: str, prob: float) -> str:
        """Внедрить вариативность длины предложений.

        Ключевой метод натурализации: однообразие длины предложений —
        характерный признак автоматически сгенерированного текста.
        """
        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 5:
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

        result = list(sentences)
        modified = False

        for i in range(len(result)):
            sent = result[i]
            words = sent.split()
            wlen = len(words)

            # Стратегия 1: Разбить очень длинные (> 25 слов)
            if wlen > 25 and self.rng.random() < prob * 0.7:
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
                  and self.rng.random() < prob * 0.4):
                # Объединяем через тире или запятую
                first = sent.rstrip().rstrip('.!?')
                second = result[i + 1]
                if second and second[0].isupper():
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

        if modified:
            return ' '.join(s for s in result if s.strip())
        return text

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
            candidates = list(range(2, len(result) - 1))
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
            candidates = list(range(3, len(result) - 1))
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
            candidates = list(range(3, len(result)))
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
            candidates = list(range(2, len(result) - 1))
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
                        if first_word in starters and starters[first_word]:
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
