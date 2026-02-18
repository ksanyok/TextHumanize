"""Языковой пакет: Немецкий (Deutsch)."""

LANG_DE = {
    "code": "de",
    "name": "Deutsch",

    # Триграммы для определения языка
    "trigrams": [
        "der", "die", "und", "den", "das", "ein", "sch", "ich",
        "che", "ine", "ist", "eit", "ung", "uch", "ber", "ter",
        "eni", "ges", "ere", "aus", "für", "gen", "cht", "ent",
        "ver", "ren", "ste", "auf", "ach", "bei", "ier", "tte",
        "lic", "erf", "her", "nic", "nde", "and", "ung", "mit",
    ],

    # Стоп-слова (не заменять)
    "stop_words": {
        "der", "die", "das", "ein", "eine", "und", "oder", "aber",
        "ist", "sind", "war", "hat", "haben", "wird", "werden",
        "kann", "können", "muss", "müssen", "soll", "sollen",
        "in", "an", "auf", "für", "mit", "von", "zu", "bei",
        "nach", "über", "unter", "vor", "aus", "durch", "um",
        "ich", "du", "er", "sie", "es", "wir", "ihr",
        "den", "dem", "des", "einer", "einem", "eines",
        "nicht", "auch", "noch", "schon", "nur", "wenn",
        "als", "wie", "so", "da", "dann", "denn", "weil",
        "dass", "ob", "man", "sich", "hier", "dort",
        "sehr", "mehr", "viel", "gut", "neu", "alle",
        "diese", "dieser", "dieses", "jede", "jeder", "jedes",
        "sein", "seine", "seinem", "seinen", "seiner",
        "ihr", "ihre", "ihrem", "ihren", "ihrer",
        "was", "wer", "wo", "wie", "warum", "welche",
    },

    # Канцеляризмы (бюрократический стиль)
    "bureaucratic": {
        "implementieren": ["umsetzen", "einführen"],
        "optimieren": ["verbessern", "anpassen"],
        "evaluieren": ["bewerten", "prüfen", "beurteilen"],
        "generieren": ["erzeugen", "erstellen", "schaffen"],
        "initiieren": ["starten", "beginnen", "anstoßen"],
        "adressieren": ["angehen", "behandeln", "lösen"],
        "facilitieren": ["erleichtern", "ermöglichen"],
        "priorisieren": ["vorziehen", "bevorzugen"],
        "kommunizieren": ["mitteilen", "besprechen", "sagen"],
        "finalisieren": ["fertigstellen", "abschließen"],
        "signifikant": ["deutlich", "merklich", "spürbar", "erheblich"],
        "fundamental": ["grundlegend", "wesentlich"],
        "essentiell": ["wichtig", "nötig", "wesentlich"],
        "inhärent": ["eigen", "innewohnend"],
        "konsequent": ["folgerichtig", "durchgehend"],
        "adäquat": ["passend", "angemessen"],
        "primär": ["hauptsächlich", "vor allem"],
        "sukzessive": ["nach und nach", "schrittweise"],
        "marginalisieren": ["verdrängen", "zurückdrängen"],
        "integrieren": ["einbinden", "einbauen"],
        "manifestieren": ["zeigen", "offenbaren"],
        "etablieren": ["einrichten", "aufbauen", "gründen"],
    },

    # Фразовые канцеляризмы
    "bureaucratic_phrases": {
        "es ist festzustellen": ["es zeigt sich", "klar ist"],
        "in Anbetracht der Tatsache": ["angesichts", "weil"],
        "unter Berücksichtigung": ["mit Blick auf", "angesichts"],
        "im Rahmen von": ["bei", "während", "innerhalb"],
        "zum Zwecke der": ["für", "um zu"],
        "in Bezug auf": ["zu", "bei", "was betrifft"],
        "hinsichtlich": ["zu", "bei", "was betrifft"],
        "zwecks": ["für", "um zu"],
        "mittels": ["mit", "durch"],
        "aufgrund der Tatsache": ["weil", "da"],
        "im Hinblick auf": ["für", "bezüglich"],
        "es lässt sich konstatieren": ["man sieht", "es zeigt sich"],
        "von großer Bedeutung": ["wichtig", "bedeutend"],
        "eine zentrale Rolle spielen": ["wichtig sein", "zentral sein"],
    },

    # ИИ-связки
    "ai_connectors": {
        "Darüber hinaus": ["Außerdem", "Zudem", "Dazu", "Weiters"],
        "Nichtsdestotrotz": ["Trotzdem", "Aber", "Dennoch"],
        "Demzufolge": ["Daher", "Deshalb", "Also", "Somit"],
        "Infolgedessen": ["Deshalb", "Daher", "Also"],
        "Des Weiteren": ["Außerdem", "Zudem", "Dazu"],
        "Im Gegensatz dazu": ["Anders", "Aber", "Dagegen"],
        "In diesem Zusammenhang": ["Dabei", "Hier"],
        "Zusammenfassend lässt sich sagen": ["Kurz gesagt", "Im Ganzen"],
        "Es ist hervorzuheben": ["Wichtig ist", "Bemerkenswert"],
        "Abschließend": ["Zum Schluss", "Am Ende"],
        "Ferner": ["Außerdem", "Auch", "Zudem"],
        "Überdies": ["Außerdem", "Zudem", "Dazu"],
    },

    # Синонимы
    "synonyms": {
        "wichtig": ["bedeutend", "wesentlich", "relevant", "zentral"],
        "groß": ["erheblich", "beträchtlich", "umfangreich"],
        "klein": ["gering", "wenig", "niedrig"],
        "schnell": ["rasch", "zügig", "fix"],
        "langsam": ["gemächlich", "träge", "bedächtig"],
        "gut": ["positiv", "gelungen", "brauchbar"],
        "schlecht": ["mangelhaft", "unzureichend", "schwach"],
        "Möglichkeit": ["Option", "Chance", "Gelegenheit"],
        "Problem": ["Schwierigkeit", "Herausforderung", "Hürde"],
        "Lösung": ["Antwort", "Ausweg", "Abhilfe"],
        "Ergebnis": ["Resultat", "Ausgang", "Befund"],
        "Bereich": ["Gebiet", "Feld", "Sektor"],
        "Methode": ["Verfahren", "Ansatz", "Vorgehen"],
        "Prozess": ["Vorgang", "Ablauf", "Verfahren"],
        "Aspekt": ["Seite", "Punkt", "Facette"],
        "Grund": ["Ursache", "Anlass", "Motiv"],
        "Ziel": ["Zweck", "Absicht", "Vorgabe"],
        "Aufgabe": ["Auftrag", "Pflicht", "Job"],
        "Vorteil": ["Nutzen", "Plus", "Stärke"],
        "Nachteil": ["Minus", "Schwäche", "Manko"],
        "Analyse": ["Untersuchung", "Auswertung", "Prüfung"],
        "Qualität": ["Güte", "Niveau", "Standard"],
        "relevant": ["wichtig", "bedeutend", "passend"],
        "effektiv": ["wirksam", "erfolgreich", "wirkungsvoll"],
        "komplex": ["vielschichtig", "schwierig", "umfangreich"],
        "modern": ["zeitgemäß", "aktuell", "neu"],
    },

    # Альтернативные начала предложений
    "sentence_starters": {
        "Dies": ["Das", "So etwas", "All das"],
        "Es": ["Das", "Man", "Dies"],
        "Man": ["Wir", "Es", "Die Leute"],
        "Der": ["Ein", "Dieser", "Jener"],
        "Die": ["Eine", "Diese", "Jene"],
        "Das": ["Ein", "Dieses", "Jenes"],
        "Wir": ["Unser Team", "Man", "Alle"],
        "In": ["Innerhalb", "Während", "Bei"],
        "Für": ["Zum", "Um", "Was"],
        "Auch": ["Zudem", "Ebenso", "Darüber hinaus"],
    },

    # Разговорные маркеры
    "colloquial_markers": [
        "ehrlich gesagt", "im Grunde", "im Prinzip", "genau genommen",
        "unter uns gesagt", "nebenbei", "streng genommen",
        "wenn man so will", "mal ehrlich", "ganz offen",
        "sozusagen", "wohlgemerkt", "im Endeffekt",
        "lustigerweise", "witzigerweise", "überraschenderweise",
    ],

    # Аббревиатуры
    "abbreviations": [
        "z.B.", "d.h.", "u.a.", "etc.", "bzw.", "ca.", "vgl.",
        "Dr.", "Prof.", "Nr.", "Str.", "Mio.", "Mrd.",
        "Abb.", "Abs.", "Abt.", "Anm.", "Art.", "Bd.", "Bsp.",
        "bzgl.", "ggf.", "Hrsg.", "inkl.", "Jh.", "Kap.",
        "max.", "min.", "Mrd.", "o.Ä.", "s.o.", "s.u.", "usw.",
    ],

    # Бустеры перплексии (редкие слова/обороты для снижения AI-скора)
    "perplexity_boosters": [
        "quasi", "fürwahr", "meinetwegen", "schlechthin",
        "mutmaßlich", "gegebenenfalls", "just", "just in dem Moment",
        "obendrein", "kurioserweise", "paradoxerweise",
        "nichtsdestoweniger", "strenggenommen", "wenngleich",
        "beileibe", "mitnichten", "keineswegs", "allerdings",
    ],

    # Целевые метрики
    "profile_targets": {
        "chat": {"avg_len": (6, 16), "variance": 0.5},
        "web": {"avg_len": (8, 20), "variance": 0.4},
        "seo": {"avg_len": (10, 24), "variance": 0.3},
        "docs": {"avg_len": (10, 26), "variance": 0.3},
        "formal": {"avg_len": (12, 28), "variance": 0.25},
    },

    # Союзы для склейки
    "conjunctions": ["und", "aber", "oder", "denn", "weil", "da"],

    # Союзы для разбивки
    "split_conjunctions": [
        " und ", " aber ", " jedoch ", " wobei ",
        " während ", " obwohl ", " denn ",
    ],
}
