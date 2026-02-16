"""Языковой пакет: Французский (Français)."""

LANG_FR = {
    "code": "fr",
    "name": "Français",

    "trigrams": [
        "les", "des", "ent", "que", "ion", "tion", "est", "ous",
        "ait", "our", "res", "men", "ant", "par", "eur", "con",
        "com", "une", "pas", "ete", "dans", "sur", "ave", "pou",
        "ont", "ais", "ell", "aux", "ess", "ien", "ire", "eme",
        "pre", "ait", "ons", "ans", "ous", "qui", "tre", "ais",
    ],

    "stop_words": {
        "le", "la", "les", "un", "une", "des", "de", "du",
        "et", "ou", "mais", "donc", "or", "ni", "car",
        "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
        "me", "te", "se", "en", "y",
        "est", "sont", "a", "ont", "fait", "être", "avoir",
        "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
        "son", "sa", "ses", "notre", "votre", "leur", "leurs",
        "dans", "sur", "sous", "avec", "pour", "par", "sans",
        "ne", "pas", "plus", "que", "qui", "quoi", "dont",
        "si", "bien", "très", "plus", "moins", "aussi",
        "tout", "tous", "toute", "toutes", "autre", "autres",
        "ici", "là", "où", "quand", "comme", "même",
    },

    "bureaucratic": {
        "implémenter": ["mettre en place", "réaliser"],
        "optimiser": ["améliorer", "ajuster"],
        "conceptualiser": ["penser", "imaginer", "concevoir"],
        "finaliser": ["terminer", "finir", "achever"],
        "prioriser": ["privilégier", "favoriser"],
        "préconiser": ["recommander", "conseiller"],
        "appréhender": ["comprendre", "saisir"],
        "concrétiser": ["réaliser", "accomplir"],
        "matérialiser": ["réaliser", "produire"],
        "substantiel": ["important", "considérable", "notable"],
        "significatif": ["notable", "important", "marquant"],
        "fondamental": ["essentiel", "de base", "central"],
        "primordial": ["essentiel", "capital", "vital"],
        "inhérent": ["propre", "naturel", "lié"],
        "conséquent": ["important", "notable"],
        "adéquat": ["adapté", "convenable", "approprié"],
        "préalable": ["avant", "d'abord", "initial"],
        "subséquent": ["suivant", "après", "ultérieur"],
        "exhaustif": ["complet", "détaillé", "approfondi"],
        "innovant": ["nouveau", "novateur", "créatif"],
    },

    "bureaucratic_phrases": {
        "il convient de noter": ["notons que", "on remarque que"],
        "il est à souligner": ["soulignons", "important:"],
        "force est de constater": ["on voit que", "clairement"],
        "dans le cadre de": ["dans", "pendant", "lors de"],
        "en vue de": ["pour", "afin de"],
        "à l'égard de": ["envers", "pour", "concernant"],
        "eu égard à": ["vu", "étant donné"],
        "au regard de": ["par rapport à", "face à"],
        "de manière significative": ["nettement", "clairement", "beaucoup"],
        "joue un rôle crucial": ["est très important", "compte beaucoup"],
        "revêt une importance": ["est important", "compte"],
    },

    "ai_connectors": {
        "En outre": ["De plus", "Aussi", "Par ailleurs"],
        "Néanmoins": ["Toutefois", "Cependant", "Mais", "Pourtant"],
        "Par conséquent": ["Donc", "Du coup", "Ainsi", "Alors"],
        "En revanche": ["Par contre", "Mais", "À l'inverse"],
        "De surcroît": ["En plus", "De plus", "Aussi"],
        "En définitive": ["Au final", "En fin de compte"],
        "Il convient de souligner": ["Notons", "À noter"],
        "Force est de constater": ["On voit que", "Clairement"],
        "Dans cette perspective": ["Ici", "Dans ce sens"],
        "À cet égard": ["À ce sujet", "Là-dessus"],
        "En somme": ["Bref", "En résumé", "Au fond"],
        "Subséquemment": ["Ensuite", "Puis", "Après"],
    },

    "synonyms": {
        "important": ["capital", "essentiel", "majeur", "notable"],
        "grand": ["vaste", "considérable", "immense"],
        "petit": ["réduit", "modeste", "faible"],
        "rapide": ["vite", "prompt", "agile"],
        "problème": ["difficulté", "souci", "obstacle", "défi"],
        "solution": ["réponse", "issue", "remède"],
        "résultat": ["bilan", "effet", "aboutissement"],
        "méthode": ["approche", "technique", "procédé"],
        "processus": ["démarche", "procédure", "parcours"],
        "objectif": ["but", "visée", "cible"],
        "avantage": ["atout", "plus", "bénéfice"],
        "développement": ["évolution", "progression", "essor"],
        "amélioration": ["progrès", "avancée", "gain"],
        "analyse": ["étude", "examen", "exploration"],
        "domaine": ["champ", "secteur", "sphère"],
        "efficace": ["performant", "productif", "utile"],
        "complexe": ["compliqué", "élaboré", "dense"],
        "moderne": ["actuel", "récent", "d'aujourd'hui"],
        "pertinent": ["adapté", "juste", "approprié"],
        "qualité": ["niveau", "valeur", "calibre"],
    },

    "sentence_starters": {},

    "colloquial_markers": [
        "franchement", "en fait", "au fond", "à vrai dire",
        "disons", "en gros",
    ],

    "abbreviations": [
        "M.", "Mme.", "Dr.", "Prof.", "etc.", "p. ex.",
        "c.-à-d.", "cf.", "vol.", "éd.",
    ],

    "profile_targets": {
        "chat": {"avg_len": (6, 16), "variance": 0.5},
        "web": {"avg_len": (8, 20), "variance": 0.4},
        "seo": {"avg_len": (10, 24), "variance": 0.3},
        "docs": {"avg_len": (10, 26), "variance": 0.3},
        "formal": {"avg_len": (12, 28), "variance": 0.25},
    },

    "conjunctions": ["et", "mais", "ou", "car", "donc", "puis"],

    "split_conjunctions": [
        " et ", " mais ", " cependant ", " tandis que ",
        " bien que ", " car ", " puisque ",
    ],
}
