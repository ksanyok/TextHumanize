"""Модуль антидетекции — обход систем проверки AI-текста.

Системы детекции AI-текста (GPTZero, Originality.ai, ZeroGPT,
Turnitin, Copyleaks) анализируют:

1. **Perplexity (перплексия)** — насколько предсказуем текст.
   AI-текст имеет низкую перплексию = высокую предсказуемость.
   Решение: вставить менее предсказуемые конструкции.

2. **Burstiness (взрывчатость)** — вариация длины предложений.
   AI пишет равномерно (10-20 слов). Люди — от 2 до 40 слов.
   Решение: создать рваный ритм.

3. **Coherence uniformity** — равномерная связность.
   AI идеально связывает абзацы. Люди — не всегда.
   Решение: варьировать переходы.

4. **Vocabulary uniformity** — AI использует «безопасные» слова.
   Решение: использовать менее частотные синонимы.

5. **Sentence structure** — AI предпочитает SVO.
   Решение: инверсия, вставки, фрагменты.

6. **Perfect grammar** — AI никогда не ошибается.
   Решение: естественные конструкции (но не ошибки!).

Этот модуль — КЛЮЧЕВОЙ для обхода AI-детекторов.
"""

from __future__ import annotations

import random
import re
from collections import Counter

from texthumanize.lang import get_lang_pack, LANGUAGES


# ─── Паттерны AI-текста, которые детекторы ищут ───────────────

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

# Замены для AI-характерных слов (язык → {слово → [замены]})
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
        "optimieren": ["verbessern", "anpassen", "verfeinern"],
        "signifikant": ["deutlich", "merklich", "spürbar"],
        "fundamental": ["grundlegend", "wesentlich", "elementar"],
        "innovativ": ["neu", "neuartig", "kreativ"],
        "umfassend": ["breit", "vollständig", "gründlich"],
        "gewährleisten": ["sicherstellen", "sorgen für"],
        "darüber hinaus": ["außerdem", "zudem", "dazu"],
        "nichtsdestotrotz": ["trotzdem", "aber", "dennoch"],
        "demzufolge": ["daher", "deshalb", "also"],
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
        "hedges": ["wahrscheinlich", "vermutlich", "wohl", "irgendwie"],
        "discourse_markers": ["naja", "eigentlich", "im Grunde", "ehrlich gesagt"],
        "fragments": ["Nicht immer.", "Logisch.", "Kein Wunder."],
    },
    "fr": {
        "hedges": ["probablement", "sans doute", "peut-être", "en quelque sorte"],
        "discourse_markers": ["bon", "en fait", "franchement", "disons"],
        "fragments": ["Pas toujours.", "Logique.", "C'est normal."],
    },
    "es": {
        "hedges": ["probablemente", "seguramente", "quizás", "en cierto modo"],
        "discourse_markers": ["bueno", "la verdad", "o sea", "digamos"],
        "fragments": ["No siempre.", "Lógico.", "Normal."],
    },
}


class AntiDetector:
    """Модуль антидетекции — обход AI-детекторов.

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

        # Загружаем данные для языка (или пустые)
        self._replacements = _AI_WORD_REPLACEMENTS.get(lang, {})
        self._phrase_patterns = _AI_PHRASE_PATTERNS.get(lang, {})
        self._boosters = _PERPLEXITY_BOOSTERS.get(lang, {})

    def process(self, text: str) -> str:
        """Применить антидетекцию к тексту.

        Args:
            text: Текст (уже прошедший базовую обработку).

        Returns:
            Текст, устойчивый к AI-детекции.
        """
        self.changes = []

        if not text or len(text.strip()) < 30:
            return text

        prob = self.intensity / 100.0

        # 1. Замена AI-характерных фраз (сначала фразы, потом слова)
        text = self._replace_ai_phrases(text, prob)

        # 2. Замена AI-характерных слов
        text = self._replace_ai_words(text, prob)

        # 3. Burstiness injection — вариация длины предложений
        text = self._inject_burstiness(text, prob)

        # 4. Perplexity boost — вставка «человеческих» конструкций
        if self.profile in ("chat", "web"):
            text = self._boost_perplexity(text, prob)

        # 5. Sentence structure variation
        text = self._vary_sentence_structure(text, prob)

        # 6. Контрактива / разговорность (для EN и профилей chat/web)
        if self.lang == "en" and self.profile in ("chat", "web"):
            text = self._apply_contractions(text, prob)

        return text

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
                    "type": "antidetect_phrase",
                    "original": original,
                    "replacement": replacement,
                })
                break  # Одна замена на фразу

        return text

    def _replace_ai_words(self, text: str, prob: float) -> str:
        """Заменить слова, характерные для AI."""
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

            # Сохраняем регистр
            if original[0].isupper() and replacement[0].islower():
                replacement = replacement[0].upper() + replacement[1:]
            elif original.isupper():
                replacement = replacement.upper()

            text = text[:match.start()] + replacement + text[match.end():]
            replaced += 1
            self.changes.append({
                "type": "antidetect_word",
                "original": original,
                "replacement": replacement,
            })

        return text

    def _inject_burstiness(self, text: str, prob: float) -> str:
        """Внедрить вариативность длины предложений.

        Ключевой метод! AI-детекторы сильно полагаются на
        однообразие длины предложений как маркер AI.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 5:
            return text

        lengths = [len(s.split()) for s in sentences]
        avg = sum(lengths) / len(lengths) if lengths else 0
        if avg == 0:
            return text

        # CV — коэффициент вариации
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
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
                        "type": "antidetect_burstiness",
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
                    "type": "antidetect_burstiness",
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
        «непредсказуемость» текста для AI-детекторов.
        """
        if not self._boosters:
            return text

        sentences = re.split(r'(?<=[.!?])\s+', text)
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
                    # Вставляем после первого слова
                    words.insert(1, f"{marker},")
                    result[idx] = ' '.join(words)
                    insertions += 1
                    self.changes.append({
                        "type": "antidetect_perplexity",
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
                        "type": "antidetect_perplexity",
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
                    "type": "antidetect_perplexity",
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
                    "type": "antidetect_perplexity",
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

        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 4:
            return text

        modified = False
        result = list(sentences)

        # Проверяем: начинаются ли многие предложения одинаково
        starts = [s.split()[0].lower().rstrip('.,;:') if s.split() else '' for s in sentences]
        start_counts = Counter(starts)
        repeated_starts = {s: c for s, c in start_counts.items() if c >= 3 and s}

        if repeated_starts:
            # Перестраиваем предложения с повторяющимися началами
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

                    # Пробуем инвертировать: переставить обстоятельство/дополнение вперёд
                    if len(words) > 6:
                        # Ищем запятую — обычно после вводного оборота
                        sent_text = result[i]
                        comma_idx = sent_text.find(',')
                        if comma_idx > 0 and comma_idx < len(sent_text) // 2:
                            # Есть вводный оборот — уже хорошо
                            pass
                        else:
                            # Пробуем перенести последние 2-3 слова в начало
                            # Это грубая эвристика, но повышает вариативность
                            pass
                    fixed += 1

                    if fixed >= count:
                        break

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

        modified = False
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
                modified = True
                self.changes.append({
                    "type": "antidetect_contraction",
                    "original": original,
                    "replacement": replacement,
                })
                break  # Одна замена за паттерн

        return text
