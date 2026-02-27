"""Rule-based морфологический движок — лемматизация и генерация словоформ.

Позволяет:
- Приводить слова к лемме (начальной форме)
- Генерировать все словоформы из леммы
- Находить синоним для любой словоформы, а не только для леммы
- Определять часть речи по суффиксу

Поддержка: RU, UK, EN, DE (rule-based, zero dependencies).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  РУССКИЙ ЯЗЫК — суффиксные правила
# ═══════════════════════════════════════════════════════════════

# Окончания прилагательных → лемма (м.р. ед.ч. Им.п.)
_RU_ADJ_ENDINGS = {
    # Мужской род
    "ого": "ый", "ому": "ый", "ым": "ый", "ом": "ый",
    "его": "ий", "ему": "ий", "им": "ий", "ем": "ий",
    # Женский род
    "ая": "ый", "ой": "ый", "ую": "ый",
    "яя": "ий", "ей": "ий", "юю": "ий",
    # Средний род
    "ое": "ый", "ее": "ий",
    # Множественное число
    "ые": "ый", "ых": "ый", "ыми": "ый",
    "ие": "ий", "их": "ий", "ими": "ий",
}

# Генерация форм прилагательных из леммы (м.р. -ый/-ий)
_RU_ADJ_FORMS = {
    "ый": ["ый", "ого", "ому", "ым", "ом", "ая", "ой", "ую", "ое", "ые", "ых", "ыми"],
    "ий": ["ий", "его", "ему", "им", "ем", "яя", "ей", "юю", "ее", "ие", "их", "ими"],
}

# Окончания существительных → примерная лемма
_RU_NOUN_ENDINGS = {
    # 1-е склонение (ж.р. -а/-я)
    "ы": "а", "е": "а", "у": "а", "ой": "а", "ою": "а",
    "и": "я", "ю": "я", "ей": "я", "ёй": "я",
    # 2-е склонение (м.р. -ø, ср.р. -о/-е)
    "а": "", "ов": "", "ам": "а", "ами": "а", "ах": "",
}

# Окончания глаголов → инфинитив (-ть/-ти)
_RU_VERB_ENDINGS = {
    # Настоящее время
    "ю": "ть", "у": "ть",
    "ешь": "ть", "ёшь": "ть", "ишь": "ть",
    "ет": "ть", "ёт": "ть", "ит": "ть",
    "ем": "ть", "ём": "ть", "им": "ть",
    "ете": "ть", "ёте": "ть", "ите": "ть",
    "ют": "ть", "ут": "ть", "ят": "ть", "ат": "ть",
    # Прошедшее время
    "л": "ть", "ла": "ть", "ло": "ть", "ли": "ть",
    # Причастие/деепричастие
    "ющий": "ть", "ущий": "ть", "ящий": "ть", "ащий": "ть",
    "вший": "ть", "ший": "ть",
    "емый": "ть", "имый": "ть",
    "нный": "ть", "тый": "ть",
    "я": "ть", "в": "ть", "вши": "ть",
}

# Генерация форм глаголов (упрощённая)
_RU_VERB_FORMS_I = {  # I спряжение (-ать/-ять)
    "ть": ["ю", "ешь", "ет", "ем", "ете", "ют",
           "л", "ла", "ло", "ли"],
}

_RU_VERB_FORMS_II = {  # II спряжение (-ить)
    "ть": ["ю", "ишь", "ит", "им", "ите", "ят",
           "л", "ла", "ло", "ли"],
}


# ═══════════════════════════════════════════════════════════════
#  УКРАИНСКИЙ ЯЗЫК — суффиксные правила
# ═══════════════════════════════════════════════════════════════

_UK_ADJ_ENDINGS = {
    "ого": "ий", "ому": "ий", "им": "ий", "ім": "ій",
    "ою": "ий", "ій": "ій",
    "а": "ий", "у": "ий", "е": "ий",
    "і": "ий", "их": "ий", "ими": "ій",
    "є": "ій", "ього": "ій", "ьому": "ій",
}

_UK_ADJ_FORMS = {
    "ий": ["ий", "ого", "ому", "им", "ім", "а", "ою", "у", "е", "і", "их", "ими"],
    "ій": ["ій", "ього", "ьому", "ім", "ій", "є", "і", "іх", "іми"],
}


# ═══════════════════════════════════════════════════════════════
#  АНГЛИЙСКИЙ ЯЗЫК — суффиксные правила
# ═══════════════════════════════════════════════════════════════

_EN_VERB_ENDINGS = {
    "s": "", "es": "", "ed": "", "ing": "",
    "ied": "y", "ies": "y",
}

_EN_ADJ_ENDINGS = {
    "er": "", "est": "", "ly": "",
    "ier": "y", "iest": "y",
    "ily": "y",
}

_EN_NOUN_ENDINGS = {
    "s": "", "es": "", "ies": "y",
    "tion": "te", "sion": "de",
    "ment": "",
    "ness": "",
    "ity": "",
}

# Генерация форм для EN
_EN_VERB_FORMS = {
    "": ["s", "es", "ed", "ing"],
}

_EN_IRREGULAR_FORMS = {
    "be": ["am", "is", "are", "was", "were", "been", "being"],
    "have": ["has", "had", "having"],
    "do": ["does", "did", "doing", "done"],
    "go": ["goes", "went", "going", "gone"],
    "get": ["gets", "got", "getting", "gotten"],
    "make": ["makes", "made", "making"],
    "say": ["says", "said", "saying"],
    "take": ["takes", "took", "taking", "taken"],
    "come": ["comes", "came", "coming"],
    "give": ["gives", "gave", "giving", "given"],
    "find": ["finds", "found", "finding"],
    "think": ["thinks", "thought", "thinking"],
    "know": ["knows", "knew", "knowing", "known"],
    "see": ["sees", "saw", "seeing", "seen"],
    "write": ["writes", "wrote", "writing", "written"],
    "run": ["runs", "ran", "running"],
    "begin": ["begins", "began", "beginning", "begun"],
    "keep": ["keeps", "kept", "keeping"],
    "hold": ["holds", "held", "holding"],
    "bring": ["brings", "brought", "bringing"],
    "build": ["builds", "built", "building"],
    "buy": ["buys", "bought", "buying"],
    "catch": ["catches", "caught", "catching"],
    "choose": ["chooses", "chose", "choosing", "chosen"],
    "draw": ["draws", "drew", "drawing", "drawn"],
    "drive": ["drives", "drove", "driving", "driven"],
    "eat": ["eats", "ate", "eating", "eaten"],
    "fall": ["falls", "fell", "falling", "fallen"],
    "feel": ["feels", "felt", "feeling"],
    "grow": ["grows", "grew", "growing", "grown"],
    "hear": ["hears", "heard", "hearing"],
    "lead": ["leads", "led", "leading"],
    "leave": ["leaves", "left", "leaving"],
    "lose": ["loses", "lost", "losing"],
    "meet": ["meets", "met", "meeting"],
    "pay": ["pays", "paid", "paying"],
    "read": ["reads", "reading"],
    "rise": ["rises", "rose", "rising", "risen"],
    "sell": ["sells", "sold", "selling"],
    "send": ["sends", "sent", "sending"],
    "show": ["shows", "showed", "showing", "shown"],
    "sit": ["sits", "sat", "sitting"],
    "speak": ["speaks", "spoke", "speaking", "spoken"],
    "spend": ["spends", "spent", "spending"],
    "stand": ["stands", "stood", "standing"],
    "teach": ["teaches", "taught", "teaching"],
    "tell": ["tells", "told", "telling"],
    "understand": ["understands", "understood", "understanding"],
    "win": ["wins", "won", "winning"],
}

# Обратный индекс: форма → лемма
_EN_IRREGULAR_REVERSE: dict[str, str] = {}
for _lemma, _forms in _EN_IRREGULAR_FORMS.items():
    for _form in _forms:
        _EN_IRREGULAR_REVERSE[_form.lower()] = _lemma


# ═══════════════════════════════════════════════════════════════
#  НЕМЕЦКИЙ ЯЗЫК — суффиксные правила
# ═══════════════════════════════════════════════════════════════

_DE_ADJ_ENDINGS = {
    "er": "", "es": "", "em": "", "en": "", "e": "",
}

_DE_VERB_ENDINGS = {
    "e": "en", "st": "en", "t": "en", "en": "en",
    "te": "en", "test": "en", "tet": "en", "ten": "en",
}

_DE_NOUN_ENDINGS = {
    "en": "", "er": "", "es": "", "e": "", "n": "", "s": "",
    "ung": "", "heit": "", "keit": "", "schaft": "",
    "tion": "", "nis": "", "tum": "",
}


# ═══════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API
# ═══════════════════════════════════════════════════════════════

class MorphologyEngine:
    """Rule-based морфологический движок.

    Позволяет лемматизировать слова и генерировать словоформы
    без внешних зависимостей.
    """

    def __init__(self, lang: str = "ru"):
        self.lang = lang
        self._lemma_cache: dict[str, str] = {}

    def lemmatize(self, word: str) -> str:
        """Привести слово к лемме (начальной форме).

        Args:
            word: Слово в любой форме.

        Returns:
            Лемма (начальная форма) слова.
        """
        lower = word.lower().strip()
        if lower in self._lemma_cache:
            return self._lemma_cache[lower]

        lemma = self._do_lemmatize(lower)
        self._lemma_cache[lower] = lemma
        return lemma

    def _do_lemmatize(self, word: str) -> str:
        """Внутренняя лемматизация."""
        if self.lang == "en":
            return self._lemmatize_en(word)
        elif self.lang in ("ru",):
            return self._lemmatize_ru(word)
        elif self.lang == "uk":
            return self._lemmatize_uk(word)
        elif self.lang == "de":
            return self._lemmatize_de(word)
        return word  # Для неподдерживаемых — без изменений

    def generate_forms(self, lemma: str) -> list[str]:
        """Сгенерировать возможные словоформы из леммы.

        Args:
            lemma: Лемма (начальная форма).

        Returns:
            Список словоформ, включая саму лемму.
        """
        if self.lang == "en":
            return self._generate_forms_en(lemma)
        elif self.lang == "ru":
            return self._generate_forms_ru(lemma)
        elif self.lang == "uk":
            return self._generate_forms_uk(lemma)
        elif self.lang == "de":
            return self._generate_forms_de(lemma)
        return [lemma]

    def find_synonym_form(
        self,
        original_word: str,
        synonym_lemma: str,
    ) -> str:
        """Подобрать форму синонима, соответствующую форме оригинала.

        Args:
            original_word: Исходное слово в определённой форме.
            synonym_lemma: Лемма синонима.

        Returns:
            Синоним в форме, соответствующей оригиналу.
        """
        if self.lang == "en":
            return self._match_form_en(original_word, synonym_lemma)
        elif self.lang in ("ru", "uk"):
            return self._match_form_slavic(original_word, synonym_lemma)
        elif self.lang == "de":
            return self._match_form_de(original_word, synonym_lemma)
        return synonym_lemma

    def is_same_lemma(self, word1: str, word2: str) -> bool:
        """Проверить, имеют ли два слова одну лемму."""
        return self.lemmatize(word1) == self.lemmatize(word2)

    def detect_pos(self, word: str) -> str:
        """Определить часть речи по суффиксу (грубая эвристика).

        Returns:
            'adj', 'noun', 'verb', 'adv', 'other'
        """
        if self.lang in ("ru", "uk"):
            return self._detect_pos_slavic(word)
        elif self.lang == "en":
            return self._detect_pos_en(word)
        elif self.lang == "de":
            return self._detect_pos_de(word)
        return "other"

    # ─── Русский ──────────────────────────────────────────────

    def _lemmatize_ru(self, word: str) -> str:
        """Лемматизация русского слова."""
        if len(word) < 3:
            return word

        # Прилагательные: ищем по окончаниям (от длинных к коротким)
        for ending, base_ending in sorted(
            _RU_ADJ_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                candidate = stem + base_ending
                return candidate

        # Глаголы: окончания → -ть
        for ending, base in sorted(
            _RU_VERB_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                return stem + base

        return word

    def _generate_forms_ru(self, lemma: str) -> list[str]:
        """Генерация словоформ для русского."""
        forms = [lemma]

        # Прилагательные
        for base, form_list in _RU_ADJ_FORMS.items():
            if lemma.endswith(base):
                stem = lemma[:-len(base)]
                forms.extend(stem + f for f in form_list if stem + f != lemma)
                return list(set(forms))

        # Глаголы на -ать/-ять (I спряжение)
        if lemma.endswith(("ать", "ять")):
            stem = lemma[:-2]
            for suffixes in _RU_VERB_FORMS_I.values():
                forms.extend(stem + s for s in suffixes)
            return list(set(forms))

        # Глаголы на -ить (II спряжение)
        if lemma.endswith("ить"):
            stem = lemma[:-2]
            for suffixes in _RU_VERB_FORMS_II.values():
                forms.extend(stem + s for s in suffixes)
            return list(set(forms))

        # Существительные — простые формы мн.ч.
        if lemma.endswith("а"):
            stem = lemma[:-1]
            forms.extend([stem + "ы", stem + "е", stem + "у",
                         stem + "ой", stem + "ам", stem + "ами", stem + "ах"])
        elif lemma.endswith("о"):
            stem = lemma[:-1]
            forms.extend([stem + "а", stem + "у", stem + "ом",
                         stem + "е", stem + "ам", stem + "ами"])
        elif lemma.endswith("я"):
            stem = lemma[:-1]
            forms.extend([stem + "и", stem + "е", stem + "ю",
                         stem + "ей", stem + "ям", stem + "ями"])
        else:
            # М.р. нулевое окончание
            forms.extend([lemma + "а", lemma + "у", lemma + "ом",
                         lemma + "е", lemma + "ы", lemma + "ов",
                         lemma + "ам", lemma + "ами", lemma + "ах"])

        return list(set(forms))

    # ─── Украинский ───────────────────────────────────────────

    def _lemmatize_uk(self, word: str) -> str:
        """Лемматизация украинского слова."""
        if len(word) < 3:
            return word

        # Прилагательные
        for ending, base_ending in sorted(
            _UK_ADJ_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                return stem + base_ending

        # Используем русские правила для глаголов (славянская группа)
        for ending, base in sorted(
            _RU_VERB_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                return stem + base

        return word

    def _generate_forms_uk(self, lemma: str) -> list[str]:
        """Генерация словоформ для украинского."""
        forms = [lemma]

        for base, form_list in _UK_ADJ_FORMS.items():
            if lemma.endswith(base):
                stem = lemma[:-len(base)]
                forms.extend(stem + f for f in form_list if stem + f != lemma)
                return list(set(forms))

        # Для глаголов и существительных — аналогично русскому
        return self._generate_forms_ru(lemma)

    # ─── Английский ───────────────────────────────────────────

    def _lemmatize_en(self, word: str) -> str:
        """Лемматизация английского слова."""
        # Сначала — неправильные глаголы
        if word in _EN_IRREGULAR_REVERSE:
            return _EN_IRREGULAR_REVERSE[word]

        if len(word) < 3:
            return word

        # Doubling consonant removal: running → run
        if word.endswith("ing") and len(word) > 5:
            stem = word[:-3]
            # running → run (double consonant)
            if len(stem) > 2 and stem[-1] == stem[-2]:
                return stem[:-1]
            # Stem ending in vowel or 'y' → stem as-is: playing → play
            if stem[-1] in "aeiouy":
                return stem
            # Consonant stem → try with silent e: making → make, writing → write
            return stem + "e"

        # -ied → -y: carried → carry
        if word.endswith("ied"):
            return word[:-3] + "y"
        if word.endswith("ies"):
            return word[:-3] + "y"

        # -ed removal
        if word.endswith("ed") and len(word) > 4:
            stem = word[:-2]
            if len(stem) > 2 and stem[-1] == stem[-2]:
                return stem[:-1]  # stopped → stop
            # Stem ends in vowel or 'y' → return stem: played → play
            if stem[-1] in "aeiouy":
                return stem
            # Consonant stem → try with silent e: hoped → hope, used → use
            return stem + "e"

        # -s/-es removal
        if word.endswith("es") and len(word) > 4:
            if word.endswith(("shes", "ches", "xes", "zes", "sses")):
                return word[:-2]
            # houses → house, cases → case (keep the e)
            if word.endswith("ses") or word.endswith("ces") \
                    or word.endswith("ges") or word.endswith("zes"):
                return word[:-1]
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            return word[:-1]

        # -er/-est → base
        if word.endswith("est") and len(word) > 5:
            return word[:-3]
        if word.endswith("er") and len(word) > 4:
            return word[:-2]

        # -ly → base adj
        if word.endswith("ly") and len(word) > 4:
            base = word[:-2]
            if base.endswith("i"):
                return base[:-1] + "y"
            return base

        return word

    def _generate_forms_en(self, lemma: str) -> list[str]:
        """Генерация словоформ для английского."""
        forms = [lemma]

        # Неправильные глаголы
        if lemma in _EN_IRREGULAR_FORMS:
            forms.extend(_EN_IRREGULAR_FORMS[lemma])
            return list(set(forms))

        # Правильные глаголы/существительные
        if lemma.endswith("e"):
            forms.extend([
                lemma + "s",       # makes
                lemma + "d",       # made (для правильных: hoped)
                lemma[:-1] + "ing",  # making
                lemma + "r",       # maker
            ])
        elif lemma.endswith("y") and len(lemma) > 2 and lemma[-2] not in "aeiou":
            forms.extend([
                lemma[:-1] + "ies",
                lemma[:-1] + "ied",
                lemma + "ing",
                lemma[:-1] + "ier",
                lemma[:-1] + "iest",
            ])
        else:
            forms.extend([
                lemma + "s",
                lemma + "es",
                lemma + "ed",
                lemma + "ing",
                lemma + "er",
                lemma + "est",
            ])

        # Наречие
        if lemma.endswith("y"):
            forms.append(lemma[:-1] + "ily")
        else:
            forms.append(lemma + "ly")

        return list(set(forms))

    def _match_form_en(self, original: str, synonym_lemma: str) -> str:
        """Подобрать форму синонима под оригинал (EN)."""
        orig_lower = original.lower()

        # Неправильные глаголы
        if orig_lower in _EN_IRREGULAR_REVERSE:
            orig_lemma = _EN_IRREGULAR_REVERSE[orig_lower]
            if synonym_lemma in _EN_IRREGULAR_FORMS:
                # Пытаемся найти ту же «позицию» формы
                orig_forms = _EN_IRREGULAR_FORMS.get(orig_lemma, [])
                syn_forms = _EN_IRREGULAR_FORMS[synonym_lemma]
                for i, f in enumerate(orig_forms):
                    if f.lower() == orig_lower and i < len(syn_forms):
                        return syn_forms[i]

        # -s, -es, -ed, -ing, -er, -est, -ly
        if orig_lower.endswith("ing"):
            if synonym_lemma.endswith("e"):
                return synonym_lemma[:-1] + "ing"
            return synonym_lemma + "ing"
        if orig_lower.endswith("ed"):
            if synonym_lemma.endswith("e"):
                return synonym_lemma + "d"
            return synonym_lemma + "ed"
        if orig_lower.endswith("ies") and not orig_lower.endswith("dies"):
            if synonym_lemma.endswith("y"):
                return synonym_lemma[:-1] + "ies"
            return synonym_lemma + "s"
        if orig_lower.endswith("es"):
            return synonym_lemma + "es"
        if orig_lower.endswith("s") and not orig_lower.endswith("ss"):
            return synonym_lemma + "s"
        if orig_lower.endswith("er"):
            return synonym_lemma + "er"
        if orig_lower.endswith("est"):
            return synonym_lemma + "est"
        if orig_lower.endswith("ly"):
            if synonym_lemma.endswith("y"):
                return synonym_lemma[:-1] + "ily"
            return synonym_lemma + "ly"

        return synonym_lemma

    # ─── Немецкий ─────────────────────────────────────────────

    def _lemmatize_de(self, word: str) -> str:
        """Лемматизация немецкого слова."""
        if len(word) < 3:
            return word

        # Прилагательные
        for ending, _base in sorted(
            _DE_ADJ_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 3:
                return word[:-len(ending)]

        # Глаголы
        for ending, _base in sorted(
            _DE_VERB_ENDINGS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                return stem + "en"

        return word

    def _generate_forms_de(self, lemma: str) -> list[str]:
        """Генерация словоформ для немецкого."""
        forms = [lemma]

        # Прилагательные — добавляем склоняемые формы
        if not lemma.endswith("en"):
            forms.extend([
                lemma + "e", lemma + "er", lemma + "es",
                lemma + "em", lemma + "en",
            ])

        # Глаголы на -en
        if lemma.endswith("en"):
            stem = lemma[:-2]
            forms.extend([
                stem + "e", stem + "st", stem + "t",
                stem + "te", stem + "test", stem + "ten",
            ])

        # Существительные
        for suffix in ["en", "er", "e", "s", "n"]:
            forms.append(lemma + suffix)

        return list(set(forms))

    def _match_form_de(self, original: str, synonym_lemma: str) -> str:
        """Подобрать форму синонима под оригинал (DE)."""
        orig_lower = original.lower()

        for ending in sorted(_DE_ADJ_ENDINGS.keys(), key=len, reverse=True):
            if orig_lower.endswith(ending):
                return synonym_lemma + ending

        for ending in sorted(_DE_VERB_ENDINGS.keys(), key=len, reverse=True):
            if orig_lower.endswith(ending) and synonym_lemma.endswith("en"):
                stem = synonym_lemma[:-2]
                return stem + ending

        return synonym_lemma

    # ─── Славянская группа (RU/UK) ────────────────────────────

    def _match_form_slavic(self, original: str, synonym_lemma: str) -> str:
        """Подобрать форму синонима под оригинал (RU/UK)."""
        orig_lower = original.lower()

        endings_map = _RU_ADJ_ENDINGS if self.lang == "ru" else _UK_ADJ_ENDINGS

        # Прилагательные: определяем окончание оригинала
        for ending in sorted(endings_map.keys(), key=len, reverse=True):
            if orig_lower.endswith(ending) and len(orig_lower) > len(ending) + 2:
                # Определяем, на что заканчивается лемма синонима
                for base in ("ый", "ий", "ій"):
                    if synonym_lemma.endswith(base):
                        stem = synonym_lemma[:-len(base)]
                        return stem + ending
                break

        # Глаголы: определяем окончание
        for ending in sorted(_RU_VERB_ENDINGS.keys(), key=len, reverse=True):
            if orig_lower.endswith(ending) and len(orig_lower) > len(ending) + 2:
                if synonym_lemma.endswith("ть") or synonym_lemma.endswith("ти"):
                    stem = synonym_lemma[:-2]
                    return stem + ending
                break

        return synonym_lemma

    # ─── Определение части речи ───────────────────────────────

    def _detect_pos_slavic(self, word: str) -> str:
        """Определить часть речи для славянских языков."""
        w = word.lower()

        # Наречия
        if w.endswith(("о", "е", "и")) and len(w) > 3 and w.endswith(("ски", "чески", "ично", "ально")):
            return "adv"

        # Прилагательные
        adj_endings = ("ый", "ий", "ой", "ая", "яя", "ое", "ее",
                       "ые", "ие", "ій", "а", "є")
        for end in adj_endings:
            if w.endswith(end) and len(w) > len(end) + 2:
                return "adj"

        # Глаголы
        if w.endswith(("ть", "ти", "ться", "тись")):
            return "verb"
        verb_ends = ("ет", "ит", "ют", "ят", "ут", "ат",
                     "ешь", "ишь", "ете", "ите", "ем", "им")
        for end in verb_ends:
            if w.endswith(end) and len(w) > len(end) + 1:
                return "verb"

        return "noun"

    def _detect_pos_en(self, word: str) -> str:
        """Определить часть речи для английского."""
        w = word.lower()

        if w.endswith("ly") and len(w) > 4:
            return "adv"
        if w.endswith(("ing", "ed")) and len(w) > 4:
            return "verb"
        if w.endswith(("tion", "sion", "ment", "ness", "ity", "ance", "ence")):
            return "noun"
        if w.endswith(("ful", "less", "ous", "ive", "able", "ible", "al", "ical")):
            return "adj"
        if w.endswith("ize"):
            return "verb"

        return "other"

    def _detect_pos_de(self, word: str) -> str:
        """Определить часть речи для немецкого."""
        w = word.lower()

        if w.endswith(("ung", "heit", "keit", "schaft", "tion", "nis", "tum")):
            return "noun"
        if w.endswith(("en", "ern", "eln")):
            return "verb"
        if w.endswith(("lich", "ig", "isch", "bar", "sam", "haft")):
            return "adj"

        # Немецкие существительные начинаются с заглавной
        if word and word[0].isupper() and len(word) > 2:
            return "noun"

        return "other"


# ─── Singleton-like helper ────────────────────────────────────

_engines: dict[str, MorphologyEngine] = {}


def get_morphology(lang: str) -> MorphologyEngine:
    """Получить экземпляр морфологического движка для языка."""
    if lang not in _engines:
        _engines[lang] = MorphologyEngine(lang)
    return _engines[lang]
